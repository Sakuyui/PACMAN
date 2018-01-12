from pacman.model.constraints.key_allocator_constraints.\
    share_key_constraint import ShareKeyConstraint
from pacman.model.graphs.common import EdgeTrafficType
from spinn_utilities.progress_bar import ProgressBar

# pacman imports
from pacman.model.constraints.key_allocator_constraints\
    import AbstractKeyAllocatorConstraint
from pacman.model.constraints.key_allocator_constraints\
    import FixedMaskConstraint
from spinn_utilities.log import FormatAdapter
from pacman.model.constraints.key_allocator_constraints \
    import FixedKeyAndMaskConstraint
from pacman.model.constraints.key_allocator_constraints \
    import ContiguousKeyRangeContraint
from pacman.operations.routing_info_allocator_algorithms\
    .malloc_based_routing_allocator.key_field_generator \
    import KeyFieldGenerator
from pacman.model.routing_info \
    import RoutingInfo, BaseKeyAndMask, PartitionRoutingInfo
from pacman.utilities.utility_calls import \
    check_algorithm_can_support_constraints, \
    compress_from_bit_array, expand_to_bit_array
from pacman.utilities.algorithm_utilities import ElementAllocatorAlgorithm
from pacman.utilities.algorithm_utilities import \
    routing_info_allocator_utilities as utilities
from pacman.exceptions \
    import PacmanConfigurationException, PacmanRouteInfoAllocationException

# general imports
import math
import numpy
import logging

logger = FormatAdapter(logging.getLogger(__name__))


