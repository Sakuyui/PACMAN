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
from pacman.exceptions import PacmanConfigurationException
from pacman.model.partitioner_splitters import SplitterFixedLegacy
from pacman_test_objects import (
    DuckLegacyApplicationVertex, NonLegacyApplicationVertex, SimpleTestVertex)


class TestSplitterFixedLegacy(unittest.TestCase):

    def setUp(self):
        unittest_setup()

    def test_api(self):
        splitter = SplitterFixedLegacy()
        a = str(splitter)
        self.assertIsNotNone(a)
        v1 = SimpleTestVertex(1, "v1")
        splitter.set_governed_app_vertex(v1)
        a = str(splitter)
        self.assertIsNotNone(a)
        splitter.set_governed_app_vertex(v1)
        v2 = SimpleTestVertex(1, "v2")
        with self.assertRaises(PacmanConfigurationException):
            splitter.set_governed_app_vertex(v2)

    def test_not_api(self):
        splitter = SplitterFixedLegacy()
        v1 = NonLegacyApplicationVertex("v1")
        with self.assertRaises(PacmanConfigurationException):
            splitter.set_governed_app_vertex(v1)

    def test_legacy(self):
        splitter = SplitterFixedLegacy()
        v1 = DuckLegacyApplicationVertex("v1")
        splitter.set_governed_app_vertex(v1)
