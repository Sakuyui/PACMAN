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

import logging
import os
import time
from spinn_utilities.progress_bar import ProgressBar
from spinn_utilities.log import FormatAdapter
from spinn_machine import Router
from pacman import exceptions
from pacman.model.graphs import AbstractSpiNNakerLinkVertex, AbstractFPGAVertex
from pacman.model.graphs.common import EdgeTrafficType

logger = FormatAdapter(logging.getLogger(__name__))

_LINK_LABELS = {0: 'E', 1: 'NE', 2: 'N', 3: 'W', 4: 'SW', 5: 'S'}

_C_ROUTING_TABLE_DIR = "compressed_routing_tables_generated"
_COMPARED_FILENAME = "comparison_of_compressed_uncompressed_routing_tables.rpt"
_COMPRESSED_ROUTING_SUMMARY_FILENAME = "compressed_routing_summary.rpt"
_PARTITIONING_FILENAME = "partitioned_by_vertex.rpt"
_PLACEMENT_VTX_GRAPH_FILENAME = "placement_by_vertex_using_graph.rpt"
_PLACEMENT_VTX_SIMPLE_FILENAME = "placement_by_vertex_without_graph.rpt"
_PLACEMENT_CORE_GRAPH_FILENAME = "placement_by_core_using_graph.rpt"
_PLACEMENT_CORE_SIMPLE_FILENAME = "placement_by_core_without_graph.rpt"
_ROUTING_FILENAME = "edge_routing_info.rpt"
_ROUTING_SUMMARY_FILENAME = "routing_summary.rpt"
_ROUTING_TABLE_DIR = "routing_tables_generated"
_SDRAM_FILENAME = "chip_sdram_usage_by_core.rpt"
_TAGS_FILENAME = "tags.rpt"
_VIRTKEY_FILENAME = "virtual_key_space_information_report.rpt"

_LOWER_16_BITS = 0xFFFF


def tag_allocator_report(report_folder, tag_infos):
    """ Reports the tags that are being used by the tool chain for this\
        simulation

    :param report_folder: the folder to which the reports are being written
    :param tag_infos: the tags container generated by the tools.
    :rtype: None
    """

    file_name = os.path.join(report_folder, _TAGS_FILENAME)
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(
                len(list(tag_infos.ip_tags)) +
                len(list(tag_infos.reverse_ip_tags)),
                "Reporting Tags")
            for ip_tag in progress.over(tag_infos.ip_tags, False):
                f.write(str(ip_tag) + "\n")
            for reverse_ip_tag in progress.over(tag_infos.reverse_ip_tags):
                f.write(str(reverse_ip_tag) + "\n")
    except IOError:
        logger.error("Generate_tag_report: Can't open file {} for "
                     "writing.", file_name)


def placer_reports_with_application_graph(
        report_folder, hostname, graph, graph_mapper, placements, machine):
    """ Reports that can be produced from placement given a application\
        graph's existence

    :param report_folder: the folder to which the reports are being written
    :param hostname: the machine's hostname to which the placer worked on
    :param graph: the application graph to which placements were built
    :param graph_mapper: \
        the mapping between application and machine graphs
    :param placements: the placements objects built by the placer.
    :param machine: the python machine object
    :rtype: None
    """
    placement_report_with_application_graph_by_vertex(
        report_folder, hostname, graph, graph_mapper, placements)
    placement_report_with_application_graph_by_core(
        report_folder, hostname, placements, machine, graph_mapper)


def placer_reports_without_application_graph(
        report_folder, hostname, machine_graph, placements, machine):
    """

    :param report_folder: the folder to which the reports are being written
    :param hostname: the machine's hostname to which the placer worked on
    :param placements: the placements objects built by the placer.
    :param machine: the python machine object
    :param machine_graph: \
        the machine graph to which the reports are to operate on
    :rtype: None
    """
    placement_report_without_application_graph_by_vertex(
        report_folder, hostname, placements, machine_graph)
    placement_report_without_application_graph_by_core(
        report_folder, hostname, placements, machine)


