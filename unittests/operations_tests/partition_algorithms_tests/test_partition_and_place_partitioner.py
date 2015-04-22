"""
test for partitioning
"""

# pacman imports
from pacman.model.constraints.partitioner_constraints\
    .partitioner_same_size_as_vertex_constraint \
    import PartitionerSameSizeAsVertexConstraint
from pacman.exceptions import PacmanPartitionException, \
    PacmanInvalidParameterException, PacmanValueError
from pacman.model.constraints.partitioner_constraints.\
    partitioner_maximum_size_constraint import \
    PartitionerMaximumSizeConstraint
from pacman.model.partitionable_graph.multi_cast_partitionable_edge import \
    MultiCastPartitionableEdge
from pacman.operations.partition_algorithms import PartitionAndPlacePartitioner
from pacman.model.partitionable_graph.partitionable_graph \
    import PartitionableGraph

# spinnMachine imports
from spinn_machine.machine import Machine
from spinn_machine.processor import Processor
from spinn_machine.sdram import SDRAM
from spinn_machine.link import Link
from spinn_machine.router import Router
from spinn_machine.chip import Chip

# general imports
import unittest
from uinit_test_objects.test_partitioning_constraint import \
    NewPartitionerConstraint
from uinit_test_objects.test_vertex import TestVertex


