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
from datetime import datetime

from neo.io.baseio import BaseIO
from neo.core import Block, Segment

try:
    import nix
except ImportError:
    raise ImportError("Failed to import NIX (NIXPY not found). "
                      "The NixIO requires the Python bindings for NIX.")


# NOTE: Relying on the following dictionary breaks down once we have even the
#  slightest bit of deviation from direct mapping. For instance, even though
#  neo.Block.rec_datetime maps directly to nix.Block.created_at, the mapping
#  relies on a conversion between a datetime object and an integer timestamp
attribute_mappings = {"name": "name",
                      "description": "definition"}
container_mappings = {"segments": "groups"}


class NixIO(BaseIO):
    """
    Class for reading and writing NIX files.
    """

    is_readable = False  # for now
    is_writable = True

    supported_objects = [Block, Segment]
    readable_objects = []
    writeable_objects = [Block, Segment]

    name = "NIX"
    extensions = ["h5"]
    mode = "file"

    def __init__(self, filename):
        """
        Initialise IO instance and NIX file.

        :param filename: full path to the file
        :return:
        """
        BaseIO.__init__(self, filename=None)
        self.filename = filename
        if self.filename:
            self.nix_file = nix.File.open(self.filename, nix.FileMode.Overwrite)

    def __del__(self):
        self.nix_file.close()

    def write_block(self, neo_block, cascade=True):
        """
        Write the provided block to the self.filename

        :param neo_block: Neo block to be written
        :param cascade: save all child objects (default: True)
        :return:
        """
        nix_name = neo_block.name
        nix_type = "neo.block"
        nix_definition = neo_block.description
        nix_block = self.nix_file.create_block(nix_name, nix_type)
        nix_block.definition = nix_definition
        if neo_block.rec_datetime:
            # Truncating timestamp to seconds
            nix_block.force_created_at(int(neo_block.rec_datetime.timestamp()))
        if neo_block.file_datetime:
            block_metadata = self._get_or_init_metadata(nix_block)
            # Truncating timestamp to seconds
            block_metadata.create_property(
                    "neo.file_datetime",
                    nix.Value(int(neo_block.file_datetime.timestamp())))
        if neo_block.file_origin:
            block_metadata = self._get_or_init_metadata(nix_block)
            block_metadata.create_property("neo.file_origin",
                                           nix.Value(neo_block.file_origin))
        if cascade:
            for segment in neo_block.segments:
                NixIO.write_segment(segment, nix_block)
            for rcg in neo_block.recordingchannelgroups:
                NixIO.write_rcg(rcg, nix_block)

    @staticmethod
    def write_segment(segment, parent_block):
        """
        Write the provided segment to the NIX file as a child of parent_block.
        The neo.Segment object is added to the nix.Block as a nix.Group object.

        :param segment: Neo segment to be written
        :param parent_block: The parent NIX block
        :return:
        """
        nix_name = segment.name
        nix_type = "neo.segment"
        nix_definition = segment.description
        nix_group = parent_block.create_group(nix_name, nix_type)
        nix_group.definition = nix_definition

    @staticmethod
    def write_rcg(rcg, parent_block):
        """
        Write the provided RecordingChannelGroup (rcg) to the NIX file as a
        child of parent_block. The neo.RecordingChannelGroup is added to the
        nix.Block as a nix.Source object.

        :param rcg: The Neo rcg to be written
        :param parent_block: The parent neo block of the provided rcg
        :return:
        """
        nix_name = rcg.name
        nix_type = "neo.recordingchannelgroup"
        nix_definition = rcg.description
        nix_source = parent_block.create_source(nix_name, nix_type)
        nix_source.definition = nix_definition

    def _get_or_init_metadata(self, nix_obj):
        """
        Creates a metadata Section for the provided NIX object if it doesn't
        have one already. Returns the new or existing metadata section.

        :param nix_obj: The object to which the Section is attached.
        :return: The metadata section of the provided object.
        """
        if nix_obj.metadata is None:
            nix_obj.metadata = self.nix_file.create_section(
                    nix_obj.name, nix_obj.type+".metadata")
        return nix_obj.metadata

    @staticmethod
    def _equals(neo_obj, nix_obj, cascade=True):
        """
        Returns 'true' if the attributes of the neo object (neo_obj) match the
        attributes of the nix object (nix_obj)

        :param neo_obj: a neo object (block, segment, etc.)
        :param nix_obj: a nix object to compare to (block, group, etc.)
        :param cascade: test all child objects for equivalence recursively
                        (default: True)
        :return: true if the attributes and child objects (if cascade=True)
         of the two objects, as defined in the object mapping, are equal.
        """
        if not NixIO._equals_attribs(neo_obj, nix_obj):
            return False
        if cascade:
            return NixIO._equals_child_objects(neo_obj, nix_obj)
        else:
            return True

    @staticmethod
    def _equals_attribs(neo_obj, nix_obj):
        for neo_attr_name, nix_attr_name in attribute_mappings.items():
            neo_attr = getattr(neo_obj, neo_attr_name, None)
            nix_attr = getattr(nix_obj, nix_attr_name, None)
            if neo_attr != nix_attr:
                return False

        if neo_obj.rec_datetime and\
                (int(neo_obj.rec_datetime.timestamp()) != nix_obj.created_at):
            return False

        if neo_obj.file_datetime and\
                (int(neo_obj.file_datetime.timestamp()) !=
                 nix_obj.metadata["neo.file_datetime"]):
            return False

        if neo_obj.file_origin and\
                neo_obj.file_origin != nix_obj.metadata["neo.file_origin"]:
            return False

        return True

    @staticmethod
    def _equals_child_objects(neo_obj, nix_obj):
        for neo_container_name, nix_container_name \
                in container_mappings.items():
            neo_container = getattr(neo_obj, neo_container_name, None)
            nix_container = getattr(nix_obj, nix_container_name, None)
            if not (neo_container is nix_container is None):
                if len(neo_container) != len(nix_container):
                    return False
                for neo_child_obj, nix_child_obj in zip(neo_container,
                                                        nix_container):
                    if not NixIO._equals(neo_child_obj, nix_child_obj):
                        return False
        else:
            return True