def router_summary_report(
        report_folder, routing_tables,  hostname, machine):
    """ Generates a text file of routing summaries

    :param report_folder: the report folder to store this value
    :param routing_tables: the original routing tables
    :param hostname: the machine's hostname to which the placer worked on
    :param machine: the python machine object
    :rtype: None
    """
    file_name = os.path.join(report_folder, _ROUTING_SUMMARY_FILENAME)
    progress = ProgressBar(machine.n_chips,
                           "Generating Routing summary report")
    _do_router_summary_report(
        file_name, progress, routing_tables,  hostname, machine)


def router_compressed_summary_report(
        report_folder, routing_tables, hostname, machine):
    """ Generates a text file of routing summaries

    :param report_folder: the report folder to store this value
    :param routing_tables: the original routing tables
    :param hostname: the machine's hostname to which the placer worked on
    :param machine: the python machine object
    :rtype: None
    """
    file_name = os.path.join(
        report_folder, _COMPRESSED_ROUTING_SUMMARY_FILENAME)
    progress = ProgressBar(machine.n_chips,
                           "Generating Routing summary report")
    _do_router_summary_report(
        file_name, progress, routing_tables, hostname, machine)


def _do_router_summary_report(
        file_name, progress, routing_tables,  hostname, machine):
    time_date_string = time.strftime("%c")
    convert = Router.convert_routing_table_entry_to_spinnaker_route
    try:
        with open(file_name, "w") as f:
            f.write("        Routing Summary Report\n")
            f.write("        ======================\n\n")
            f.write("Generated: {} for target machine '{}'\n\n".format(
                time_date_string, hostname))

            total_entries = 0
            max_entries = 0
            max_none_defaultable = 0
            max_link_only = 0
            max_spinnaker_routes = 0
            for (x, y) in progress.over(machine.chip_coordinates):
                table = routing_tables.get_routing_table_for_chip(x, y)
                if table is not None:
                    entries = table.number_of_entries
                    defaultable = table.number_of_defaultable_entries
                    link_only = 0
                    spinnaker_routes = set()
                    for entry in table.multicast_routing_entries:
                        if not entry.processor_ids:
                            link_only += 1
                        spinnaker_routes.add(convert(entry))
                    f.write("Chip {}:{} has {} entries of which {} are "
                            "defaultable and {} link only with {} unique "
                            "spinnaker routes\n"
                            "".format(x, y, entries, defaultable, link_only,
                                      len(spinnaker_routes)))
                    total_entries += entries
                    max_entries = max(max_entries, entries)
                    max_none_defaultable = max(
                        max_none_defaultable, entries - defaultable)
                    max_link_only = max(max_link_only, link_only)
                    max_spinnaker_routes = max(
                        max_spinnaker_routes, len(spinnaker_routes))

            f.write("\n Total entries {}, max per chip {} max none "
                    "defaultable {} max link only {} "
                    "max unique spinnaker routes {}\n\n".format(
                        total_entries, max_entries, max_none_defaultable,
                        max_link_only, max_spinnaker_routes))

    except IOError:
        logger.exception("Generate_routing summary reports: "
                         "Can't open file {} for writing.", file_name)


def router_report_from_paths(
        report_folder, routing_tables, routing_infos, hostname,
        machine_graph, placements, machine):
    """ Generates a text file of routing paths

    :param report_folder: the report folder to store this value
    :param routing_tables: the original routing tables
    :param hostname: the machine's hostname to which the placer worked on
    :param routing_infos:
    :param machine_graph:
    :param placements:
    :param machine: the python machine object
    :rtype: None
    """
    file_name = os.path.join(report_folder, _ROUTING_FILENAME)
    time_date_string = time.strftime("%c")
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(machine_graph.n_outgoing_edge_partitions,
                                   "Generating Routing path report")

            f.write("        Edge Routing Report\n")
            f.write("        ===================\n\n")
            f.write("Generated: {} for target machine '{}'\n\n".format(
                time_date_string, hostname))

            for partition in progress.over(
                    machine_graph.outgoing_edge_partitions):
                if partition.traffic_type == EdgeTrafficType.MULTICAST:
                    _write_one_router_partition_report(
                        f, partition, machine, placements, routing_infos,
                        routing_tables)
    except IOError:
        logger.exception("Generate_routing_reports: Can't open file {} for "
                         "writing.", file_name)


