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

from .application_edge import ApplicationEdge
from .application_vertex import ApplicationVertex
from pacman.model.graphs import OutgoingEdgePartition
from pacman.model.graphs import Graph


class ApplicationGraph(Graph):
    """ An application-level abstraction of a graph.
    """

    __slots__ = []

    def __init__(self, label):
        """
        :param label: The label on the graph, or None
        :type label: str or None
        """
        super(ApplicationGraph, self).__init__(
            ApplicationVertex, ApplicationEdge, OutgoingEdgePartition,
            label)