class TestBasicPartitioner(unittest.TestCase):
    """
    test for basic parittioning algorithum
    """

    def setup(self):
        """
        setup for all absic partitioner tests
        :return:
        """
        self.vert1 = TestVertex(10, "New AbstractConstrainedVertex 1")
        self.vert2 = TestVertex(5, "New AbstractConstrainedVertex 2")
        self.vert3 = TestVertex(3, "New AbstractConstrainedVertex 3")
        self.edge1 = MultiCastPartitionableEdge(self.vert1, self.vert2,
                                                None, "First edge")
        self.edge2 = MultiCastPartitionableEdge(self.vert2, self.vert1,
                                                None, "Second edge")
        self.edge3 = MultiCastPartitionableEdge(self.vert1, self.vert3,
                                                None, "Third edge")
        self.verts = [self.vert1, self.vert2, self.vert3]
        self.edges = [self.edge1, self.edge2, self.edge3]
        self.graph = PartitionableGraph("Graph", self.verts, self.edges)

        flops = 1000
        (e, ne, n, w, sw, s) = range(6)

        processors = list()
        for i in range(18):
            processors.append(Processor(i, flops))

        links = list()
        links.append(Link(0, 0, 0, 0, 1, s, s))

        _sdram = SDRAM(128 * (2**20))

        links = list()

        links.append(Link(0, 0, 0, 1, 1, n, n))
        links.append(Link(0, 1, 1, 1, 0, s, s))
        links.append(Link(1, 1, 2, 0, 0, e, e))
        links.append(Link(1, 0, 3, 0, 1, w, w))
        r = Router(links, False, 100, 1024)

        ip = "192.162.240.253"
        chips = list()
        for x in range(5):
            for y in range(5):
                chips.append(Chip(x, y, processors, r, _sdram, 0, 0, ip))

        self.machine = Machine(chips)
        self.bp = PartitionAndPlacePartitioner()

    def test_new_basic_partitioner(self):
        """
        test that the basic partitioner only can handle
        PartitionerMaximumSizeConstraints
        :return:
        """
        self.setup()
        self.assertEqual(self.bp._supported_constraints[0],
                         PartitionerMaximumSizeConstraint)

    def test_partition_with_no_additional_constraints(self):
        """
        test a partitionign with a graph with no extra constraints
        :return:
        """
        self.setup()
        subgraph, mapper = self.bp.partition(self.graph, self.machine)
        self.assertEqual(len(subgraph.subvertices), 3)
        vert_sizes = []
        for vert in self.verts:
            vert_sizes.append(vert.n_atoms)
        self.assertEqual(len(subgraph.subedges), 3)
        for subvert in subgraph.subvertices:
            self.assertIn(mapper.get_subvertex_slice(subvert).n_atoms,
                          vert_sizes)

    def test_partition_with_no_additional_constraints_extra_edge(self):
        """
        test that the basic form with an extra edge works
        :return:
        """
        self.setup()
        self.graph.add_edge(MultiCastPartitionableEdge(self.vert3, self.vert1,
                                                       None, "Extra edge"))
        subgraph, mapper = self.bp.partition(self.graph, self.machine)
        self.assertEqual(len(subgraph.subvertices), 3)
        self.assertEqual(len(subgraph.subedges), 4)

    def test_partition_on_large_vertex_than_has_to_be_split(self):
        """
        test that partitioning 1 lage vertex can make it into 2 small ones
        :return:
        """
        self.setup()
        large_vertex = TestVertex(300, "Large vertex")
        self.graph = PartitionableGraph(
            "Graph with large vertex", [large_vertex], [])
        subgraph, mapper = self.bp.partition(self.graph, self.machine)
        self.assertEqual(large_vertex._model_based_max_atoms_per_core, 256)
        self.assertGreater(len(subgraph.subvertices), 1)

    def test_partition_on_very_large_vertex_than_has_to_be_split(self):
        """
        test that partitioning 1 lage vertex can make it into multiple small ones
        :return:
        """
        self.setup()
        large_vertex = TestVertex(500, "Large vertex")
        self.assertEqual(large_vertex._model_based_max_atoms_per_core, 256)
        self.graph = PartitionableGraph(
            "Graph with large vertex", [large_vertex], [])
        subgraph, mapper = self.bp.partition(self.graph, self.machine)
        self.assertEqual(large_vertex._model_based_max_atoms_per_core, 256)
        self.assertGreater(len(subgraph.subvertices), 1)

    def test_partition_on_target_size_vertex_than_has_to_be_split(self):
        """
        test that fixed partitioning causes correct number of subvertices
        :return:
        """
        self.setup()
        large_vertex = TestVertex(1000, "Large vertex")
        large_vertex.add_constraint(PartitionerMaximumSizeConstraint(10))
        self.graph = PartitionableGraph(
            "Graph with large vertex", [large_vertex], [])
        subgraph, mapper = self.bp.partition(self.graph, self.machine)
        self.assertEqual(len(subgraph.subvertices), 100)

    def test_partition_with_barely_sufficient_space(self):
        """
        test that partitioning will work when close to filling the machine
        :return:
        """
        self.setup()
        flops = 1000
        (e, ne, n, w, sw, s) = range(6)

        processors = list()
        for i in range(18):
            processors.append(Processor(i, flops))

        links = list()
        links.append(Link(0, 0, 0, 0, 1, s, s))

        _sdram = SDRAM(2**12)

        links = list()

        links.append(Link(0, 0, 0, 1, 1, n, n))
        links.append(Link(0, 1, 1, 1, 0, s, s))
        links.append(Link(1, 1, 2, 0, 0, e, e))
        links.append(Link(1, 0, 3, 0, 1, w, w))
        r = Router(links, False, 100, 1024)

        ip = "192.162.240.253"
        chips = list()
        for x in range(5):
            for y in range(5):
                chips.append(Chip(x, y, processors, r, _sdram, 0, 0, ip))

        self.machine = Machine(chips)
        singular_vertex = TestVertex(450, "Large vertex", max_atoms_per_core=1)
        self.assertEqual(singular_vertex._model_based_max_atoms_per_core, 1)
        self.graph = PartitionableGraph(
            "Graph with large vertex", [singular_vertex], [])
        subgraph, mapper = self.bp.partition(self.graph, self.machine)
        self.assertEqual(singular_vertex._model_based_max_atoms_per_core, 1)
        self.assertEqual(len(subgraph.subvertices), 450)

    def test_partition_with_insufficient_space(self):
        """
        test that if theres not enough space, the test the partitioner will
         raise an error
        :return:
        """
        self.setup()
        flops = 1000
        (e, ne, n, w, sw, s) = range(6)

        processors = list()
        for i in range(18):
            processors.append(Processor(i, flops))

        links = list()
        links.append(Link(0, 0, 0, 0, 1, s, s))

        _sdram = SDRAM(2**11)

        links = list()

        links.append(Link(0, 0, 0, 1, 1, n, n))
        links.append(Link(0, 1, 1, 1, 0, s, s))
        links.append(Link(1, 1, 2, 0, 0, e, e))
        links.append(Link(1, 0, 3, 0, 1, w, w))
        r = Router(links, False, 100, 1024)

        ip = "192.162.240.253"
        chips = list()
        for x in range(5):
            for y in range(5):
                chips.append(Chip(x, y, processors, r, _sdram, 0, 0, ip))

        self.machine = Machine(chips)
        large_vertex = TestVertex(3000, "Large vertex", max_atoms_per_core=1)
        self.assertEqual(large_vertex._model_based_max_atoms_per_core, 1)
        self.graph = PartitionableGraph(
            "Graph with large vertex", [large_vertex], [])
        self.assertRaises(PacmanValueError, self.bp.partition,
                          self.graph, self.machine)

    def test_partition_with_less_sdram_than_default(self):
        """
        test that the partitioner works when its machine is slightly malformed
        in that it has less sdram avilable
        :return:
        """
        self.setup()
        flops = 1000
        (e, ne, n, w, sw, s) = range(6)

        processors = list()
        for i in range(18):
            processors.append(Processor(i, flops))

        links = list()
        links.append(Link(0, 0, 0, 0, 1, s, s))

        _sdram = SDRAM(128 * (2**19))

        links = list()

        links.append(Link(0, 0, 0, 1, 1, n, n))
        links.append(Link(0, 1, 1, 1, 0, s, s))
        links.append(Link(1, 1, 2, 0, 0, e, e))
        links.append(Link(1, 0, 3, 0, 1, w, w))
        r = Router(links, False, 100, 1024)

        ip = "192.162.240.253"
        chips = list()
        for x in range(5):
            for y in range(5):
                chips.append(Chip(x, y, processors, r, _sdram, 0, 0, ip))

        self.machine = Machine(chips)
        self.bp.partition(self.graph, self.machine)

    def test_partition_with_more_sdram_than_default(self):
        """
        test that the partitioner works when its machine is slightly malformed
        in that it has more sdram avilable
        :return:
        """
        self.setup()
        flops = 1000
        (e, ne, n, w, sw, s) = range(6)

        processors = list()
        for i in range(18):
            processors.append(Processor(i, flops))

        links = list()
        links.append(Link(0, 0, 0, 0, 1, s, s))

        _sdram = SDRAM(128 * (2**21))

        links = list()

        links.append(Link(0, 0, 0, 1, 1, n, n))
        links.append(Link(0, 1, 1, 1, 0, s, s))
        links.append(Link(1, 1, 2, 0, 0, e, e))
        links.append(Link(1, 0, 3, 0, 1, w, w))
        r = Router(links, False, 100, 1024)

        ip = "192.162.240.253"
        chips = list()
        for x in range(5):
            for y in range(5):
                chips.append(Chip(x, y, processors, r, _sdram, 0, 0, ip))

        self.machine = Machine(chips)
        self.bp.partition(self.graph, self.machine)

    def test_partition_with_unsupported_constraints(self):
        """
        test that when a vertex has a constraint that is unrecognised,
        it raises an error
        :return:
        """
        self.setup()
        constrained_vertex = TestVertex(13, "Constrained")
        constrained_vertex.add_constraint(
            NewPartitionerConstraint("Mock constraint"))
        graph = PartitionableGraph("Graph", [constrained_vertex], None)
        partitioner = PartitionAndPlacePartitioner()
        self.assertRaises(PacmanInvalidParameterException,
                          partitioner.partition, graph, self.machine)

    def test_partition_with_empty_graph(self):
        """
        test that the partitioner can work with an empty graph
        :return:
        """
        self.setup()
        self.graph = PartitionableGraph()
        subgraph, mapper = self.bp.partition(self.graph, self.machine)
        self.assertEqual(len(subgraph.subvertices), 0)