def _write_one_router_partition_report(f, partition, machine, placements,
                                       routing_infos, routing_tables):
    source_placement = placements.get_placement_of_vertex(partition.pre_vertex)
    key_and_mask = routing_infos.get_routing_info_from_partition(
        partition).first_key_and_mask
    for edge in partition.edges:
        destination_placement = placements.get_placement_of_vertex(
            edge.post_vertex)
        path, number_of_entries = _search_route(
            source_placement, destination_placement,
            key_and_mask, routing_tables, machine)
        text = ("**** Edge '{}', from vertex: '{}' to vertex: '{}'".format(
            edge.label, edge.pre_vertex.label, edge.post_vertex.label))
        text += " Takes path \n {}\n".format(path)
        f.write(text)
        f.write("Route length: {}\n".format(number_of_entries))

        # End one entry:
        f.write("\n")


def partitioner_report(report_folder, hostname, graph, graph_mapper):
    """ Generate report on the placement of vertices onto cores.
    :param report_folder: the folder to which the reports are being written
    :param hostname: the machine's hostname to which the placer worked on
    """

    # Cycle through all vertices, and for each cycle through its vertices.
    # For each vertex, describe its core mapping.
    file_name = os.path.join(report_folder, _PARTITIONING_FILENAME)
    time_date_string = time.strftime("%c")
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(graph.n_vertices,
                                   "Generating partitioner report")

            f.write("        Placement Information by Vertex\n")
            f.write("        ===============================\n\n")
            f.write("Generated: {} for target machine '{}'\n\n".format(
                time_date_string, hostname))

            for vertex in progress.over(graph.vertices):
                _write_one_vertex_partition(f, vertex, graph_mapper)
    except IOError:
        logger.exception("Generate_placement_reports: Can't open file {} for"
                         " writing.", file_name)


def _write_one_vertex_partition(f, vertex, graph_mapper):
    vertex_name = vertex.label
    vertex_model = vertex.__class__.__name__
    num_atoms = vertex.n_atoms
    f.write("**** Vertex: '{}'\n".format(vertex_name))
    f.write("Model: {}\n".format(vertex_model))
    f.write("Pop size: {}\n".format(num_atoms))
    f.write("Machine Vertices: \n")

    machine_vertices = sorted(graph_mapper.get_machine_vertices(vertex),
                              key=lambda x: x.label)
    machine_vertices = sorted(machine_vertices,
                              key=lambda x: graph_mapper.get_slice(x).lo_atom)
    for sv in machine_vertices:
        lo_atom = graph_mapper.get_slice(sv).lo_atom
        hi_atom = graph_mapper.get_slice(sv).hi_atom
        f.write("  Slice {}:{} ({} atoms) \n".format(
            lo_atom, hi_atom, hi_atom - lo_atom + 1))
    f.write("\n")


def placement_report_with_application_graph_by_vertex(
        report_folder, hostname, graph, graph_mapper, placements):
    """ Generate report on the placement of vertices onto cores by vertex.

    :param report_folder: the folder to which the reports are being written
    :param hostname: the machine's hostname to which the placer worked on
    :param graph: the graph to which placements were built
    :param graph_mapper: the mapping between graphs
    :param placements: the placements objects built by the placer.
    """

    # Cycle through all vertices, and for each cycle through its vertices.
    # For each vertex, describe its core mapping.
    file_name = os.path.join(report_folder, _PLACEMENT_VTX_GRAPH_FILENAME)
    time_date_string = time.strftime("%c")
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(graph.n_vertices,
                                   "Generating placement report")

            f.write("        Placement Information by Vertex\n")
            f.write("        ===============================\n\n")
            f.write("Generated: {} for target machine '{}'\n\n".format(
                time_date_string, hostname))

            used_processors_by_chip = dict()
            used_sdram_by_chip = dict()
            vertex_by_processor = dict()

            for vertex in progress.over(graph.vertices):
                _write_one_vertex_application_placement(
                    f, vertex, placements, graph_mapper,
                    used_processors_by_chip, used_sdram_by_chip,
                    vertex_by_processor)
    except IOError:
        logger.exception("Generate_placement_reports: Can't open file {} for"
                         " writing.", file_name)


