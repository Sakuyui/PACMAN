from pacman.model.routing_tables.multicast_routing_table\
    import MulticastRoutingTable
from pacman.model.routing_tables.multicast_routing_tables\
    import MulticastRoutingTables
from spinn_machine.multicast_routing_entry import MulticastRoutingEntry

import numpy
from pacman.utilities.utility_objs.progress_bar import ProgressBar


class BasicRouteMerger(object):

    def __call__(self, router_tables):
        tables = MulticastRoutingTables()
        previous_masks = dict()

        progress = ProgressBar(
            len(router_tables.routing_tables) * 2,
            "Compressing Routing Tables")

        # Create all masks without holes
        last_mask = 0
        allowed_masks = [0xFFFFFFFFL - ((2 ** i) - 1) for i in range(33)]

        # Check if all the keys have the same mask, and that none have holes
        all_masks_same = False
        for router_table in router_tables.routing_tables:
            last_mask = None
            for entry in router_table.multicast_routing_entries:
                if entry.mask not in allowed_masks:
                    raise Exception(
                        "Only masks without holes are allowed in tables for"
                        " BasicRouteMerger (disallowed mask={})".format(
                            hex(entry.mask)))
                if last_mask is None:
                    last_mask = entry.mask
                elif last_mask != entry.mask:
                    all_masks_same = False
            if not all_masks_same:
                break

        for router_table in router_tables.routing_tables:
            new_table = self._merge_routes(
                router_table, previous_masks, all_masks_same)
            if len(new_table.multicast_routing_entries) > 1023:
                raise Exception("Could not compress table enough")
            tables.add_routing_table(new_table)
            progress.update()
        progress.end()
        return {'routing_tables': tables}

    def _get_merge_masks(self, mask, previous_masks, all_masks_same):
        if mask in previous_masks:
            return previous_masks[mask]

        last_one = 33 - bin(mask).rfind('1')
        n_bits = 16 - last_one
        merge_masks = None

        if all_masks_same:

            merge_masks = numpy.array(
                sorted(
                    range(0, (1 << n_bits) - 1),
                    key=lambda x: bin(x).count("1")),
                dtype="uint32")
            merge_masks = merge_masks << last_one

        else:
            merge_masks = sorted(
                [0xFFFF - ((2 ** n) - 1) for n in range(n_bits - 1, 17)],
                key=lambda x: bin(x).count("1"))

        # print hex(mask), [hex(m) for m in merge_masks]
        previous_masks[mask] = merge_masks
        return merge_masks

    def _merge_routes(self, router_table, previous_masks, all_masks_same):
        if router_table.x != 0 or router_table.y != 0:
            return router_table
        merged_routes = MulticastRoutingTable(router_table.x, router_table.y)
        keys_merged = set()

        entries = router_table.multicast_routing_entries
        for router_entry in entries:
            if router_entry.routing_entry_key in keys_merged:
                continue

            # print "key =", hex(router_entry.routing_entry_key)

            mask = router_entry.mask
            if mask & 0xFFFF0000 == 0xFFFF0000:
                merge_done = False

                for extra_bits in self._get_merge_masks(
                        mask, previous_masks, all_masks_same):

                    new_mask = 0xFFFF0000 | extra_bits
                    # print "trying mask =", hex(new_mask), hex(extra_bits)

                    masked_key = router_entry.routing_entry_key & new_mask

                    # Check that all the cores on this chip have the same route
                    # as this is the only way we can merge here
                    mergable = True
                    potential_merges = set()
                    for router_entry_2 in entries:

                        masked_key2 = (
                            router_entry_2.routing_entry_key & new_mask)

                        if (masked_key == masked_key2 and (
                                (router_entry_2.mask != mask) or
                                (router_entry_2.routing_entry_key in
                                    keys_merged) or
                                (router_entry.processor_ids !=
                                    router_entry_2.processor_ids) or
                                (router_entry.link_ids !=
                                    router_entry_2.link_ids))):
                            # print(
                            #     "    ", hex(key), "and", hex(key2),
                            #     "have mismatched routes")
                            mergable = False
                            break
                        elif masked_key == masked_key2:
                            # print(
                            #     "    ", hex(key), "and", hex(key2),
                            #     "can be merged")
                            potential_merges.add(router_entry_2)

                    if mergable and len(potential_merges) > 1:
                        # print("Merging", [
                        #     hex(route.routing_entry_key)
                        #     for route in potential_merges], "using mask =",
                        #     hex(new_mask), "and key =", hex(masked_key),
                        #     "and route =", router_entry.processor_ids,
                        #     router_entry.link_ids)

                        # if masked_key in merged_routes:
                        #     raise Exception(
                        #         "Attempting to merge an existing key")
                        merged_routes.add_mutlicast_routing_entry(
                            MulticastRoutingEntry(
                                masked_key, new_mask,
                                router_entry.processor_ids,
                                router_entry.link_ids, defaultable=False))
                        keys_merged.update([
                            route.routing_entry_key
                            for route in potential_merges])
                        merge_done = True
                        break

                if not merge_done:
                    # print "Was not able to merge", hex(key)
                    merged_routes.add_mutlicast_routing_entry(router_entry)
                    keys_merged.add(router_entry.routing_entry_key)
            else:
                merged_routes.add_mutlicast_routing_entry(router_entry)
                keys_merged.add(router_entry.routing_entry_key)
        return merged_routes
