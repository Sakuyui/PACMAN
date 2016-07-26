from pacman.model.graphs.application.abstract_application_vertex \
    import AbstractApplicationVertex

from pacman.model.graphs.abstract_classes.abstract_application_edge \
    import AbstractApplicationEdge
from pacman.model.graphs.simple_graph import SimpleGraph


class ApplicationGraph(SimpleGraph):
    """ An application-level abstraction of a graph
    """

    __slots__ = ()

    def __init__(self):
        SimpleGraph.__init__(
            self, AbstractApplicationVertex, AbstractApplicationEdge)