def _write_one_vertex_application_placement(
        f, vertex, placements, graph_mapper,
        used_processors_by_chip, used_sdram_by_chip, vertex_by_processor):
    vertex_name = vertex.label
    vertex_model = vertex.__class__.__name__
    num_atoms = vertex.n_atoms
    f.write("**** Vertex: '{}'\n".format(vertex_name))
    f.write("Model: {}\n".format(vertex_model))
    f.write("Pop size: {}\n".format(num_atoms))
    f.write("Machine Vertices: \n")

    machine_vertices = sorted(graph_mapper.get_machine_vertices(vertex),
                              key=lambda vert: vert.label)
    machine_vertices = sorted(machine_vertices,
                              key=lambda vert:
                              graph_mapper.get_slice(vert).lo_atom)
    for sv in machine_vertices:
        lo_atom = graph_mapper.get_slice(sv).lo_atom
        hi_atom = graph_mapper.get_slice(sv).hi_atom
        num_atoms = hi_atom - lo_atom + 1
        cur_placement = placements.get_placement_of_vertex(sv)
        x, y, p = cur_placement.x, cur_placement.y, cur_placement.p
        key = "{},{}".format(x, y)
        if key in used_processors_by_chip:
            used_pros = used_processors_by_chip[key]
        else:
            used_pros = list()
            used_sdram_by_chip.update({key: 0})
        vertex_by_processor["{},{},{}".format(x, y, p)] = sv
        new_pro = [p, cur_placement]
        used_pros.append(new_pro)
        used_processors_by_chip.update({key: used_pros})
        f.write("  Slice {}:{} ({} atoms) on core ({}, {}, {}) \n"
                .format(lo_atom, hi_atom, num_atoms, x, y, p))
    f.write("\n")


def placement_report_without_application_graph_by_vertex(
        report_folder, hostname, placements, machine_graph):
    """ Generate report on the placement of vertices onto cores by vertex.

    :param report_folder: the folder to which the reports are being written
    :param hostname: the machine's hostname to which the placer worked on
    :param placements: the placements objects built by the placer.
    :param machine_graph: the machine graph generated by the end user
    """

    # Cycle through all vertices, and for each cycle through its vertices.
    # For each vertex, describe its core mapping.
    file_name = os.path.join(report_folder, _PLACEMENT_VTX_SIMPLE_FILENAME)
    time_date_string = time.strftime("%c")
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(machine_graph.n_vertices,
                                   "Generating placement report")

            f.write("        Placement Information by Vertex\n")
            f.write("        ===============================\n\n")
            f.write("Generated: {} for target machine '{}'\n\n".format(
                time_date_string, hostname))

            used_processors_by_chip = dict()
            used_sdram_by_chip = dict()
            vertex_by_processor = dict()

            for vertex in progress.over(machine_graph.vertices):
                _write_one_vertex_machine_placement(
                    f, vertex, placements, used_processors_by_chip,
                    used_sdram_by_chip, vertex_by_processor)
    except IOError:
        logger.exception("Generate_placement_reports: Can't open file {} for"
                         " writing.", file_name)


def _write_one_vertex_machine_placement(
        f, vertex, placements, used_processors_by_chip, used_sdram_by_chip,
        vertex_by_processor):
    vertex_name = vertex.label
    vertex_model = vertex.__class__.__name__
    f.write("**** Vertex: '{}'\n".format(vertex_name))
    f.write("Model: {}\n".format(vertex_model))

    cur_placement = placements.get_placement_of_vertex(vertex)
    x, y, p = cur_placement.x, cur_placement.y, cur_placement.p
    key = "{},{}".format(x, y)
    if key in used_processors_by_chip:
        used_pros = used_processors_by_chip[key]
    else:
        used_pros = list()
        used_sdram_by_chip.update({key: 0})
    vertex_by_processor["{},{},{}".format(x, y, p)] = vertex
    new_pro = [p, cur_placement]
    used_pros.append(new_pro)
    used_processors_by_chip.update({key: used_pros})
    f.write(" Placed on core ({}, {}, {})\n\n".format(x, y, p))


