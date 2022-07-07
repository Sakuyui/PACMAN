# Copyright (c) 2021 The University of Manchester
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
from .vertex_routing_info import VertexRoutingInfo
from spinn_machine.multicast_routing_entry import MulticastRoutingEntry
from spinn_utilities.overrides import overrides

import math
import logging

logger = logging.getLogger(__name__)


class AppVertexRoutingInfo(VertexRoutingInfo):

    __slots__ = [
        "__app_vertex",
        "__machine_mask",
        "__n_bits_atoms",
        "__max_machine_index"]

    def __init__(
            self, keys_and_masks, partition_id, app_vertex, machine_mask,
            n_bits_atoms, max_machine_index):
        super(AppVertexRoutingInfo, self).__init__(
            keys_and_masks, partition_id)
        self.__app_vertex = app_vertex
        self.__machine_mask = machine_mask
        self.__n_bits_atoms = n_bits_atoms
        self.__max_machine_index = max_machine_index

    def merge_machine_entries(self, entries):
        n_entries = len(entries)
        (_, _, _, last_r_info) = entries[-1]
        is_last = last_r_info.index == self.__max_machine_index
        i = 0
        while i < n_entries:
            # The maximum number of next entries
            (_, _, entry, r_info) = entries[i]
            next_entries = self.__n_sequential_entries(r_info.index, n_entries)

            # If that is OK, we can just use them
            if next_entries <= (n_entries - i) or is_last:
                mask = self.__group_mask(next_entries)
                yield MulticastRoutingEntry(
                    r_info.first_key, mask, defaultable=entry.defaultable,
                    spinnaker_route=entry.spinnaker_route)
                i += next_entries

            # Otherwise, we have to break down into powers of two
            else:
                entries_to_go = n_entries - i
                while entries_to_go > 0:
                    next_entries = 2 ** int(math.log2(entries_to_go))
                    mask = self.__group_mask(next_entries)
                    (_, _, entry, r_info) = entries[i]
                    yield MulticastRoutingEntry(
                        r_info.first_key, mask,
                        defaultable=entry.defaultable,
                        spinnaker_route=entry.spinnaker_route)
                    entries_to_go -= next_entries
                    i += next_entries

    def __group_mask(self, n_entries):
        return self.__machine_mask - ((n_entries - 1) << self.__n_bits_atoms)

    def __n_sequential_entries(self, i, n_entries):
        # This finds the maximum number of entries that can be joined following
        # the starting entry index.  This is calculated by finding how many
        # zero bits are in the least significant position in the index.  These
        # can then be masked out to merge entries.
        # Works because -v == not v + 1
        if i > 0:
            return i & -i
        return 2 ** int(math.ceil(math.log2(n_entries)))

    @property
    @overrides(VertexRoutingInfo.vertex)
    def vertex(self):
        return self.__app_vertex

    @property
    def machine_mask(self):
        """ The mask that covers a specific machine vertex

        :rtype: int
        """

        return self.__machine_mask

    @property
    def n_bits_atoms(self):
        """ The number of bits for the atoms

        :rtype: int
        """
        return self.__n_bits_atoms
