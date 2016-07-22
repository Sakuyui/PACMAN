from pacman.model.graph.application.abstract_virtual_application_vertex \
    import AbstractVirtualApplicationVertex
from pacman.model.constraints.tag_allocator_constraints.\
    abstract_tag_allocator_constraint import AbstractTagAllocatorConstraint
from pacman.utilities import utility_calls
from pacman.utilities import file_format_schemas

from spinn_machine.utilities.progress_bar import ProgressBar

from collections import defaultdict

import os
import json
import jsonschema

DEFAULT_NOUMBER_OF_CORES_USED_PER_VERTEX = 1


class ConvertToFileMachineGraph(object):
    """ Converts a memory based graph into a file based graph
    """

    def __call__(self, machine_graph, file_path):
        """

        :param machine_graph:
        :param folder_path:
        :return:
        """
        progress_bar = ProgressBar(
            len(machine_graph.vertices), "Converting to json graph")

        # write basic stuff
        json_graph_dictory_rep = dict()

        # write vertices data
        vertices_resources = dict()
        json_graph_dictory_rep["vertices_resources"] = vertices_resources

        edges_resources = defaultdict()
        json_graph_dictory_rep["edges"] = edges_resources

        vertex_by_id = dict()
        partition_by_id = dict()
        for vertex in machine_graph.vertices:

            vertex_id = str(id(vertex))
            vertex_by_id[vertex_id] = vertex

            # handle external devices
            if isinstance(vertex, AbstractVirtualApplicationVertex):
                vertex_resources = dict()
                vertices_resources[vertex_id] = vertex_resources
                vertex_resources["cores"] = 0

            # handle tagged vertices
            elif len(utility_calls.locate_constraints_of_type(
                    vertex.constraints, AbstractTagAllocatorConstraint)) != 0:

                # handle the edge between the tag-able vertex and the fake
                # vertex
                tag_id = vertex_id + "_tag"
                hyper_edge_dict = dict()
                edges_resources[tag_id] = hyper_edge_dict
                hyper_edge_dict["source"] = vertex_id
                hyper_edge_dict['sinks'] = tag_id
                hyper_edge_dict["weight"] = 1.0
                hyper_edge_dict["type"] = "FAKE_TAG_EDGE"

                # add the tag-able vertex
                vertex_resources = dict()
                vertices_resources[vertex_id] = vertex_resources
                vertex_resources["cores"] = \
                    DEFAULT_NOUMBER_OF_CORES_USED_PER_VERTEX
                vertex_resources["sdram"] = \
                    int(vertex.resources_required.sdram.get_value())

                # add fake vertex
                vertex_resources = dict()
                vertices_resources[tag_id] = vertex_resources
                vertex_resources["cores"] = 0
                vertex_resources["sdram"] = 0

            # handle standard vertices
            else:
                vertex_resources = dict()
                vertices_resources[vertex_id] = vertex_resources
                vertex_resources["cores"] = \
                    DEFAULT_NOUMBER_OF_CORES_USED_PER_VERTEX
                vertex_resources["sdram"] = \
                    int(vertex.resources_required.sdram.get_value())

            vertex_outgoing_partitions = machine_graph\
                .get_outgoing_edge_partitions_starting_at_vertex(vertex)

            # handle the vertex edges
            for partition in vertex_outgoing_partitions:
                partition_id = str(id(partition))
                partition_by_id[partition_id] = partition

                hyper_edge_dict = dict()
                edges_resources[partition_id] = hyper_edge_dict
                hyper_edge_dict["source"] = str(id(vertex))

                sinks_string = []
                weight = 0

                for edge in partition.edges:
                    sinks_string.append(str(id(edge.post_vertex)))
                    weight += edge.weight
                hyper_edge_dict['sinks'] = sinks_string
                hyper_edge_dict["weight"] = weight
                hyper_edge_dict["type"] = partition.traffic_type.name.lower()
            progress_bar.update()

        file_to_write = open(file_path, "w")
        json.dump(json_graph_dictory_rep, file_to_write)
        file_to_write.close()

        # validate the schema
        graph_schema_file_path = os.path.join(
            os.path.dirname(file_format_schemas.__file__),
            "machine_graph.json"
        )
        file_to_read = open(graph_schema_file_path, "r")
        graph_schema = json.load(file_to_read)
        jsonschema.validate(json_graph_dictory_rep, graph_schema)

        progress_bar.end()

        return file_path, vertex_by_id, partition_by_id
