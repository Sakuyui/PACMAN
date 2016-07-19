
# pacman imports
from pacman.model.abstract_classes.abstract_virtual_vertex import \
    AbstractVirtualVertex
from pacman import exceptions

# general imports
from abc import ABCMeta
from six import add_metaclass

from pacman.model.partitioned_graph.virtual_spinnaker_link_partitioned_vertex import \
    VirtualSpinnakerLinkPartitionedVertex


@add_metaclass(ABCMeta)
class AbstractSpiNNakerLinkVertex(AbstractVirtualVertex):
    """ A class that allows models to define that they are virtual
    """

    def __init__(self, n_atoms, label, max_atoms_per_core, board_address,
                 spinnaker_link_id=None, constraints=None):

        AbstractVirtualVertex.__init__(
            n_atoms, label, max_atoms_per_core, board_address, constraints)

        self._spinnaker_link_id = spinnaker_link_id

        if self._spinnaker_link_id is None:
            raise exceptions.PacmanConfigurationException(
                "The spinnaker link vertex needs to connec to a spinnaker "
                "link.")
    @property
    def spinnaker_link_id(self):
        """ property for returning the spinnaker link being used
        :return:
        """
        return self._spinnaker_link_id

    def create_subvertex(
            self, vertex_slice, resources_required, label=None,
            constraints=None):
        subvertex = VirtualSpinnakerLinkPartitionedVertex(
            resources_required, label, self._spinnaker_link_id,
            constraints=constraints)

        subvertex.set_virtual_chip_coordinates(
            self._virtual_chip_x, self._virtual_chip_y, self._real_chip_x,
            self._real_chip_y, self._real_link)
        return subvertex
