from pacman.model.constraints.abstract_partitioner_constraint import AbstractPartitionerConstraint


class PartitionerSameSizeAsVertexConstraint(AbstractPartitionerConstraint):
    """ A constraint which indicates that a vertex must be partitioned so that\
        there are the same number of subvertices and the same number of atoms\
        in each subvertex as those created for another vertex
    """
    
    def __init__(self, vertex):
        """

        :param vertex: The vertex to which the constraint refers
        :type vertex: :py:class:`pacman.model.graph.vertex.Vertex`
        :raise None: does not raise any known exceptions
        """
        pass
    
    def is_partitioner_constraint(self):
        """ Overridden method to indicate that this is a partitioner constraint
        """
        return True

    @property
    def vertex(self):
        """ The vertex to partition with

        :return: the vertex
        :rtype: :py:class:`pacman.model.graph.vertex.Vertex`
        :raise None: does not raise any known exceptions
        """
        pass