def placement_report_with_application_graph_by_core(
        report_folder, hostname, placements, machine, graph_mapper):
    """ Generate report on the placement of vertices onto cores by core.

    :param report_folder: the folder to which the reports are being written
    :param hostname: the machine's hostname to which the placer worked on
    :param graph_mapper: \
        the mapping between application and machine graphs
    :param machine: the SpiNNaker machine object
    :param placements: the placements objects built by the placer.
    """

    # File 2: Placement by core.
    # Cycle through all chips and by all cores within each chip.
    # For each core, display what is held on it.
    file_name = os.path.join(report_folder, _PLACEMENT_CORE_GRAPH_FILENAME)
    time_date_string = time.strftime("%c")
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(machine.n_chips,
                                   "Generating placement by core report")

            f.write("        Placement Information by Core\n")
            f.write("        =============================\n\n")
            f.write("Generated: {} for target machine '{}'\n\n".format(
                time_date_string, hostname))

            for chip in progress.over(machine.chips):
                _write_one_chip_application_placement(
                    f, chip, placements, graph_mapper)
    except IOError:
        logger.exception("Generate_placement_reports: Can't open file {} for "
                         "writing.", file_name)


def _write_one_chip_application_placement(f, chip, placements, graph_mapper):
    written_header = False
    for processor in chip.processors:
        if placements.is_processor_occupied(
                chip.x, chip.y, processor.processor_id):
            if not written_header:
                f.write("**** Chip: ({}, {})\n".format(chip.x, chip.y))
                f.write("Application cores: {}\n".format(
                    len(list(chip.processors))))
                written_header = True
            pro_id = processor.processor_id
            vertex = placements.get_vertex_on_processor(
                chip.x, chip.y, processor.processor_id)
            app_vertex = graph_mapper.get_application_vertex(vertex)
            vertex_label = app_vertex.label
            vertex_model = app_vertex.__class__.__name__
            vertex_atoms = app_vertex.n_atoms
            lo_atom = graph_mapper.get_slice(vertex).lo_atom
            hi_atom = graph_mapper.get_slice(vertex).hi_atom
            num_atoms = hi_atom - lo_atom + 1
            f.write("  Processor {}: Vertex: '{}', pop size: {}\n".format(
                pro_id, vertex_label, vertex_atoms))
            f.write("              Slice on this core: {}:{} ({} atoms)\n"
                    .format(lo_atom, hi_atom, num_atoms))
            f.write("              Model: {}\n\n".format(vertex_model))


def placement_report_without_application_graph_by_core(
        report_folder, hostname, placements, machine):
    """ Generate report on the placement of vertices onto cores by core.

    :param report_folder: the folder to which the reports are being written
    :param hostname: the machine's hostname to which the placer worked on
    :param machine: the SpiNNaker machine object
    :param placements: the placements objects built by the placer.
    """

    # File 2: Placement by core.
    # Cycle through all chips and by all cores within each chip.
    # For each core, display what is held on it.
    file_name = os.path.join(report_folder, _PLACEMENT_CORE_SIMPLE_FILENAME)
    time_date_string = time.strftime("%c")
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(machine.chips,
                                   "Generating placement by core report")

            f.write("        Placement Information by Core\n")
            f.write("        =============================\n\n")
            f.write("Generated: {}".format(time_date_string))
            f.write(" for target machine '{}'".format(hostname))
            f.write("\n\n")

            for chip in progress.over(machine.chips):
                _write_one_chip_machine_placement(f, chip, placements)
    except IOError:
        logger.exception("Generate_placement_reports: Can't open file {} for "
                         "writing.", file_name)


def _write_one_chip_machine_placement(f, c, placements):
    written_header = False
    for pr in c.processors:
        if placements.is_processor_occupied(c.x, c.y, pr.processor_id):
            if not written_header:
                f.write("**** Chip: ({}, {})\n".format(c.x, c.y))
                f.write("Application cores: {}\n".format(
                    len(list(c.processors))))
                written_header = True
            vertex = placements.get_vertex_on_processor(
                c.x, c.y, pr.processor_id)
            f.write("  Processor {}: Vertex: '{}' \n".format(
                pr.processor_id, vertex.label))
            f.write("              Model: {}\n\n".format(
                vertex.__class__.__name__))
            f.write("\n")


