from pacman.utilities.utility_objs import ResourceTracker
from pacman.utilities.algorithm_utilities import placer_algorithm_utilities
from pacman.model.placements import Placement, Placements
from pacman.model.constraints.placer_constraints import SameChipAsConstraint

from spinn_utilities.progress_bar import ProgressBar

import random as default_random
import itertools


class RandomPlacer(object):

    def __call__(self, machine_graph, machine):

        # check that the algorithm can handle the constraints
        ResourceTracker.check_constraints(machine_graph.vertices)

        placements = Placements()
        vertices = \
            placer_algorithm_utilities.sort_vertices_by_known_constraints(
                machine_graph.vertices)

        # Iterate over vertices and generate placements
        progress = ProgressBar(machine_graph.n_vertices,
                               "Placing graph vertices")
        resource_tracker = ResourceTracker(machine,
                                           self._generate_random_chips(
                                               machine))
        vertices_on_same_chip = \
            placer_algorithm_utilities.get_same_chip_vertex_groups(
                    machine_graph.vertices)
        all_vertices_placed = set()
        for vertex in progress.over(vertices):
            if vertex not in all_vertices_placed:
                vertices_placed = self._place_vertex(
                    vertex, resource_tracker, machine,
                    # placements_copy,
                    placements,
                    vertices_on_same_chip)
                all_vertices_placed.update(vertices_placed)
        # return placements_copy
        return placements

    def _check_constraints(
            self, vertices, additional_placement_constraints=None):
        placement_constraints = {SameChipAsConstraint}
        if additional_placement_constraints is not None:
            placement_constraints.update(additional_placement_constraints)
        ResourceTracker.check_constraints(
            vertices, additional_placement_constraints=placement_constraints)

    def _generate_random_chips(self, machine, random=default_random,
                               resource_tracker=None):
        """ Generates the list of chips in a random order, with the option \
         to provide a starting point.
        :param resource_tracker:\
            the resource tracker object which contains what resources of the\
            machine have currently been used
        :type resource_tracker: None or \
                :py:class:`ResourceTracker`

        get max x and y dimensions of board
        check if that chip exists
        check if it is full
        attempt to place vertex on that chip
        """

        chips = set(machine)

        for x in range(0, machine.max_chip_x):
            for y in range(0, machine.max_chip_y):
                chips.add((x, y))

        for x, y in chips:
            randomized_chips = random.sample(chips, 1)[0]
            if machine.is_chip_at(x, y):
                yield x, y in randomized_chips

    def _place_vertex(self, vertex, resource_tracker, machine,
                      placements, location):

        vertices = location[vertex]
        #random x and y value within the maximum of the machine
        chips = self._generate_random_chips(machine)

        if len(vertices) > 1:
            assigned_values = \
                resource_tracker.allocate_constrained_group_resources([
                    (vert.resources_required, vert.constraints)
                    for vert in vertices], chips)
            for (x, y, p, _, _), vert in zip(assigned_values, vertices):
                placement = Placement(vert, x, y, p)
                placements.add_placement(placement)
        else:
            (x, y, p, _, _) = resource_tracker.allocate_constrained_resources(
                vertex.resources_required, vertex.constraints, chips)
            placement = Placement(vertex, x, y, p)
            placements.add_placement(placement)

        return vertices
