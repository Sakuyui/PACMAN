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

import random
import unittest
from spinn_machine import virtual_machine
from pacman.model.graphs.machine import (MachineGraph, SDRAMMachineEdge)
from pacman.model.graphs.machine import ConstantSDRAMMachinePartition
from pacman.model.resources import ResourceContainer
from pacman.model.routing_info import DictBasedMachinePartitionNKeysMap
from pacman.executor.pacman_algorithm_executor import PACMANAlgorithmExecutor
from pacman_test_objects import MockMachineVertex


class TestSameChipConstraint(unittest.TestCase):

    def _do_test(self, placer):
        machine = virtual_machine(width=8, height=8)
        graph = MachineGraph("Test")
        plan_n_timesteps = 100

        vertices = [
            MockMachineVertex(
                ResourceContainer(), label="v{}".format(i), sdram_requirement=20)
            for i in range(100)
        ]
        for vertex in vertices:
            graph.add_vertex(vertex)

        same_vertices = [
            MockMachineVertex(ResourceContainer(), label="same{}".format(i),
                              sdram_requirement=20)
            for i in range(10)
        ]
        random.seed(12345)
        sdram_edges = list()
        for vertex in same_vertices:
            graph.add_vertex(vertex)
            graph.add_outgoing_edge_partition(
                ConstantSDRAMMachinePartition(
                    identifier="Test", pre_vertex=vertex, label="bacon"))
            for _i in range(0, random.randint(1, 5)):
                sdram_edge = SDRAMMachineEdge(
                    vertex, vertices[random.randint(0, 99)], label="bacon",
                    app_edge=None)
                sdram_edges.append(sdram_edge)
                graph.add_edge(sdram_edge, "Test")
        n_keys_map = DictBasedMachinePartitionNKeysMap()

        inputs = {
            "MemoryExtendedMachine": machine,
            "MemoryMachine": machine,
            "MemoryMachineGraph": graph,
            "PlanNTimeSteps": plan_n_timesteps,
            "MemoryMachinePartitionNKeysMap": n_keys_map
        }
        algorithms = [placer]
        xml_paths = []
        executor = PACMANAlgorithmExecutor(
            algorithms, [], inputs, [], [], [], xml_paths)
        executor.execute_mapping()
        placements = executor.get_item("MemoryPlacements")
        for edge in sdram_edges:
            pre_place = placements.get_placement_of_vertex(edge.pre_vertex)
            post_place = placements.get_placement_of_vertex(edge.post_vertex)
            assert pre_place.x == post_place.x
            assert pre_place.y == post_place.y

    def test_one_to_one(self):
        self._do_test("OneToOnePlacer")

    def test_radial(self):
        self._do_test("RadialPlacer")

    def test_spreader(self):
        self._do_test("SpreaderPlacer")
