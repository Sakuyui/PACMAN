from pacman.model.routing_tables \
    import MulticastRoutingTable, MulticastRoutingTables
from pacman.operations.router_compressors.mundys_router_compressor.\
    routing_table_condenser import MundyRouterCompressor
from pacman.exceptions import PacmanRoutingException
from spinn_machine import MulticastRoutingEntry

from collections import OrderedDict
import unittest

WILDCARD = "*"

def check_route(o_route, compressed):
    for c_route in compressed.multicast_routing_entries:
        if o_route.routing_entry_key == c_route.routing_entry_key:
            if o_route.mask == c_route.mask:
                print "\tsame: ", c_route
                return True
            if c_route.mask & o_route.mask == c_route.mask:
                print "\twider mask: ", c_route
                return True
        xor_route = o_route.routing_entry_key ^ c_route.routing_entry_key
        if xor_route & c_route.mask == 0:
            print "\tmask covers difference: ", c_route
            return True
        #print "\t", c_route
        #print "\t\t", xor_route, xor_route & o_route.mask

    print "DANGER"
    return False

def codify(route, length=4):
    """
    This method discovers all the routing keys covered by this route

    Starts of with the assumption thsat the key is always covered/

    Whenever a mask bit is zero the list of covered keys is doubled to
        include both the key with a aero and a one at that place

    :param route: single routing Entry
    :type route: :py:class:`spinn_machine.MulticastRoutingEntry`
    :param length: length in bits of the key and mask
    ;type length int
    :return: set of routing_keys covered by this route
    """
    mask = route.mask
    routing_entry_key = route.routing_entry_key
    code = ""
    # Check each bit in the mask
    for i in range(length):
        bit_value = 2**i
        # If the mask bit is zero then both zero and one acceptable
        if mask & bit_value == 0:
            # Safety key 1 with mask 0 is an error
            if routing_entry_key & bit_value == 1:
                msg = "Bit {} on the mask:{} is 0 but 1 in the key:{}" \
                      "".format(i, bin(mask), bin(routing_entry_key))
                raise AssertionError(msg)
            code = WILDCARD + code
        else:
            if routing_entry_key & bit_value == 0:
                code = "0" + code
            else:
                code = "1" + code
    return code

def codify_table(table, length=4):
    code_dict = OrderedDict()
    for route in table.multicast_routing_entries:
        code_dict[codify(route)]= route
    return code_dict

"""
def remainder(original, compressed):
    if original == compressed:
        # Same so no remainder
        return []
    if len(original) == 1:
        # Covered by wildcard so no remainder
        if compressed == WILDCARD:
            return []
        # No match so original stays
        return [original]
    if original[0] == compressed[0]:
        for remain in remainder(original[1:], compressed[1:]):
            pass
"""

def covers(o_code, c_code):
    return True


def calc_remainders(o_code, c_code):
    return []


def compare_route(o_route, compressed_dict, o_code=None, start=0):
    if o_code is None:
        o_code = codify(o_route)
    keys = compressed_dict.keys()
    for i in range(start, len(keys)):
        c_code = keys[i]
        print o_code, c_code
        if covers(o_code, c_code):
            c_route = compressed_dict[c_code]
            if o_route.defaultable != c_route.defaultable:
                msg = "Compressed route {} covers orignal route {} but has " \
                      "a different defaulatable value." \
                      "".format(c_route, o_route)
                PacmanRoutingException(msg)
        if o_route.processor_ids != c_route.processor_ids:
            msg = "Compressed route {} covers orignal route {} but has " \
                  "a different processor_ids." \
                  "".format(c_route, o_route)
            PacmanRoutingException(msg)
        if o_route.link_ids != c_route.link_ids:
            msg = "Compressed route {} covers orignal route {} but has " \
                  "a different link_ids." \
                  "".format(c_route, o_route)
            PacmanRoutingException(msg)
        remainders = calc_remainders(o_code, c_code)
        compare_route(o_route, compressed_dict, o_code=o_code, start=i+1)
        return


def compare_table(original, compressed):
    compressed_dict = codify_table(compressed)
    print compressed_dict
    print "-------------"
    for o_route in original.multicast_routing_entries:
        compare_route(o_route, compressed_dict)
    #print type(original.multicast_routing_entries)
    #for o_route in original.multicast_routing_entries:
    #    print o_route
    #    print codify(c_route)
    #    print bin(o_route.routing_entry_key), bin(o_route.mask)
    #    check_route(o_route, compressed)

#           self._routing_entry_key, self._mask, self._defaultable,  self._processor_ids, self._link_ids)

class MyTestCase(unittest.TestCase):

    def test(self):
        """Test minimising a table of the form:

            0000 -> N NE
            0001 -> E
            0101 -> SW
            1000 -> N NE
            1001 -> E
            1110 -> SW
            1100 -> N NE
            0X00 -> S SW

        The result (worked out by hand) should be:

            0000 -> N NE
            0X00 -> S SW
            1X00 -> N NE
            X001 -> E
            X1XX -> SW
        """

        original_tables = MulticastRoutingTables()
        original_table = MulticastRoutingTable(x=0, y=0)
        original_table.add_multicast_routing_entry(
            MulticastRoutingEntry(0b0000, 0b1111, [1, 2], [], False))
        original_table.add_multicast_routing_entry(
            MulticastRoutingEntry(0b0001, 0b1111, [0], [], False))
        original_table.add_multicast_routing_entry(
            MulticastRoutingEntry(0b0101, 0b1111, [4], [], False))
        original_table.add_multicast_routing_entry(
            MulticastRoutingEntry(0b1000, 0b1111, [1, 2], [], False))
        original_table.add_multicast_routing_entry(
            MulticastRoutingEntry(0b1001, 0b1111, [0], [], False))
        original_table.add_multicast_routing_entry(
            MulticastRoutingEntry(0b1110, 0b1111, [4], [], False))
        original_table.add_multicast_routing_entry(
            MulticastRoutingEntry(0b1100, 0b1111, [1, 2], [], False))
        original_table.add_multicast_routing_entry(
            MulticastRoutingEntry(0b0000, 0b1011, [4, 5], [], False))
        original_tables.add_routing_table(original_table)

        mundy_compressor = MundyRouterCompressor()
        compressed_tables = mundy_compressor(original_tables)
        compressed_table = compressed_tables.get_routing_table_for_chip(0, 0)

        # TODO: FIX THIS SO THAT WE TEST THAT THE RESULT IS VALID
        # result_table_expected = MulticastRoutingTable(x=0, y=0)
        # result_table_expected.add_multicast_routing_entry(
        #     MulticastRoutingEntry(0b0000, 0b1111, [1, 2], [], False))
        # result_table_expected.add_multicast_routing_entry(
        #     MulticastRoutingEntry(0b0000, 0b1011, [4, 5], [], False))
        # result_table_expected.add_multicast_routing_entry(
        #     MulticastRoutingEntry(0b1000, 0b1011, [1, 2], [], False))
        # result_table_expected.add_multicast_routing_entry(
        #     MulticastRoutingEntry(0b0001, 0b0111, [0], [], False))
        # result_table_expected.add_multicast_routing_entry(
        #     MulticastRoutingEntry(0b0100, 0b0100, [4], [], False))

        # Minimise as far as possible
        assert compressed_table.number_of_entries == 5
        # assert compressed_table == result_table_expected
        compare_table(original_table, compressed_table)

if __name__ == '__main__':
    unittest.main()
