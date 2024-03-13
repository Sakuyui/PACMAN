from pacman.operations.partition_algorithms.ga.solution_representations.abst_ga_solution_representation import AbstractGASolutionRepresentation
from pacman.operations.partition_algorithms.ga.crossover_operators.abst_crossover import AbstractGaCrossover
from pacman.operations.partition_algorithms.ga.solution_representations.common_ga_solution_representation import CommonGASolutionRepresentation

from spinn_utilities.overrides import overrides
from typing import Tuple
import random
import numpy as np

class CommonGaCrossoverKPoints(AbstractGaCrossover):
    def __init__(self, k: int, use_ptype=True) -> None:
        super().__init__()
        self._k = k
        self._use_ptype = use_ptype

    @overrides(AbstractGaCrossover._do_crossover)
    def _do_crossover(self, individual1: AbstractGASolutionRepresentation, individual2: AbstractGASolutionRepresentation) -> Tuple[AbstractGaCrossover, AbstractGaCrossover]:
        if not isinstance(individual1, CommonGASolutionRepresentation) or not isinstance(individual2, CommonGASolutionRepresentation):
            raise TypeError
        individual1_rep = individual1.get_ptype_solution_representation() if self._use_ptype else individual1.get_gtype_solution_representation()
        individual2_rep = individual2.get_ptype_solution_representation() if self._use_ptype else individual2.get_gtype_solution_representation()
        single_neuron_encoding_length = individual1.get_single_neuron_encoding_length()

        if (len(individual1_rep) != len(individual2_rep)) or \
            (individual1.get_single_neuron_encoding_length() != individual2.get_single_neuron_encoding_length()) or \
                ((not self._use_ptype) and (len(individual1_rep) % single_neuron_encoding_length != 0)):
            raise ValueError

        neuron_count = (len(individual1_rep) / single_neuron_encoding_length) if self._use_ptype else len(individual1_rep)
        max_cores_per_chip = individual1.get_max_cores_per_chip()
        max_chips = individual1.get_max_chips()
        points = np.sort(random.sample(range(1, neuron_count - 1), k = self._k))
        new_individual1 = bytearray(single_neuron_encoding_length * neuron_count) if self._use_ptype else [0] * neuron_count
        new_individual2 = bytearray(single_neuron_encoding_length * neuron_count) if self._use_ptype else [0] * neuron_count
        parents = [individual1, individual2]
        previous_index = 0
        if not self._use_ptype:
            single_neuron_encoding_length = 1

        for p in points:
            neuron_encoding_begin = previous_index * single_neuron_encoding_length
            neuron_encoding_end = p * single_neuron_encoding_length
            new_individual1_select_parent_id = random.choice([0, 1])
            new_individual1[neuron_encoding_begin:neuron_encoding_end] = \
                parents[new_individual1_select_parent_id][neuron_encoding_begin:neuron_encoding_end]
            new_individual2[neuron_encoding_begin:neuron_encoding_end] = \
                parents[1 - new_individual1_select_parent_id][neuron_encoding_begin:neuron_encoding_end]

        return (CommonGASolutionRepresentation(new_individual1, max_cores_per_chip, max_chips, self._use_ptype), CommonGASolutionRepresentation(new_individual2, max_cores_per_chip, max_chips, self._use_ptype))
    
    def get_k(self):
        return self._k

    def __str__(self):
        return "comm_k_points_crossover"
    


class CommonGaCrossoverUniform(AbstractGaCrossover):
    def __init__(self, k: int, use_ptype=True) -> None:
        super().__init__()
        self._k = k
        self._use_ptype = use_ptype

    @overrides(AbstractGaCrossover._do_crossover)
    def _do_crossover(self, individual1: AbstractGASolutionRepresentation, individual2: AbstractGASolutionRepresentation) -> Tuple[AbstractGaCrossover, AbstractGaCrossover]:
        if not isinstance(individual1, CommonGASolutionRepresentation) or not isinstance(individual2, CommonGASolutionRepresentation):
            raise TypeError
        individual1_rep = individual1.get_ptype_solution_representation() if self._use_ptype else individual1.get_gtype_solution_representation()
        individual2_rep = individual2.get_ptype_solution_representation() if self._use_ptype else individual2.get_gtype_solution_representation()
        single_neuron_encoding_length = individual1.get_single_neuron_encoding_length()

        if (len(individual1_rep) != len(individual2_rep)) or \
            (individual1.get_single_neuron_encoding_length() != individual2.get_single_neuron_encoding_length()) or \
                (not self._use_ptype or (len(individual1_rep) % single_neuron_encoding_length != 0)):
            raise ValueError

        neuron_count = (len(individual1_rep) / single_neuron_encoding_length) if self._use_ptype else len(individual1_rep)
        max_cores_per_chip = individual1.get_max_cores_per_chip()
        max_chips = individual1.get_max_chips()
        new_individual1 = bytearray(single_neuron_encoding_length * neuron_count) if self._use_ptype else [0] * neuron_count
        new_individual2 = bytearray(single_neuron_encoding_length * neuron_count) if self._use_ptype else [0] * neuron_count
        parents = [individual1, individual2]

        if not self._use_ptype:
            single_neuron_encoding_length = 1

        for p in range(0, neuron_count):
            neuron_encoding_begin = p * single_neuron_encoding_length
            neuron_encoding_end = (p + 1) * single_neuron_encoding_length
            new_individual1_select_parent_id = random.choice([0, 1])
            new_individual1[neuron_encoding_begin:neuron_encoding_end] = \
                parents[new_individual1_select_parent_id][neuron_encoding_begin:neuron_encoding_end]
            new_individual2[neuron_encoding_begin:neuron_encoding_end] = \
                parents[1 - new_individual1_select_parent_id][neuron_encoding_begin:neuron_encoding_end]

        return (CommonGASolutionRepresentation(new_individual1, max_cores_per_chip, max_chips, self._use_ptype), CommonGASolutionRepresentation(new_individual2, max_cores_per_chip, max_chips, self._use_ptype))
    
    def get_k(self):
        return self._k

    def __str__(self):
        return "comm_k_points"
    
