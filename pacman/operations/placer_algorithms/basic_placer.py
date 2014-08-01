from pacman.model.constraints.abstract_placer_constraint import \
    AbstractPlacerConstraint
from pacman.operations.placer_algorithms.abstract_placer_algorithm import\
    AbstractPlacerAlgorithm
from pacman.model.constraints.placer_chip_and_core_constraint \
    import PlacerChipAndCoreConstraint
from pacman.model.constraints.placer_subvertex_same_chip_constraint \
    import PlacerSubvertexSameChipConstraint
from pacman.model.placements.placements import Placements
from pacman.model.placements.placement import Placement
from pacman import exceptions
from pacman.utilities import utility_calls
from pacman.utilities.progress_bar import ProgressBar

import logging
from spinn_machine.sdram import SDRAM

logger = logging.getLogger(__name__)


class BasicPlacer(AbstractPlacerAlgorithm):
    """ An basic algorithm that can place a subgraph onto a machine based off a
    raster behaviour
    """

    def __init__(self, machine, graph):
        """constructor to build a \
        pacman.operations.placer_algorithms.BasicPlacer.BasicPlacer
        :param machine: The machine on which to place the graph
        :type machine: :py:class:`spinn_machine.machine.Machine`
        """
        AbstractPlacerAlgorithm.__init__(self, machine, graph)
        self._supported_constrants.append(PlacerChipAndCoreConstraint)
        self._supported_constrants.append(PlacerSubvertexSameChipConstraint)

    def place(self, subgraph, graph_to_subgraph_mapper):
        """ Place a subgraph so that each subvertex is placed on a core

        :param subgraph: The subgraph to place
        :type subgraph: :py:class:`pacman.model.subgraph.subgraph.Subgraph`
        :param graph_to_subgraph_mapper: the mappings between graph and subgraph
        :type graph_to_subgraph_mapper:
    pacman.model.graph_subgraph_mapper.graph_subgraph_mapper.GraphSubgraphMapper
        :return: A set of placements
        :rtype: :py:class:`pacman.model.placements.placements.Placements`
        :raise pacman.exceptions.PacmanPlaceException: If something\
                   goes wrong with the placement
        """
        #check that the algorithum can handle the constraints
        self._check_can_support_constraints(subgraph)

        placements = Placements()
        ordered_subverts = \
            self.sort_subverts_by_constraint_authority(subgraph.subvertices)

        # Iterate over subvertices and generate placements
        progress_bar = ProgressBar(len(ordered_subverts),
                                   "for placing the subgraph's subvertices")
        for subvertex in ordered_subverts:

            # Create and store a new placement
            placement = self._place_subvertex(subvertex, self._graph,
                                              graph_to_subgraph_mapper,
                                              placements)
            placements.add_placement(placement)
            progress_bar.update()
        progress_bar.end()
        return placements

    def _place_subvertex(self, subvertex, graph, graph_to_subgraph_mapper,
                         placements):
        #get resources of a subvertex
        vertex = graph_to_subgraph_mapper.get_vertex_from_subvertex(subvertex)
        resources = vertex.get_resources_used_by_atoms(
            subvertex.lo_atom, subvertex.hi_atom,
            graph.incoming_edges_to_vertex(vertex))

        placement_constraints = \
            utility_calls.locate_constrants_of_type(subvertex.constraints,
                                                    AbstractPlacerConstraint)
        placement_constraint = None
        if len(placement_constraints) > 1:
            placement_constraint = \
                self.reduce_constraints(placement_constraints, subvertex.label,
                                        placements)
        #if theres a placement constraint, then check out the chip and only that
        #chip
        if placement_constraint is not None:
            return self._deal_with_constraint_placement(placement_constraint,
                                                        subvertex, resources)
        else:
            chips = self._machine.chips
            return self._deal_with_non_constrainted_placement(subvertex,
                                                              resources,
                                                              chips)

    def _deal_with_constraint_placement(self, placement_constraint, subvertex,
                                        subvertex_resources):
        x = placement_constraint.x
        y = placement_constraint.y
        p = placement_constraint.p
        if not self._placement_tracker.has_avilable_cores_left(x, y, p):
            if p is None:
                raise exceptions.PacmanPlaceException(
                    "cannot place subvertex {} in chip {}:{} as there is no"
                    "avilable cores to place subvertexes on"
                    .format(subvertex.label, x, y))
            else:
                raise exceptions.PacmanPlaceException(
                    "cannot place subvertex {} in processor {}:{}:{} as "
                    "it has already been assigned".format(subvertex.label,
                                                          x, y))
        else:
            chip_usage = self._sdram_tracker.get_usage(x, y)
            total_usage_after_assigment =\
                chip_usage + subvertex_resources.sdram.get_value()
            if total_usage_after_assigment <= SDRAM.DEFAULT_SDRAM_BYTES:
                x, y, p = self._placement_tracker.assign_core(x, y, p)
                self._sdram_tracker.add_usage(
                    x, y, subvertex_resources.sdram.get_value())
                placement = Placement(subvertex, x, y, p)
                return placement
            else:
                raise exceptions.PacmanPlaceException(
                    "cannot place subvertex {} on chip {}:{} as there is "
                    "not enough avilable memory".format(subvertex.label, x,
                                                        y))

    def _deal_with_non_constrainted_placement(self, subvertex, resources,
                                              chips_in_a_ordering):
        # Record when a constraint is met at least somewhere to produce a richer
        # error message.
        free_cores_met = False
        free_sdram_met = False
        cpu_speed_met = False
        dtcm_per_proc_met = False
        x = None
        y = None
        p = None
        for chip in chips_in_a_ordering:
            for processor in chip.processors:
                if (processor.processor_id != 0 and
                        self._placement_tracker.has_avilable_cores_left(
                        chip.x, chip.y, processor.processor_id)):
                    #locate avilable sdram
                    avilable_sdram = \
                        chip.sdram.size - \
                        (self._sdram_tracker.get_usage(chip.x, chip.y))
                    free_cores_met = True
                    free_sdram_met |= \
                        avilable_sdram >= resources.sdram.get_value()
                    cpu_speed_met |= (processor.clock_speed >=
                                      resources.cpu.get_value())
                    dtcm_per_proc_met |= (processor.dtcm_avilable >=
                                          resources.dtcm.get_value())

                    if (avilable_sdram >= resources.sdram.get_value()
                        and (processor.clock_speed >=
                             resources.cpu.get_value())
                        and (processor.dtcm_avilable >=
                             resources.dtcm.get_value())):
                        x, y, p = self._placement_tracker.assign_core(
                            chip.x, chip.y, processor.processor_id)
                        self._sdram_tracker.add_usage(
                            x, y, resources.sdram.get_value())
                        placement = Placement(subvertex, x, y, p)
                        return placement

        msg = "Failed to place subvertex {}.".format(subvertex.label)
        if not free_cores_met:
            msg += " No free cores available on any chip."
        elif not (free_sdram_met and cpu_speed_met and dtcm_per_proc_met):
            msg += " No core available with:"
            if not free_sdram_met:
                msg += " {} SDRAM;".format(resources.sdram.get_value())
            if not cpu_speed_met:
                msg += " {} clock ticks;".format(resources.cpu.get_value())
            if not dtcm_per_proc_met:
                msg += " {} DTCM;".format(resources.dtcm.get_value())
            msg = msg.rstrip(";") + "."
        raise exceptions.PacmanPlaceException(msg)
