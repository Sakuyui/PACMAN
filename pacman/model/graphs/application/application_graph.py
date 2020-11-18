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
from .application_edge_partition import ApplicationEdgePartition
from spinn_utilities.overrides import overrides
from pacman.exceptions import (
    PacmanAlreadyExistsException, PacmanInvalidParameterException)
from pacman.model.graphs.graph import Graph


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
            ApplicationVertex, ApplicationEdge, label)

    def forget_machine_graph(self):
        """ Forget the whole mapping from this graph to an application graph.
        """
        for v in self.vertices:
            v.forget_machine_vertices()
        for e in self.edges:
            e.forget_machine_edges()

    def forget_machine_edges(self):
        """ Ensure that all application edges in this graph forget what
            machine edges they map to. The mapping of vertices is unaffected.
        """
        for e in self.edges:
            e.forget_machine_edges()

    @overrides(Graph.new_edge_partition)
    def new_edge_partition(self, name, edge):
        return ApplicationEdgePartition(
            identifier=name, pre_vertex=edge.pre_vertex)

    @overrides(Graph.add_outgoing_edge_partition)
    def add_outgoing_edge_partition(self, edge_partition):
        """ Add an existing outgoing edge partition to the graph. Note that \
            the edge partition probably needs to have at least one edge \
            before this will work.

        :param OutgoingEdgePartition edge_partition:
            The outgoing edge partition to add
        :raises PacmanAlreadyExistsException:
            If a partition already exists with the same pre_vertex and
            identifier
        """
        # verify that this partition is suitable for this graph
        if not isinstance(edge_partition, ApplicationEdgePartition):
            raise PacmanInvalidParameterException(
                "outgoing_edge_partition", edge_partition.__class__,
                "Partitions of this graph must be an ApplicationEdgePartition")

        # check this partition doesn't already exist
        key = (edge_partition.pre_vertex,
               edge_partition.identifier)
        if key in self._outgoing_edge_partitions_by_name:
            raise PacmanAlreadyExistsException(
                str(ApplicationEdgePartition), key)

        self._outgoing_edge_partitions_by_pre_vertex[
            edge_partition.pre_vertex].add(edge_partition)
        self._outgoing_edge_partitions_by_name[key] = edge_partition
