from pacman.data import PacmanDataView
from spinn_utilities.progress_bar import ProgressBar
from pacman.utilities.utility_objs.chip_counter import ChipCounter
from pacman.model.graphs.common import Slice


def variance_size_splitter_partitioner(slice_lengths: list):
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
    n_slices = len(slice_lengths)

    print(slice_lengths)
    
    current_maximum_slice_ending = 0
    current_slice_ending = 0
    slice_index = 0
    application_vertex_index = 0
    for vertex in progress.over(PacmanDataView.iterate_vertices()):
        current_maximum_slice_ending += vertex.n_atoms 
        print(vertex.n_atoms)
        print("maximum_slice_ending in current vertex = %d" % current_maximum_slice_ending)
        slice_ending_in_current_application_vertex = 0

        # make slices
        slice_length_for_current_application_vertex = []
        while slice_index < n_slices and current_slice_ending < current_maximum_slice_ending:
            slice_length = slice_lengths[slice_index]
            current_slice_ending += slice_length
            slice_length_for_current_application_vertex.append(slice_length)
            
            slice_ending_in_current_application_vertex += slice_length
            slice_index += 1
        
        print("%d neurons in this vertex, with splitting into slice with lengths %s" % (slice_ending_in_current_application_vertex, slice_length_for_current_application_vertex))
        total_neurons_current_vertex = slice_ending_in_current_application_vertex
        vertex.splitter.create_slices_from_slice_lentghs(slice_length_for_current_application_vertex)
    
    for vertex in progress.over(PacmanDataView.iterate_vertices()):
        vertex.splitter.create_machine_vertices_various_slice_size(chip_counter)

            
        
    return chip_counter.n_chips


'''
def create_machine_vertices(self, chip_counter: ChipCounter):
        app_vertex = self.governed_app_vertex
        app_vertex.synapse_recorder.add_region_offset(
            len(app_vertex.neuron_recorder.get_recordable_variables()))

        max_atoms_per_core = min(
            app_vertex.get_max_atoms_per_core(), app_vertex.n_atoms)

        ring_buffer_shifts = app_vertex.get_ring_buffer_shifts()
        weight_scales = app_vertex.get_weight_scales(ring_buffer_shifts)
        all_syn_block_sz = app_vertex.get_synapses_size(
            max_atoms_per_core)
        structural_sz = app_vertex.get_structural_dynamics_size(
            max_atoms_per_core)
        sdram = self.get_sdram_used_by_atoms(
            max_atoms_per_core, all_syn_block_sz, structural_sz)
        synapse_regions = PopulationMachineVertex.SYNAPSE_REGIONS
        synaptic_matrices = SynapticMatrices(
            app_vertex, synapse_regions, max_atoms_per_core, weight_scales,
            all_syn_block_sz)
        neuron_data = NeuronData(app_vertex)

        for index, vertex_slice in enumerate(self._get_fixed_slices()):
            chip_counter.add_core(sdram)
            label = f"{app_vertex.label}{vertex_slice}"
            machine_vertex = self.create_machine_vertex(
                vertex_slice, sdram, label,
                structural_sz, ring_buffer_shifts, weight_scales,
                index, max_atoms_per_core, synaptic_matrices, neuron_data)
            app_vertex.remember_machine_vertex(machine_vertex)
'''