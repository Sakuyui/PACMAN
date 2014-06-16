__author__ = 'daviess'

class Subvertex(object):
    """ a subvertex object """

    def __init__(self, label, vertex, lo_atom, hi_atom, constraints=None):
        """ Create a new vertex
        :param label: The name of the vertex
        :type label: str
        :param vertex: The vertex to which this subvertex refers
        :type vertex: pacman.graph.vertex.Vertex
        :param lo_atom: The id of the first atom in the subvertex with
        reference to the atoms in the vertex
        :type lo_atom: int
        :param hi_atom: The id of the last atom in the subvertex with
        reference to the atoms in the vertex
        :type hi_atom: int
        :param constraints: The constraints for partitioning and placement
        :type constraints: list of Constraint objects
        :return: a Vertex object
        :rtype: pacman.graph.vertex.Vertex
        :raises None: Raises no known exceptions
        """
        pass

    @property
    def label(self):
        """ Get the label of the subvertex
        :return: The name of the subvertex
        :rtype: str
        :raises None: Raises no known exceptions
        """
        pass

    @property
    def n_atoms(self):
        """ Get the number of atoms in the subvertex
        :return: The number of atoms in the subvertex
        :rtype: int
        :raises None: Raises no known exceptions
        """
        pass

    @property
    def lo_atom(self):
        """ Get the id of the first atom in the subvertex
        :return: The id of the first atom in the subvertex
        :rtype: int
        :raises None: Raises no known exceptions
        """
        pass

    @property
    def hi_atom(self):
        """ Get the id of the last atom in the subvertex
        :return: The id of the last atom in the subvertex
        :rtype: int
        :raises None: Raises no known exceptions
        """
        pass

    @property
    def constraints(self):
        """

        """
        pass

    @property
    def vertex(self):
        """
        Returns the vertex object to which the subvertex refers
        :return: The vertex object to which the subvertex refers
        :rtype: pacman.graph.vertex.Vertex
        :raises None: Raises no known exceptions
        """
        pass