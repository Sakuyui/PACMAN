from .abst_ga_solution_representation import AbstractGASolutionRepresentation
from .common_ga_solution_representation import CommonGASolutionRepresentation
from spinn_utilities.overrides import overrides

# PTYPE := List[(slice_neuron_from: int, slice_neuron_to: int, chip_index: int, core_index: int)]

class GASliceSolutionRepresentation(AbstractGASolutionRepresentation):
    SLICE_NEURON_FROM_INDEX = 0
    SLICE_NEURON_TO_INDEX = 1
    CHIP_INDEX = 2
    CORE_INDEX = 3
    
    def __init__(self) -> None:
          super().__init__([], -1, -1)
          

    def __init__(self, slices_end_points, slices_chip_indexes, slices_core_indexes, max_cores_per_chip, max_chips) -> None:
          super().__init__([], max_cores_per_chip, max_chips, False)
          previous_pos = 0
          slice_index = 0
          for endpoint in slices_end_points:
               slice_neuron_from = previous_pos
               slice_neuron_to = endpoint
               chip_index = slices_chip_indexes[slice_index]
               core_index = slices_core_indexes[slice_index]
               slice_index += 1
               self._solution.append((slice_neuron_from, slice_neuron_to, chip_index, core_index))

    def get_slice_neuron_from_in_solution(self, element_index):
         if self._use_ptype:
            return self._solution[element_index][self.SLICE_NEURON_FROM_INDEX]
         raise NotImplementedError
    
    def get_slice_neuron_to_in_solution(self, element_index):
         if self._use_ptype:
            return self._solution[element_index][self.SLICE_NEURON_TO_INDEX]
         raise NotImplementedError

    def get_chip_index_in_solution(self, element_index):
         if self._use_ptype:
            return self._solution[element_index][self.CHIP_INDEX]
         raise NotImplementedError

    def get_core_index_in_solution(self, element_index):
         if self._use_ptype:
            return self._solution[element_index][self.CORE_INDEX]
         raise NotImplementedError

    def set_slice_neuron_from_in_solution(self, element_index, value):
         if self._use_ptype:
            self._solution[element_index][self.SLICE_NEURON_FROM_INDEX] = value
         raise NotImplementedError

    def set_slice_neuron_to_in_solution(self, element_index, value):
         if self._use_ptype:
            self._solution[element_index][self.SLICE_NEURON_TO_INDEX] = value
         raise NotImplementedError

    def set_chip_index_in_solution(self, element_index, value):
         if self._use_ptype:
            self._solution[element_index][self.CHIP_INDEX] = value
         raise NotImplementedError

    def set_core_index_in_solution(self, element_index, value):
         if self._use_ptype:
            self._solution[element_index][self.CORE_INDEX] = value
         raise NotImplementedError

    @overrides(AbstractGASolutionRepresentation._get_gtype_solution_representation)
    def _get_gtype_solution_representation(self) -> bytearray:
        solution = self._solution
        gtype_length = len(solution) * 32 * 4
        gtype_represent = bytearray(gtype_length)
        for i in range(0, len(solution)):
            for j in range(0, 4):
                binary_string_len32 = ('{0:32b}').format(solution[i][j])
                gtype_represent[(i * 4 + j) * 32: (i * 4 + j + 1) * 32] = binary_string_len32
        return gtype_represent
    
    @overrides(AbstractGASolutionRepresentation._get_ptype_solution_representation)
    def _get_ptype_solution_representation(self) -> bytearray:
        ptype_solution_representation = self.get_solution()
        ptype_length = len(ptype_solution_representation)
        solution = []
        slice_info = []
        for neuron_index in range(0, ptype_length / 32):
            slice_info.append(int(ptype_solution_representation[neuron_index * 32, (neuron_index + 1) * 32], 2))
            if(len(slice_info) == 4):
                 solution.append((*slice_info, ))
                 slice_info = []
        return solution

    @overrides(AbstractGASolutionRepresentation.to_common_representation)
    def to_common_representation(self):
        solution = self.get_solution()
        single_neuron_encoding_length = self._single_neuron_encoding_length
        comm_solution = bytearray(single_neuron_encoding_length)
        neuron_index = 0
        for i in range(0, len(solution)):
            slice_info = solution[i]
            slice_neuron_from = slice_info[0]
            slice_neuron_to = slice_info[1]
            chip_index = slice_info[2]
            core_index = slice_info[3]
            write_common_solution_from = slice_neuron_from * single_neuron_encoding_length
            write_common_solution_to = (slice_neuron_to + 1) * single_neuron_encoding_length
            chip_core_represent = chip_index * self._max_cores_per_chip + core_index
            slice_length = slice_neuron_to - slice_neuron_from + 1
            binary_string = ('{0:' + str(single_neuron_encoding_length) + 'b}').format(chip_core_represent) * slice_length

            comm_solution[write_common_solution_from:write_common_solution_to] = binary_string
        return CommonGASolutionRepresentation(comm_solution, single_neuron_encoding_length, self._max_cores_per_chip, self._max_chips)

    @overrides(AbstractGASolutionRepresentation.from_common_representation)
    def from_common_representation(self, solution: CommonGASolutionRepresentation):
        self._solution = []
        solution_in_bytes_representation = solution.get_ptype_solution_representation()
        single_neuron_encoding_length = solution.get_single_neuron_encoding_length()
        bytearray_length = len(solution_in_bytes_representation)
        neuron_count = bytearray_length / single_neuron_encoding_length
        pos = 0
        max_chips = solution.get_max_chips()
        max_cores_per_chip = solution.get_max_cores_per_chip()
        last_chip_index = -1
        last_core_index = -1
        last_neuron_index = -1
        self._max_chips = max_chips
        self._max_cores_per_chip = max_cores_per_chip
        self._single_neuron_encoding_length = solution.get_single_neuron_encoding_length()

        solution_in_bytes_representation.extend('1' * single_neuron_encoding_length)
        
        for neuron_index in range(0, neuron_count + 1):
            nueron_loc_encoding_from = neuron_index * single_neuron_encoding_length
            neuron_loc_encoding_to = (neuron_index + 1) * single_neuron_encoding_length
            neuron_loc_binary_string_rep = solution_in_bytes_representation[nueron_loc_encoding_from: neuron_loc_encoding_to].decode()
            neuron_loc_int_rep = int(neuron_loc_binary_string_rep, 2)
            chip_index = neuron_loc_int_rep / max_cores_per_chip
            core_index = neuron_loc_int_rep % max_cores_per_chip
            if last_chip_index == -1 or last_core_index == -1 or last_neuron_index == -1:
                last_chip_index = chip_index
                last_core_index = core_index
                last_neuron_index = neuron_index
                continue

            if chip_index == last_chip_index and core_index == last_core_index:
                continue
            
            self._solution.append([last_neuron_index, neuron_index - 1, last_chip_index, last_core_index])

            last_neuron_index = neuron_index
            last_chip_index = chip_index
            last_core_index = core_index

        del solution_in_bytes_representation[-single_neuron_encoding_length:]
        
        return self

    def __str__(self):
            return "slice_rep"