from pacman.model.routing_tables import (
    MulticastRoutingTable, MulticastRoutingTables)
from pacman.model.routing_tables.multicast_routing_tables import (from_json, to_json)
from spinn_machine import MulticastRoutingEntry
import json

MAX_SUPPORTED_LENGTH = 1023


def intersect(key_a, mask_a, key_b, mask_b):
    """Return if key-mask pairs intersect (i.e., would both match some of the
    same keys).
    For example, the key-mask pairs ``00XX`` and ``001X`` both match the keys
    ``0010`` and ``0011`` (i.e., they do intersect)::
        >>> intersect(0b0000, 0b1100, 0b0010, 0b1110)
        True
    But the key-mask pairs ``00XX`` and ``11XX`` do not match any of the same
    keys (i.e., they do not intersect)::
        >>> intersect(0b0000, 0b1100, 0b1100, 0b1100)
        False
    Parameters
    ----------
    key_a : int
    mask_a : int
        The first key-mask pair
    key_b : int
    mask_b : int
        The second key-mask pair
    Returns
    -------
    bool
        True if the two key-mask pairs intersect otherwise False.
    """
    return (key_a & mask_b) == (key_b & mask_a)


def merge(entry1, entry2):
    any_ones = entry1.routing_entry_key | entry2.routing_entry_key
    all_ones = entry1.routing_entry_key & entry2.routing_entry_key
    all_selected = entry1.mask & entry2.mask

    # Compute the new mask  and key
    any_zeros = ~all_ones
    new_xs = any_ones ^ any_zeros
    mask = all_selected & new_xs  # Combine existing and new Xs
    key = all_ones & mask
    return MulticastRoutingEntry(key, mask, entry1.processor_ids, entry2.link_ids, entry1.defaultable and entry2.defaultable)


def find_merge(entry1, entry2, unchecked):
    m1 = merge(entry1, entry2)
    for check in unchecked:
        if intersect(m1.routing_entry_key, m1.mask, check.routing_entry_key, check.mask):
            return None
    return m1

def compress_by_route(to_check, unchecked):
    unmergable = []
    while len(to_check) > 1:
        entry = to_check.pop()
        for other in to_check:
            merged = find_merge(entry, other, unchecked)
            if merged is not None:
                to_check.remove(other)
                to_check.append(merged)
                break
        if merged is None:
            unmergable.append(entry)
    unmergable.append(to_check.pop())
    return unmergable

def compress_table(router_table):
    compressed_table = MulticastRoutingTable(router_table.x, router_table.y)
    unchecked = []
    spinnaker_routes = set()
    for entry in router_table.multicast_routing_entries:
        unchecked.append(entry)
        spinnaker_routes.add(entry.spinnaker_route)

    for spinnaker_route in spinnaker_routes:
        to_check = []
        for i in range(len(unchecked) - 1, -1, -1):
            entry = unchecked[i]
            if entry.spinnaker_route == spinnaker_route:
                del unchecked[i]
                to_check.append(entry)

        for entry in compress_by_route(to_check, unchecked):
            compressed_table.add_multicast_routing_entry(entry)
            unchecked.append(entry)
    print(router_table.number_of_entries, len(spinnaker_routes), compressed_table.number_of_entries)
    return compressed_table


def compress_tables(router_tables):
    compressed_tables = MulticastRoutingTables()
    for table in router_tables:
        print(table.number_of_entries)
        #if table.number_of_entries < MAX_SUPPORTED_LENGTH:
        #    compressed_table = table
        #else:
        compressed_table = compress_table(table)
        compressed_tables.add_routing_table(compressed_table)

    return compressed_tables


from pacman.operations.algorithm_reports.routing_compression_checker_report \
    import generate_routing_compression_checker_report

if __name__ == '__main__':
    router_tables = from_json("D:\spinnaker\my_spinnaker\malloc_routing_tables.json")
    #router_tables = from_json("small_routing_tables.json")
    compressed = compress_tables(router_tables)
    generate_routing_compression_checker_report("", router_tables, compressed)
    with open("compressed_routing_tables.json", "w") as f:
        json.dump(to_json(compressed), f)

