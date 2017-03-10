from abc import abstractproperty, ABCMeta
from six import add_metaclass
from pacman.model.graphs.abstract_vertex import AbstractVertex


@add_metaclass(ABCMeta)
class MachineVertex(AbstractVertex):
    """ A simple implementation of a machine vertex
    """

    __slots__ = []

    def __init__(self, label=None, constraints=None):
        """
        :param label: The optional name of the vertex
        :type label: str
        :param constraints: The optional initial constraints of the vertex
        :type constraints: \
            iterable of\
            :py:class:`pacman.model.constraints.abstract_constraint.AbstractConstraint`
        :raise pacman.exceptions.PacmanInvalidParameterException:
                    * If one of the constraints is not valid
        """
        AbstractVertex.__init__(self, label, constraints)

    def __str__(self):
        l = self.label
        return self.__repr__() if l is None else l

    def __repr__(self):
        return "MachineVertex(label={}, constraints={}".format(
            self.label, self.constraints)

    @abstractproperty
    def resources_required(self):
        """ The resources required by the vertex

        :rtype:\
            :py:class:`pacman.model.resources.resource_container.ResourceContainer`
        """
