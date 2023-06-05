# Copyright (c) 2014 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Collection of functions which together validate routes.
"""
from collections import defaultdict
import logging
from typing import NamedTuple, List
from spinn_utilities.ordered_set import OrderedSet
from spinn_utilities.progress_bar import ProgressBar
from spinn_utilities.log import FormatAdapter
from pacman.data import PacmanDataView
from pacman.exceptions import (
    PacmanConfigurationException, PacmanRoutingException)
from pacman.model.graphs.application import ApplicationVertex
from pacman.utilities.constants import FULL_MASK
from pacman.utilities.algorithm_utilities.routing_algorithm_utilities import (
    get_app_partitions)

logger = FormatAdapter(logging.getLogger(__name__))
range_masks = {FULL_MASK - ((2 ** i) - 1) for i in range(33)}


class PlacementTuple(NamedTuple):
    """
    A particular location in placement.
    """
    #: The X coordinate of the chip
    x: int
    #: The Y coordinate of the chip
    y: int
    #: The ID of the CPU core on the chip
    p: int


class _Failure(NamedTuple):
    router_x: int
    router_y: int
    keys: List[int]
    source_mask: int


def validate_routes(placements, routing_tables):
    """
    Go though the placements given and check that the routing entries
    within the routing tables support reach the correction destinations
    as well as not producing any cycles.

    :param Placements placements: the placements container
    :param RoutingInfo routing_infos: the routing info container
    :param MulticastRoutingTables routing_tables:
        the routing tables generated by the routing algorithm
    :raises PacmanRoutingException: when either no routing table entry is
        found by the search on a given router, or a cycle is detected
    """
    # Find all partitions that need to be dealt with
    partitions = get_app_partitions()
    routing_infos = PacmanDataView.get_routing_infos()
    # Now go through the app edges and route app vertex by app vertex
    progress = ProgressBar(len(partitions), "Checking Routes")
    for partition in progress.over(partitions):
        source = partition.pre_vertex

        # Destination cores by source machine vertices
        destinations = defaultdict(OrderedSet)

        for edge in partition.edges:
            target = edge.post_vertex
            target_vertices = \
                target.splitter.get_source_specific_in_coming_vertices(
                    source, partition.identifier)

            for tgt, srcs in target_vertices:
                place = placements.get_placement_of_vertex(tgt)
                for src in srcs:
                    if isinstance(src, ApplicationVertex):
                        for s in src.splitter.get_out_going_vertices(
                                partition.identifier):
                            destinations[s].add(PlacementTuple(
                                x=place.x, y=place.y, p=place.p))
                    else:
                        destinations[src].add(PlacementTuple(
                            x=place.x, y=place.y, p=place.p))

        outgoing = OrderedSet(source.splitter.get_out_going_vertices(
            partition.identifier))
        internal = source.splitter.get_internal_multicast_partitions()
        for in_part in internal:
            if in_part.partition_id == partition.identifier:
                outgoing.add(in_part.pre_vertex)
                for edge in in_part.edges:
                    place = placements.get_placement_of_vertex(
                        edge.post_vertex)
                    destinations[in_part.pre_vertex].add(PlacementTuple(
                        x=place.x, y=place.y, p=place.p))

        # locate all placements to which this placement/vertex will
        # communicate with for a given key_and_mask and search its
        # determined destinations
        for m_vertex in outgoing:
            placement = placements.get_placement_of_vertex(m_vertex)
            r_info = routing_infos.get_routing_info_from_pre_vertex(
                m_vertex, partition.identifier)

            # search for these destinations
            _search_route(
                placement, destinations[m_vertex], r_info.key_and_mask,
                routing_tables, m_vertex.vertex_slice.n_atoms)


def _search_route(source_placement, dest_placements, key_and_mask,
                  routing_tables, n_atoms):
    """
    Locate if the routing tables work for the source to desks as defined.

    :param Placement source_placement:
        the placement from which the search started
    :param iterable(Placement) dest_placements:
        the placements to which this trace should visit only once
    :param BaseKeyAndMask key_and_mask:
        the key and mask associated with this set of edges
    :param MulticastRoutingTables routing_tables:
    :param int n_atoms: the number of atoms going through this path
    :param bool is_continuous:
        whether the keys and atoms mapping is continuous
    :raise PacmanRoutingException:
        when the trace completes and there are still destinations not visited
    """
    if logger.isEnabledFor(logging.DEBUG):
        for dest in dest_placements:
            logger.debug("[{}:{}:{}]", dest.x, dest.y, dest.p)

    located_destinations = set()

    failed_to_cover_all_keys_routers = list()

    _start_trace_via_routing_tables(
        source_placement, key_and_mask, located_destinations, routing_tables,
        n_atoms, failed_to_cover_all_keys_routers)

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
        failures = ", ".join(
            f"[{dest.x}:{dest.y}:{dest.p}]"
            for dest in failed_to_reach_destinations)
        error_message += (
            "failed to locate all destinations with vertex "
            f"{source_placement.vertex.label} on processor "
            f"[{source_placement.x}:{source_placement.y}:{source_placement.p}]"
            f" with keys {key_and_mask} as it did not reach destinations "
            f"{failures}")

    # check for error if the trace went to a destination it shouldn't have
    if located_destinations:
        failures = ", ".join(
             f"[{dest.x}:{dest.y}:{dest.p}]"
             for dest in located_destinations)
        error_message += (
            "trace went to more failed to locate all destinations with "
            f"vertex {source_placement.vertex.label} on processor "
            f"[{source_placement.x}:{source_placement.y}:{source_placement.p}]"
            f" with keys {key_and_mask} as it didn't reach destinations "
            f"{failures}")

    if failed_to_cover_all_keys_routers:
        failures = ", ".join(
            f"[{router.router_x}, {router.router_y}, "
            f"{router.keys}, {router.source_mask}]"
            for router in failed_to_cover_all_keys_routers)
        error_message += (
            "trace detected that there were atoms which the routing entries "
            "won't cover and therefore packets will fly off to unknown places."
            f" These keys came from the vertex {source_placement.vertex.label}"
            f" on processor [{source_placement.x}:{source_placement.y}:"
            f"{source_placement.p}] and the failed routers are {failures}")

    # raise error if required
    if error_message != "":
        raise PacmanRoutingException(error_message)
    logger.debug("successful test between {} and {}",
                 source_placement.vertex.label, dest_placements)


def _start_trace_via_routing_tables(
        source_placement, key_and_mask, reached_placements, routing_tables,
        n_atoms, failed_to_cover_all_keys_routers):
    """
    Start the trace, by using the source placement's router and tracing
    from the route.

    :param Placement source_placement: the source placement used by the trace
    :param BaseKeyAndMask key_and_mask:
        the key being used by the vertex which resides on the source placement
    :param set(PlacementTuple) reached_placements:
        the placements reached during the trace
    :param MulticastRoutingTables routing_tables:
    :param int n_atoms: the number of atoms going through this path
    :param list(_Failure) failed_to_cover_all_keys_routers:
        list of failed routers for all keys
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
        reached_placements, routing_tables, n_atoms,
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
        reached_placements, routing_tables, n_atoms,
        failed_to_cover_all_keys_routers):
    """
    Recursively search though routing tables until no more entries are
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
                routing_tables, n_atoms, failed_to_cover_all_keys_routers)

    # only goes to a processor
    elif processor_values:
        _is_dest(processor_values, current_router, reached_placements)


def _check_visited_routers(chip_x, chip_y, visited_routers):
    """
    Check if the trace has visited this router already.

    :param int chip_x: the x coordinate of the chip being checked
    :param int chip_y: the y coordinate of the chip being checked
    :param set(tuple(int,int)) visited_routers: routers already visited
    :raise PacmanRoutingException: when a router has been visited twice.
    """
    visited_routers_router = (chip_x, chip_y)
    if visited_routers_router in visited_routers:
        raise PacmanRoutingException(
            "visited this router before, there is a cycle here. "
            f"The routers I've currently visited are {visited_routers} and "
            f"the router i'm visiting is {visited_routers_router}")
    visited_routers.add(visited_routers_router)


def _is_dest(processor_ids, current_router, reached_placements):
    """
    Collect processors to be removed.

    :param iterable(int) processor_ids:
        the processor IDs which the last router entry said the trace should
        visit
    :param MulticastRoutingTable current_router:
        the current router being used in the trace
    :param set(PlacementTuple) reached_placements:
        the placements to which the trace visited
    """
    dest_x, dest_y = current_router.x, current_router.y
    for processor_id in processor_ids:
        reached_placements.add(PlacementTuple(dest_x, dest_y, processor_id))


def _locate_routing_entry(current_router, key, n_atoms):
    """
    Locate the entry from the router based off the edge.

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
                        f"Full key range not covered: key:0x{key:x} "
                        f"key_combo:0x{key_combo:x} mask:0x{entry.mask:x}, "
                        f"last_key:0x{last_key:x}, e_key:0x{e_key:x}")
        elif entry.mask in range_masks:
            last_atom = key + n_atoms
            last_key = e_key + (~entry.mask & FULL_MASK)
            if min(last_key, last_atom) - max(e_key, key) + 1 > 0:
                raise PacmanConfigurationException(
                    f"Key range partially covered:  key:0x{key:x}, "
                    f"key_combo:0x{key_combo:x} mask:0x{entry.mask:x}, "
                    f"last_key:0x{last_key:x}, e_key:0x{e_key:x}")
    if found_entry is None:
        raise PacmanRoutingException("no entry located")
    return found_entry