#                #                     #                     #                      #                #           #

    def test_operation_with_same_size_as_vertex_constraint(self):
        """
        test that the partition and place partitioner can handle same size as
        constraints ona  vertex that is split into one core
        :return:
        """
        self.setup()
        constrained_vertex = TestVertex(5, "Constrained")
        constrained_vertex.add_constraint(
            PartitionerSameSizeAsVertexConstraint(self.vert2))
        self.graph.add_vertex(constrained_vertex)
        partitioner = PartitionAndPlacePartitioner()
        subgraph, graph_to_sub_graph_mapper = \
            partitioner.partition(self.graph, self.machine)
        self.assertEqual(len(subgraph.subvertices), 3)

    def test_operation_with_same_size_as_vertex_constraint_large_vertices(self):
        """
        test that the partition and place partitioner can handle same size as
        constraints on a vertex which has to be split over many cores
        :return:
        """
        self.setup()
        constrained_vertex = TestVertex(300, "Constrained")
        new_large_vertex = TestVertex(300, "Non constrained")
        constrained_vertex.add_constraint(
            PartitionerSameSizeAsVertexConstraint(new_large_vertex))
        self.graph = PartitionableGraph(
            "New graph", [new_large_vertex, constrained_vertex])
        partitioner = PartitionAndPlacePartitioner()
        subgraph, graph_to_sub_graph_mapper = \
            partitioner.partition(self.graph, self.machine)
        self.assertEqual(len(subgraph.subvertices), 3)

    def test_operation_same_size_as_vertex_constraint_different_order(self):
        """
        test that the partition and place partitioner can handle same size as
        constraints on a vertex which has to be split over many cores where
        the order of the vetices being added is different.
        :return:
        """
        self.setup()
        constrained_vertex = TestVertex(300, "Constrained")
        new_large_vertex = TestVertex(300, "Non constrained")
        constrained_vertex.add_constraint(
            PartitionerSameSizeAsVertexConstraint(new_large_vertex))
        self.graph = PartitionableGraph("New graph",
                                        [constrained_vertex, new_large_vertex])
        partitioner = PartitionAndPlacePartitioner()
        subgraph, graph_to_sub_graph_mapper = \
            partitioner.partition(self.graph, self.machine)
        self.assertEqual(len(subgraph.subvertices), 3)

    def test_operation_with_same_size_as_vertex_constraint_exception(self):
        """
        test that a partition same as constraint with differetn size atoms
         causes errors
        :return:
        """
        self.setup()
        constrained_vertex = TestVertex(100, "Constrained")
        constrained_vertex.add_constraint(
            PartitionerSameSizeAsVertexConstraint(self.vert2))
        self.graph.add_vertex(constrained_vertex)
        partitioner = PartitionAndPlacePartitioner()
        self.assertRaises(PacmanPartitionException, partitioner.partition,
                          self.graph, self.machine)

    @unittest.skip("Test not implemented yet")
    def test_detect_subclass_hierarchy(self):
        self.assertEqual(True, False, "Test not implemented yet")

    @unittest.skip("Test not implemented yet")
    def test_partition_by_atoms(self):
        self.assertEqual(True, False, "Test not implemented yet")

    @unittest.skip("Test not implemented yet")
    def test_scale_down_resource_usage(self):
        self.assertEqual(True, False, "Test not implemented yet")

    @unittest.skip("Test not implemented yet")
    def test_scale_up_resource_usage(self):
        self.assertEqual(True, False, "Test not implemented yet")

    @unittest.skip("Test not implemented yet")
    def test_find_max_ratio(self):
        self.assertEqual(True, False, "Test not implemented yet")

    @unittest.skip("Test not implemented yet")
    def test_locate_vertices_to_partition_now(self):
        self.assertEqual(True, False, "Test not implemented yet")

    @unittest.skip("Test not implemented yet")
    def test_partition_with_supported_constraints_enough_space(self):
        self.assertEqual(True, False, "Test not implemented yet")

    @unittest.skip("Test not implemented yet")
    def test_partition_with_supported_constraints_not_enough_space(self):
        self.assertEqual(True, False, "Test not implemented yet")

if __name__ == '__main__':
    unittest.main()
