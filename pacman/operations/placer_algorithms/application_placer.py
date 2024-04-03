# Copyright (c) 2021 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations
import logging
import os
from typing import Iterable, List, Optional, Set, Tuple

from spinn_utilities.config_holder import get_config_bool, get_config_str
from spinn_utilities.log import FormatAdapter
from spinn_utilities.ordered_set import OrderedSet
from spinn_utilities.progress_bar import ProgressBar

from spinn_machine import Chip

from pacman.data import PacmanDataView
from pacman.model.placements import Placements, Placement
from pacman.model.graphs import AbstractVirtual
from pacman.model.graphs.machine import MachineVertex
from pacman.model.graphs.application import ApplicationVertex
from pacman.exceptions import (
    PacmanPlaceException, PacmanConfigurationException, PacmanTooBigToPlace)

logger = FormatAdapter(logging.getLogger(__name__))


def place_application_graph(system_placements: Placements) -> Placements:
    """
    Perform placement of an application graph on the machine.

    .. note::
        app_graph must have been partitioned

    :param Placements system_placements:
        The placements of cores doing system tasks. This is what we start from.
    :return: Placements for the application. *Includes the system placements.*
    :rtype: Placements
    """
    # Track the placements and space
    placements = Placements(system_placements)

    plan_n_timesteps = PacmanDataView.get_plan_n_timestep()
    spaces = _Spaces(placements, plan_n_timesteps)

    # Go through the application graph by application vertex
    progress = ProgressBar(
        PacmanDataView.get_n_vertices(), "Placing Vertices")
    for app_vertex in progress.over(PacmanDataView.iterate_vertices()):
        spaces.restore_chips()

        # Try placements from the next chip, but try again if fails
        placed = False
        while not placed:
            chips_attempted = list()
            try:
                same_chip_groups = app_vertex.splitter.get_same_chip_groups()
                if not same_chip_groups:
                    placed = True
                    break

                # Start a new space
                try:
                    next_chip_space, space = spaces.get_next_chip_and_space()
                except PacmanPlaceException as e:
                    raise _place_error(
                        placements, system_placements, e,
                        plan_n_timesteps) from e
                
                # next_chip_space hold a chip, and cores that avaliable be used. 
                logger.debug(f"Starting placement from {next_chip_space}")

                placements_to_make: List = list()

                # Go through the groups
                last_chip_space: Optional[_ChipWithSpace] = None
                for vertices, sdram in same_chip_groups:
                    # It need to find out that how slices property in a vertex is used in placement.
                    vertices_to_place = [
                        vertex
                        for vertex in vertices
                        # No need to place virtual vertices
                        if not isinstance(vertex, AbstractVirtual)
                        and not placements.is_vertex_placed(vertex)]
                    actual_sdram = sdram.get_total_sdram(plan_n_timesteps)
                    n_cores = len(vertices_to_place)

                    # If this group has a fixed location, place it there
                    # it seems that all verteces in the `vertices_to_place` 
                    # are belongs to the same group. 
                    if _do_fixed_location(vertices_to_place, actual_sdram,
                                          placements, next_chip_space):
                        continue

                    # Try to find a chip with space; this might result in a
                    # _SpaceExceededException
                    while not next_chip_space.is_space(n_cores, actual_sdram):
                        next_chip_space = spaces.get_next_chip_space(
                            space, last_chip_space)
                        last_chip_space = None

                    # If this worked, store placements to be made
                    last_chip_space = next_chip_space
                    chips_attempted.append(next_chip_space.chip)

                    # Vertices are appended to `placements_to_make` 
                    _store_on_chip(
                        placements_to_make, vertices_to_place, actual_sdram,
                        next_chip_space)

                # Now make the placements having confirmed all can be done
                placements.add_placements(placements_to_make)
                placed = True
                logger.debug(f"Used {chips_attempted}")
            except _SpaceExceededException:
                # This might happen while exploring a space; this may not be
                # fatal since the last space might have just been bound by
                # existing placements, and there might be bigger spaces out
                # there to use
                _check_could_fit(app_vertex, vertices_to_place, actual_sdram)
                logger.debug(f"Failed, saving {chips_attempted}")
                spaces.save_chips(chips_attempted)
                chips_attempted.clear()

    if get_config_bool("Reports", "draw_placements"):
        from .draw_placements import draw_placements as dp
        dp(placements, system_placements)

    return placements

