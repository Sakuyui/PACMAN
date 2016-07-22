from pacman.model.graph.abstract_vertex import AbstractVertex
from abc import abstractproperty


class AbstractMachineVertex(AbstractVertex):
    """ A vertex of a graph which has certain resource requirements
    """

    @abstractproperty
    def resources_required(self):
        """ The resources required by the vertex

        :rtype:\
            :py:class:`pacman.model.resources.resource_container.ResourceContainer`
        """
