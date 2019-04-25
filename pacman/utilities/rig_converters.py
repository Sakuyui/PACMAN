# These two warnings are disabled; because Enum Python hackery.
# pylint: disable=not-an-iterable, not-callable
from six import iteritems, itervalues
try:
    from collections.abc import OrderedDict
except ImportError:
    from collections import OrderedDict
from pacman.model.constraints.placer_constraints import (
    ChipAndCoreConstraint, RadialPlacementFromChipConstraint)
from pacman.model.graphs import (
    AbstractFPGAVertex, AbstractVirtualVertex, AbstractSpiNNakerLinkVertex)
from pacman.model.graphs.common import EdgeTrafficType
from pacman.utilities.algorithm_utilities.placer_algorithm_utilities import (
    get_same_chip_vertex_groups)
from pacman.model.placements import Placement, Placements
from pacman.model.routing_table_by_partition import (
    MulticastRoutingTableByPartition, MulticastRoutingTableByPartitionEntry)
from pacman.utilities.constants import EDGES
#from pacman.minirig.place_and_route.machine import Machine
from pacman.minirig.links import Links
from pacman.minirig.netlist import Net
from pacman.minirig.place_and_route.constraints import (
    LocationConstraint, ReserveResourceConstraint, RouteEndpointConstraint)
from pacman.minirig.place_and_route.routing_tree import RoutingTree
from pacman.minirig.routing_table.entries import Routes
from pacman.minirig.place_and_route.constraints import SameChipConstraint

# A lookup from link name (string) to Links enum entry.
LINK_LOOKUP = {l.name: l for l in Links}
ROUTE_LOOKUP = {"core_{}".format(r.core_num) if r.is_core else r.name: r
                for r in Routes}

CHIP_HOMOGENEOUS_CORES = 18
CHIP_HOMOGENEOUS_SDRAM = 119275520
CHIP_HOMOGENEOUS_SRAM = 24320
CHIP_HOMOGENEOUS_TAGS = 0
ROUTER_MAX_NUMBER_OF_LINKS = 6
ROUTER_HOMOGENEOUS_ENTRIES = 1023

N_CORES_PER_VERTEX = 1

_SUPPORTED_VIRTUAL_VERTEX_TYPES = (
    AbstractFPGAVertex, AbstractSpiNNakerLinkVertex)


def _is_dead(machine, chip, link_id):
    router = chip.router
    if not router.is_link(link_id):
        return True
    link = router.get_link(link_id)
    if not machine.is_chip_at(
            link.destination_x, link.destination_y):
        return True
    dest_chip = machine.get_chip_at(
        link.destination_x, link.destination_y)
    return dest_chip.virtual



def convert_to_rig_graph(machine_graph, vertex_to_xy_dict):
    net_to_partition_dict = OrderedDict()
    for source_vertex in machine_graph.vertices:
        # handle the vertex edges
        for partition in \
                machine_graph.get_outgoing_edge_partitions_starting_at_vertex(
                    source_vertex):
            if partition.traffic_type == EdgeTrafficType.MULTICAST:
                post_vertexes = list(e.post_vertex for e in partition.edges)
                source_xy = vertex_to_xy_dict[source_vertex]
                net = Net(source_xy, post_vertexes)
                net_to_partition_dict[net] = partition

    return net_to_partition_dict