def _place_error(
        placements: Placements, system_placements: Placements,
        exception: Exception,
        plan_n_timesteps: Optional[int]) -> PacmanPlaceException:
    """
    :param Placements placements:
    :param Placements system_placements:
    :param PacmanPlaceException exception:
    :param int plan_n_timesteps:
    :rtype: PacmanPlaceException
    """
    unplaceable = list()
    vertex_count = 0
    n_vertices = 0
    for app_vertex in PacmanDataView.iterate_vertices():
        same_chip_groups = app_vertex.splitter.get_same_chip_groups()
        app_vertex_placed = True
        found_placed_cores = False
        for vertices, _sdram in same_chip_groups:
            if isinstance(vertices[0], AbstractVirtual):
                break
            if placements.is_vertex_placed(vertices[0]):
                found_placed_cores = True
            elif found_placed_cores:
                vertex_count += len(vertices)
                n_vertices = len(same_chip_groups)
                app_vertex_placed = False
                break
            else:
                app_vertex_placed = False
                break
        if not app_vertex_placed:
            unplaceable.append(app_vertex)

    report_file = os.path.join(
        PacmanDataView.get_run_dir_path(), "placements_error.txt")
    with open(report_file, 'w', encoding="utf-8") as f:
        f.write(f"Could not place {len(unplaceable)} of "
                f"{PacmanDataView.get_n_vertices()} application vertices.\n")
        f.write(f"    Could not place {vertex_count} of {n_vertices} in the"
                " last app vertex\n\n")
        for x, y in placements.chips_with_placements:
            first = True
            for placement in placements.placements_on_chip(x, y):
                if system_placements.is_vertex_placed(placement.vertex):
                    continue
                if first:
                    f.write(f"Chip ({x}, {y}):\n")
                    first = False
                f.write(f"    Processor {placement.p}:"
                        f" Vertex {placement.vertex}\n")
            if not first:
                f.write("\n")
        f.write("\n")
        f.write("Not placed:\n")
        for app_vertex in unplaceable:
            f.write(f"Vertex: {app_vertex}\n")
            same_chip_groups = app_vertex.splitter.get_same_chip_groups()
            for vertices, sdram in same_chip_groups:
                f.write(f"    Group of {len(vertices)} vertices uses "
                        f"{sdram.get_total_sdram(plan_n_timesteps)} "
                        "bytes of SDRAM:\n")
                for vertex in vertices:
                    f.write(f"        Vertex {vertex}")
                    if placements.is_vertex_placed(vertex):
                        plce = placements.get_placement_of_vertex(vertex)
                        f.write(f" (placed at {plce.x}, {plce.y}, {plce.p})")
                    f.write("\n")
        f.write("\n")
        f.write("Unused chips:\n")
        machine = PacmanDataView.get_machine()
        for x, y in machine.chip_coordinates:
            n_placed = placements.n_placements_on_chip(x, y)
            system_placed = system_placements.n_placements_on_chip(x, y)
            if n_placed - system_placed == 0:
                n_procs = machine[x, y].n_user_processors
                f.write(f"    {x}, {y} ({n_procs - system_placed}"
                        " free cores)\n")

    if get_config_bool("Reports", "draw_placements_on_error"):
        from .draw_placements import draw_placements as dp
        dp(placements, system_placements)

    return PacmanPlaceException(
        f" {exception}."
        f" Report written to {report_file}.")


