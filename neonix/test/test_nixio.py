# Copyright (c) 2014, German Neuroinformatics Node (G-Node)
#                     Achilleas Koutsou <achilleas.k@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the BSD License. See
# LICENSE file in the root of the Project.

import os
from datetime import datetime
import unittest

import numpy as np
import quantities as pq

import nix
from neo.core import (Block, Segment, RecordingChannelGroup, AnalogSignal,
                      IrregularlySampledSignal, Unit, SpikeTrain, Event, Epoch)

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
        nix_block = self.io.write_block(neo_block)
        self.assertEqual(neo_block.name, nix_block.name)
        self.assertEqual(neo_block.description, nix_block.definition)
        self.assertEqual(nix_block.type, "neo.block")

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
        # self.assertTrue(NixIO._equals(neo_segment, nix_group))
        # self.assertTrue(NixIO._equals(neo_rcg, nix_source))
        # self.assertTrue(NixIO._equals(neo_block, nix_block))

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
        self.assertNotEqual(len(neo_block.segments), len(nix_block.groups))

    def test_block_metadata(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_block.rec_datetime = datetime(year=2015, month=12, day=18, hour=20)
        neo_block.file_datetime = datetime(year=2016, month=1, day=1, hour=15)
        neo_block.file_origin = "test_file_origin"
        self.io.write_block(neo_block, cascade=True)
        nix_block = self.io.nix_file.blocks[0]

        self.assertEqual(neo_block.name, nix_block.name)
        self.assertEqual(neo_block.description, nix_block.definition)
        self.assertEqual(neo_block.file_origin,
                         nix_block.metadata["file_origin"])
        self.assertEqual(neo_block.file_datetime,
                         datetime.fromtimestamp(
                             nix_block.metadata["file_datetime"]))
        self.assertEqual(neo_block.rec_datetime,
                         datetime.fromtimestamp(nix_block.created_at))

    def test_all(self):
        # Test writing of all objects based on examples from the neo docs
        # api_reference.html

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
                asig_data = np.array([np.linspace(0, ind+1, 1000)*(ind+1),
                                      np.linspace(0, ind+2, 1000)*(ind+1),
                                      np.linspace(0, ind+3, 1000)*(ind+1)]
                                     ).transpose()*pq.mV
                asignal = AnalogSignal(asig_data,
                                       t_start=0*pq.s,
                                       sampling_rate=10*pq.kHz)
                seg.analogsignals.append(asignal)

                isig_times = np.cumsum(np.random.random(300))*pq.ms
                isig_data = np.random.random((300, 10))*pq.nA
                isignal = IrregularlySampledSignal(isig_times, isig_data)
                seg.irregularlysampledsignals.append(isignal)

        seg_train = SpikeTrain(times=[0.01, 0.1, 0.93], units="sec", t_stop=1)
        neo_blocks[0].segments[0].spiketrains.append(seg_train)

        # group 3 channels from the analog signal in the first segment of the
        # first block
        rcg_a = RecordingChannelGroup(
            name="RCG_1",
            channel_names=np.array(["ch1", "ch4", "ch6"]),
            channel_indexes=np.array([0, 3, 5]))
        rcg_a.analogsignals.append(neo_block_a.segments[0].analogsignals[0])

        # RCG with units
        octotrode_rcg = RecordingChannelGroup(name="octotrode A",
                                              channel_indexes=range(3))
        neo_block_b.recordingchannelgroups.append(octotrode_rcg)
        for ind in range(5):
            octo_unit = Unit(name="unit_{}".format(ind),
                             description="after a long and hard spike sorting")
            octotrode_rcg.units.append(octo_unit)

        # Unit as a spiketrain container
        spiketrain_container_rcg = RecordingChannelGroup(name="PyramRCG",
                                                         channel_indexes=[1])
        neo_block_b.recordingchannelgroups.append(spiketrain_container_rcg)
        pyram_unit = Unit(name="Pyramidal neuron")
        train0 = SpikeTrain(times=[0.01, 3.3, 9.3], units="sec", t_stop=10)
        pyram_unit.spiketrains.append(train0)
        train1 = SpikeTrain(times=[100.01, 103.3, 109.3], units="sec",
                            t_stop=110)
        pyram_unit.spiketrains.append(train1)
        spiketrain_container_rcg.units.append(pyram_unit)

        # TODO: Add waveforms to spiketrains

        # Events associated with first segment of first block
        evt = Event(name="Trigger events",
                    times=np.arange(0, 30, 10)*pq.s,
                    labels=np.array(["trig0", "trig1", "trig2"], dtype="S"))
        neo_block_a.segments[0].events.append(evt)

        # Epochs associated with the second segment of the first block
        epc = Epoch(name="Button events",
                    times=np.arange(0, 30, 10)*pq.s,
                    durations=[10, 5, 7]*pq.ms,
                    labels=np.array(["btn0", "btn1", "btn2"], dtype="S"))
        neo_block_a.segments[1].epochs.append(epc)

        # Write all the blocks
        nix_blocks = self.io.write_all_blocks(neo_blocks)

        for nixblk, neoblk in zip(nix_blocks, neo_blocks):
            self.assertEqual(nixblk.name, neoblk.name)
            self.assertEqual(nixblk.definition, neoblk.description)
            self.assertEqual(nixblk.type, "neo.block")

            for nixgrp in nixblk.groups:
                analog_signals = [da for da in nixgrp.data_arrays
                                  if da.type == "neo.analogsignal"]
                irreg_signals = [da for da in nixgrp.data_arrays
                                 if da.type == "neo.irregularlysampledsignal"]
                self.assertEqual(len(analog_signals), 3)
                self.assertEqual(len(irreg_signals), 10)

                for nixasig in analog_signals:
                    self.assertEqual(nixasig.unit, "mV")
                    self.assertEqual(nixasig.dimensions[0].dimension_type,
                                     nix.DimensionType.Sample)
                    self.assertEqual(nixasig.dimensions[1].dimension_type,
                                     nix.DimensionType.Set)
                    self.assertEqual(nixasig.dimensions[0].unit, "s")
                    self.assertEqual(nixasig.dimensions[0].label, "time")
                    self.assertEqual(nixasig.dimensions[0].offset, 0)
                    self.assertEqual(nixasig.dimensions[0].sampling_interval,
                                     0.1)  # 1/(10 kHz)

                    # TODO: Check data values

                for nixisig in irreg_signals:
                    self.assertEqual(nixisig.unit, "nA")
                    self.assertEqual(nixisig.dimensions[0].dimension_type,
                                     nix.DimensionType.Range)
                    self.assertEqual(nixisig.dimensions[1].dimension_type,
                                     nix.DimensionType.Set)
                    self.assertEqual(nixisig.dimensions[0].unit, "s")
                    self.assertEqual(nixisig.dimensions[0].label, "time")

                    # TODO: Check tick and data values

            # TODO: Check RCGs

            # TODO: Check Events

            # TODO: Check Epochs

