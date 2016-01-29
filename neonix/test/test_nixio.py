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

import numpy as np
import quantities as pq

from neo.core import (Block, Segment, RecordingChannelGroup,
                      AnalogSignal, IrregularlySampledSignal)

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
        neo_rcg = RecordingChannelGroup(name="test_rcg",
                                        description="rcg for testing",
                                        channel_indexes=[])
        neo_rcg.coordinates = []
        neo_block.segments.append(neo_segment)
        neo_block.recordingchannelgroups.append(neo_rcg)
        self.io.write_block(neo_block, cascade=True)

        nix_block = self.io.nix_file.blocks[0]
        nix_group = nix_block.groups[0]
        nix_source = nix_block.sources[0]

        # block -> block base attr
        self.assertEqual(nix_block.name, neo_block.name)
        self.assertEqual(nix_block.type, "neo.block")
        self.assertEqual(nix_block.definition, neo_block.description)

        # segment -> group base attr
        self.assertEqual(nix_group.name, neo_segment.name)
        self.assertEqual(nix_group.type, "neo.segment")
        self.assertEqual(nix_group.definition, neo_segment.description)

        # rcg -> source base attr
        self.assertEqual(nix_source.name, neo_rcg.name)
        self.assertEqual(nix_source.type, "neo.recordingchannelgroup")
        self.assertEqual(nix_source.definition, neo_rcg.description)

        # Using _equals
        self.assertTrue(NixIO._equals(neo_segment, nix_group))
        self.assertTrue(NixIO._equals(neo_rcg, nix_source))
        self.assertTrue(NixIO._equals(neo_block, nix_block))

    def test_segment(self):
        neo_block = Block(name="test_block", description="block for testing")
        self.io.write_block(neo_block)
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        neo_block.segments.append(neo_segment)
        nix_block = self.io.nix_file.blocks[0]
        self.io.write_segment(neo_segment, [("block", neo_block.name)])
        nix_group = nix_block.groups[0]
        self.assertEqual(nix_group.name, neo_segment.name)
        self.assertEqual(nix_group.type, "neo.segment")
        self.assertEqual(nix_group.definition, neo_segment.description)
        self.assertTrue(NixIO._equals(neo_segment, nix_group))
        self.assertTrue(NixIO._equals(neo_block, nix_block))

    def test_recording_channel_group(self):
        neo_block = Block(name="test_block", description="block for testing")
        self.io.write_block(neo_block)
        neo_rcg = RecordingChannelGroup(name="test_rcg",
                                        description="rcg for testing",
                                        channel_indexes=[])
        nix_block = self.io.nix_file.blocks[0]
        self.io.write_recordingchannelgroup(neo_rcg, [("block",
                                                       neo_block.name)])
        nix_source = nix_block.sources[0]
        self.assertEqual(nix_source.name, neo_rcg.name)
        self.assertEqual(nix_source.type, "neo.recordingchannelgroup")
        self.assertEqual(nix_source.definition, neo_rcg.description)
        self.assertTrue(NixIO._equals(neo_rcg, nix_source))

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

    def test_full(self):
        neo_block_a = Block(name="full_test_block_1",
                            description="root block one for full test")

        neo_block_b = Block(name="full_test_block_2",
                            description="root block two for full test")
        neo_blocks = [neo_block_a, neo_block_b]
        for blk in neo_blocks:
            for ind in range(3):
                seg = Segment(name="segment_{}".format(ind),
                              description="{} segment {}".format(blk.name, ind))
                blk.segments.append(seg)
                asig_data = np.array([np.linspace(0, ind+1, 1000)*ind,
                                      np.linspace(0, ind+2, 1000)*ind,
                                      np.linspace(0, ind+3, 1000)*ind])*pq.mV
                asignal = AnalogSignal(asig_data, sampling_rate=10*pq.kHz)
                seg.analogsignals.append(asignal)

                isig_times = np.cumsum(np.random.random(300))*pq.ms
                isig_data = np.random.random((300, 1000))*pq.nA
                isignal = IrregularlySampledSignal(isig_times, isig_data)
                seg.irregularlysampledsignals.append(isignal)

        nix_blocks = self.io.write_all_blocks(neo_blocks)
        for nix_block, neo_block in zip(nix_blocks, neo_blocks):
            self.assertTrue(NixIO._equals(nix_block, neo_block))
