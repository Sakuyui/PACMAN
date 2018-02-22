from pacman.utilities import file_format_schemas

from spinn_utilities.progress_bar import ProgressBar

import os
import json
import jsonschema
from collections import OrderedDict


class ConvertToFileCoreAllocations(object):
    """ Converts placements to core allocations
    """

    __slots__ = []

    def __call__(self, placements, file_path):
        """

        :param placements:
        :param file_path:
        """

        progress = ProgressBar(len(placements) + 1,
                               "Converting to json core allocations")

        # write basic stuff
        json_dict = OrderedDict()
        json_dict['type'] = "cores"
        vertex_by_id = OrderedDict()

        # process placements
        for placement in progress.over(placements, False):
            self._convert_placement(placement, vertex_by_id, json_dict)

        # dump dict into json file
        with open(file_path, "w") as file_to_write:
            json.dump(json_dict, file_to_write)
        progress.update()

        # validate the schema
        core_allocations_schema_file_path = os.path.join(
            os.path.dirname(file_format_schemas.__file__),
            "core_allocations.json")
        with open(core_allocations_schema_file_path, "r") as file_to_read:
            core_allocations_schema = json.load(file_to_read)
        jsonschema.validate(json_dict, core_allocations_schema)

        # complete progress bar
        progress.end()

        # return the file format
        return file_path, vertex_by_id

    def _convert_placement(self, placement, vertex_map, allocations_dict):
        vertex_id = str(id(placement.vertex))
        vertex_map[vertex_id] = placement.vertex
        allocations_dict[vertex_id] = [placement.p, placement.p + 1]