def create_rig_graph_constraints(machine_graph, machine):
    constraints = []
    foo = LINK_LOOKUP[EDGES(2).name.lower()]
    for vertex in machine_graph.vertices:
        # We only support FPGA and SpiNNakerLink virtual vertices
        if isinstance(vertex, _SUPPORTED_VIRTUAL_VERTEX_TYPES):
            if isinstance(vertex, AbstractFPGAVertex):
                link_data = machine.get_fpga_link_with_id(
                    vertex.fpga_id, vertex.fpga_link_id, vertex.board_address)
            else:
                link_data = machine.get_spinnaker_link_with_id(
                    vertex.spinnaker_link_id, vertex.board_address)
            constraints.append(LocationConstraint(
                vertex,
                (link_data.connected_chip_x, link_data.connected_chip_y)))
            constraints.append(RouteEndpointConstraint(
                vertex, LINK_LOOKUP[EDGES(
                    link_data.connected_link).name.lower()]))
        else:
            for constraint in vertex.constraints:
                if isinstance(constraint, (
                        ChipAndCoreConstraint,
                        RadialPlacementFromChipConstraint)):
                    constraints.append(LocationConstraint(
                        vertex, (constraint.x, constraint.y)))

    for group in itervalues(get_same_chip_vertex_groups(machine_graph)):
        if len(group) > 1:
            constraints.append(SameChipConstraint(group))
    return constraints


def create_rig_machine_constraints(machine):
    return [
        ReserveResourceConstraint(
            "cores",
            slice(processor.processor_id, processor.processor_id + 1),
            (chip.x, chip.y))
        for chip in machine.chips for processor in chip.processors
        if processor.is_monitor]


def convert_to_vertex_xy_dict(placements, machine):
    vertex_to_xy_dict = dict()
    for placement in placements:
        if not isinstance(placement.vertex, AbstractVirtualVertex):
            vertex_to_xy_dict[placement.vertex] = (placement.x, placement.y)
            continue
        link_data = None
        vertex = placement.vertex
        if isinstance(vertex, AbstractFPGAVertex):
            link_data = machine.get_fpga_link_with_id(
                vertex.fpga_id, vertex.fpga_link_id, vertex.board_address)
        elif isinstance(vertex, AbstractSpiNNakerLinkVertex):
            link_data = machine.get_spinnaker_link_with_id(
                vertex.spinnaker_link_id, vertex.board_address)
        vertex_to_xy_dict[placement.vertex] = (
            link_data.connected_chip_x, link_data.connected_chip_y)

    return vertex_to_xy_dict


def convert_to_vertex_to_p_dict(placements):
    vertex_to_p_dict = {
        p.vertex: p.p
        for p in placements.placements
        if not isinstance(p.vertex, AbstractVirtualVertex)}

    return vertex_to_p_dict


def convert_from_rig_placements(
        rig_placements, rig_allocations, machine_graph):
    placements = Placements()
    for vertex in rig_placements:
        if isinstance(vertex, AbstractVirtualVertex):
            placements.add_placement(Placement(
                vertex, vertex.virtual_chip_x, vertex.virtual_chip_y, None))
        else:
            x, y = rig_placements[vertex]
            p = rig_allocations[vertex]["cores"].start
            placements.add_placement(Placement(vertex, x, y, p))

    return placements


def convert_from_rig_routes(rig_routes):
    routing_tables = MulticastRoutingTableByPartition()
    for partition in rig_routes:
        partition_route = rig_routes[partition]
        _convert_next_route(
            routing_tables, partition, 0, None, partition_route)
    return routing_tables


def _convert_next_route(
        routing_tables, partition, incoming_processor, incoming_link,
        partition_route):
    x, y = partition_route.chip

    next_hops = list()
    processor_ids = list()
    link_ids = list()
    for (route, next_hop) in partition_route.children:
        if route is not None:
            link = None
            if isinstance(route, Routes):
                if route.is_core:
                    processor_ids.append(route.core_num)
                else:
                    link = route.value
                    link_ids.append(link)
            elif isinstance(route, Links):
                link = route.value
                link_ids.append(link)
            if isinstance(next_hop, RoutingTree):
                next_incoming_link = None
                if link is not None:
                    next_incoming_link = (link + 3) % 6
                next_hops.append((next_hop, next_incoming_link))

    entry = MulticastRoutingTableByPartitionEntry(
        link_ids, processor_ids, incoming_processor, incoming_link)
    routing_tables.add_path_entry(entry, x, y, partition)

    for next_hop, next_incoming_link in next_hops:
        _convert_next_route(
            routing_tables, partition, None, next_incoming_link, next_hop)
