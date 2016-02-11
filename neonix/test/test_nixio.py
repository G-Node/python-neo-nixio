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
import string

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
        self.assertEqual(nix_block.type, "neo.block")
        self.check_equal_attr(neo_block, nix_block)

    def test_block_cascade(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        neo_rcg = RecordingChannelGroup(name="test_rcg",
                                        description="rcg for testing",
                                        channel_indexes=[])
        neo_block.segments.append(neo_segment)
        neo_block.recordingchannelgroups.append(neo_rcg)
        self.io.write_block(neo_block)

        nix_block = self.io.nix_file.blocks[0]
        nix_group = nix_block.groups[0]
        nix_source = nix_block.sources[0]

        # block -> block base attr
        self.assertEqual(nix_block.type, "neo.block")
        self.check_equal_attr(neo_block, nix_block)

        # segment -> group base attr
        self.assertEqual(nix_group.type, "neo.segment")
        self.check_equal_attr(neo_segment, nix_group)

        # rcg -> source base attr
        self.assertEqual(nix_source.type, "neo.recordingchannelgroup")
        self.check_equal_attr(neo_rcg, nix_source)

    def test_container_len_neq(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block)
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
        self.io.write_block(neo_block)
        nix_block = self.io.nix_file.blocks[0]

        self.check_equal_attr(neo_block, nix_block)

    def test_anonymous_objects(self):
        """
        Create multiple trees that contain all types of objects, with no name or
        data to test the unique name generation.
        """
        nblocks = 3
        nsegs = 4
        nanasig = 4
        nirrseg = 2
        nepochs = 3
        nevents = 4
        nspiketrains = 5
        nrcg = 5
        nunits = 30

        times = np.array([1])*pq.s
        signal = np.array([1])*pq.V
        blocks = []
        for blkidx in range(nblocks):
            blk = Block()
            blocks.append(blk)
            for segidx in range(nsegs):
                seg = Segment()
                blk.segments.append(seg)
                for anaidx in range(nanasig):
                    seg.analogsignals.append(AnalogSignal(signal=signal,
                                                          sampling_rate=pq.Hz))
                for irridx in range(nirrseg):
                    seg.irregularlysampledsignals.append(
                        IrregularlySampledSignal(times=times,
                                                 signal=signal,
                                                 time_units=pq.s)
                    )
                for epidx in range(nepochs):
                    seg.epochs.append(Epoch(times=times, durations=times))
                for evidx in range(nevents):
                    seg.events.append(Event(times=times))
                for stidx in range(nspiketrains):
                    seg.spiketrains.append(SpikeTrain(times=times, t_stop=pq.s,
                                                      units=pq.s))
            for rcgidx in range(nrcg):
                rcg = RecordingChannelGroup(channel_indexes=[1, 2])
                blk.recordingchannelgroups.append(rcg)
                for unidx in range(nunits):
                    unit = Unit()
                    rcg.units.append(unit)

        self.io.write_all_blocks(blocks)

    def test_annotations(self):
        def rand_word():
            return "".join(np.random.choice(list(string.ascii_letters), 10))

        def rand_dict(nitems):
            rd = dict()
            for _ in range(nitems):
                key = rand_word()
                value = rand_word() if np.random.choice((0, 1))\
                    else np.random.uniform()
                rd[key] = value
            return rd

        times = np.array([1])*pq.s
        signal = np.array([1])*pq.V
        blk = Block()
        blk.annotate(**rand_dict(3))

        seg = Segment()
        seg.annotate(**rand_dict(4))
        blk.segments.append(seg)

        asig = AnalogSignal(signal=signal, sampling_rate=pq.Hz)
        asig.annotate(**rand_dict(2))
        seg.analogsignals.append(asig)

        isig = IrregularlySampledSignal(times=times, signal=signal,
                                        time_units=pq.s)
        isig.annotate(**rand_dict(2))
        seg.irregularlysampledsignals.append(isig)

        epoch = Epoch(times=times, durations=times)
        epoch.annotate(**rand_dict(4))
        seg.epochs.append(epoch)

        event = Event(times=times)
        event.annotate(**rand_dict(4))
        seg.events.append(event)

        spiketrain = SpikeTrain(times=times, t_stop=pq.s, units=pq.s)
        spiketrain.annotate(**rand_dict(6))
        seg.spiketrains.append(spiketrain)

        rcg = RecordingChannelGroup(channel_indexes=[1, 2])
        rcg.annotate(**rand_dict(4))
        blk.recordingchannelgroups.append(rcg)

        unit = Unit()
        unit.annotate(**rand_dict(2))
        rcg.units.append(unit)

        nixblk = self.io.write_block(blk)

        self.check_equal_attr(blk, nixblk)
        self.check_equal_attr(seg, nixblk.groups[0])
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.analogsignal"]:
            self.check_equal_attr(asig, signal)
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.irregularlysampledsignal"]:
            self.check_equal_attr(isig, signal)
        nixepochs = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.epoch"]
        self.check_equal_attr(epoch, nixepochs[0])
        nixevents = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.event"]
        self.check_equal_attr(event, nixevents[0])
        nixspiketrains = [mtag for mtag in nixblk.groups[0].multi_tags
                          if mtag.type == "neo.spiketrain"]
        self.check_equal_attr(spiketrain, nixspiketrains[0])
        nixrcgs = [src for src in nixblk.sources
                   if src.type == "neo.recordingchannelgroup"]
        self.check_equal_attr(rcg, nixrcgs[0])

    def test_waveforms(self):
        blk = Block()
        seg = Segment()

        # create a spiketrain with some waveforms and attach it to a segment
        wf_array = np.array([[[1., 10.]], [[2., 20.]], [[3., 30.]]]) * pq.mV
        spkt = SpikeTrain([1.0, 50.0, 60.0]*pq.s, waveforms=wf_array,
                          name='spkt_with_waveform', t_stop=100.0,
                          t_start=0.5, left_sweep=5*pq.ms)
        seg.spiketrains.append(spkt)
        blk.segments.append(seg)

        nix_block = self.io.write_block(blk)

        nix_spkt = nix_block.multi_tags["spkt_with_waveform"]
        self.assertAlmostEqual(nix_spkt.metadata["t_stop"], 100)
        self.assertAlmostEqual(nix_spkt.metadata["t_start"], 0.5)

        nix_wf = nix_spkt.features[0].data
        self.assertAlmostEqual(nix_wf.metadata["left_sweep"], 0.005)
        nspk, nchan, ntime = np.shape(nix_wf)
        for spk in range(nspk):
            for chan in range(nchan):
                for t in range(ntime):
                    self.assertAlmostEqual(nix_wf[spk, chan, t],
                                           wf_array[spk, chan, t])

    def test_basic_attr(self):
        def rand_date():
            return datetime(year=np.random.randint(1980, 2020),
                            month=np.random.randint(1, 13),
                            day=np.random.randint(1, 29))

        def populate_dates(obj):
            obj.file_datetime = rand_date()
            obj.rec_datetime = rand_date()

        times = np.array([1])*pq.s
        signal = np.array([1])*pq.V
        blk = Block()
        blk.file_origin = "/home/user/data/blockfile"
        populate_dates(blk)

        seg = Segment()
        populate_dates(seg)
        seg.file_origin = "/home/user/data/segfile"
        blk.segments.append(seg)

        asig = AnalogSignal(signal=signal, sampling_rate=pq.Hz)
        asig.file_origin = "/home/user/data/asigfile"
        seg.analogsignals.append(asig)

        isig = IrregularlySampledSignal(times=times, signal=signal,
                                        time_units=pq.s)
        isig.file_origin = "/home/user/data/isigfile"
        seg.irregularlysampledsignals.append(isig)

        epoch = Epoch(times=times, durations=times)
        epoch.file_origin = "/home/user/data/epochfile"
        seg.epochs.append(epoch)

        event = Event(times=times)
        event.file_origin = "/home/user/data/eventfile"
        seg.events.append(event)

        spiketrain = SpikeTrain(times=times, t_stop=pq.s, units=pq.s)
        spiketrain.file_origin = "/home/user/data/spiketrainfile"
        seg.spiketrains.append(spiketrain)

        rcg = RecordingChannelGroup(channel_indexes=[1, 2])
        rcg.file_origin = "/home/user/data/rcgfile"
        blk.recordingchannelgroups.append(rcg)

        unit = Unit()
        unit.file_origin = "/home/user/data/unitfile"
        rcg.units.append(unit)

        nixblk = self.io.write_block(blk)

        self.check_equal_attr(blk, nixblk)
        self.check_equal_attr(seg, nixblk.groups[0])
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.analogsignal"]:
            self.check_equal_attr(asig, signal)
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.irregularlysampledsignal"]:
            self.check_equal_attr(isig, signal)
        nixepochs = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.epoch"]
        self.check_equal_attr(epoch, nixepochs[0])
        nixevents = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.event"]
        self.check_equal_attr(event, nixevents[0])
        nixspiketrains = [mtag for mtag in nixblk.groups[0].multi_tags
                          if mtag.type == "neo.spiketrain"]
        self.check_equal_attr(spiketrain, nixspiketrains[0])
        nixrcgs = [src for src in nixblk.sources
                   if src.type == "neo.recordingchannelgroup"]
        self.check_equal_attr(rcg, nixrcgs[0])

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
                asig_data = np.array([np.linspace(0, ind+1, 100)*(ind+1),
                                      np.linspace(0, ind+2, 100)*(ind+1),
                                      np.linspace(0, ind+3, 100)*(ind+1)]
                                     ).transpose()*pq.mV
                asignal = AnalogSignal(asig_data,
                                       name="some_sort_of_signal_{}".format(ind),
                                       t_start=0*pq.s,
                                       sampling_rate=10*pq.kHz)
                seg.analogsignals.append(asignal)

                isig_times = np.cumsum(np.random.random(50))*pq.ms
                isig_data = np.random.random((50, 10))*pq.nA
                isignal = IrregularlySampledSignal(isig_times, isig_data)
                seg.irregularlysampledsignals.append(isignal)

        # create a spiketrain with some waveforms and attach it to a segment
        wf_array = np.array([[[0., 1.]], [[2., 3.]], [[4., 5.]]]) * pq.mV
        seg_train = SpikeTrain([3, 4, 5]*pq.s, waveforms=wf_array,
                               name='segment_spiketrain', t_stop=10.0,
                               t_start=0.0, left_sweep=1*pq.ms)
        neo_blocks[0].segments[0].spiketrains.append(seg_train)

        # group 3 channels from the analog signal in the first segment of the
        # first block
        rcg_a = RecordingChannelGroup(
            name="RCG_1",
            channel_names=np.array(["ch1", "ch4", "ch6"]),
            channel_indexes=np.array([0, 3, 5]))
        rcg_a.analogsignals.append(neo_block_a.segments[0].analogsignals[0])
        neo_block_a.recordingchannelgroups.append(rcg_a)

        # RCG with units
        octotrode_rcg = RecordingChannelGroup(name="octotrode A",
                                              channel_indexes=range(3))

        octotrode_rcg.coordinates = [(1*pq.cm, 2*pq.cm, 3*pq.cm),
                                     (1*pq.cm, 2*pq.cm, 4*pq.cm),
                                     (1*pq.cm, 2*pq.cm, 5*pq.cm)]
        neo_block_b.recordingchannelgroups.append(octotrode_rcg)
        for ind in range(5):
            octo_unit = Unit(name="unit_{}".format(ind),
                             description="after a long and hard spike sorting")
            octotrode_rcg.units.append(octo_unit)

        # RCG and Unit as a spiketrain container
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
        # spiketrains must also exist in segments
        neo_block_b.segments[0].spiketrains.append(train0)
        neo_block_b.segments[0].spiketrains.append(train1)

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

        # ================== TESTING WRITTEN DATA ==================

        for nixblk, neoblk in zip(nix_blocks, neo_blocks):
            self.assertEqual(nixblk.type, "neo.block")
            self.check_equal_attr(neoblk, nixblk)

            for nixgrp, neoseg in zip(nixblk.groups, neoblk.segments):
                self.check_equal_attr(neoseg, nixgrp)
                nix_analog_signals = [da for da in nixgrp.data_arrays
                                      if da.type == "neo.analogsignal"]
                nix_analog_signals = sorted(nix_analog_signals,
                                            key=lambda da: da.name)
                nix_irreg_signals = [da for da in nixgrp.data_arrays
                                     if da.type ==
                                     "neo.irregularlysampledsignal"]
                nix_irreg_signals = sorted(nix_irreg_signals,
                                           key=lambda da: da.name)

                neo_analog_signals = np.transpose(neoseg.analogsignals[0])
                neo_irreg_signals = np.transpose(
                    neoseg.irregularlysampledsignals[0])

                self.assertEqual(len(nix_analog_signals),
                                 len(neo_analog_signals))
                self.assertEqual(len(nix_irreg_signals),
                                 len(neo_irreg_signals))

                for nixasig, neoasig in zip(nix_analog_signals,
                                            neo_analog_signals):
                    self.assertEqual(nixasig.unit, "mV")
                    self.assertIs(nixasig.dimensions[0].dimension_type,
                                  nix.DimensionType.Sample)
                    self.assertIs(nixasig.dimensions[1].dimension_type,
                                  nix.DimensionType.Set)
                    self.assertEqual(nixasig.dimensions[0].unit, "s")
                    self.assertEqual(nixasig.dimensions[0].label, "time")
                    self.assertEqual(nixasig.dimensions[0].offset, 0)
                    self.assertEqual(nixasig.dimensions[0].sampling_interval,
                                     0.0001)  # 1/(10 kHz)
                    self.assertEqual(len(nixasig), len(neoasig))

                    for nixvalue, neovalue in zip(nixasig, neoasig):
                        self.assertAlmostEqual(nixvalue.item(), neovalue.item())

                for nixisig, neoisig in zip(nix_irreg_signals,
                                            neo_irreg_signals):
                    self.assertEqual(nixisig.unit, "nA")
                    self.assertIs(nixisig.dimensions[0].dimension_type,
                                  nix.DimensionType.Range)
                    self.assertIs(nixisig.dimensions[1].dimension_type,
                                  nix.DimensionType.Set)
                    self.assertEqual(nixisig.dimensions[0].unit, "ms")
                    self.assertEqual(nixisig.dimensions[0].label, "time")

                    for nixvalue, neovalue in zip(nixisig, neoisig):
                        self.assertAlmostEqual(nixvalue.item(), neovalue.item())

                    nixtime = nixisig.dimensions[0].ticks
                    neotime = neoseg.irregularlysampledsignals[0].times
                    self.assertEqual(len(nixtime), len(neotime))
                    for nixt, neot in zip(nixtime, neotime):
                        self.assertAlmostEqual(nixt, neot)

        # spiketrains and waveforms
        neo_spiketrain = neo_blocks[0].segments[0].spiketrains[0]
        nix_spiketrain = nix_blocks[0].groups[0].multi_tags[neo_spiketrain.name]
        self.check_equal_attr(neo_spiketrain, nix_spiketrain)

        self.assertEqual(len(nix_spiketrain.positions),
                         len(neo_spiketrain))

        for nixvalue, neovalue in zip(nix_spiketrain.positions, neo_spiketrain):
            self.assertAlmostEqual(nixvalue, neovalue)

        nix_t_stop = nix_spiketrain.metadata["t_stop"]
        neo_t_stop = neo_spiketrain.t_stop
        self.assertAlmostEqual(nix_t_stop, neo_t_stop)

        self.assertEqual(nix_spiketrain.positions.unit, "s")

        neo_waveforms = neo_spiketrain.waveforms
        nix_waveforms = nix_spiketrain.features[0].data

        self.assertEqual(np.shape(nix_waveforms), np.shape(neo_waveforms))
        self.assertEqual(nix_waveforms.unit, "mV")
        nspk, nchan, ntime = np.shape(nix_waveforms)
        for spk in range(nspk):
            for chan in range(nchan):
                for t in range(ntime):
                    self.assertAlmostEqual(nix_waveforms[spk, chan, t],
                                           neo_waveforms[spk, chan, t])

        self.assertIs(nix_waveforms.dimensions[0].dimension_type,
                      nix.DimensionType.Set)
        self.assertIs(nix_waveforms.dimensions[1].dimension_type,
                      nix.DimensionType.Set)
        self.assertIs(nix_waveforms.dimensions[2].dimension_type,
                      nix.DimensionType.Sample)

        # no time dimension specified when creating - defaults to 1 s
        wf_time_dim = nix_waveforms.dimensions[2].unit
        wf_time_interval = nix_waveforms.dimensions[2].sampling_interval
        self.assertEqual(wf_time_dim, "s")
        self.assertAlmostEqual(wf_time_interval, 1.0)

        # RCGs
        # - Octotrode
        nix_octotrode = nix_blocks[1].sources["octotrode A"]
        self.check_equal_attr(octotrode_rcg, nix_octotrode)
        nix_channels = [src for src in nix_octotrode.sources
                        if src.type == "neo.recordingchannel"]
        self.assertEqual(len(nix_channels),
                         len(octotrode_rcg.channel_indexes))

        nix_units = [src for src in nix_octotrode.sources
                     if src.type == "neo.unit"]
        self.assertEqual(len(nix_units), len(octotrode_rcg.units))
        for nix_u, neo_u in zip(nix_units, octotrode_rcg.units):
            self.check_equal_attr(neo_u, nix_u)

        nix_coordinates = [chan.metadata["coordinates"] for chan in nix_channels]
        nix_coordinate_units = [chan.metadata["coordinates.units"]
                                for chan in nix_channels]
        neo_coordinates = octotrode_rcg.coordinates

        for nix_xyz, neo_xyz in zip(nix_coordinates, neo_coordinates):
            for cnix, cneo in zip(nix_xyz, neo_xyz):
                self.assertAlmostEqual(cnix, cneo.magnitude)

        for nix_xyz, neo_xyz in zip(nix_coordinate_units, neo_coordinates):
            for cnix, cneo in zip(nix_xyz, neo_xyz):
                self.assertEqual(cnix, str(cneo.dimensionality))

        # - Spiketrain Container
        nix_pyram_rcg = nix_blocks[1].sources["PyramRCG"]
        self.check_equal_attr(spiketrain_container_rcg, nix_pyram_rcg)
        nix_channels = [src for src in nix_pyram_rcg.sources
                        if src.type == "neo.recordingchannel"]
        self.assertEqual(len(nix_channels),
                         len(spiketrain_container_rcg.channel_indexes))

        nix_units = [src for src in nix_pyram_rcg.sources
                     if src.type == "neo.unit"]
        self.assertEqual(len(nix_units), len(spiketrain_container_rcg.units))

        # - Pyramidal neuron Unit
        nix_pyram_nrn = nix_pyram_rcg.sources["Pyramidal neuron"]
        self.check_equal_attr(pyram_unit, nix_pyram_nrn)

        # - PyramRCG and Pyram neuron must be referenced by the same spiketrains
        all_spiketrains = [mtag for mtag in nix_blocks[1].multi_tags
                           if mtag.type == "neo.spiketrain"]
        nrn_spiketrains = [src for src in nix_pyram_nrn.sources
                           if src.type == "neo.spiketrain"]
        rcg_spiketrains = [src for chan in nix_channels
                           for src in chan.sources
                           if src.type == "neo.spiketrain"]
        for spiketrain in all_spiketrains:
            if spiketrain in nrn_spiketrains:
                if spiketrain not in rcg_spiketrains:
                    self.fail("Spiketrain reference failure: "
                              "{} referenced by Unit but not by parent RCG."
                              "".format(spiketrain))
            if spiketrain in rcg_spiketrains:
                if spiketrain not in nrn_spiketrains:
                    self.fail("Spiketrain reference failure: "
                              "{} referenced by RCG but not by a child Unit."
                              "".format(spiketrain))

        # - RCG_1 referenced by first signal
        neo_first_signal = neo_blocks[0].segments[0].analogsignals[0]
        _, n_neo_signals = np.shape(neo_first_signal)
        nix_first_signal_group = []
        for sig_idx in range(n_neo_signals):
            nix_name = "{}.{}".format(neo_first_signal.name, sig_idx)
            nix_signal = nix_blocks[0].groups[0].data_arrays[nix_name]
            nix_rcg_a = nix_blocks[0].sources["RCG_1"]
            self.assertIn(nix_rcg_a, nix_signal.sources)
            nix_first_signal_group.append(nix_signal)
        # test metadata grouping
        for signal in nix_first_signal_group[1:]:
            self.assertEqual(signal.metadata.id,
                             nix_first_signal_group[0].metadata.id)

        # Get Event and compare attributes
        nix_event = nix_blocks[0].multi_tags["Trigger events"]
        self.assertIn(nix_event, nix_blocks[0].groups[0].multi_tags)
        # - times, units, labels
        # TODO: times units labels

        # Get Epoch and compare attributes
        nix_epoch = nix_blocks[0].multi_tags["Button events"]
        self.assertIn(nix_epoch, nix_blocks[0].groups[1].multi_tags)
        # - times, units, labels
        # TODO: times durations units labels

    def check_equal_attr(self, neoobj, nixobj):
        if neoobj.name:
            self.assertEqual(neoobj.name, nixobj.name)
        self.assertEqual(neoobj.description, nixobj.definition)
        if hasattr(neoobj, "rec_datetime") and neoobj.rec_datetime:
            self.assertEqual(neoobj.rec_datetime,
                             datetime.fromtimestamp(nixobj.created_at))
        if hasattr(neoobj, "file_datetime") and neoobj.file_datetime:
            self.assertEqual(neoobj.file_datetime,
                             datetime.fromtimestamp(
                                 nixobj.metadata["file_datetime"]))
        if neoobj.file_origin:
            self.assertEqual(neoobj.file_origin,
                             nixobj.metadata["file_origin"])
        if neoobj.annotations:
            annotations = nixobj.metadata.name+".annotations"
            nixannotations = nixobj.metadata.sections[annotations]
            for k, v, in neoobj.annotations.items():
                self.assertEqual(nixannotations[k], v)