def _check_could_fit(
        app_vertex: ApplicationVertex, vertices_to_place: List[MachineVertex],
        sdram: int):
    """
    :param ApplicationVertex app_vertex:
    :param list(MachineVertex) vertices_to_place:
    :param int sdram:
    :raises PacmanTooBigToPlace:
    """
    version = PacmanDataView.get_machine_version()
    max_sdram = (version.max_sdram_per_chip - PacmanDataView.get_monitor_sdram())
    max_cores = (
            version.max_cores_per_chip - version.n_non_user_cores -
            PacmanDataView.get_monitor_cores())
    n_cores = len(vertices_to_place)
    if sdram <= max_sdram and n_cores <= max_cores:
        # should fit somewhere
        return
    message = (
        f"{app_vertex} will not fit on any possible Chip "
        f"the reason is that {vertices_to_place} ")
    if sdram > max_sdram:
        message += f"requires {sdram} bytes but "
        if sdram > version.max_sdram_per_chip:
            message += f"a Chip only has {version.max_sdram_per_chip} bytes "
        else:
            message += f"after monitors only {max_sdram} bytes are available "
        message += "Lowering max_core_per_chip may resolve this."
        raise PacmanTooBigToPlace(message)
    if n_cores > version.max_cores_per_chip:
        message += " is more vertices than the number of cores on a chip."
        raise PacmanTooBigToPlace(message)
    user_cores = version.max_cores_per_chip - version.n_non_user_cores
    if n_cores > user_cores:
        message += (
            f"is more vertices than the user cores ({user_cores}) "
            "available on a Chip")
    else:
        message += (
            f"is more vertices than the {max_cores} cores available on a "
            f"Chip once {PacmanDataView.get_monitor_cores()} "
            "are reserved for monitors")
    raise PacmanTooBigToPlace(message)


class _SpaceExceededException(Exception):
    pass


def _do_fixed_location(
        vertices: list[MachineVertex], sdram: int, placements: Placements,
        next_chip_space: _ChipWithSpace) -> bool:
    """
    :param list(MachineVertex) vertices:
    :param int sdram:
    :param Placements placements:
    :param _ChipWithSpace next_chip_space:
    :rtype: bool
    :raise PacmanConfigurationException:
    """
    for vertex in vertices:
        loc = vertex.get_fixed_location()
        if loc:
            x, y = loc.x, loc.y
            break
    else:
        return False

    machine = PacmanDataView.get_machine()
    chip = machine.get_chip_at(x, y)
    if chip is None:
        raise PacmanConfigurationException(
            f"Constrained to chip {x, y} but no such chip")
    on_chip = placements.placements_on_chip(x, y)
    cores_used = {p.p for p in on_chip}
    cores = set(p.processor_id for p in chip.processors
                if not p.is_monitor) - cores_used
    next_cores = iter(cores)
    for vertex in vertices:
        next_core = None
        fixed = vertex.get_fixed_location()
        if fixed and fixed.p is not None:
            if fixed.p not in next_cores:
                raise PacmanConfigurationException(
                    f"Core {fixed.p} on {x}, {y} not available to "
                    f"place {vertex} on")
            next_core = fixed.p
        else:
            try:
                next_core = next(next_cores)
            except StopIteration:
                # pylint: disable=raise-missing-from
                raise PacmanConfigurationException(
                    f"No more cores available on {x}, {y}: {on_chip}")
        placements.add_placement(Placement(vertex, x, y, next_core))
        if next_chip_space.x == x and next_chip_space.y == y:
            next_chip_space.cores.remove(next_core)
            next_chip_space.use_sdram(sdram)
    return True


def _store_on_chip(
        placements_to_make: List[Placement], vertices: List[MachineVertex],
        sdram: int, next_chip_space: _ChipWithSpace):
    """
    :param list(Placement) placements_to_make:
    :param list(MachineVertex) vertices:
    :param int sdram:
    :param _ChipWithSpace next_chip_space:
    """
    for vertex in vertices:
        core = next_chip_space.use_next_core()
        placements_to_make.append(Placement(
            vertex, next_chip_space.x, next_chip_space.y, core))
    next_chip_space.use_sdram(sdram)


