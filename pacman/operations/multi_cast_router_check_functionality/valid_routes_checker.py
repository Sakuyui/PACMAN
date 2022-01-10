# Copyright (c) 2017-2019 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Collection of functions which together validate routes.
"""
from collections import namedtuple
import logging
from spinn_utilities.ordered_set import OrderedSet
from spinn_utilities.progress_bar import ProgressBar
from spinn_utilities.log import FormatAdapter
from pacman.data import PacmanDataView
from pacman.exceptions import PacmanRoutingException
from pacman.model.constraints.key_allocator_constraints import (
    ContiguousKeyRangeContraint)
from pacman.model.graphs.common import EdgeTrafficType
from pacman.utilities.utility_calls import locate_constraints_of_type
from pacman.utilities.constants import FULL_MASK

logger = FormatAdapter(logging.getLogger(__name__))
range_masks = {FULL_MASK - ((2 ** i) - 1) for i in range(33)}

# Define an internal class for placements
PlacementTuple = namedtuple('PlacementTuple', 'x y p')
# Define an internal class for failures
_Failure = namedtuple('_Failure', 'router_x router_y keys source_mask')


def validate_routes(placements, routing_tables):
    """ Go though the placements given and check that the routing entries\
        within the routing tables support reach the correction destinations\
        as well as not producing any cycles.

    :param Placements placements: the placements container
    :param RoutingInfo routing_infos: the routing info container
    :raises PacmanRoutingException: when either no routing table entry is
        found by the search on a given router, or a cycle is detected
    """

    def traffic_multicast(edge):
        return edge.traffic_type == EdgeTrafficType.MULTICAST

    machine_graph = PacmanDataView.get_runtime_machine_graph()
    routing_infos = PacmanDataView.get_routing_infos()
    progress = ProgressBar(
        placements.n_placements,
        "Verifying the routes from each core travel to the correct locations")
    for placement in progress.over(placements):

        # locate all placements to which this placement/vertex will
        # communicate with for a given key_and_mask and search its
        # determined destinations

        # gather keys and masks per partition
        partitions = machine_graph.\
            get_multicast_edge_partitions_starting_at_vertex(placement.vertex)

        n_atoms = placement.vertex.vertex_slice.n_atoms

        for partition in partitions:
            r_info = routing_infos.get_routing_info_from_partition(
                partition)
            is_continuous = _check_if_partition_has_continuous_keys(partition)
            if not is_continuous:
                logger.warning(
                    "Due to the none continuous nature of the keys in this "
                    "partition {}, we cannot check all atoms will be routed "
                    "correctly, but will check the base key instead",
                    partition)

            destination_placements = OrderedSet()

            # filter for just multicast edges, we don't check other types of
            # edges here.
            out_going_edges = filter(traffic_multicast, partition.edges)

            # for every outgoing edge, locate its destination and store it.
            for outgoing_edge in out_going_edges:
                dest_placement = placements.get_placement_of_vertex(
                    outgoing_edge.post_vertex)
                destination_placements.add(
                    PlacementTuple(x=dest_placement.x,
                                   y=dest_placement.y,
                                   p=dest_placement.p))

            # search for these destinations
            for key_and_mask in r_info.keys_and_masks:
                _search_route(
                    placement, destination_placements, key_and_mask,
                    routing_tables, n_atoms, is_continuous)


def _check_if_partition_has_continuous_keys(partition):
    """
    :param AbstractSingleSourcePartition partition:
    :rtype: bool
    """
    continuous_constraints = locate_constraints_of_type(
        partition.constraints, ContiguousKeyRangeContraint)
    # TODO: Can we do better here?
    return len(continuous_constraints) > 0


def _search_route(source_placement, dest_placements, key_and_mask,
                  routing_tables, n_atoms, is_continuous):
    """ Locate if the routing tables work for the source to desks as\
        defined

    :param Placement source_placement:
        the placement from which the search started
    :param iterable(PlacementTuple) dest_placements:
        the placements to which this trace should visit only once
    :param BaseKeyAndMask key_and_mask:
        the key and mask associated with this set of edges
    :param MulticastRoutingTables routing_tables:
    :param int n_atoms: the number of atoms going through this path
    :param bool is_continuous:
        whether the keys and atoms mapping is continuous
    :rtype: None
    :raise PacmanRoutingException:
        when the trace completes and there are still destinations not visited
    """
    if logger.isEnabledFor(logging.DEBUG):
        for dest in dest_placements:
            logger.debug("[{}:{}:{}]", dest.x, dest.y, dest.p)

    located_destinations = set()

    failed_to_cover_all_keys_routers = list()

    _start_trace_via_routing_tables(
        source_placement, key_and_mask, located_destinations,
        routing_tables, n_atoms, is_continuous,
        failed_to_cover_all_keys_routers)

    # start removing from located_destinations and check if destinations not
    #  reached
    failed_to_reach_destinations = list()
    for dest in dest_placements:
        if dest in located_destinations:
            located_destinations.remove(dest)
        else:
            failed_to_reach_destinations.append(dest)

    # check for error if trace didn't reach a destination it was meant to
    error_message = ""
    if failed_to_reach_destinations:
        output_string = ""
        for dest in failed_to_reach_destinations:
            output_string += "[{}:{}:{}]".format(dest.x, dest.y, dest.p)
        source_processor = "[{}:{}:{}]".format(
            source_placement.x, source_placement.y, source_placement.p)
        error_message += ("failed to locate all destinations with vertex"
                          " {} on processor {} with keys {} as it did not "
                          "reach destinations {}".format(
                              source_placement.vertex.label, source_processor,
                              key_and_mask, output_string))

    # check for error if the trace went to a destination it shouldn't have
    if located_destinations:
        output_string = ""
        for dest in located_destinations:
            output_string += "[{}:{}:{}]".format(dest.x, dest.y, dest.p)
        source_processor = "[{}:{}:{}]".format(
            source_placement.x, source_placement.y, source_placement.p)
        error_message += ("trace went to more failed to locate all "
                          "destinations with vertex {} on processor {} "
                          "with keys {} as it didn't reach destinations {}"
                          .format(
                              source_placement.vertex.label, source_processor,
                              key_and_mask, output_string))

    if failed_to_cover_all_keys_routers:
        output_string = ""
        for data_entry in failed_to_cover_all_keys_routers:
            output_string += "[{}, {}, {}, {}]".format(
                data_entry.router_x, data_entry.router_y,
                data_entry.keys, data_entry.source_mask)
        source_processor = "[{}:{}:{}]".format(
            source_placement.x, source_placement.y, source_placement.p)
        error_message += (
            "trace detected that there were atoms which the routing entry's"
            " wont cover and therefore packets will fly off to unknown places."
            " These keys came from the vertex {} on processor {} and the"
            " failed routers are {}".format(
                source_placement.vertex.label, source_processor,
                output_string))

    # raise error if required
    if error_message != "":
        raise PacmanRoutingException(error_message)
    logger.debug("successful test between {} and {}",
                 source_placement.vertex.label, dest_placements)


def _start_trace_via_routing_tables(
        source_placement, key_and_mask, reached_placements, routing_tables,
        n_atoms, is_continuous, failed_to_cover_all_keys_routers):
    """ Start the trace, by using the source placement's router and tracing\
        from the route.

    :param Placement source_placement: the source placement used by the trace
    :param BaseKeyAndMask key_and_mask:
        the key being used by the vertex which resides on the source placement
    :param set(PlacementTuple) reached_placements:
        the placements reached during the trace
    :param MulticastRoutingTables routing_tables:
    :param int n_atoms: the number of atoms going through this path
    :param bool is_continuous: if the keys and atoms mapping is continuous
    :param list(_Failure) failed_to_cover_all_keys_routers:
        list of failed routers for all keys
    :rtype: None
    """
    current_router_table = routing_tables.get_routing_table_for_chip(
        source_placement.x, source_placement.y)
    visited_routers = set()
    visited_routers.add((current_router_table.x, current_router_table.y))

    # get src router
    entry = _locate_routing_entry(
        current_router_table, key_and_mask.key, n_atoms)

    _recursive_trace_to_destinations(
        entry, current_router_table, source_placement.x,
        source_placement.y, key_and_mask, visited_routers,
        reached_placements, routing_tables, is_continuous, n_atoms,
        failed_to_cover_all_keys_routers)


def _check_all_keys_hit_entry(entry, n_atoms, base_key):
    """
    :param ~spinn_machine.MulticastRoutingEntry entry:
        routing entry discovered
    :param int n_atoms: the number of atoms this partition covers
    :param int base_key: the base key of the partition
    :return: the list of keys which this entry doesn't cover which it should
    :rtype: list(int)
    """
    bad_entries = list()
    for atom_id in range(0, n_atoms):
        key = base_key + atom_id
        if entry.mask & key != entry.routing_entry_key:
            bad_entries.append(key)
    return bad_entries


# locates the next dest position to check
def _recursive_trace_to_destinations(
        entry, current_router, chip_x, chip_y, key_and_mask, visited_routers,
        reached_placements, routing_tables, is_continuous, n_atoms,
        failed_to_cover_all_keys_routers):
    """ Recursively search though routing tables until no more entries are\
        registered with this key.

    :param ~spinn_machine.MulticastRoutingEntry entry:
        the original entry used by the first router which resides on the
        source placement chip.
    :param MulticastRoutingTable current_router:
        the router currently being visited during the trace
    :param int chip_x: the x coordinate of the chip being considered
    :param int chip_y: the y coordinate of the chip being considered
    :param BaseKeyAndMask key_and_mask:
        the key and mask being used by the vertex which resides on the source
        placement
    :param set(tuple(int,int)) visited_routers:
        the list of routers which have been visited during this trace so far
    :param set(PlacementTuple) reached_placements:
        the placements reached during the trace
    :param MulticastRoutingTables routing_tables:
    :param bool is_continuous:
        whether the keys and atoms mapping is continuous
    :param int n_atoms: the number of atoms going through this path
    :param list(_Failure) failed_to_cover_all_keys_routers:
        list of failed routers for all keys
    :rtype: None
    """

    # determine where the route takes us
    chip_links = entry.link_ids
    processor_values = entry.processor_ids

    # if goes down a chip link
    if chip_links:
        # also goes to a processor
        if processor_values:
            _is_dest(processor_values, current_router, reached_placements)
        # only goes to new chip
        for link_id in chip_links:

            # locate next chips router
            machine_router = PacmanDataView.get_chip_at(chip_x, chip_y).router
            link = machine_router.get_link(link_id)
            next_router = routing_tables.get_routing_table_for_chip(
                link.destination_x, link.destination_y)

            # check that we've not visited this router before
            _check_visited_routers(
                next_router.x, next_router.y, visited_routers)

            # locate next entry
            entry = _locate_routing_entry(
                next_router, key_and_mask.key, n_atoms)

            if is_continuous:
                bad_entries = _check_all_keys_hit_entry(
                    entry, n_atoms, key_and_mask.key)
                if bad_entries:
                    failed_to_cover_all_keys_routers.append(
                        _Failure(next_router.x, next_router.y,
                                 bad_entries, key_and_mask.mask))

            # get next route value from the new router
            _recursive_trace_to_destinations(
                entry, next_router, link.destination_x, link.destination_y,
                key_and_mask, visited_routers, reached_placements,
                routing_tables, is_continuous, n_atoms,
                failed_to_cover_all_keys_routers)

    # only goes to a processor
    elif processor_values:
        _is_dest(processor_values, current_router, reached_placements)


def _check_visited_routers(chip_x, chip_y, visited_routers):
    """ Check if the trace has visited this router already

    :param int chip_x: the x coordinate of the chip being checked
    :param int chip_y: the y coordinate of the chip being checked
    :param set(tuple(int,int)) visited_routers: routers already visited
    :rtype: None
    :raise PacmanRoutingException: when a router has been visited twice.
    """
    visited_routers_router = (chip_x, chip_y)
    if visited_routers_router in visited_routers:
        raise PacmanRoutingException(
            "visited this router before, there is a cycle here. "
            "The routers I've currently visited are {} and the router i'm "
            "visiting is {}"
            .format(visited_routers, visited_routers_router))
    visited_routers.add(visited_routers_router)


def _is_dest(processor_ids, current_router, reached_placements):
    """ Check for processors to be removed

    :param list(int) processor_ids:
        the processor IDs which the last router entry said the trace should
        visit
    :param MulticastRoutingTable current_router:
        the current router being used in the trace
    :param set(PlacementTuple) reached_placements:
        the placements to which the trace visited
    :rtype: None
    """
    dest_x, dest_y = current_router.x, current_router.y
    for processor_id in processor_ids:
        reached_placements.add(PlacementTuple(dest_x, dest_y, processor_id))


def _locate_routing_entry(current_router, key, n_atoms):
    """ Locate the entry from the router based off the edge

    :param MulticastRoutingTable current_router:
        the current router being used in the trace
    :param int key: the key being used by the source placement
    :param int n_atoms: the number of atoms
    :rtype: ~spinn_machine.MulticastRoutingEntry
    :raise PacmanRoutingException:
        when there is no entry located on this router
    """
    found_entry = None
    for entry in current_router.multicast_routing_entries:
        key_combo = entry.mask & key
        e_key = entry.routing_entry_key
        if key_combo == e_key:
            if found_entry is None:
                found_entry = entry
            else:
                logger.warning(
                    "Found more than one entry for key {}. This could be "
                    "an error, as currently no router supports overloading"
                    " of entries.", hex(key))
            if entry.mask in range_masks:
                last_atom = key + n_atoms - 1
                last_key = e_key + (~entry.mask & FULL_MASK)
                if last_key < last_atom:
                    raise PacmanRoutingException(
                        "Full key range not covered: key:{} key_combo:{} "
                        "mask:{}, last_key:{}, e_key:{}".format(
                            hex(key), hex(key_combo), hex(entry.mask),
                            hex(last_key), hex(e_key)))
        elif entry.mask in range_masks:
            last_atom = key + n_atoms
            last_key = e_key + (~entry.mask & FULL_MASK)
            if min(last_key, last_atom) - max(e_key, key) + 1 > 0:
                raise Exception(
                    "Key range partially covered:  key:{} key_combo:{} "
                    "mask:{}, last_key:{}, e_key:{}".format(
                        hex(key), hex(key_combo), hex(entry.mask),
                        hex(last_key), hex(e_key)))
    if found_entry is None:
        raise PacmanRoutingException("no entry located")
    return found_entry
