# Copyright (c) 2015 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from spinn_utilities.log import FormatAdapter
from pacman.operations.router_compressors import (AbstractCompressor, RTEntry)
from .ordered_covering import minimise

logger = FormatAdapter(logging.getLogger(__name__))


def ordered_covering_compressor():
    """
    Compressor from rig that has been tied into the main tool chain stack.

    :rtype: MulticastRoutingTables
    """
    compressor = _OrderedCoveringCompressor()
    return compressor.compress_all_tables()


class _OrderedCoveringCompressor(AbstractCompressor):
    """
    Compressor from rig that has been tied into the main tool chain stack.
    """
    __slots__ = ()

    def __init__(self):
        super().__init__(True)

    def compress_table(self, router_table):
        """
        :param UnCompressedMulticastRoutingTable router_table:
        :rtype: list(RTEntry)
        """
        # compress the router entries
        return minimise(list(map(
            RTEntry.from_MulticastRoutingEntry,
            router_table.multicast_routing_entries)))
