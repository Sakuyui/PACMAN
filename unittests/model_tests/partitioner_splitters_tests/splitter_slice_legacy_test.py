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
from testfixtures import LogCapture
from pacman.exceptions import PacmanConfigurationException
from pacman.model.partitioner_splitters import SplitterSliceLegacy
from pacman_test_objects import (
    DuckLegacyApplicationVertex, NonLegacyApplicationVertex, SimpleTestVertex)


class TestSplitterSliceLegacy(unittest.TestCase):
    """ Tester for pacman.model.constraints.placer_constraints
    """

    def test_no_api(self):
        splitter = SplitterSliceLegacy()
        vertex = NonLegacyApplicationVertex()
        with self.assertRaises(PacmanConfigurationException):
            splitter.set_governed_app_vertex(vertex)

    def test_with_methods(self):
        splitter = SplitterSliceLegacy()
        vertex = DuckLegacyApplicationVertex()
        with LogCapture() as lc:
            splitter.set_governed_app_vertex(vertex)
            found = False
            for record in lc.records:
                if record.msg.fmt == splitter.NOT_API_WARNING:
                    found = True
            self.assertTrue(found)

    def test_with_api(self):
        splitter = SplitterSliceLegacy()
        vertex = SimpleTestVertex(12)
        with LogCapture() as lc:
            splitter.set_governed_app_vertex(vertex)
            found = False
            for record in lc.records:
                if record.msg.fmt == splitter.NOT_API_WARNING:
                    found = True
            self.assertFalse(found)
