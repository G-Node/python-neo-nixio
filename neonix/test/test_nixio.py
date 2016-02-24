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


def rdate():
    return datetime(year=np.random.randint(1980, 2020),
                    month=np.random.randint(1, 13),
                    day=np.random.randint(1, 29))


def populate_dates(obj):
    obj.file_datetime = rdate()
    obj.rec_datetime = rdate()


def rword(n=10):
    return "".join(np.random.choice(list(string.ascii_letters), n))


def rsentence(n=3, maxwl=10):
    return " ".join(rword(np.random.randint(1, maxwl)) for _ in range(n))


def rdict(nitems):
    rd = dict()
    for _ in range(nitems):
        key = rword()
        value = rword() if np.random.choice((0, 1)) \
            else np.random.uniform()
        rd[key] = value
    return rd


def rquant(shape, unit, incr=False):
    try:
        dim = len(shape)
    except TypeError:
        dim = 1
    if incr and dim > 1:
        raise TypeError("Shape of quantity array may only be one-dimensional "
                        "when incremental values are requested.")
    arr = np.random.random(shape)
    if incr:
        arr = np.array(np.cumsum(arr))
    return arr*unit


def create_all_annotated():
    times = rquant(1, pq.s)
    signal = rquant(1, pq.V)
    blk = Block()
    blk.annotate(**rdict(3))

    seg = Segment()
    seg.annotate(**rdict(4))
    blk.segments.append(seg)

    asig = AnalogSignal(signal=signal, sampling_rate=pq.Hz)
    asig.annotate(**rdict(2))
    seg.analogsignals.append(asig)

    isig = IrregularlySampledSignal(times=times, signal=signal,
                                    time_units=pq.s)
    isig.annotate(**rdict(2))
    seg.irregularlysampledsignals.append(isig)

    epoch = Epoch(times=times, durations=times)
    epoch.annotate(**rdict(4))
    seg.epochs.append(epoch)

    event = Event(times=times)
    event.annotate(**rdict(4))
    seg.events.append(event)

    spiketrain = SpikeTrain(times=times, t_stop=pq.s, units=pq.s)
    spiketrain.annotate(**rdict(6))
    seg.spiketrains.append(spiketrain)

    rcg = RecordingChannelGroup(channel_indexes=[1, 2])
    rcg.annotate(**rdict(5))
    blk.recordingchannelgroups.append(rcg)

    unit = Unit()
    unit.annotate(**rdict(2))
    rcg.units.append(unit)

    return blk


