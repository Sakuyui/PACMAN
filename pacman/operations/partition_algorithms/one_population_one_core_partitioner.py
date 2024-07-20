
from pacman.data import PacmanDataView
from spinn_utilities.progress_bar import ProgressBar
from pacman.utilities.utility_objs.chip_counter import ChipCounter
from pacman.data import PacmanDataView


def one_population_one_core_partitioner(config = None):
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
    chip_counter = ChipCounter(n_cores_per_chip = 6)
    vertexes = list(PacmanDataView.iterate_vertices())
    if config != None and "placement" in config:
        vertexes_permutation = config["placement"].get('vertex_permutation', list(range(len(vertexes))))
        PacmanDataView.set_vertex_permutation(vertexes_permutation)
        
    print("all vertexes:" + str(len(vertexes)))
    for index, vertex in enumerate(vertexes):
        print(f"Vertex {index}")
        vertex.splitter.set_one_population_one_core(True)
        print(f"[Before] >> n_chips = ${chip_counter.n_chips}, ${chip_counter.n_core_free}. Vertex Atoms = {vertex.n_atoms}")
        print( vertex.splitter)
        vertex.splitter.create_machine_vertices(chip_counter)
        
        print(f"![After]  >> n_chips = ${chip_counter.n_chips}, ${chip_counter.n_core_free}")

    return chip_counter.n_chips
