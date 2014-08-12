import logging
from pacman.operations.routing_info_allocator_algorithms.\
    basic_routing_info_allocator import BasicRoutingInfoAllocator
from pacman.utilities import reports

logger = logging.getLogger(__name__)


class RoutingInfoAllocator:
    """ Used to obtain routing information from a placed partitioned_graph
    """

    def __init__(self, machine, report_states, graph_mapper,
                 report_folder=None, hostname=None,
                 routing_info_allocator_algorithm=None):
        """
        :param routing_info_allocator_algorithm: The routing info allocator\
                    algorithm.  If not specified, a default algorithm will be\
                    used
        :param hostname: the hostname of the machine
        :param machine: the machine object used to represent the spinnaker\
         machine
        :param graph_mapper: the partitionable_graph to partitioned_graph mapper object
        :param report_folder: the folder used to store reports
        :param report_states: the pacman states for different reports
        :type hostname: str
        :type machine: spinnmachine.machine.Machine
        :type report_states: pacman.utility.report_states.ReportStates
        :type report_folder: str
        :type routing_info_allocator_algorithm:\
:py:class:`pacman.operations.routing_info_allocator_algorithms.abstract_routing_info_allocator_algorithm.AbstractRoutingInfoAllocatorAlgorithm`
        :raise pacman.exceptions.PacmanInvalidParameterException: If\
                    routing_info_allocator_algorithm is not valid
        """
        self._machine = machine
        self._report_folder = report_folder
        self.report_states = report_states
        self._hostname = hostname
        self._machine = machine
        self._graph_mapper = graph_mapper
        self._routing_info_allocator_algorithm = \
            routing_info_allocator_algorithm

        #set up a default placer algorithm if none are specified
        if self._routing_info_allocator_algorithm is None:
            self._routing_info_allocator_algorithm = \
                BasicRoutingInfoAllocator(self._graph_mapper)
        else:
            self._routing_info_allocator_algorithm = \
                routing_info_allocator_algorithm(self._graph_mapper)

    def run(self, partitioned_graph, placements):
        """ Execute the algorithm on the partitioned_graph
        
        :param partitioned_graph: The partitioned_graph to allocate the routing\
         info for
        :type partitioned_graph:
 :py:class:`pacman.model.partitioned_graph.partitioned_graph.PartitionedGraph`
        :param placements: The placements of the subvertices
        :type placements: :py:class:`pacman.model.placements.placements.Placements`
        :return: The routing information
        :rtype: :py:class:`pacman.model.routing_info.routing_info.RoutingInfo`
        :raise pacman.exceptions.PacmanRouteInfoAllocationException: If\
                   something goes wrong with the allocation
        """
        #execute routing info generator
        routing_infos = \
            self._routing_info_allocator_algorithm.allocate_routing_info(
                partitioned_graph, placements)

        #generate reports
        if (self.report_states is not None and
                self.report_states.routing_info_report):
            reports.routing_info_reports(self._report_folder, self._hostname,
                                         partitioned_graph, placements,
                                         routing_infos)

        return routing_infos