class NixIOTest(unittest.TestCase):

    def setUp(self):
        self.filename = "nixio_testfile.hd5"
        self.io = NixIO(self.filename, "ow")

    def tearDown(self):
        del self.io
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_block(self):
        neo_block = Block(name=rword(), description=rsentence())
        nix_block = self.io.write_block(neo_block)
        self.assertEqual(nix_block.type, "neo.block")
        self.check_equal_attr(neo_block, nix_block)

    def test_block_cascade(self):
        neo_block = Block(name=rword(), description=rsentence())
        neo_segment = Segment(name=rword(),
                              description=rsentence(100))
        neo_rcg = RecordingChannelGroup(name=rword(30),
                                        description=rsentence(4),
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
        neo_block = Block(name=rword(20), description=rsentence(10, 10))
        neo_segment = Segment(name=rsentence(3, 13),
                              description=rsentence(10, 23))
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block)
        nix_block = self.io.nix_file.blocks[0]
        neo_segment_new = Segment(name=rword(40),
                                  description=rsentence(6, 7))
        neo_block.segments.append(neo_segment_new)
        self.assertNotEqual(len(neo_block.segments), len(nix_block.groups))

    def test_block_metadata(self):
        neo_block = Block(name=rword(44), description=rsentence(5))
        neo_block.rec_datetime = rdate()
        neo_block.file_datetime = rdate()
        neo_block.file_origin = "test_file_origin"
        self.io.write_block(neo_block)
        nix_block = self.io.nix_file.blocks[0]

        self.check_equal_attr(neo_block, nix_block)

    def test_anonymous_objects(self):
        """
        Create multiple trees that contain all types of objects, with no name or
        data to test the unique name generation.

        Results are not checked. The purpose of this test it to check that the
        data can be written without causing conflicts in NIX.
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

        times = rquant(1, pq.s)
        signal = rquant(1, pq.V)
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
        blk = create_all_annotated()

        nixblk = self.io.write_block(blk)

        self.check_equal_attr(blk, nixblk)

        seg = blk.segments[0]
        self.check_equal_attr(seg, nixblk.groups[0])

        asig = seg.analogsignals[0]
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.analogsignal"]:
            self.check_equal_attr(asig, signal)

        isig = seg.irregularlysampledsignals[0]
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.irregularlysampledsignal"]:
            self.check_equal_attr(isig, signal)

        epoch = seg.epochs[0]
        nixepochs = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.epoch"]
        self.check_equal_attr(epoch, nixepochs[0])

        event = seg.events[0]
        nixevents = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.event"]
        self.check_equal_attr(event, nixevents[0])

        spiketrain = seg.spiketrains[0]
        nixspiketrains = [mtag for mtag in nixblk.groups[0].multi_tags
                          if mtag.type == "neo.spiketrain"]
        self.check_equal_attr(spiketrain, nixspiketrains[0])

        rcg = blk.recordingchannelgroups[0]
        nixrcgs = [src for src in nixblk.sources
                   if src.type == "neo.recordingchannelgroup"]
        self.check_equal_attr(rcg, nixrcgs[0])

    def test_metadata_structure(self):
        blk = create_all_annotated()
        blk = self.io.write_block(blk)

        blkmd = blk.metadata
        self.assertEqual(blk.name, blkmd.name)

        grp = blk.groups[0]  # segment
        self.assertIn(grp.name, blkmd.sections)

        grpmd = blkmd.sections[grp.name]
        for da in grp.data_arrays:  # signals
            name = ".".join(da.name.split(".")[:-1])
            self.assertIn(name, grpmd.sections)
        for mtag in grp.multi_tags:  # spiketrains, events, and epochs
            self.assertIn(mtag.name, grpmd.sections)

        srcrcg = blk.sources[0]  # rcg
        self.assertIn(srcrcg.name, blkmd.sections)

        for srcunit in blk.sources:  # units
            self.assertIn(srcunit.name, blkmd.sections)

    def test_waveforms(self):
        blk = Block()
        seg = Segment()

        # create a spiketrain with some waveforms and attach it to a segment
        wf_array = rquant((20, 5, 10), pq.mV)
        times = rquant(20, pq.s, incr=True)+0.5*pq.s
        spkt = SpikeTrain(times, waveforms=wf_array,
                          name="spkt_with_waveform", t_stop=100.0,
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
        times = rquant(1, pq.s)
        signal = rquant(1, pq.V)
        blk = Block(name=rword(5), description=rsentence(2))
        blk.file_origin = "/home/user/data/blockfile"
        populate_dates(blk)

        seg = Segment(name=rword(4), description=rsentence(5))
        populate_dates(seg)
        seg.file_origin = "/home/user/data/segfile"
        blk.segments.append(seg)

        asig = AnalogSignal(name=rword(9),
                            description=rsentence(4),
                            signal=signal, sampling_rate=pq.Hz)
        asig.file_origin = "/home/user/data/asigfile"
        seg.analogsignals.append(asig)

        isig = IrregularlySampledSignal(name=rword(30),
                                        description=rsentence(5, 7),
                                        times=times, signal=signal,
                                        time_units=pq.s)
        isig.file_origin = "/home/user/data/isigfile"
        seg.irregularlysampledsignals.append(isig)

        epoch = Epoch(name=rword(14), description=rsentence(40, 10),
                      times=times, durations=times)
        epoch.file_origin = "/home/user/data/epochfile"
        seg.epochs.append(epoch)

        event = Event(name=rword(), description=rsentence(50, 3),
                      times=times)
        event.file_origin = "/home/user/data/eventfile"
        seg.events.append(event)

        spiketrain = SpikeTrain(name=rword(20),
                                description=rsentence(70, 5),
                                times=times, t_stop=pq.s, units=pq.s)
        spiketrain.file_origin = "/home/user/data/spiketrainfile"
        seg.spiketrains.append(spiketrain)

        rcg = RecordingChannelGroup(
            name=rsentence(3, 10),
            description=rsentence(10, 8),
            channel_indexes=[1, 2]
        )
        rcg.file_origin = "/home/user/data/rcgfile"
        blk.recordingchannelgroups.append(rcg)

        unit = Unit(name=rword(40), description=rsentence(30))
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

        neo_block_a = Block(name=rword(10),
                            description=rsentence(10))

        neo_block_b = Block(name=rword(3),
                            description=rsentence(7, 20))
        neo_blocks = [neo_block_a, neo_block_b]

        for blk in neo_blocks:
            for ind in range(3):
                seg = Segment(name="segment_{}".format(ind),
                              description="{} segment {}".format(blk.name, ind))
                blk.segments.append(seg)
                asig_data = rquant((100, 3), pq.mV)
                asignal = AnalogSignal(asig_data,
                                       name="some_sort_of_signal_{}".format(ind),
                                       t_start=0*pq.s,
                                       sampling_rate=10*pq.kHz)
                seg.analogsignals.append(asignal)

                isig_times = rquant(50, pq.ms, True)
                isig_data = rquant((50, 10), pq.nA)
                isignal = IrregularlySampledSignal(isig_times, isig_data)
                seg.irregularlysampledsignals.append(isignal)

        # create a spiketrain with some waveforms and attach it to a segment
        wf_array = rquant((40, 10, 35), pq.mV)
        seg_train_times = rquant(40, pq.s, True)
        t_stop = max(seg_train_times)+10.0*pq.s
        seg_train = SpikeTrain(seg_train_times, waveforms=wf_array,
                               name="segment_spiketrain", t_stop=t_stop,
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
                    times=np.random.random(3)*pq.s,
                    labels=np.array(["trig0", "trig1", "trig2"], dtype="S"))
        neo_block_a.segments[0].events.append(evt)

        # Epochs associated with the second segment of the first block
        epc = Epoch(name="Button events",
                    times=np.random.random(3)*pq.s,
                    durations=np.random.random(3)*pq.ms,
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
                    self.check_equal_attr(neoseg.analogsignals[0],
                                          nixasig)
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
                    self.check_equal_attr(neoseg.irregularlysampledsignals[0],
                                          nixisig)
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
        nix_channels = nix_octotrode.sources
        self.assertEqual(len(nix_channels),
                         len(octotrode_rcg.channel_indexes))
        # nix_units = [unit for unit in nix_blocks[1].sources
        #              if nix_octotrode in unit.sources]
        # self.assertEqual(len(nix_units), len(octotrode_rcg.units))
        # for nix_u, neo_u in zip(nix_units, octotrode_rcg.units):
        #     self.check_equal_attr(neo_u, nix_u)

        nix_coordinates = [chan.metadata["coordinates"] for chan in nix_channels]
        nix_coordinate_units = [chan.metadata["coordinates.units"]
                                for chan in nix_channels]
        neo_coordinates = octotrode_rcg.coordinates

        for nix_xyz, neo_xyz in zip(nix_coordinates, neo_coordinates):
            for cnix, cneo in zip(nix_xyz, neo_xyz):
                self.assertAlmostEqual(cnix, cneo.magnitude)

        for cnix, neo_xyz in zip(nix_coordinate_units, neo_coordinates):
            for cneo in neo_xyz:
                self.assertEqual(cnix, str(cneo.dimensionality))

        # - Spiketrain Container
        nix_pyram_rcg = nix_blocks[1].sources["PyramRCG"]
        self.check_equal_attr(spiketrain_container_rcg, nix_pyram_rcg)
        nix_channels = [src for src in nix_pyram_rcg.sources
                        if src.type == "neo.recordingchannel"]
        self.assertEqual(len(nix_channels),
                         len(spiketrain_container_rcg.channel_indexes))

        # nix_units = [src for src in nix_blocks[1].sources
        #              if src.type == "neo.unit" and src.]
        # self.assertEqual(len(nix_units), len(spiketrain_container_rcg.units))

        # - Pyramidal neuron Unit
        nix_pyram_nrn = nix_blocks[1].sources["Pyramidal neuron"]
        self.check_equal_attr(pyram_unit, nix_pyram_nrn)

        # - PyramRCG and Pyram neuron must be referenced by the same spiketrains
        pyram_spiketrains = [mtag for mtag in nix_blocks[1].multi_tags
                             if mtag.type == "neo.spiketrain" and
                             nix_pyram_nrn in mtag.sources]
        for spiketrain in pyram_spiketrains:
            self.assertIn(nix_pyram_rcg, spiketrain.sources)

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
        self.check_equal_attr(evt, nix_event)
        neo_evt_times = evt.times.magnitude
        nix_evt_times = nix_event.positions
        for nix_value, neo_value in zip(nix_evt_times, neo_evt_times):
            self.assertAlmostEqual(nix_value, neo_value)
        self.assertEqual(nix_event.positions.unit, "s")
        neo_evt_labels = evt.labels
        nix_evt_labels = nix_event.positions.dimensions[0].labels
        for nix_label, neo_label in zip(nix_evt_labels, neo_evt_labels):
            self.assertEqual(nix_label, neo_label.decode())

        # Get Epoch and compare attributes
        nix_epoch = nix_blocks[0].multi_tags["Button events"]
        self.assertIn(nix_epoch, nix_blocks[0].groups[1].multi_tags)
        # - times, units, labels
        self.check_equal_attr(epc, nix_epoch)
        neo_epc_times = epc.times.magnitude
        nix_epc_times = nix_epoch.positions
        for nix_value, neo_value in zip(nix_epc_times, neo_epc_times):
            self.assertAlmostEqual(nix_value, neo_value)
        neo_epc_dura = epc.durations.magnitude
        nix_epc_dura = nix_epoch.extents
        for nix_value, neo_value in zip(nix_epc_dura, neo_epc_dura):
            self.assertAlmostEqual(nix_value, neo_value)
        self.assertEqual(nix_epoch.positions.unit, "s")
        self.assertEqual(nix_epoch.extents.unit, "ms")
        neo_epc_labels = epc.labels
        nix_epc_labels = nix_epoch.positions.dimensions[0].labels
        for nix_label, neo_label in zip(nix_epc_labels, neo_epc_labels):
            self.assertEqual(nix_label, neo_label.decode())

    def check_equal_attr(self, neoobj, nixobj):
        if neoobj.name:
            if isinstance(neoobj, (AnalogSignal, IrregularlySampledSignal)):
                nix_name = ".".join(nixobj.name.split(".")[:-1])
            else:
                nix_name = nixobj.name
            self.assertEqual(neoobj.name, nix_name)
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
            nixmd = nixobj.metadata
            for k, v, in neoobj.annotations.items():
                self.assertEqual(nixmd[k], v)

