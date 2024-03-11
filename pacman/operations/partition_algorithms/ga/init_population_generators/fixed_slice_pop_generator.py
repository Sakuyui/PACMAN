from pacman.operations.partition_algorithms.ga.init_population_generators.abst_init_pop_generator import AbstractGaInitialPopulationGenerator
from pacman.operations.partition_algorithms.ga.solution_representations.common_ga_solution_representation import CommonGASolutionRepresentation
from pacman.operations.partition_algorithms.ga.solution_representations.slice_representation import GASliceSolutionRepresentation
from pacman.model.graphs.application import ApplicationGraph
from typing import List
from spinn_utilities.overrides import overrides
import numpy as np

class GaFixedSlicePopulationGenerator(AbstractGaInitialPopulationGenerator):
    def __init__(self, population_size, application_graph: ApplicationGraph, fixed_slice_size: List[int], max_cores_per_chip = 18) -> None:
        super().__init__(population_size)
        if(max_cores_per_chip < 0 or fixed_slice_size < 0):
            raise ValueError
        self._application_graph = application_graph
        self._fixed_slice_size = fixed_slice_size
        self._max_core_per_chips = max_cores_per_chip
            

    def _make_solution(self, fix_slice_size):
        ag = self._application_graph
        neuron_count = int(np.sum([vertex.n_atoms for vertex in ag.vertices]))
        max_chips = neuron_count
        max_cores_per_chip = self._max_core_per_chips
        single_neuron_encoding_length = int(np.ceil(np.log2(max_chips * max_cores_per_chip))) * neuron_count
        
        slices_end_points = []
        slices_chip_indexes = []
        slices_core_indexes = []
        slice_index = 0
        current_chip_index = 0
        current_chip_remains_core = self._max_core_per_chips
        for neuron_index in range(0, neuron_count, fix_slice_size):
            slice_neuron_from = neuron_index
            slice_neuron_to = min(slice_neuron_from + fix_slice_size, neuron_count)
            slices_end_points.append(slice_neuron_to)
            if current_chip_remains_core <= 0:
                current_chip_index += 1 
                current_chip_remains_core = self._max_core_per_chips
            slices_chip_indexes.append(current_chip_index)
            slices_core_indexes.append(self._max_core_per_chips - current_chip_remains_core)
            current_chip_remains_core -= 1
            slice_index += 1

        return GASliceSolutionRepresentation(slices_end_points=slices_end_points,
                slices_chip_indexes=slices_chip_indexes, slices_core_indexes=slices_core_indexes, 
                max_cores_per_chip=max_cores_per_chip, max_chips=max_chips, 
                single_neuron_encoding_length=single_neuron_encoding_length)

    @overrides(AbstractGaInitialPopulationGenerator.generate_initial_population)
    def generate_initial_population(self) -> List[CommonGASolutionRepresentation]:
        solutions = []
        for fix_slice_size in self._fixed_slice_size:
            solutions.append(self._make_solution(fix_slice_size))
        return solutions

    def __str__(self):
        return "abst_init_gen"