class _Spaces(object):
    __slots__ = ("__machine", "__chips", "__next_chip", "__used_chips",
                 "__system_placements", "__placements", "__plan_n_timesteps",
                 "__last_chip_space", "__saved_chips", "__restored_chips")

    def __init__(
            self, placements: Placements, plan_n_timesteps: Optional[int]):
        """
        :param Placements placements:
        :param int plan_n_timesteps:
        """
        self.__machine = PacmanDataView.get_machine()
        self.__placements = placements
        self.__plan_n_timesteps = plan_n_timesteps
        self.__chips = iter(self.__chip_order())
        self.__next_chip = next(self.__chips)
        self.__used_chips: Set[Chip] = set()
        self.__last_chip_space: Optional[_ChipWithSpace] = None
        self.__saved_chips: OrderedSet[Chip] = OrderedSet()
        self.__restored_chips: OrderedSet[Chip] = OrderedSet()

    def __chip_order(self):
        """
        :param Machine machine:
        :rtype: iterable(Chip)
        """
        s_x, s_y = get_config_str("Mapping", "placer_start_chip").split(",")
        s_x = int(s_x)
        s_y = int(s_y)

        for x in range(self.__machine.width):
            for y in range(self.__machine.height):
                c_x = (x + s_x) % self.__machine.width
                c_y = (y + s_y) % self.__machine.height
                chip = self.__machine.get_chip_at(c_x, c_y)
                if chip:
                    yield chip

    def __cores_and_sdram(self, chip: Chip) -> Tuple[Set[int], int]:
        """
        :param Chip chip:
        :return cores, sdram
        :rtype: tuple(int, int)
        """
        on_chip = self.__placements.placements_on_chip(chip.x, chip.y)
        cores_used = {p.p for p in on_chip}
        sdram_used = sum(
            p.vertex.sdram_required.get_total_sdram(
                self.__plan_n_timesteps) for p in on_chip)
        return cores_used, sdram_used

    def get_next_chip_and_space(self) -> Tuple[_ChipWithSpace, _Space]:
        """
        :rtype: (_ChipWithSpace, _Space)
        """
        try:
            if self.__last_chip_space is None:
                chip = self.__get_next_chip()
                cores_used, sdram_used = self.__cores_and_sdram(chip)
                self.__last_chip_space = _ChipWithSpace(
                    chip, cores_used, sdram_used)
                self.__used_chips.add(chip)

            # Start a new space by finding all the chips that can be reached
            # from the start chip but have not been used
            return (self.__last_chip_space,
                    _Space(self.__last_chip_space.chip))

        except StopIteration:
            raise PacmanPlaceException(  # pylint: disable=raise-missing-from
                f"No more chips to place on; {self.n_chips_used} of "
                f"{self.__machine.n_chips} used")

    def __get_next_chip(self) -> Chip:
        """
        :rtype: Chip
        :raises: StopIteration
        """
        while self.__restored_chips:
            chip = self.__restored_chips.pop(last=False)
            if chip not in self.__used_chips:
                return chip
        while self.__next_chip in self.__used_chips:
            self.__next_chip = next(self.__chips)
        return self.__next_chip

    def get_next_chip_space(
            self, space: _Space,
            last_chip_space: Optional[_ChipWithSpace]) -> _ChipWithSpace:
        """
        :param _Space space:
        :param _ChipWithSpace last_chip_space:
        :rtype: _ChipWithSpace
        :raises _SpaceExceededException:
        """
        # If we are reporting a used chip, update with reachable chips
        if last_chip_space is not None:
            last_chip = last_chip_space.chip
            space.update(self.__usable_from_chip(last_chip))

        # If no space, error
        if not space:
            self.__last_chip_space = None
            raise _SpaceExceededException(
                "No more chips to place on in this space; "
                f"{self.n_chips_used} of {self.__machine.n_chips} used")
        chip = space.pop()
        self.__used_chips.add(chip)
        self.__restored_chips.discard(chip)
        cores_used, sdram_used = self.__cores_and_sdram(chip)
        self.__last_chip_space = _ChipWithSpace(chip, cores_used, sdram_used)
        return self.__last_chip_space

    @property
    def n_chips_used(self) -> int:
        """
        The number of chips used.

        :rtype: int
        """
        return len(self.__used_chips)

    def __usable_from_chip(self, chip: Chip) -> Iterable[Chip]:
        """
        :param Chip chip:
        :rtype set(Chip)
        """
        for link in chip.router.links:
            target = self.__machine[link.destination_x, link.destination_y]
            if target not in self.__used_chips:
                yield target

    def save_chips(self, chips: Iterable[Chip]):
        """
        :param iterable(Chip) chips:
        """
        self.__saved_chips.update(chips)

    def restore_chips(self) -> None:
        for chip in self.__saved_chips:
            self.__used_chips.remove(chip)
            self.__restored_chips.add(chip)
        self.__saved_chips.clear()


