# Copyright (c) 2019-2020 The University of Manchester
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
from pacman.model.graphs.abstract_single_source_partition import (
    AbstractSingleSourcePartition)
from pacman.model.graphs.abstract_sdram_partition import (
    AbstractSDRAMPartition)
from spinn_utilities.abstract_base import AbstractBase


@add_metaclass(AbstractBase)
class AbstractSDRAMSinglePartition(
        AbstractSingleSourcePartition, AbstractSDRAMPartition):

    __slots__ = []

    def __init__(
            self, pre_vertex, identifier, allowed_edge_types, constraints,
            label, traffic_weight, class_name):
        super(AbstractSDRAMSinglePartition, self).__init__(
            pre_vertex, identifier, allowed_edge_types, constraints,
            label, traffic_weight, class_name)
