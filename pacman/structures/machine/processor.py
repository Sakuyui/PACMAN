__author__ = 'daviess'


class Processor(object):
    """ A processor object included in a SpiNNaker chip """

    def __init__(self, id):
        """

        :param id: id of the processor in the chip
        :type id: int
        :return: a SpiNNaker chip object
        :rtype: pacman.machine.chip.Processor
        :raise None: does not raise any known exceptions
        """
        self._id = id

    @property
    def id(self):
        """
        Returns the id of the processor

        :return: id of the processor
        :rtype: int
        :raise None: does not raise any known exceptions
        """
        return self._id

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "{}".format(self._id)