def sdram_usage_report_per_chip(
        report_folder, hostname, placements, machine, plan_n_timesteps,
        data_n_timesteps):
    """ Reports the SDRAM used per chip

    :param report_folder: the folder to which the reports are being written
    :param hostname: the machine's hostname to which the placer worked on
    :param placements: the placements objects built by the placer.
    :param machine: the python machine object
    :param plan_n_timesteps: The number of timesteps for which placer \
        reserved space.
    :param data_n_timesteps: The number of timesteps for which data can be
    saved on the machine.
    :rtype: None
    """

    file_name = os.path.join(report_folder, _SDRAM_FILENAME)
    time_date_string = time.strftime("%c")
    progress = ProgressBar((len(placements) * 2 + machine.n_chips * 2),
                           "Generating SDRAM usage report")
    try:
        with open(file_name, "w") as f:
            f.write("        Memory Usage by Core\n")
            f.write("        ====================\n\n")
            f.write("Generated: {} for target machine '{}'\n\n".format(
                time_date_string, hostname))
            f.write("Planned by partitioner\n")
            f.write("----------------------\n")
            _sdram_usage_report_per_chip_with_timesteps(
                f, placements, machine, plan_n_timesteps, progress, False)
            f.write("\nActual space reserved on the machine\n")
            f.write("----------------------\n")
            _sdram_usage_report_per_chip_with_timesteps(
                f, placements, machine, data_n_timesteps, progress, True)
    except IOError:
        logger.exception("Generate_placement_reports: Can't open file {} for "
                         "writing.", file_name)


def _sdram_usage_report_per_chip_with_timesteps(
        f, placements, machine, timesteps, progress, end_progress):
    f.write("Based on {} timesteps\n\n".format(timesteps))
    used_sdram_by_chip = dict()
    placements = sorted(placements.placements,
                        key=lambda x: x.vertex.label)
    for placement in progress.over(placements, False):
        sdram = placement.vertex.resources_required.sdram.get_total_sdram(
            timesteps)
        x, y, p = placement.x, placement.y, placement.p
        f.write("SDRAM reqs for core ({},{},{}) is {} KB ({} bytes) for {}\n"
                "".format(x, y, p, int(sdram / 1024.0), sdram, placement))
        key = (x, y)
        if key not in used_sdram_by_chip:
            used_sdram_by_chip[key] = sdram
        else:
            used_sdram_by_chip[key] += sdram
    for chip in progress.over(machine.chips, end_progress):
        try:
            used_sdram = used_sdram_by_chip[chip.x, chip.y]
            if used_sdram:
                f.write(
                    "**** Chip: ({}, {}) has total memory usage of"
                    " {} KB ({} bytes) out of a max of "
                    "{} KB ({} bytes)\n\n".format(
                        chip.x, chip.y,
                        int(used_sdram / 1024.0), used_sdram,
                        int(chip.sdram.size / 1024.0), chip.sdram.size))
        except KeyError:
            # Do Nothing
            pass


def routing_info_report(report_folder, machine_graph, routing_infos):
    """ Generates a report which says which keys is being allocated to each\
        vertex

    :param report_folder: the report folder to store this value
    :param machine_graph:
    :param routing_infos:
    """
    file_name = os.path.join(report_folder, _VIRTKEY_FILENAME)
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(machine_graph.n_outgoing_edge_partitions,
                                   "Generating Routing info report")
            for vertex in machine_graph.vertices:
                _write_vertex_virtual_keys(
                    f, vertex, machine_graph, routing_infos, progress)
            progress.end()
    except IOError:
        logger.exception("generate virtual key space information report: "
                         "Can't open file {} for writing.", file_name)


def _write_vertex_virtual_keys(
        f, vertex, graph, routing_infos, progress):
    f.write("Vertex: {}\n".format(vertex))
    for partition in progress.over(
            graph.get_outgoing_edge_partitions_starting_at_vertex(vertex),
            False):
        if partition.traffic_type == EdgeTrafficType.MULTICAST:
            rinfo = routing_infos.get_routing_info_from_partition(partition)
            f.write("    Partition: {}, Routing Info: {}\n".format(
                partition.identifier, rinfo.keys_and_masks))


def router_report_from_router_tables(report_folder, routing_tables):
    """
    :param report_folder: the report folder to store this value
    :param routing_tables: the original routing tables
    :rtype: None
    """

    top_level_folder = os.path.join(report_folder, _ROUTING_TABLE_DIR)
    if not os.path.exists(top_level_folder):
        os.mkdir(top_level_folder)
    progress = ProgressBar(routing_tables.routing_tables,
                           "Generating Router table report")
    for routing_table in progress.over(routing_tables.routing_tables):
        if routing_table.number_of_entries:
            _generate_routing_table(routing_table, top_level_folder)


