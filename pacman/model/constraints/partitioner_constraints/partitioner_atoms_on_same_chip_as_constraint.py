from pacman.model.constraints.partitioner_constraints\
    .abstract_partitioner_constraint import AbstractPartitionerConstraint


class PartitionerAtomsOnSameChipAsConstraint(
        AbstractPartitionerConstraint):
    """ Indicate that the same ranges of atoms of subvertices of this vertex\
        should be on the same chip as the same ranges of atoms of subvertices\
        of another vertex i.e. not all subvertices have to be on the same chip\
        only those containing the same ranges of atoms.
    """

    def __init__(self, vertex):
        """

        :param vertex:\
            The vertex with which the atoms of this subvertex should be placed
        """
        self._vertex = vertex

    @property
    def vertex(self):
        return self._vertex
