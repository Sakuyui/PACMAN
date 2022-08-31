# Copyright (c) 2022 The University of Manchester
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

import unittest
from pacman.config_setup import unittest_setup
from pacman.data.pacman_data_writer import PacmanDataWriter
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.partitioner_splitters import SplitterFixedLegacy
from pacman.model.placements import Placements
from pacman.operations.placer_algorithms import place_application_graph
from pacman.operations.partition_algorithms import splitter_partitioner
from pacman.operations.router_algorithms.application_router import (
    route_application_graph)
from pacman.model.routing_info import RoutingInfo
from pacman.operations.routing_info_allocator_algorithms import (
    ZonedRoutingInfoAllocator)
from pacman.operations.routing_table_generators import (
    merged_routing_table_generator)
from pacman_test_objects import SimpleTestVertex


class TestCompressor(unittest.TestCase):

    def setUp(self):
        unittest_setup()

    def create_graphs1(self, writer):
        v1 = SimpleTestVertex(
            10, "app1", max_atoms_per_core=10, splitter=SplitterFixedLegacy())
        v2 = SimpleTestVertex(
            10, "app2", max_atoms_per_core=10, splitter=SplitterFixedLegacy())
        writer.add_vertex(v1)
        writer.add_vertex(v2)
        writer.add_edge(ApplicationEdge(v1, v2), "foo")

    def create_graphs2(self, writer):
        v1 = SimpleTestVertex(
            100, "app1", max_atoms_per_core=10, splitter=SplitterFixedLegacy())
        v2 = SimpleTestVertex(
            100, "app2", max_atoms_per_core=10, splitter=SplitterFixedLegacy())
        v3 = SimpleTestVertex(
            10, "app3", max_atoms_per_core=10, splitter=SplitterFixedLegacy())
        v4 = SimpleTestVertex(
            10, "app4", max_atoms_per_core=10, splitter=SplitterFixedLegacy())
        writer.add_vertex(v1)
        writer.add_vertex(v2)
        writer.add_vertex(v3)
        writer.add_vertex(v4)
        writer.add_edge(ApplicationEdge(v1, v2), "foo")
        writer.add_edge(ApplicationEdge(v3, v4), "foo")

    def make_data(self, writer):
        splitter_partitioner()
        writer.set_placements(place_application_graph(Placements()))
        writer.set_routing_table_by_partition(route_application_graph())
        allocator = ZonedRoutingInfoAllocator()
        writer.set_routing_infos(allocator.__call__([], flexible=False))

    def test_empty(self):
        writer = PacmanDataWriter.mock()
        self.make_data(writer)
        data = merged_routing_table_generator()
        self.assertEqual(0, data.max_number_of_entries)
        self.assertEqual(0, len(list(data.routing_tables)))

    def test_small(self):
        writer = PacmanDataWriter.mock()
        self.create_graphs1(writer)
        self.make_data(writer)
        data = merged_routing_table_generator()
        self.assertEqual(1, data.max_number_of_entries)
        self.assertEqual(1, len(list(data.routing_tables)))

    def test_medium(self):
        writer = PacmanDataWriter.mock()
        self.create_graphs2(writer)
        self.make_data(writer)
        data = merged_routing_table_generator()
        self.assertEqual(2, data.max_number_of_entries)
        self.assertEqual(2, len(list(data.routing_tables)))

    def test_bad_infos(self):
        writer = PacmanDataWriter.mock()
        self.create_graphs1(writer)
        self.make_data(writer)
        writer.set_routing_infos(RoutingInfo())
        try:
            merged_routing_table_generator()
            raise Exception("Should not get here")
        except Exception as ex:
            self.assertIn("Missing Routing information", str(ex))