class _Space(object):
    __slots__ = ("__same_board_chips", "__remaining_chips",
                 "__board_x", "__board_y", "__first_chip")

    def __init__(self, chip: Chip):
        self.__board_x = chip.nearest_ethernet_x
        self.__board_y = chip.nearest_ethernet_y
        self.__same_board_chips: OrderedSet[Chip] = OrderedSet()
        self.__remaining_chips: OrderedSet[Chip] = OrderedSet()

    def __len__(self) -> int:
        return len(self.__same_board_chips) + len(self.__remaining_chips)

    def __on_same_board(self, chip: Chip) -> bool:
        return (chip.nearest_ethernet_x == self.__board_x and
                chip.nearest_ethernet_y == self.__board_y)

    def pop(self) -> Chip:
        """
        :rtype: Chip
        :raise: StopIteration
        """
        if self.__same_board_chips:
            return self.__same_board_chips.pop(last=False)
        if self.__remaining_chips:
            next_chip = self.__remaining_chips.pop(last=False)
            self.__board_x = next_chip.nearest_ethernet_x
            self.__board_y = next_chip.nearest_ethernet_y
            to_remove = list()
            for chip in self.__remaining_chips:
                if self.__on_same_board(chip):
                    to_remove.append(chip)
                    self.__same_board_chips.add(chip)
            for chip in to_remove:
                self.__remaining_chips.remove(chip)
            return next_chip
        raise StopIteration

    def update(self, chips: Iterable[Chip]):
        """
        :param iterable(Chip) chips:
        """
        for chip in chips:
            if self.__on_same_board(chip):
                self.__same_board_chips.add(chip)
            else:
                self.__remaining_chips.add(chip)


class _ChipWithSpace(object):
    """
    A chip with space for placement.
    """
    __slots__ = ("chip", "cores", "sdram")

    def __init__(
            self, chip: Chip, used_processors: Set[int], used_sdram: int):
        self.chip = chip
        self.cores = set(p.processor_id for p in chip.processors
                         if not p.is_monitor)
        self.cores -= used_processors
        self.sdram = chip.sdram - used_sdram

    @property
    def x(self) -> int:
        return self.chip.x

    @property
    def y(self) -> int:
        return self.chip.y

    def is_space(self, n_cores: int, sdram: int) -> bool:
        return len(self.cores) >= n_cores and self.sdram >= sdram

    def use_sdram(self, sdram: int):
        self.sdram -= sdram

    def use_next_core(self) -> int:
        core = next(iter(self.cores))
        self.cores.remove(core)
        return core

    def __repr__(self):
        return f"({self.x}, {self.y})"
