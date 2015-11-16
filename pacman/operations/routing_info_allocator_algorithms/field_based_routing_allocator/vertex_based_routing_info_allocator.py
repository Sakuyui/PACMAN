"""

"""
from pacman.model.constraints.key_allocator_constraints.\
    key_allocator_contiguous_range_constraint import \
    KeyAllocatorContiguousRangeContraint
from pacman.model.constraints.key_allocator_constraints.\
    key_allocator_fixed_field_constraint import \
    KeyAllocatorFixedFieldConstraint
from pacman.model.constraints.key_allocator_constraints.\
    key_allocator_fixed_key_and_mask_constraint import \
    KeyAllocatorFixedKeyAndMaskConstraint
from pacman.model.constraints.key_allocator_constraints.\
    key_allocator_fixed_mask_constraint import \
    KeyAllocatorFixedMaskConstraint
from pacman.model.constraints.key_allocator_constraints.\
    key_allocator_flexi_field_constraint import \
    KeyAllocatorFlexiFieldConstraint
# swiped from rig currently.
from pacman.model.routing_info.routing_info import RoutingInfo
from pacman.model.routing_info.subedge_routing_info import SubedgeRoutingInfo
from pacman.model.routing_tables.multicast_routing_tables import \
    MulticastRoutingTables
from pacman.model.routing_info.base_key_and_mask import BaseKeyAndMask
from pacman.operations.routing_info_allocator_algorithms.\
    field_based_routing_allocator.rigs_bitfield import \
    RigsBitField
from pacman.utilities import utility_calls
from pacman.utilities.algorithm_utilities import \
    routing_info_allocator_utilities
from pacman import exceptions
from pacman.utilities.utility_objs.field import Field
from pacman.utilities.utility_objs.flexi_field import FlexiField, SUPPORTED_TAGS

from enum import Enum
import uuid
import math

NUM_BITS_IN_ROUTING = 31
ROUTING_MASK_BIT = 1
APPLICATION_MASK_BIT = 0
START_OF_ROUTING_KEY_POSITION = 0

TYPES_OF_FIELDS = Enum(
    value="TYPES_OF_FIELDS",
    names=[("FIXED_MASK", 0),
           ("FIXED_KEY", 1),
           ("FIXED_FIELD", 2)])


