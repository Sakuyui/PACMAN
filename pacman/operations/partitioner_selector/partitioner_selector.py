from pacman.operations.partition_algorithms.splitter_partitioner import splitter_partitioner
from pacman.operations.partition_algorithms.variance_size_splitter_partitioner import variance_size_splitter_partitioner
from pacman.operations.partition_algorithms.one_population_one_core_partitioner import one_population_one_core_partitioner
from pacman.operations.partition_algorithms.ga.entities.resource_configuration import ResourceConfiguration
from pacman.data import PacmanDataView

import os

class PartitionerSelector(object):
    def __init__(self, resource_constraint_configuration, optimization_configuration:dict) -> None:
        partitioner_name = optimization_configuration['partitioner']
        self._partitioner_name = partitioner_name
        print(partitioner_name)
        self._resource_constraint_configuration: ResourceConfiguration = resource_constraint_configuration
        if partitioner_name == "splitter":
            self._partitioner = None
            self._n_chips = splitter_partitioner()
        elif partitioner_name == "variant_splitter":
            self._partitioner = None
            self._n_chips = variance_size_splitter_partitioner(optimization_configuration['config']['slice_lengths'])
        elif partitioner_name == "one_population_one_core":
            self._partitioner = None
            self._n_chips = one_population_one_core_partitioner(optimization_configuration['config'])
#         if partitioner_name == "random":
#             self._partitioner = RandomPartitioner(100, resource_constraint_configuration).partitioning()
#             self._n_chips = self._partitioner.get_n_chips()
#         if partitioner_name == "ga":
#             ising_model, samples = \
#                 load_neurodynamics_record(optimization_configuration['config']['neurodynamics_configuration_name'], 
#                                           optimization_configuration['config']['neurodynamics_configuration_base_path'])

#             ga_configuration: GAAlgorithmConfiguration = \
#                 GAAlgorithmConfiguration(
#                     init_solutions_generator = \
#                         GaFixedSlicePopulationPTypeGeneratorOneSliceOneCore([50, 100, 200, 300, 400, 500, 600, 700, 800, 900], resource_constraint_configuration),
#                     solution_representation_strategy='slice',
#                     crossover_individuals_selection_strategy=GaussianWeightInvidualSelection(),
#                     crossover_perform_strategy=GaSliceSliceInfoCombinationUniformCrossover(True),
#                     variation_strategy=GaSliceVariationuUniformGaussian(True, 0.05, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0), 
#                     solution_fixing_strategy=GaSliceRepresenationSolutionSimpleFillingFixing(resource_constraint_configuration, PacmanDataView.get_graph()), 
#                     solution_cost_calculation_strategy=ProfilingSamplingBasedIsingModelCost(ising_model=ising_model, samples=samples),
#                     selection_strategy=GaEliteProbabilisticSelection(8, 3),
#                     log_processing=True,
#                     output_population_all_epoch=True, 
#                     output_final_epoch_population=True,
#                     epochs=10, 
#                     max_individuals_each_epoch=20,
#                     individual_survivals_each_epoch=10, 
#                     base_path_for_output="./ga_algorithm_records/",
#                     initial_solution_count=10
#             )

#             self._partitioner = \
#                 GAPartitioner(
#                     resource_contraints_configuration=resource_constraint_configuration,
#                     max_slice_length=10 ** 9,
#                     solution_file_path=None,
#                     read_solution_from_file=False,
#                     serialize_solution_to_file=True,
#                     ga_algorithm_configuration=ga_configuration).partitioning()

    def get_partitioner_instance(self):
        return self._partitioner
    
    def get_n_chips(self):
        return self._n_chips