def router_report_from_compressed_router_tables(report_folder, routing_tables):
    """
    :param report_folder: the report folder to store this value
    :param routing_tables: the original routing tables
    :rtype: None
    """

    top_level_folder = os.path.join(report_folder, _C_ROUTING_TABLE_DIR)
    if not os.path.exists(top_level_folder):
        os.mkdir(top_level_folder)
    progress = ProgressBar(routing_tables.routing_tables,
                           "Generating compressed router table report")
    for routing_table in progress.over(routing_tables.routing_tables):
        if routing_table.number_of_entries:
            _generate_routing_table(routing_table, top_level_folder)


def format_route(entry):
    line_format = "0x{:08X} 0x{:08X} 0x{:08X} {: <7s} {}"

    key = entry.routing_entry_key
    mask = entry.mask
    route = _reduce_route_value(entry.processor_ids, entry.link_ids)
    route_txt = _expand_route_value(entry.processor_ids, entry.link_ids)
    return line_format.format(key, mask, route, str(entry.defaultable),
                              route_txt)


def _generate_routing_table(routing_table, top_level_folder):
    file_name = "routing_table_{}_{}.rpt".format(
        routing_table.x, routing_table.y)
    file_path = os.path.join(top_level_folder, file_name)
    try:
        with open(file_path, "w") as f:
            f.write("Router contains {} entries\n".format(
                routing_table.number_of_entries))

            f.write("{: <5s} {: <10s} {: <10s} {: <10s} {: <7s} {}\n".format(
                "Index", "Key", "Mask", "Route", "Default", "[Cores][Links]"))
            f.write(
                "{:-<5s} {:-<10s} {:-<10s} {:-<10s} {:-<7s} {:-<14s}\n".format(
                    "", "", "", "", "", ""))
            line_format = "{: >5d} {}\n"

            entry_count = 0
            n_defaultable = 0
            for entry in routing_table.multicast_routing_entries:
                index = entry_count & _LOWER_16_BITS
                entry_str = line_format.format(index, format_route(entry))
                entry_count += 1
                if entry.defaultable:
                    n_defaultable += 1
                f.write(entry_str)
            f.write("{} Defaultable entries\n".format(n_defaultable))
    except IOError:
        logger.exception("Generate_placement_reports: Can't open file"
                         " {} for writing.", file_path)


def generate_comparison_router_report(
        report_folder, routing_tables, compressed_routing_tables):
    """ Make a report on comparison of the compressed and uncompressed \
        routing tables

    :param report_folder: the folder to store the resulting report
    :param routing_tables: the original routing tables
    :param compressed_routing_tables: the compressed routing tables
    :rtype: None
    """
    file_name = os.path.join(report_folder, _COMPARED_FILENAME)
    try:
        with open(file_name, "w") as f:
            progress = ProgressBar(
                routing_tables.routing_tables,
                "Generating comparison of router table report")
            total_uncompressed = 0
            total_compressed = 0
            max_compressed = 0
            uncompressed_for_max = None
            for table in progress.over(routing_tables.routing_tables):
                x = table.x
                y = table.y
                compressed_table = compressed_routing_tables.\
                    get_routing_table_for_chip(x, y)
                n_entries_uncompressed = table.number_of_entries
                total_uncompressed += n_entries_uncompressed
                n_entries_compressed = compressed_table.number_of_entries
                total_compressed += n_entries_compressed
                ratio = ((n_entries_uncompressed - n_entries_compressed) /
                         float(n_entries_uncompressed))
                f.write(
                    "Uncompressed table at {}:{} has {} entries "
                    "whereas compressed table has {} entries. "
                    "This is a decrease of {} %\n".format(
                        x, y, n_entries_uncompressed, n_entries_compressed,
                        ratio * 100))
                if max_compressed < n_entries_compressed:
                    max_compressed = n_entries_compressed
                    uncompressed_for_max = n_entries_uncompressed
            ratio = ((total_uncompressed - total_compressed) /
                     float(total_uncompressed))
            f.write(
                "Total has {} entries whereas compressed tables "
                "have {} entries. This is an average decrease of {} %\n "
                "".format(
                    total_uncompressed, total_compressed, ratio * 100))
            ratio = ((uncompressed_for_max - max_compressed) /
                     float(uncompressed_for_max))
            f.write(
                "Worst has {} entries whereas compressed tables "
                "have {} entries. This is a decrease of {} %\n ".format(
                    uncompressed_for_max, max_compressed, ratio * 100))
    except IOError:
        logger.exception("Generate_router_comparison_reports: Can't open file"
                         " {} for writing.", file_name)


