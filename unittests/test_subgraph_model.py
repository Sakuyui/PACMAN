import unittest
from pacman.model.subgraph.subvertex import Subvertex
from pacman.model.subgraph.subgraph import Subgraph
from pacman.model.subgraph.subedge import Subedge
from pacman.model.graph.graph import Graph, Vertex, Edge
from pacman.exceptions import PacmanInvalidParameterException
from pacman.exceptions import PacmanAlreadyExistsException
class MyVertex(Vertex):
    def get_resources_used_by_atoms(self, lo_atom, hi_atom,
                                    number_of_machine_time_steps):
        pass

class TestSubgraphModel(unittest.TestCase):
    def test_new_vertex(self):
        vert = MyVertex(10, 'vertex')
        subvert = Subvertex(0,9)

    def test_new_vertex_lo_eq_hi(self):
        vert = MyVertex(10, 'vertex')
        subvert = Subvertex(5,5)

    def test_new_vertex_lo_gt_hi(self):
        with self.assertRaises(PacmanInvalidParameterException):
            subvert = Subvertex(9,0)

    def test_new_empty_subgraph(self):
        Subgraph()

    def test_new_subgraph(self):
        subvertices = list()
        subedges = list()
        for i in range(10):
            subvertices.append(Subvertex(0,4))
        for i in range(5):
            subedges.append(Subedge(subvertices[0],subvertices[(i+1)]))
        for i in range(5,10):
            subedges.append(Subedge(subvertices[5],subvertices[(i+1)%10]))
        subgraph = Subgraph(None, subvertices, subedges)
        outgoing = subgraph.outgoing_subedges_from_subvertex(subvertices[0])
        for i in range(5):
            if subedges[i] not in outgoing:
                raise AssertionError("subedges[" + str(i) +  "] is not in outgoing and should be")
        for i in range(5,10):
            if subedges[i] in outgoing:
                raise AssertionError("subedges[" + str(i) +  "] is in outgoing and shouldn't be")

        incoming = subgraph.incoming_subedges_from_subvertex(subvertices[0])

        if subedges[9] not in incoming:
            raise AssertionError("subedges[" + str(i) +  "] is not in incoming and should be")
        for i in range(9):
            if subedges[i] in incoming:
                raise AssertionError("subedges[" + str(i) +  "] is in incoming and shouldn't be")

        subvertices_from_subgraph = list(subgraph.subvertices)
        subvedges_from_subgraph = list(subgraph.subedges)

    def test_delete_subedge(self):
        subvertices = list()
        subedges = list()
        subvertices.append(Subvertex(0,4))
        subvertices.append(Subvertex(5,9))
        subedges.append(Subedge(subvertices[0],subvertices[(1)]))
        subedges.append(Subedge(subvertices[1],subvertices[(0)]))
        subgraph = Subgraph(None, subvertices, subedges)
        outgoing = subgraph.outgoing_subedges_from_subvertex(subvertices[0])
        for i in range(1):
            if subedges[i] not in outgoing:
                raise AssertionError("subedges[" + str(i) +  "] is not in outgoing and should be")
        subgraph.remove_subedge(subedges[0])
        outgoing = subgraph.outgoing_subedges_from_subvertex(subvertices[0])

        self.assertEqual(len(outgoing),0)

    def test_delete_subedge_2(self):
        subvertices = list()
        subedges = list()
        subvertices.append(Subvertex(0,4))
        subvertices.append(Subvertex(5,9))
        subedges.append(Subedge(subvertices[0],subvertices[(1)]))
        subedges.append(Subedge(subvertices[1],subvertices[(0)]))
        subgraph = Subgraph(None, subvertices, subedges)
        incoming = subgraph.incoming_subedges_from_subvertex(subvertices[0])
        if subedges[1] not in incoming:
            raise AssertionError("subedges[1] is not in outgoing and should be")
        subgraph.remove_subedge(subedges[0])
        incoming = subgraph.outgoing_subedges_from_subvertex(subvertices[0])

        self.assertEqual(len(incoming),0)

    def test_add_duplicate_subvertex(self):
        with self.assertRaises(PacmanAlreadyExistsException):
            subvertices = list()
            subedges = list()
            subv = Subvertex(0,4)
            subvertices.append(subv)
            subvertices.append(Subvertex(5,9))
            subvertices.append(subv)
            subedges.append(Subedge(subvertices[0],subvertices[(1)]))
            subedges.append(Subedge(subvertices[1],subvertices[(0)]))
            subgraph = Subgraph(None, subvertices, subedges)


    def test_get_subvertices_from_vertex(self):
        with self.assertRaises(PacmanInvalidParameterException):
            subvertices = list()
            subedges = list()
            subvertices.append(Subvertex(0,4))
            subvertices.append(Subvertex(5,9))
            subedges.append(Subedge(subvertices[0],subvertices[(1)]))
            subedges.append(Subedge(subvertices[1],subvertices[(0)]))
            subgraph = Subgraph(None, subvertices, subedges)
            subgraph.remove_subedge(Subedge(subvertices[0],subvertices[0]))

    def test_add_duplicate_subedge(self):
        with self.assertRaises(PacmanAlreadyExistsException):
            subvertices = list()
            subedges = list()
            subvertices.append(Subvertex(5,9))
            subvertices.append(Subvertex(5,9))
            sube = Subedge(subvertices[0],subvertices[(1)])
            subedges.append(sube)
            subedges.append(sube)
            subgraph = Subgraph(None, subvertices, subedges)

    def test_add_duplicate_subedge_as_part_of_a_different_edge(self):
        with self.assertRaises(PacmanAlreadyExistsException):
            subvertices = list()
            subedges = list()
            subvertices.append(Subvertex(0,4))
            subvertices.append(Subvertex(5,9))
            subedges.append(Subedge(subvertices[0],subvertices[(1)]))
            sube= Subedge(subvertices[1],subvertices[(0)])
            subedges.append(sube)
            graph = Subgraph(None, subvertices, subedges)
            edge = Edge(MyVertex(10,"pre"),MyVertex(5,"post"))
            graph.add_subedge(sube, edge)

    def test_get_subedges_from_edge(self):
        pass

    def test_get_vertex_from_subvertex(self):
        pass

    def test_get_edge_from_subedge(self):
        pass

    def test_delete_inexistent_subedge(self):
        with self.assertRaises(PacmanInvalidParameterException):
            subvertices = list()
            subedges = list()
            subvertices.append(Subvertex(0,4))
            subvertices.append(Subvertex(5,9))
            subedges.append(Subedge(subvertices[0],subvertices[(1)]))
            subedges.append(Subedge(subvertices[1],subvertices[(0)]))
            subgraph = Subgraph(None, subvertices, subedges)
            subgraph.remove_subedge(Subedge(subvertices[1],subvertices[(0)]))

    def test_add_subedge_with_no_ex2isting_pre_subvertex_in_subgraph(self):
        with self.assertRaises(PacmanInvalidParameterException):
            subvertices = list()
            subedges = list()
            subvertices.append(Subvertex(0,4))
            subvertices.append(Subvertex(5,9))
            subedges.append(Subedge(subvertices[0],subvertices[(1)]))
            subedges.append(Subedge(Subvertex(0,100),subvertices[(0)]))
            subgraph = Subgraph(None, subvertices, subedges)

    def test_add_subedge_with_no_existing_post_subvertex_in_subgraph(self):
        with self.assertRaises(PacmanInvalidParameterException):
            subvertices = list()
            subedges = list()
            subvertices.append(Subvertex(0,4))
            subvertices.append(Subvertex(5,9))
            subedges.append(Subedge(subvertices[0],subvertices[(1)]))
            subedges.append(Subedge(subvertices[(0)],Subvertex(0,100)))
            subgraph = Subgraph(None, subvertices, subedges)


if __name__ == '__main__':
    unittest.main()
