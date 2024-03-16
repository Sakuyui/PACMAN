from .ga.solution_representations.abst_ga_solution_representation import AbstractGASolutionRepresentation
from .ga.init_population_generators.abst_init_pop_generator import AbstractGaInitialPopulationGenerator
from .ga.crossover_individuals_selectors.abst_crossover_individuals_selector import AbstractGaCrossoverIndividualSelector
from .ga.crossover_operators.abst_crossover import AbstractGaCrossover
from .ga.variation_operators.abst_variation import AbstractGaVariation
from .ga.solution_fixing_operators.abst_solution_fixing import AbstractGaSolutionFixing
from .ga.cost_caculators.abst_cost_calculator import AbstractGaCostCalculator
from .ga.selection_operators.abst_selection import AbstractGaSelection
from .ga.entities.ga_algorithm_configuration import GAAlgorithmConfiguration
from pacman.model.graphs.application import ApplicationGraph


import numpy as np

class GaLogger(object):
    def log(self, message):
        print(message)

class GaAlgorithm(object):
    def __init__(self, ga_configuration: GAAlgorithmConfiguration) -> None:
        self.init_solutions_common_representation_generator = ga_configuration.init_solutions_common_representation_generator
        self.solution_representation_strategy = ga_configuration.solution_representation_strategy
        self.crossover_individuals_selection_strategy = ga_configuration.crossover_individuals_selection_strategy
        self.crossover_perform_strategy = ga_configuration.crossover_perform_strategy
        self.variation_strategy = ga_configuration.variation_strategy
        self.solution_fixing_strategy = ga_configuration.solution_fixing_strategy
        self.solution_cost_calculation_strategy = ga_configuration.solution_cost_calculation_strategy
        self.selection_strategy = ga_configuration.selection_strategy
        self.log_processing = ga_configuration.log_processing
        self.output_populaton_all_epoch = ga_configuration.output_population_all_epoch
        self.output_final_epoch_population = ga_configuration.output_final_epoch_population
        self.epochs = ga_configuration.epochs
        self.max_individuals_each_epoch = ga_configuration.max_individuals_each_epoch
        self.remains_individuals = ga_configuration.remains_individuals
        self.base_path_for_output = ga_configuration.base_path_for_output
        self.initial_solution_count = ga_configuration.initial_solution_count
        if self.log_processing:
            self.GaLogger = GaLogger()


    def _log(self, message):
        if self.log_processing:
            self.GaLogger.log(message)

    def _out_solutions_of_a_epoch_before_selection(self, epoch, solutions):
        filename = "[%s][%s][%s][%s][%s][%s][%s][%s]epoch-%d.npy" % \
            (self.init_solutions_common_representation_generator,
             self.solution_representation_strategy,
             self.crossover_individuals_selection_strategy,
             self.crossover_perform_strategy,
             self.variation_strategy,
             self.solution_fixing_strategy,
             self.solution_cost_calculation_strategy,
             self.selection_strategy,
             epoch)
        
        data = np.array([solution.get_narray_data() for solution in solutions])
        np.save("%s/%s" % (self.base_path_for_output, filename), data, allow_pickle=True)
    
    def do_GA_algorithm(self, application_graph: ApplicationGraph) -> AbstractGASolutionRepresentation:
        init_solution = self.init_solutions_common_representation_generator.generate_initial_population(self.initial_solution_count, application_graph)
        solutions = init_solution # self.solution_representation_strategy.from_common_representation(init_solution)
        for epoch in range(0, self.epochs):
            self._log("begin epoch %d..." % epoch)
            avaliable_parents_count = len(solutions)
            costs = self.solution_cost_calculation_strategy.calculate(solutions)
            while len(solutions) < self.max_individuals_each_epoch:
                individual1, individual2 = self.crossover_individuals_selection_strategy.do_select_individuals(solutions[:avaliable_parents_count], costs)
                new_individual = self.crossover_perform_strategy.do_crossover(individual1, individual2)
                new_individual = self.variation_strategy.do_variation(new_individual)
                new_individual = self.solution_fixing_strategy.do_solution_fixing(new_individual)
                solutions.append(new_individual)
                self._log("[In Epoch %d] Finish solution %d/%d" % (len(solutions), self.max_individuals_each_epoch))
            self._log("[In Epoch %d] Finish. Begin calculating cost of each individual." % epoch)
            costs.append(self.solution_cost_calculation_strategy.calculate(solutions[avaliable_parents_count:]))
            self._log("[In Epoch %d] Finish. Costs = %s" % str(costs))
            if self.output_populaton_all_epoch:
                self._log("[In Epoch %d] Output solution of current epoch...")
                self._out_solutions_of_a_epoch_before_selection(epoch, solutions)
            self._log("[In Epoch %d] Selection Begin...")
            solutions = self.selection_strategy.select(costs, solutions)
            self._log("[In Epoch %d] Cost after selection: %s" % str(costs))

        costs = self.solution_cost_calculation_strategy.calculate(solutions)
        self._log("Finish GA. Costs = %s" % str(costs))

        return [solution for _, solution in sorted(zip(costs, solutions))][0]