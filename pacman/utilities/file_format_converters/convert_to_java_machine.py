from collections import OrderedDict
import json

from pacman.utilities import file_format_schemas
from spinn_utilities.progress_bar import ProgressBar
from spinn_machine.router import Router


class ConvertToJavaMachine(object):
    """ Converter from memory machine to java machine
    """

    __slots__ = []

    def __call__(self, machine, file_path):
        """
        Runs the code to write the machine in Java readable json.

        :param machine: Machine to convert
        :param file_path: Location to write file to. Warning will overwrite!
        """
        progress = ProgressBar(
            (machine.max_chip_x + 1) * (machine.max_chip_y + 1) + 2,
            "Converting to JSON machine")

        for chip in machine.chips:
            if (chip.ip_address is None):
                s_monitors = chip.n_processors - chip.n_user_processors
                s_router_entries = chip.router.n_available_multicast_entries
                s_router_clock_speed = chip.router.clock_speed
                s_sdram = chip.sdram.size
                s_virtual = chip.virtual
                s_tags = chip._tag_ids
                break

        chip = machine.boot_chip
        e_monitors = chip.n_processors - chip.n_user_processors
        e_router_entries = chip.router.n_available_multicast_entries
        e_router_clock_speed = chip.router.clock_speed
        e_sdram = chip.sdram.size
        e_virtual = chip.virtual
        e_tags = chip._tag_ids

        standardResources = OrderedDict()
        standardResources["monitors"] = s_monitors
        standardResources["routerEntries"] = s_router_entries
        standardResources["routerClockSpeed"] = s_router_clock_speed
        standardResources["sdram"] = s_sdram
        standardResources["virtual"] = s_virtual
        standardResources["tags"] = list(s_tags)

        ethernetResources = OrderedDict()
        ethernetResources["monitors"] = e_monitors
        ethernetResources["routerEntries"] = e_router_entries
        ethernetResources["routerClockSpeed"] = e_router_clock_speed
        ethernetResources["sdram"] = e_sdram
        ethernetResources["virtual"] = e_virtual
        ethernetResources["tags"] = list(e_tags)

        # write basic stuff
        json_obj = OrderedDict()
        json_obj["height"] = machine.max_chip_y + 1
        json_obj["width"] = machine.max_chip_x + 1
        json_obj["root"] = list((machine.boot_x, machine.boot_y))
        json_obj["standardResources"] = standardResources
        json_obj["ethernetResources"] = ethernetResources
        json_obj["chips"] = []

        # handle chips
        for chip in machine.chips:
            details = OrderedDict()
            details["cores"] = chip.n_processors
            details["ethernet"] =\
                [chip.nearest_ethernet_x, chip.nearest_ethernet_x]
            dead_links = []
            for link_id in range(0, Router.MAX_LINKS_PER_ROUTER):
                if not chip.router.is_link(link_id):
                    dead_links.append(link_id)
            if len(dead_links) > 0:
                details["deadLinks"] = dead_links

            exceptions = OrderedDict()
            if chip.ip_address is not None:
                details['ipAddress'] = chip.ip_address
                if (chip.n_processors - chip.n_user_processors) != e_monitors:
                    exceptions["monitors"] = \
                        chip.n_processors - chip.n_user_processors
                if (chip.router.n_available_multicast_entries !=
                        e_router_entries):
                    exceptions["routerEntries"] = \
                        chip.router.n_available_multicast_entries
                if (chip.router.clock_speed != e_router_clock_speed):
                    exceptions["routerClockSpeed"] = \
                        chip.router.n_available_multicast_entries
                if chip.sdram.size != e_sdram:
                    exceptions["sdram"] = chip.sdram.size
                if chip.virtual != e_virtual:
                    exceptions["virtual"] = chip.virtual
                if chip.tag_ids != e_tags:
                    details["tags"] = list(chip.tag_ids)
            else:
                if (chip.n_processors - chip.n_user_processors) != s_monitors:
                    exceptions["monitors"] = \
                        chip.n_processors - chip.n_user_processors
                if (chip.router.n_available_multicast_entries !=
                        s_router_entries):
                    exceptions["routerEntries"] = \
                        chip.router.n_available_multicast_entries
                if (chip.router.clock_speed != s_router_clock_speed):
                    exceptions["routerClockSpeed"] = \
                        chip.router.n_available_multicast_entries
                if chip.sdram.size != s_sdram:
                    exceptions["sdram"] = chip.sdram.size
                if chip.virtual != s_virtual:
                    exceptions["virtual"] = chip.virtual
                if chip.tag_ids != s_tags:
                    details["tags"] = list(chip.tag_ids)

            if len(exceptions) > 0:
                json_obj["chips"].append([chip.x, chip.y, details, exceptions])
            else:
                json_obj["chips"].append([chip.x, chip.y, details])
        progress.update()

        # dump to json file
        with open(file_path, "w") as f:
            json.dump(json_obj, f)

        progress.update()

        # validate the schema
        file_format_schemas.validate(json_obj, "jmachine.json")

        # update and complete progress bar
        progress.end()

        return file_path
