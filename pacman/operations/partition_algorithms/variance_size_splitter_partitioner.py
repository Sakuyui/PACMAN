
from pacman.data import PacmanDataView
from spinn_utilities.progress_bar import ProgressBar
from pacman.utilities.utility_objs.chip_counter import ChipCounter


def variance_size_splitter_partitioner():
    """
    Call the splitter of each application vertex to create the machine vertices
    needed.

    :return: The number of chips needed to satisfy this partitioning.
    :rtype: int
    :raise PacmanPartitionException:
        If something goes wrong with the partitioning
    """
    progress = ProgressBar(
        PacmanDataView.get_n_vertices(), "Partitioning Graph")

    # Partition one vertex at a time
    chip_counter = ChipCounter()
    graph = PacmanDataView.get_graph()
    vertexes = list(graph.vertices)
    atom_count_each_application_vertex = [vertex.n_atoms for vertex in vertexes]
    
    for vertex in progress.over(PacmanDataView.iterate_vertices()):
        vertex.splitter.create_machine_vertices(chip_counter)

    return chip_counter.n_chips
