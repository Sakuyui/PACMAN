from pacman.operations.partition_algorithms.basic_partitioner \
    import BasicPartitioner
from pacman.utilities import reports

import logging

logger = logging.getLogger(__name__)


class Partitioner:
    """ Used to partition a graph into a subgraph
    """

    def __init__(self, machine_time_step, no_machine_time_steps,
                 report_states, partition_algorithm, placer_alogrithm=None,
                 report_folder=None, hostname=None):
        """
        :param partition_algorithm: A partitioning algorithm.  If not specified\
                    a default algorithm will be used
        :type partition_algorithm:\
                    :py:class:`pacman.operations.partition_algorithms.abstract_partition_algorithm.AbstractPartitionAlgorithm`
        :raise pacman.exceptions.PacmanInvalidParameterException: If\
                    partition_algorithm is not valid
        """
        self._report_folder = report_folder
        self.report_states = report_states
        self._hostname = hostname
        self._optimal_placer_alogrithum = placer_alogrithm

        #set up partitioner algorithum
        if partition_algorithm is None:
            self._partitoner_algorithum = \
                BasicPartitioner(machine_time_step, no_machine_time_steps)
        else:
            self._partitoner_algorithum = \
                partition_algorithm(machine_time_step, no_machine_time_steps)

        #if the algortihum requires a placer, set up tis placer param
        if hasattr(self._partitoner_algorithum, "set_placer_algorithum"):
            self._partitoner_algorithum.set_placer_algorithum(
                self._optimal_placer_alogrithum)

    def run(self, graph, machine):
        """ Execute the algorithm on the graph, and partition it to fit on\
            the cores of the machine
            
        :param graph: The graph to partition
        :type graph: :py:class:`pacman.model.graph.graph.Graph`
        :param machine: The machine with respect to which to partition the graph
        :type machine: :py:class:`spinn_machine.machine.Machine`
        :return: A subgraph of partitioned vertices and edges from the graph
        and a graph to subgraph mapper object which links the graph to the
        subgraph objects
        :rtype: :py:class:`pacman.model.subgraph.subgraph.Subgraph`
        :raise pacman.exceptions.PacmanPartitionException: If something\
                   goes wrong with the partitioning
        """
        subgraph, graph_to_subgraph_mapper = \
            self._partitoner_algorithum.partition(graph, machine)

        if (self.report_states is not None and
                self.report_states.partitioner_report):
            reports.partitioner_report(self._report_folder, self._hostname,
                                       graph, graph_to_subgraph_mapper)

        return subgraph, graph_to_subgraph_mapper
