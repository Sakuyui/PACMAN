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

from pacman.exceptions import PacmanInvalidParameterException
from spinn_utilities.overrides import overrides
from pacman.model.graphs.common.slice import Slice
from pacman.model.graphs.application.abstract import (
    AbstractVirtualApplicationVertex)


class ApplicationFPGAVertex(AbstractVirtualApplicationVertex):
    """ A virtual application vertex connected to one or more FPGA links
    """

    __slots__ = [
        "_n_atoms",
        "_incoming_fpga_connections",
        "_outgoing_fpga_connection",
        "_n_machine_vertices_per_link"]

    def __init__(
            self, n_atoms, incoming_fpga_connections=None,
            outgoing_fpga_connection=None, label=None, constraints=None,
            n_machine_vertices_per_link=1):
        """

        :param int n_atoms: The number of atoms in the vertex
        :param incoming_fpga_connections:
            The connections from one or more FPGAs that that packets are
            expected to be received from for this device, or None if no
            incoming traffic is expected from the device
        :type incoming_fpga_connections: list(FPGAConnection) or None
        :param outgoing_fpga_connection:
            The connection to an FPGA that packets to be sent to this device
            should be sent down, or None if no outgoing traffic is expected to
            be sent to the device.
        :type outgoing_fpga_connection: FPGAConnection or None
        :param str label: The optional name of the vertex.
        :param iterable(AbstractConstraint) constraints:
            The optional initial constraints of the vertex.
        :param int n_machine_vertices_per_link:
            The optional number of machine vertices to create for each FPGA
            link (1 by default)
        """
        super().__init__(label=label, constraints=constraints)
        self._n_atoms = n_atoms
        self._incoming_fpga_connections = incoming_fpga_connections
        self._outgoing_fpga_connection = outgoing_fpga_connection
        self._n_machine_vertices_per_link = n_machine_vertices_per_link

        if (outgoing_fpga_connection is not None and
                not outgoing_fpga_connection.is_concrete):
            raise PacmanInvalidParameterException(
                "outgoing_fpga_connection", outgoing_fpga_connection,
                "The outgoing connection must have a specific FPGA ID and "
                "link ID")

    @property
    @overrides(AbstractVirtualApplicationVertex.n_atoms)
    def n_atoms(self):
        return self._n_atoms

    @property
    def n_machine_vertices_per_link(self):
        """ The number of machine vertices to create for each link of the FPGA
        :rtype: int
        """
        return self._n_machine_vertices_per_link

    def get_incoming_slice_for_link(self, link, index):
        """ Get the slice to be given to the connection from the given link

        :param FPGAConnection link: The FPGA connection to get the slice for
        :param int index:
            The index of the connection on the FGPA link, for when
            n_machine_vertices_per_link > 1

        :rtype: ~pacman.model.graphs.common.Slice
        """
        atoms_per_slice = self.n_atoms // self._n_machine_vertices_per_link
        low_atom = atoms_per_slice * index
        hi_atom = (atoms_per_slice * (index + 1)) - 1
        hi_atom = min((hi_atom, self.n_atoms - 1))
        return Slice(low_atom, hi_atom)

    def get_outgoing_slice(self):
        """ Get the slice to be given to the outgoing connection

        :rtype: ~pacman.model.graphs.common.Slice
        """
        return Slice(0, self.n_atoms - 1)

    @property
    def incoming_fpga_connections(self):
        """ The connections from one or more FPGAs that packets are expected
            to be received from for this device

        :rtype: iter(FPGAConnection)
        """
        for conn in self._incoming_fpga_connections:
            yield from conn.expanded

    @property
    def outgoing_fpga_connection(self):
        """ The connection to one FPGA via one link to which packets are sent
            to this device.

        :rtype: FPGAConnection or None
        """
        return self._outgoing_fpga_connection

    @overrides(AbstractVirtualApplicationVertex.get_outgoing_link_data)
    def get_outgoing_link_data(self, machine):
        if self._outgoing_fpga_connection is None:
            raise NotImplementedError("This vertex doesn't have outgoing data")
        fpga = self._outgoing_fpga_connection
        return machine.get_fpga_link_with_id(
            fpga.fpga_id, fpga.fpga_link_id, fpga.board_address,
            fpga.chip_coords)
