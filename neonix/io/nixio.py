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

    def write_block(self, block):
        """
        Write the provided block to the self.filename

        :param block: Neo block to be written
        :return:
        """
        nixname = block.name
        nixtype = "neo.block"
        nixdefinition = block.description
        nixfile = nix.File.open(self.filename, nix.FileMode.Overwrite)
        nixblock = nixfile.create_block(nixname, nixtype)
        nixblock.definition = nixdefinition
        nixfile.close()

    def write_segment(self, segment):
        """
        Write the provided segment to the self.filename

        :param segment: Neo segment to be written
        :return:
        """
        nixname = segment.name
        nixtype = "neo.segment"
        nixdefinition = segment.description
        nixfile = nix.File.open(self.filename, nix.FileMode.ReadWrite)
        # NOTE: assuming 1 existing block and adding to it
        nixblock = nixfile.blocks[0]
        nixgroup = nixblock.create_group(nixname, nixtype)
        nixgroup.definition = nixdefinition
        nixfile.close()
