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

    def write_block(self, neo_block, cascade=True):
        """
        Write the provided block to the self.filename

        :param neo_block: Neo block to be written
        :param cascade: True/False save all child objects (default: True)
        :return:
        """
        nix_name = neo_block.name
        nix_type = "neo.block"
        nix_definition = neo_block.description
        nix_file = nix.File.open(self.filename, nix.FileMode.Overwrite)
        nix_block = nix_file.create_block(nix_name, nix_type)
        nix_block.definition = nix_definition
        if cascade:
            for segment in neo_block.segments:
                self.write_segment(segment, neo_block)
        nix_file.close()

    def write_segment(self, segment, parent_block, cascade=True):
        """
        Write the provided segment to the self.filename

        :param segment: Neo segment to be written
        :param parent_block: The parent neo block of the provided segment
        :param cascade: True/False save all child objects (default: True)
        :return:
        """
        nix_name = segment.name
        nix_type = "neo.segment"
        nix_definition = segment.description
        nix_file = nix.File.open(self.filename, nix.FileMode.ReadWrite)
        for nix_block in nix_file.blocks:
            if equals(parent_block, nix_block):
                nix_block = nix_file.blocks[0]
                nix_group = nix_block.create_group(nix_name, nix_type)
                nix_group.definition = nix_definition
                break
        else:
            raise LookupError("Parent block with name '{}' for segment with "
                              "name '{}' does not exist in file '{}'.".format(
                                parent_block.name, segment.name, self.filename))
        nix_file.close()