class MallocBasedRoutingInfoAllocator(ElementAllocatorAlgorithm):
    """ A Routing Info Allocation Allocator algorithm that keeps track of
        free keys and attempts to allocate them as requested
    """

    __slots__ = []

    def __init__(self):
        ElementAllocatorAlgorithm.__init__(self, 0, 2 ** 32)

    def __call__(self, machine_graph, n_keys_map, graph_mapper=None):
        # check that this algorithm supports the constraints
        check_algorithm_can_support_constraints(
            constrained_vertices=machine_graph.outgoing_edge_partitions,
            supported_constraints=[
                FixedMaskConstraint,
                FixedKeyAndMaskConstraint,
                ContiguousKeyRangeContraint, ShareKeyConstraint],
            abstract_constraint_type=AbstractKeyAllocatorConstraint)

        # verify that no edge has more than 1 of a constraint ,and that
        # constraints are compatible
        utilities.check_types_of_edge_constraint(machine_graph)

        # final keys allocations
        routing_infos = RoutingInfo()

        # Get the edges grouped by those that require the same key
        (fixed_key_groups, share_key_groups, fixed_mask_groups,
         fixed_field_groups, flexi_field_groups,
         continuous_groups, none_continuous_groups) = \
            utilities.get_edge_groups(
                machine_graph, EdgeTrafficType.MULTICAST)

        # Even non-continuous keys will be continuous
        for group in none_continuous_groups:
            continuous_groups.append(group)

        # Go through the groups and allocate keys
        progress = ProgressBar(
            machine_graph.n_outgoing_edge_partitions,
            "Allocating routing keys")

        # allocate the groups that have fixed keys
        for group in progress.over(fixed_key_groups, False):
            self._allocate_fixed_keys(group, routing_infos)

        for group in progress.over(fixed_mask_groups, False):
            self._allocate_fixed_masks(group, n_keys_map, routing_infos)

        for group in progress.over(fixed_field_groups, False):
            self._allocate_fixed_fields(group, n_keys_map, routing_infos)

        if flexi_field_groups:
            raise PacmanConfigurationException(
                "MallocBasedRoutingInfoAllocator does not support FlexiField")

        for group in progress.over(share_key_groups, False):
            self._allocate_share_key(group, routing_infos, n_keys_map)

        for group in continuous_groups:
            self._allocate_continuous_groups(group, routing_infos, n_keys_map)

        progress.end()
        return routing_infos

    def _get_n_keys(self, group, n_keys_map):
        return max(
            n_keys_map.n_keys_for_partition(partition) for partition in group)

    def _allocate_continuous_groups(self, group, routing_infos, n_keys_map):
        keys_and_masks = self._allocate_keys_and_masks(
            None, None, self._get_n_keys(group, n_keys_map))
        for partition in group:
            self._update_routing_objects(
                keys_and_masks, routing_infos, partition)

    def _allocate_share_key(
            self, group, routing_infos, n_keys_map):
        keys_and_masks = self._allocate_keys_and_masks(
            None, None, self._get_n_keys(group, n_keys_map))

        for partition in group:
            # update the pacman data objects
            self._update_routing_objects(keys_and_masks, routing_infos,
                                         partition)

    def _allocate_fixed_keys(self, group, routing_infos):
        # Get any fixed keys and masks from the group and attempt to
        # allocate them
        fixed_key_and_mask_constraint = group.constraint

        fixed_mask = None
        self._allocate_fixed_keys_and_masks(
            fixed_key_and_mask_constraint.keys_and_masks, fixed_mask)

        for partition in group:
            # update the pacman data objects
            self._update_routing_objects(
                fixed_key_and_mask_constraint.keys_and_masks, routing_infos,
                partition)

    def _allocate_fixed_masks(self, group, n_keys_map, routing_infos):

        # get mask and fields if need be
        fixed_mask = group.constraint.mask

        # try to allocate
        keys_and_masks = self._allocate_keys_and_masks(
            fixed_mask, None, self._get_n_keys(group, n_keys_map))

        for partition in group:
            # update the pacman data objects
            self._update_routing_objects(
                keys_and_masks, routing_infos, partition)

    def _allocate_fixed_fields(self, group, n_keys_map, routing_infos):
        fields = group.constraint.fields

        # try to allocate
        keys_and_masks = self._allocate_keys_and_masks(
            None, fields, self._get_n_keys(group, n_keys_map))

        for partition in group:
            # update the pacman data objects
            self._update_routing_objects(
                keys_and_masks, routing_infos, partition)

    @staticmethod
    def _update_routing_objects(
            keys_and_masks, routing_infos, group):
        # Allocate the routing information
        partition_info = PartitionRoutingInfo(keys_and_masks, group)
        routing_infos.add_partition_info(partition_info)

    @staticmethod
    def _get_key_ranges(key, mask):
        """ Get a generator of base_key, n_keys pairs that represent ranges
            allowed by the mask

        :param key: The base key
        :param mask: The mask
        """
        unwrapped_mask = expand_to_bit_array(mask)
        first_zeros = list()
        remaining_zeros = list()
        pos = len(unwrapped_mask) - 1

        # Keep the indices of the first set of zeros
        while pos >= 0 and unwrapped_mask[pos] == 0:
            first_zeros.append(pos)
            pos -= 1

        # Find all the remaining zeros
        while pos >= 0:
            if unwrapped_mask[pos] == 0:
                remaining_zeros.append(pos)
            pos -= 1

        # Loop over 2^len(remaining_zeros) to produce the base key,
        # with n_keys being 2^len(first_zeros)
        n_sets = 2 ** len(remaining_zeros)
        n_keys = 2 ** len(first_zeros)
        if not remaining_zeros:
            yield key, n_keys
            return
        unwrapped_key = expand_to_bit_array(key)
        for value in xrange(n_sets):
            generated_key = numpy.copy(unwrapped_key)
            generated_key[remaining_zeros] = \
                expand_to_bit_array(value)[-len(remaining_zeros):]
            yield compress_from_bit_array(generated_key), n_keys

    @staticmethod
    def _get_possible_masks(n_keys):
        """ Get the possible masks given the number of keys

        :param n_keys: The number of keys to generate a mask for
        """
        # TODO: Generate all the masks. Currently only the obvious mask with
        # the zeros at the bottom is generated but the zeros could actually be
        # anywhere
        n_zeros = int(math.ceil(math.log(n_keys, 2)))
        n_ones = 32 - n_zeros
        return [(((1 << n_ones) - 1) << n_zeros)]

    def _allocate_fixed_keys_and_masks(self, keys_and_masks, fixed_mask):
        """ allocate fixed keys and masks

        :param keys_and_masks: the fixed keys and masks combos
        :param fixed_mask: fixed mask
        :type fixed_mask: None or FixedMask object
        :rtype: None
        """
        # If there are fixed keys and masks, allocate them
        for key_and_mask in keys_and_masks:
            # If there is a fixed mask, check it doesn't clash
            if fixed_mask is not None and fixed_mask != key_and_mask.mask:
                raise PacmanRouteInfoAllocationException(
                    "Cannot meet conflicting constraints")

            # Go through the mask sets and allocate
            for key, n_keys in self._get_key_ranges(
                    key_and_mask.key, key_and_mask.mask):
                self._allocate_elements(key, n_keys)

    def _allocate_keys_and_masks(self, fixed_mask, fields, partition_n_keys):
        # If there isn't a fixed mask, generate a fixed mask based
        # on the number of keys required
        masks_available = [fixed_mask]
        if fixed_mask is None:
            masks_available = self._get_possible_masks(partition_n_keys)

        # For each usable mask, try all of the possible keys and
        # see if a match is possible
        mask_found = None
        key_found = None
        mask = None
        for mask in masks_available:
            logger.debug("Trying mask {} for {} keys",
                         hex(mask), partition_n_keys)

            key_found = None
            key_generator = KeyFieldGenerator(
                mask, fields, self._free_space_tracker)
            for key in key_generator:
                logger.debug("Trying key {}", hex(key))

                # Check if all the key ranges can be allocated
                matched_all = True
                index = 0
                for (base_key, n_keys) in self._get_key_ranges(key, mask):
                    logger.debug("Finding slot for {}, n_keys={}",
                                 hex(base_key), n_keys)
                    index = self._find_slot(base_key, lo=index)
                    logger.debug("Slot for {} is {}", hex(base_key), index)
                    if index is None:
                        matched_all = False
                        break
                    space = self._check_allocation(index, base_key, n_keys)
                    logger.debug("Space for {} is {}", hex(base_key), space)
                    if space is None:
                        matched_all = False
                        break

                if matched_all:
                    logger.debug("Matched key {}", hex(key))
                    key_found = key
                    break

            # If we found a matching key, store the mask that worked
            if key_found is not None:
                logger.debug("Matched mask {}", hex(mask))
                mask_found = mask
                break

        # If we found a working key and mask that can be assigned,
        # Allocate them
        if key_found is not None and mask_found is not None:
            for (base_key, n_keys) in self._get_key_ranges(key_found, mask):
                self._allocate_elements(base_key, n_keys)

            # If we get here, we can assign the keys to the edges
            return [BaseKeyAndMask(base_key=key_found, mask=mask)]

        raise PacmanRouteInfoAllocationException(
            "Could not find space to allocate keys")