def _reduce_route_value(processors_ids, link_ids):
    value = 0
    for link in link_ids:
        value += 1 << link
    for processor in processors_ids:
        value += 1 << (processor + 6)
    return value


def _expand_route_value(processors_ids, link_ids):
    """ Convert a 32-bit route word into a string which lists the target cores\
        and links.
    """

    # Convert processor targets to readable values:
    route_string = "["
    separator = ""
    for processor in processors_ids:
        route_string += "{}{}".format(separator, processor)
        separator = ", "

    route_string += "] ["

    # Convert link targets to readable values:
    link_labels = {0: 'E', 1: 'NE', 2: 'N', 3: 'W', 4: 'SW', 5: 'S'}

    separator = ""
    for link in link_ids:
        route_string += "{}{}".format(separator, link_labels[link])
        separator = ", "
    route_string += "]"
    return route_string


def _search_route(
        source_placement, dest_placement, key_and_mask, routing_tables,
        machine):

    # Create text for starting point
    source_vertex = source_placement.vertex
    text = ""
    if isinstance(source_vertex, AbstractSpiNNakerLinkVertex):
        text += "Virtual SpiNNaker Link "
    if isinstance(source_vertex, AbstractFPGAVertex):
        text += "Virtual FPGA Link "
    text += "{}:{}:{} -> ".format(
        source_placement.x, source_placement.y, source_placement.p)

    # Start the search
    number_of_entries = 0

    # If the destination is virtual, replace with the real destination chip
    extra_text, total_number_of_entries = _recursive_trace_to_destinations(
        source_placement.x, source_placement.y, key_and_mask,
        dest_placement.x, dest_placement.y, dest_placement.p, machine,
        routing_tables, number_of_entries)
    text += extra_text
    return text, total_number_of_entries


# locates the next dest position to check
def _recursive_trace_to_destinations(
        chip_x, chip_y, key_and_mask,
        dest_chip_x, dest_chip_y, dest_p, machine, routing_tables,
        number_of_entries):
    """ Recursively search though routing tables till no more entries are\
        registered with this key
    """

    chip = machine.get_chip_at(chip_x, chip_y)

    # If reached destination, return the core
    if (chip_x == dest_chip_x and chip_y == dest_chip_y):
        text = ""
        if chip.virtual:
            text += "Virtual "
        text += "{}:{}:{}".format(dest_chip_x, dest_chip_y, dest_p)
        return text, number_of_entries + 1

    link_id = None
    result = None
    new_n_entries = None
    if chip.virtual:
        # If the current chip is virtual, use link out
        link_id, link = next(iter(chip.router))
        result, new_n_entries = _recursive_trace_to_destinations(
            link.destination_x, link.destination_y, key_and_mask,
            dest_chip_x, dest_chip_y, dest_p, machine,
            routing_tables, number_of_entries)
        if result is None:
            return None, None
    else:
        # If the current chip is real, find the link to the destination
        table = routing_tables.get_routing_table_for_chip(chip_x, chip_y)
        entry = _locate_routing_entry(table, key_and_mask.key)
        for link_id in entry.link_ids:
            link = chip.router.get_link(link_id)
            result, new_n_entries = _recursive_trace_to_destinations(
                link.destination_x, link.destination_y, key_and_mask,
                dest_chip_x, dest_chip_y, dest_p, machine,
                routing_tables, number_of_entries)
            if result is not None:
                break
        else:
            return None, None

    text = "{}:{}:{} -> {}".format(
        chip_x, chip_y, _LINK_LABELS[link_id], result)
    return text, new_n_entries + 1


def _locate_routing_entry(current_router, key):
    """ Locate the entry from the router based off the edge

    :param current_router: the current router being used in the trace
    :param key: the key being used by the source placement
    :return: the routing table entry
    :raise PacmanRoutingException: \
        when there is no entry located on this router.
    """
    for entry in current_router.multicast_routing_entries:
        if entry.mask & key == entry.routing_entry_key:
            return entry
    raise exceptions.PacmanRoutingException("no entry located")
