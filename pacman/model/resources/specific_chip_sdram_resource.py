class SpecificChipSDRAMResource(object):
    """ Represents the SDRAm required for this Chip
    """

    __slots__ = [

        # The AbstractSDRAM object to hold the sdram usage
        "_sdram_usage",

        # the chip that has this SDRAM usage
        "_chip"
    ]

    def __init__(self, chip, sdram_usage):
        """

        :param sdram_usage:\
            The amount of SDRAM in bytes needed to be pre-allocated
        :type sdram_usage: AbstractSDRAM
        :param chip: chip of where the SDRAM is to be allocated
        :type chip: SpiNNMachine.chip.Chip
        :raise None: No known exceptions are raised
        """
        self._sdram_usage = sdram_usage
        self._chip = chip

    @property
    def sdram_usage(self):
        return self._sdram_usage

    @property
    def chip(self):
        return self._chip

    def get_value(self):
        return self._chip, self._sdram_usage
