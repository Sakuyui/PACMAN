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

from .machine_vertex import MachineVertex
from .machine_edge import MachineEdge
from pacman.model.graphs.graph import Graph
from pacman.model.graphs import OutgoingEdgePartition


class MachineGraph(Graph):
    """ A graph whose vertices can fit on the chips of a machine.
    """

    __slots__ = ["_app_graph"]

    def __init__(self, label, application_graph=None):
        """
        :param label: The label for the graph
        :type label: str or None
        :param application_graph:
            The application graph that this machine graph is derived from.
        :type application_graph: ApplicationGraph or None
        """
        super(MachineGraph, self).__init__(
<<<<<<< HEAD
            MachineVertex, MachineEdge, label)
        self._app_graph = application_graph

    @property
    def application_graph(self):
        """
        :rtype: ApplicationGraph or None
        """
        return self._app_graph

    @application_graph.setter
    def application_graph(self, application_graph):
        self._app_graph = application_graph
=======
            MachineVertex, MachineEdge, OutgoingEdgePartition, label)
>>>>>>> refs/remotes/origin/master
