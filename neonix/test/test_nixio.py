# Copyright (c) 2014, German Neuroinformatics Node (G-Node)
#                     Achilleas Koutsou <achilleas.k@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the BSD License. See
# LICENSE file in the root of the Project.

import os
import datetime
import unittest

from neo.core import Block, Segment, RecordingChannelGroup

from neonix.io.nixio import NixIO


class NixIOTest(unittest.TestCase):

    def setUp(self):
        self.filename = "nixio_testfile.hd5"
        self.io = NixIO(self.filename)

    def tearDown(self):
        del self.io
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_block(self):
        neo_block = Block(name="test_block", description="block for testing")
        self.io.write_block(neo_block)
        nix_block = self.io.nix_file.blocks[0]
        self.assertTrue(NixIO._equals(neo_block, nix_block))

    def test_block_cascade(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block, cascade=True)
        nix_block = self.io.nix_file.blocks[0]
        self.assertEqual(nix_block.name, neo_block.name)
        self.assertEqual(nix_block.type, "neo.block")
        self.assertEqual(nix_block.definition, neo_block.description)
        nix_group = nix_block.groups[0]
        self.assertEqual(nix_group.name, neo_segment.name)
        self.assertEqual(nix_group.type, "neo.segment")
        self.assertEqual(nix_group.definition, neo_segment.description)
        self.assertTrue(NixIO._equals(neo_block, nix_block))

    def test_segment(self):
        neo_block = Block(name="test_block", description="block for testing")
        self.io.write_block(neo_block)
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        nix_block = self.io.nix_file.blocks[0]
        self.io.write_segment(neo_segment, neo_block)
        nix_group = nix_block.groups[0]
        self.assertEqual(nix_group.name, neo_segment.name)
        self.assertEqual(nix_group.type, "neo.segment")
        self.assertEqual(nix_group.definition, neo_segment.description)
        self.assertTrue(NixIO._equals(neo_segment, nix_group))

    def test_recording_channel_group(self):
        neo_block = Block(name="test_block", description="block for testing")
        self.io.write_block(neo_block)
        neo_rcg = RecordingChannelGroup(name="test_segment",
                                        description="segment for testing")
        nix_block = self.io.nix_file.blocks[0]
        self.io.write_segment(neo_rcg, neo_block)
        nix_group = nix_block.groups[0]
        self.assertEqual(nix_group.name, neo_rcg.name)
        self.assertEqual(nix_group.type, "neo.segment")
        self.assertEqual(nix_group.definition, neo_rcg.description)
        self.assertTrue(NixIO._equals(neo_rcg, nix_group))

    def test_block_neq(self):
        neo_block = Block(name="test_block_neq",
                          description="block for testing neq")
        self.io.write_block(neo_block)
        nix_block = self.io.nix_file.blocks[0]
        neo_block.name = "foo"  # changing neo block name
        self.assertFalse(NixIO._equals(neo_block, nix_block))

    def test_segment_neq(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment_neq",
                              description="segment for testing neq")
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block, cascade=True)
        nix_block = self.io.nix_file.blocks[0]
        neo_segment.name = "foo"  # changing neo segment (child) name
        self.assertFalse(NixIO._equals(neo_block, nix_block))

    def test_container_len_neq(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block, cascade=True)
        nix_block = self.io.nix_file.blocks[0]
        neo_segment_new = Segment(name="test_segment_2",
                                  description="second segment for testing")
        neo_block.segments.append(neo_segment_new)
        self.assertFalse(NixIO._equals(neo_block, nix_block))

    def test_metadata(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_block.rec_datetime = datetime.datetime(year=2015, month=12, day=18,
                                                   hour=20)
        neo_block.file_datetime = datetime.datetime(year=2016, month=1, day=1,
                                                    hour=15)
        neo_block.file_origin = "test_file_origin"
        self.io.write_block(neo_block, cascade=True)
        nix_block = self.io.nix_file.blocks[0]
        self.assertTrue(NixIO._equals(neo_block, nix_block))
