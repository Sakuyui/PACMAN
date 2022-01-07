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

import unittest
from pacman.config_setup import unittest_setup
from pacman.data import PacmanDataView
from pacman.data.pacman_data_writer import PacmanDataWriter
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import MachineGraph, SimpleMachineVertex
from pacman.model.resources import (
    ConstantSDRAM, CPUCyclesPerTickResource, DTCMResource, ResourceContainer)
from pacman.exceptions import PacmanValueError
from pacman.model.constraints.placer_constraints import (
    ChipAndCoreConstraint, RadialPlacementFromChipConstraint)
from pacman.operations.placer_algorithms import radial_placer
from pacman_test_objects import (get_resourced_machine_vertex)


class TestRadialPlacer(unittest.TestCase):
    def setUp(self):
        unittest_setup()
        self.mach_graph = MachineGraph("machine")
        self.vertices = list()
        self.vertex1 = get_resourced_machine_vertex(0, 1, "First vertex")
        self.vertex2 = get_resourced_machine_vertex(1, 5, "Second vertex")
        self.vertex3 = get_resourced_machine_vertex(5, 10, "Third vertex")
        self.vertex4 = get_resourced_machine_vertex(10, 100, "Fourth vertex")
        self.vertices.append(self.vertex1)
        self.mach_graph.add_vertex(self.vertex1)
        self.vertices.append(self.vertex2)
        self.mach_graph.add_vertex(self.vertex2)
        self.vertices.append(self.vertex3)
        self.mach_graph.add_vertex(self.vertex3)
        self.vertices.append(self.vertex4)
        self.mach_graph.add_vertex(self.vertex4)
        self.edges = list()

        self.plan_n_timesteps = 100

    def test_simple(self):
        PacmanDataWriter.mock().set_runtime_machine_graph(self.mach_graph)
        placements = radial_placer(100)
        self.assertEqual(len(self.vertices), len(placements))

    def test_place_vertex_too_big_with_vertex(self):
        writer = PacmanDataWriter.mock()
        cpu_cycles = 1000
        dtcm_requirement = 1000
        chip00 = PacmanDataView.get_chip_at(0, 0)
        sdram_requirement = chip00.sdram.size * 20
        rc = ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(cpu_cycles),
            dtcm=DTCMResource(dtcm_requirement),
            sdram=ConstantSDRAM(sdram_requirement))

        large_machine_vertex = SimpleMachineVertex(
            rc, vertex_slice=Slice(0, 499), label="Second vertex")
        self.mach_graph.add_vertex(large_machine_vertex)
        writer.set_runtime_machine_graph(self.mach_graph)
        with self.assertRaises(PacmanValueError):
            radial_placer(100)

    def test_deal_with_constraint_placement_vertices_dont_have_vertex(self):
        self.vertex2.add_constraint(ChipAndCoreConstraint(3, 5, 7))
        self.vertex3.add_constraint(RadialPlacementFromChipConstraint(2, 4))
        PacmanDataWriter.mock().set_runtime_machine_graph(self.mach_graph)
        placements = radial_placer(100)
        for placement in placements:
            if placement.vertex == self.vertex2:
                self.assertEqual(placement.x, 3)
                self.assertEqual(placement.y, 5)
                self.assertEqual(placement.p, 7)
            if placement.vertex == self.vertex3:
                self.assertEqual(placement.x, 2)
                self.assertEqual(placement.y, 4)
        self.assertEqual(len(self.vertices), len(placements))

    def test_fill_machine(self):
        writer = PacmanDataWriter.mock()
        graph = MachineGraph("machine")
        chips = PacmanDataWriter.get_machine().chips
        cores = sum(chip.n_user_processors for chip in chips)
        for i in range(cores):  # 50 atoms per each processor on 20 chips
            graph.add_vertex(get_resourced_machine_vertex(
                0, 50, "vertex " + str(i)))
        writer.set_runtime_machine_graph(graph)
        placements = radial_placer(100)
        self.assertEqual(len(placements), cores)
        # One more vertex should be too many
        graph.add_vertex(get_resourced_machine_vertex(0, 50, "toomany"))
        with self.assertRaises(PacmanValueError):
            radial_placer(100)


if __name__ == '__main__':
    unittest.main()
