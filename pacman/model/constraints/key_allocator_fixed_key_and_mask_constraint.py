from pacman.model.constraints.abstract_key_allocator_constraint \
    import AbstractKeyAllocatorConstraint
from pacman.model.routing_info.key_and_mask import KeyAndMask
from pacman import exceptions


class KeyAllocatorFixedKeyAndMaskConstraint(AbstractKeyAllocatorConstraint):
    """ Key allocator constraint that fixes the key and mask of a partitioned\
        edge
    """

    def __init__(self, keys_and_masks, key_list_function=None):
        """

        :param keys_and_masks: The key and mask combinations to fix
        :type keys_and_masks: iterable of\
                    :py:class:`pacman.model.routing_info.key_and_mask.KeyAndMask`
        :param key_list_function: Optional function which will be called to\
                    translate the keys_and_masks list into individual keys.\
                    If missing, the keys will be generated by iterating\
                    through the keys_and_masks list directly.  The function\
                    parameters are:
                    * An iterable of keys and masks
                    * A partitioned edge
                    * Number of keys to generate (may be None)
        :type key_list_function: (iterable of\
                    :py:class:`pacman.model.routing_info.key_and_mask.KeyAndMask`,\
                    :py:class:`pacman.model.partitioned_graph.partitioned_edge.PartitionedEdge`,
                    int)\
                    -> iterable of int
        """
        AbstractKeyAllocatorConstraint.__init__(
            self, "key allocator constraint to fix the keys and masks to"
                  " {}".format(keys_and_masks))

        for keys_and_mask in keys_and_masks:
            if not isinstance(keys_and_mask, KeyAndMask):
                raise exceptions.PacmanConfigurationException(
                    "the keys and masks object contains a object that is not"
                    "a key_and_mask object. Please fix and try again. RTFD")

        self._keys_and_masks = keys_and_masks
        self._key_list_function = key_list_function

    def is_key_allocator_constraint(self):
        return True

    @property
    def keys_and_masks(self):
        """ The keys and masks to be fixed

        :return: An iterable of key and mask combinations
        :rtype: iterable of\
                    :py:class:`pacman.model.routing_info.key_and_mask.KeyAndMask`
        """
        return self._keys_and_masks

    @property
    def key_list_function(self):
        """ A function to call to generate the keys

        :return: A python function, or None if the default function can be used
        """
        return self._key_list_function

    def __repr__(self):
        return "fixed_key_mask_constraint_withkey_masks:{}: and key list " \
               "function {}".format(self.keys_and_masks, self.key_list_function)
