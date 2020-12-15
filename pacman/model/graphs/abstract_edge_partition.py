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
from six import add_metaclass
from spinn_utilities.abstract_base import (
    AbstractBase, abstractmethod, abstractproperty)
from spinn_utilities.ordered_set import OrderedSet
from pacman.exceptions import (
    PacmanConfigurationException, PacmanInvalidParameterException)
from pacman.model.graphs.common import ConstrainedObject

_REPR_TEMPLATE = "{}(identifier={}, edges={}, constraints={}, label={})"


@add_metaclass(AbstractBase)
class AbstractEdgePartition(ConstrainedObject):
    """ A collection of edges which start at a single vertex which have the
        same semantics and so can share a single key.
    """

    __slots__ = [
        # The partition identifier
        "_identifier",
        # The edges in the partition
        "_edges",
        # The type of edges to accept
        "_allowed_edge_types",
        # The weight of traffic going down this partition
        "_traffic_weight",
        # The label of the graph
        "_label",
        # class name
        "_class_name",
        # Safety code generated by the graph when added to that graph
        "_graph_code"
    ]

    def __init__(
            self, identifier, allowed_edge_types, constraints,
            label, traffic_weight, class_name):
        """
        :param str identifier: The identifier of the partition
        :param allowed_edge_types: The types of edges allowed
        :type allowed_edge_types: type or tuple(type, ...)
        :param iterable(AbstractConstraint) constraints:
            Any initial constraints
        :param str label: An optional label of the partition
        :param int traffic_weight:
            The weight of traffic going down this partition
        """
        ConstrainedObject.__init__(self, constraints)
        self._label = label
        self._identifier = identifier
        self._edges = OrderedSet()
        self._allowed_edge_types = allowed_edge_types
        self._traffic_weight = traffic_weight
        self._class_name = class_name
        self._graph_code = None

    @property
    def label(self):
        """ The label of the edge partition.

        :rtype: str
        """
        return self._label

    def add_edge(self, edge, graph_code):
        """ Add an edge to the edge partition.

        Note: This method should only be called by the add_edge method of the\
            graph that owns the partition. Calling it from anywhere else even
            with the correct graph_code will lead to unsupported inconsistency

        :param AbstractEdge edge: the edge to add
        :param int graph_code:
            A code to check the correct graph is calling this method
        :raises PacmanInvalidParameterException:
            If the edge does not belong in this edge partition
        """
        if graph_code != self._graph_code:
            raise PacmanConfigurationException(
                "Only one graph should add edges")
        if self._graph_code is None:
            raise PacmanConfigurationException(
                "Only Graphs can add edges to partitions")

        # Check for an incompatible edge
        if not isinstance(edge, self._allowed_edge_types):
            raise PacmanInvalidParameterException(
                "edge", str(edge.__class__),
                "Edges of this graph must be one of the following types:"
                " {}".format(self._allowed_edge_types))
        self._edges.add(edge)

    def register_graph_code(self, graph_code):
        """
        Allows the graph to register its code when the partition is added
        """
        if self._graph_code is not None:
            raise PacmanConfigurationException(
                "Illegal attempt to add partition {} to a second "
                "graph".format(self))
        self._graph_code = graph_code

    @property
    def identifier(self):
        """ The identifier of this edge partition.

        :rtype: str
        """
        return self._identifier

    @property
    def edges(self):
        """ The edges in this edge partition.

        NOTE: the order the edges were added will come out in the same order.
        IF not, please talk to the software team.

        :rtype: iterable(AbstractEdge)
        """
        return self._edges

    @property
    def n_edges(self):
        """ The number of edges in the edge partition.

        :rtype: int
        """
        return len(self._edges)

    @property
    def traffic_weight(self):
        """ The weight of the traffic in this edge partition compared to\
            other partitions.

        :rtype: int
        """
        return self._traffic_weight

    def __repr__(self):
        edges = ""
        for edge in self._edges:
            if edge.label is not None:
                edges += edge.label + ","
            else:
                edges += str(edge) + ","
        return _REPR_TEMPLATE.format(
            self._class_name, self._identifier, edges, self.constraints,
            self.label)

    def __str__(self):
        return self.__repr__()

    def __contains__(self, edge):
        """ Check if the edge is contained within this partition

        :param AbstractEdge edge: the edge to search for.
        :rtype: bool
        """
        return edge in self._edges

    @abstractmethod
    def clone_without_edges(self):
        """ Make a copy of this edge partition without any of the edges in it

        This follows the design pattern that only the graph adds edges to
        partitions already added to the graph

        :return: The copied edge partition but excluding edges
        """

    @abstractproperty
    def pre_vertices(self):
        """
        Provides the vertices associated with this partition

        Note: Most edge partitions will be AbstractSingleSourcePartition and
            therefore provide the pre_vertex method.

        :rtype: iter(AbstractVertex)
        """