class VertexBasedRoutingInfoAllocator(object):
    """
    VertexBasedRoutingInfoAllocator
    """

    def __call__(self, partitionable_graph, graph_mapper, subgraph, n_keys_map,
                 routing_paths):

        # ensure groups are stable and correct
        self._determine_groups(subgraph, graph_mapper, partitionable_graph,
                               n_keys_map)

        # define the key space
        bit_field_space = RigsBitField(32)

        # locate however many types of constrants there are
        seen_fields = self._deduce_types(subgraph)

        if len(seen_fields) > 1:
            self._locate_application_field_space(seen_fields)

        field_mapper = dict()
        # handle the application space
        self._handle_application_space(
            bit_field_space, seen_fields, field_mapper, bit_field_space)

        # assgin fields to positions in the space. if shits going to hit the
        # fan, its here
        bit_field_space.assign_fields()

        # create routing_info_allocator
        routing_info = RoutingInfo()
        routing_tables = MulticastRoutingTables()

        # extract keys and masks for each edge from the bitfield
        for partition in subgraph.partitions:
            # get keys and masks
            keys_and_masks = self._discover_keys_and_masks(
                partition, bit_field_space, n_keys_map)

            # update routing info for each edge in the partition
            for edge in partition.edges:
                sub_edge_info = SubedgeRoutingInfo(keys_and_masks, edge)
                routing_info.add_subedge_info(sub_edge_info)

                # update routing tables with entries
                routing_info_allocator_utilities.add_routing_key_entries(
                    routing_paths, sub_edge_info, edge, routing_tables)

        return {'routing_infos': routing_info,
                'routing_tables': routing_tables}

    def _locate_application_field_space(self, seen_fields):
        required_bits = math.ceil(math.log(len(seen_fields), 2))
        if TYPES_OF_FIELDS.FIXED_KEY.name in seen_fields:
            fixed_keys = seen_fields[TYPES_OF_FIELDS.FIXED_KEY.name]
            # use yield and genrator here

        else:
            if TYPES_OF_FIELDS.FIXED_MASK.name in seen_fields:
                fixed_mask_masks = seen_fields[TYPES_OF_FIELDS.FIXED_MASK.name]
                if len(fixed_mask_masks) > 1:
                    keys = list(fixed_mask_masks.keys)
                    first = fixed_mask_masks[keys[0]]
                    searching = True
                    bits = None
                    bit_generator = self._generate_bits_that_satisfy_contraints(
                        first, required_bits)
                    while not searching:
                        searching = True
                        bits = bit_generator.next()
                        value_to_check_for = None
                        for fixed_mask_mask in fixed_mask_masks:
                            fixed_mask_fields = \
                                fixed_mask_masks[fixed_mask_mask]
                            if value_to_check_for is None:
                                value_to_check_for = self._deduce_bit_value(
                                    fixed_mask_fields[0].mask, bits)
                            else:
                                if value_to_check_for != self._deduce_bit_value(
                                        fixed_mask_fields[0].mask, bits):
                                    searching = False
                else:
                    keys = list(fixed_mask_masks.keys())
                    first = fixed_mask_masks[keys[0]]
                    bit_generator = self._generate_bits_that_satisfy_contraints(
                        first, required_bits)
                    bits = bit_generator.next()
                    bit_values = self._deduce_bit_value(first[0].value, bits)


    def _deduce_bit_value(self, mask, bits):
        bit_value = mask >> int(bits[1])
        mask = int(math.pow((bits[0] - bits[1]), 2))
        bit_value &= mask
        return bit_value

    @staticmethod
    def _generate_bits_that_satisfy_contraints(
            fixed_mask_fields, required_bits):
        """
        generator for getting valid bits from the first fixed mask
        :param fixed_mask_fields: the fields from this fixed mask
        :param required_bits: the number of bits required to match the types
        :return:
        """
        routing_fields = list()

        # locate fields valid for generating collections
        for field in fixed_mask_fields:
            if field.tag == SUPPORTED_TAGS.ROUTING:
                routing_fields.append(field)

        # sort fields based on hi
        routing_fields.sort(key=lambda field: field.hi)

        # locate next set of bits to yield to higher function
        for routing_field in routing_fields:
            if routing_field.hi - routing_field.lo >= required_bits:
                current_hi = routing_field.hi
                while (current_hi - required_bits) > routing_field.lo:
                    yield (current_hi, current_hi - required_bits)
                    current_hi -= 1

    def _discover_keys_and_masks(self, partition, bit_field_space, n_keys_map):
        routing_keys_and_masks = list()
        application_keys_and_masks = list()
        fixed_key_constraints = utility_calls.locate_constraints_of_type(
            partition.constraints, KeyAllocatorFixedKeyAndMaskConstraint)
        fixed_mask_constraints = utility_calls.locate_constraints_of_type(
            partition.constraints, KeyAllocatorFixedMaskConstraint)
        fixed_field_constraints = utility_calls.locate_constraints_of_type(
            partition.constraints, KeyAllocatorFixedFieldConstraint)
        flexi_field_constraints = utility_calls.locate_constraints_of_type(
            partition.constraints, KeyAllocatorFlexiFieldConstraint)
        continious_constraints = utility_calls.locate_constraints_of_type(
            partition.constraints, KeyAllocatorContiguousRangeContraint)

        if len(fixed_key_constraints) > 0:
            print "ah"
        elif len(fixed_mask_constraints) > 0:
            print "ah2"
        elif len(fixed_field_constraints) > 0:
            print "ah3"
        elif len(flexi_field_constraints) > 0:
            inputs = dict()
            range_based_flexi_fields = list()
            for field in flexi_field_constraints[0].fields:
                if field.instance_value is not None:
                    inputs[field.id] = field.instance_value
                else:
                    range_based_flexi_fields.append(field)
            if len(range_based_flexi_fields) != 0:
                routing_keys_and_masks, application_keys_and_masks = \
                    self._handle_recursive_range_fields(
                        range_based_flexi_fields, bit_field_space,
                        routing_keys_and_masks, application_keys_and_masks,
                        inputs, 0)
                if len(continious_constraints) != 0:
                    are_continious = self._check_keys_are_continious(
                        application_keys_and_masks)
                    if not are_continious:
                        raise exceptions.PacmanConfigurationException(
                            "These keys returned from the bitfield are"
                            "not continous. Therefore cannot be used")
                    result = list()
                    result.append(routing_keys_and_masks[0])
                return result
            else:
                key = bit_field_space(**inputs).get_value()
                mask = bit_field_space(**inputs).get_mask()
                routing_keys_and_masks.append(BaseKeyAndMask(key, mask))
                return routing_keys_and_masks

        else:
            raise exceptions.PacmanConfigurationException(
                "Cant figure out what to do with a partition with no "
                "constraints. exploded.")

        return routing_keys_and_masks

    @staticmethod
    def _check_keys_are_continious(keys_and_masks):
        last_key = None
        for keys_and_mask in keys_and_masks:
            if last_key is None:
                last_key = keys_and_mask.key
            else:
                if last_key + 1 != keys_and_mask.key:
                    return False
                last_key = keys_and_mask.key
        return True

    def _handle_recursive_range_fields(
            self, range_based_flexi_fields, bit_field_space,
            routing_keys_and_masks, application_keys_and_masks, inputs,
            position):

        for value in range(0,
                           range_based_flexi_fields[position].instance_n_keys):
            inputs[range_based_flexi_fields[position].id] = value
            if position < len(range_based_flexi_fields):
                # routing keys and masks
                routing_key = bit_field_space(**inputs).get_value(
                    tag=SUPPORTED_TAGS.ROUTING.name)
                routing_mask = bit_field_space(**inputs).get_mask(
                    tag=SUPPORTED_TAGS.ROUTING.name)
                routing_keys_and_masks.append(BaseKeyAndMask(routing_key,
                                                             routing_mask))

                # application keys and masks
                application_key = bit_field_space(**inputs).get_value(
                    tag=SUPPORTED_TAGS.APPLICATION.name)
                application_mask = bit_field_space(**inputs).get_mask(
                    tag=SUPPORTED_TAGS.APPLICATION.name)
                application_keys_and_masks.append(BaseKeyAndMask(
                    application_key, application_mask))
            else:
                position += 1
                other_routing_keys_and_masks, \
                    other_application_keys_and_masks = \
                    self._handle_recursive_range_fields(
                        range_based_flexi_fields, bit_field_space,
                        routing_keys_and_masks, application_keys_and_masks,
                        inputs, position)

                routing_keys_and_masks.extend(other_routing_keys_and_masks)
                application_keys_and_masks.extend(
                    other_application_keys_and_masks)
        return routing_keys_and_masks, application_keys_and_masks

    def _handle_application_space(
            self, bit_field_space, fields, field_mapper, top_level_bit_field):

        for field in fields:
            if field == TYPES_OF_FIELDS.FIXED_MASK.name:
                for (position, length) in \
                        fields[TYPES_OF_FIELDS.FIXED_MASK.name]:
                    random_identifer = uuid.uuid4()
                    field_mapper[
                        "FIXED_MASK:{}:{}".format(position, length)] = \
                        random_identifer
                    bit_field_space.add_field(
                        random_identifer, length, position)
            elif field == TYPES_OF_FIELDS.FIXED_FIELD.name:
                for fixed_field in fields[TYPES_OF_FIELDS.FIXED_FIELD.name]:
                    fields_data = self._convert_into_fields(fixed_field.mask)
                    for (position, length) in fields_data:
                        random_identifer = uuid.uuid4()
                        field_mapper[fixed_field] = random_identifer
                        bit_field_space.add_field(
                            random_identifer, length, position)
            elif field == TYPES_OF_FIELDS.FIXED_KEY.name:
                for key_and_mask in fields[TYPES_OF_FIELDS.FIXED_KEY.name]:
                    random_identifer = uuid.uuid4()
                    top_level_bit_field.add_field(
                        random_identifer, NUM_BITS_IN_ROUTING, 0)
                    field_mapper[key_and_mask] = random_identifer
                    # set the value for the field
                    inputs = dict()
                    inputs[random_identifer] = key_and_mask.key
                    top_level_bit_field(**inputs)
            else:
                self._handle_flexi_field_allocation(bit_field_space, field,
                                                    fields)

    def _handle_flexi_field_allocation(self, bit_field_space, field, fields):
        # field must be a flexi field, work accordingly
        example_entry = self._check_entries_are_tag_consistent(fields, field)
        if example_entry.tag is None:
            bit_field_space.add_field(field)
        else:
            bit_field_space.add_field(field, tags=example_entry.tag)

        for field_instance in fields[field]:
            # only carry on if theres more to create
            if len(fields[field][field_instance]) > 0:
                inputs = dict()
                inputs[field] = field_instance.instance_value
                internal_bit_field = bit_field_space(**inputs)
                for nested_field in fields[field][field_instance]:
                    self._handle_flexi_field_allocation(
                        internal_bit_field, nested_field,
                        fields[field][field_instance])
            if field_instance.instance_n_keys is not None:
                for value in range(0, field_instance.instance_n_keys):
                    inputs = dict()
                    inputs[field] = value
                    bit_field_space(**inputs)

    @staticmethod
    def _check_entries_are_tag_consistent(fields, field):
        first = None
        for field_instance in fields[field]:
            if first is None:
                first = field_instance
            elif field_instance.tag != first.tag:
                raise exceptions.PacmanConfigurationException(
                    "Two fields with the same id, but with different tags. "
                    "This is deemed an error and therefore please fix before"
                    "trying again. thanks you")
        return first


    @staticmethod
    def _convert_into_fields(entity):
        results = list()
        expanded_mask = utility_calls.expand_to_bit_array(entity)
        # set up for first location
        detected_change = True
        detected_change_position = NUM_BITS_IN_ROUTING
        detected_last_state = expanded_mask[NUM_BITS_IN_ROUTING]
        # iterate up the key looking for fields
        for position in range(NUM_BITS_IN_ROUTING - 1,
                              START_OF_ROUTING_KEY_POSITION, -1):
            if (expanded_mask[position] != detected_last_state
                    and detected_change):
                detected_change = False
                if detected_last_state == ROUTING_MASK_BIT:
                    results.append(Field(
                        NUM_BITS_IN_ROUTING - detected_change_position,
                        (detected_change_position - position),
                        entity, SUPPORTED_TAGS.ROUTING))
                else:
                    results.append(Field(
                        NUM_BITS_IN_ROUTING - detected_change_position,
                        (detected_change_position - position),
                        entity, SUPPORTED_TAGS.APPLICATION))
                detected_last_state = expanded_mask[position]
                detected_change_position = position - 1
            if (expanded_mask[position] != detected_last_state
                    and not detected_change):
                detected_change = True
                detected_last_state = expanded_mask[position]
                detected_change_position = position
        if detected_change_position != START_OF_ROUTING_KEY_POSITION:
            if detected_last_state == ROUTING_MASK_BIT:
                results.append(
                    Field(NUM_BITS_IN_ROUTING - detected_change_position,
                          NUM_BITS_IN_ROUTING, entity, SUPPORTED_TAGS.ROUTING))
            else:
                results.append(
                    Field(NUM_BITS_IN_ROUTING - detected_change_position,
                          NUM_BITS_IN_ROUTING, entity,
                          SUPPORTED_TAGS.APPLICATION))
        return results

    def _deduce_types(self, subgraph):
        """
        deducing the number of applications required for this key space
        :param subgraph:
        :return:
        """
        seen_fields = dict()
        known_fields = list()
        for partition in subgraph.partitions:
            for constraint in partition.constraints:
                if not isinstance(constraint,
                                  KeyAllocatorContiguousRangeContraint):
                    if isinstance(constraint, KeyAllocatorFlexiFieldConstraint):
                        self._handle_felxi_field(
                            constraint, seen_fields, known_fields)
                    if isinstance(constraint,
                                  KeyAllocatorFixedKeyAndMaskConstraint):
                        if TYPES_OF_FIELDS.FIXED_KEYS.name not in seen_fields:
                            seen_fields[TYPES_OF_FIELDS.FIXED_KEYS.name] = \
                                list()
                        for key_mask in constraint.keys_and_masks:
                            seen_fields[TYPES_OF_FIELDS.FIXED_KEYS.name].\
                                append(key_mask)
                    if isinstance(constraint, KeyAllocatorFixedMaskConstraint):
                        fields = self._convert_into_fields(constraint.mask)
                        if TYPES_OF_FIELDS.FIXED_MASK.name not in seen_fields:
                            seen_fields[TYPES_OF_FIELDS.FIXED_MASK.name] =\
                                dict()
                        for field in fields:
                            if field.value not in seen_fields[
                                    TYPES_OF_FIELDS.FIXED_MASK.name]:
                                # add a new list for this mask type
                                seen_fields[
                                    TYPES_OF_FIELDS.FIXED_MASK.name][
                                    field.value] = list()
                            if field not in seen_fields[
                                    TYPES_OF_FIELDS.FIXED_MASK.name][
                                    field.value]:
                                seen_fields[
                                    TYPES_OF_FIELDS.FIXED_MASK.name][
                                    field.value].append(field)

                    if isinstance(constraint, KeyAllocatorFixedFieldConstraint):
                        if TYPES_OF_FIELDS.FIXED_FIELD not in seen_fields:
                            seen_fields[TYPES_OF_FIELDS.FIXED_FIELD.name] = \
                                list()
                        seen_fields[TYPES_OF_FIELDS.FIXED_FIELD.name].\
                            append(constraint.fields)
        return seen_fields

    @staticmethod
    def _handle_felxi_field(constraint, seen_fields, known_fields):
        # set the level of search
        current_level = seen_fields
        for constraint_field in constraint.fields:
            found_field = None

            # try to locate field in level
            for seen_field in current_level:
                if constraint_field.id == seen_field:
                    found_field = seen_field

            # seen the field before but not at this level. error
            if found_field is None and constraint_field in known_fields:
                raise exceptions.PacmanConfigurationException(
                    "Cant find the field {} in the expected position"
                        .format(constraint_field))

            # if not seen the field before
            if found_field is None and constraint_field.id not in known_fields:
                next_level = dict()
                instance_level = dict()
                current_level[constraint_field.id] = instance_level
                instance_level[constraint_field] = next_level
                known_fields.append(constraint_field.id)
                current_level = next_level

            # if found a field, check if its instance has indeed been put in
            # before
            if found_field is not None:
                instances = current_level[constraint_field.id]
                if constraint_field in instances:
                    current_level = instances[constraint_field]
                elif constraint_field.instance_value not in instances:
                    next_level = dict()
                    instance_level = dict()
                    instances[constraint_field] = instance_level
                    instances[constraint_field] = next_level
                    current_level = next_level

    def _determine_groups(self, subgraph, graph_mapper, partitionable_graph,
                          n_keys_map):

        routing_info_allocator_utilities.check_types_of_edge_constraint(
            subgraph)

        for partition in subgraph.partitions:
            fixed_key_constraints = \
                utility_calls.locate_constraints_of_type(
                    partition.constraints,
                    KeyAllocatorFixedKeyAndMaskConstraint)
            fixed_mask_constraints = \
                utility_calls.locate_constraints_of_type(
                    partition.constraints,
                    KeyAllocatorFixedMaskConstraint)
            fixed_field_constraints = \
                utility_calls.locate_constraints_of_type(
                    partition.constraints,
                    KeyAllocatorFixedFieldConstraint)

            if (len(fixed_key_constraints) == 0
                    and len(fixed_mask_constraints) == 0
                    and len(fixed_field_constraints) == 0):
                self._add_field_constraints(
                    partition, graph_mapper, partitionable_graph, n_keys_map)

    @staticmethod
    def _add_field_constraints(partition, graph_mapper, partitionable_graph,
                               n_keys_map):
        """
        searches though the subgraph adding field constraints for the key
         allocator
        :param partition:
        :param graph_mapper:
        :param partitionable_graph:
        :return:
        """

        fields = list()

        verts = list(partitionable_graph.vertices)
        subvert = partition.edges[0].pre_subvertex
        vertex = graph_mapper.get_vertex_from_subvertex(subvert)
        subverts = list(graph_mapper.get_subvertices_from_vertex(vertex))

        # pop based flexi field
        fields.append(FlexiField(flexi_field_id="Population",
                                 instance_value=verts.index(vertex),
                                 tag=SUPPORTED_TAGS.ROUTING.name))

        # subpop flexi field
        fields.append(FlexiField(
            flexi_field_id="SubPopulation{}".format(verts.index(vertex)),
            tag=SUPPORTED_TAGS.ROUTING.name,
            instance_value=subverts.index(subvert)))

        fields.append(FlexiField(
            flexi_field_id="POP({}:{})Keys"
            .format(verts.index(vertex), subverts.index(subvert)),
            tag=SUPPORTED_TAGS.APPLICATION.name,
            instance_n_keys=n_keys_map.n_keys_for_partitioned_edge(
                partition.edges[0])))

        # add constraint to the subedge
        partition.add_constraint(KeyAllocatorFlexiFieldConstraint(fields))
