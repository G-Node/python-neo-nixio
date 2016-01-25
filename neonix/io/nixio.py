# Copyright (c) 2014, German Neuroinformatics Node (G-Node)
#                     Achilleas Koutsou <achilleas.k@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the BSD License. See
# LICENSE file in the root of the Project.

from __future__ import absolute_import

import numpy as np
import quantities as pq

from neo.io.baseio import BaseIO
from neo.core import Block

import nix
# TODO: Check if NIX was imported successfully and throw ImportError if not


common_attribute_mappings = {"name": "name",
                             "description": "definition"}


def equals(neoobj, nixobj):
    """
    Returns 'true' if the attributes of the neo object (neoobj) match the
    attributes of the nix object (nixobj)

    :param neoobj: a neo object (block, segment, etc.)
    :param nixobj: a nix object to compare to (block, group, etc.)
    :return: true if the attributes of the two objects, as defined in the
     object mapping, are identical
    """
    for neoattr, nixattr in common_attribute_mappings.items():
        if getattr(neoobj, neoattr) != getattr(nixobj, nixattr):
            return False
    return True


class NixIO(BaseIO):
    """
    Class for reading and writing NIX files.
    """

    is_readable = False  # for now
    is_writable = True

    supported_objects = [Block]
    readable_objects = []
    writeable_objects = [Block]

    name = "NIX"
    extensions = ["h5"]
    mode = "file"

    def __init__(self, filename=None):
        """
        Initialise IO instance.

        :param filename: full path to the file
        :return:
        """
        BaseIO.__init__(self, filename=filename)

    def write_block(self, neoblock, cascade=True):
        """
        Write the provided block to the self.filename

        :param neoblock: Neo block to be written
        :return:
        """
        nixname = neoblock.name
        nixtype = "neo.block"
        nixdefinition = neoblock.description
        nixfile = nix.File.open(self.filename, nix.FileMode.Overwrite)
        nixblock = nixfile.create_block(nixname, nixtype)
        nixblock.definition = nixdefinition
        if cascade:
            for segment in neoblock.segments:
                nix_group_name = segment.name
                nix_group_type = "neo.segment"
                nix_group_definition = segment.description
                nixgroup = nixblock.create_group(nix_group_name, nix_group_type)
                nixgroup.definition = nix_group_definition
        nixfile.close()

    def write_segment(self, segment, parent_block):
        """
        Write the provided segment to the self.filename

        :param segment: Neo segment to be written
        :param parent_block: The parent neo block of the provided segment
        :return:
        """
        nixname = segment.name
        nixtype = "neo.segment"
        nixdefinition = segment.description
        nixfile = nix.File.open(self.filename, nix.FileMode.ReadWrite)
        for nixblock in nixfile.blocks:
            if equals(parent_block, nixblock):
                nixblock = nixfile.blocks[0]
                nixgroup = nixblock.create_group(nixname, nixtype)
                nixgroup.definition = nixdefinition
                break
        else:
            raise LookupError("Parent block with name '{}' for segment with "
                              "name '{}' does not exist in file '{}'.".format(
                                parent_block.name, segment.name, self.filename))
        nixfile.close()

