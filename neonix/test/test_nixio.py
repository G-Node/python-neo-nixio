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
try:
    from unittest import mock
    nomock = False
except ImportError:
    try:
        import mock
        nomock = False
    except ImportError:
        nomock = True
import string
import itertools

import numpy as np
import quantities as pq

import nixio
from neo.core import (Block, Segment, RecordingChannelGroup, AnalogSignal,
                      IrregularlySampledSignal, Unit, SpikeTrain, Event, Epoch)

from neonix.io.nixio import NixIO


class NixIOTest(unittest.TestCase):

    filename = None
    io = None

    def compare_blocks(self, neoblocks, nixblocks):
        for neoblock, nixblock in zip(neoblocks, nixblocks):
            self.compare_attr(neoblock, nixblock)
            self.assertEqual(len(neoblock.segments), len(nixblock.groups))
            for idx, neoseg in enumerate(neoblock.segments):
                nixgrp = nixblock.groups[neoseg.name]
                self.compare_segment_group(neoseg, nixgrp)
            for idx, neorcg in enumerate(neoblock.recordingchannelgroups):
                if neorcg.name:
                    nixsrc = nixblock.sources[neorcg.name]
                else:
                    nixsrc = nixblock.sources[idx]
                self.compare_rcg_source(neorcg, nixsrc)
            self.check_refs(neoblock, nixblock)

    def compare_rcg_source(self, neorcg, nixsrc):
        self.compare_attr(neorcg, nixsrc)
        nix_channels = list(src for src in nixsrc.sources
                            if src.type == "neo.recordingchannel")
        self.assertEqual(len(neorcg.channel_indexes), len(nix_channels))
        for nixchan in nix_channels:
            nixchanidx = nixchan.metadata["index"]
            try:
                neochanpos = list(neorcg.channel_indexes).index(nixchanidx)
            except ValueError:
                self.fail("Channel indexes do not match.")
            if len(neorcg.channel_names):
                neochanname = neorcg.channel_names[neochanpos]
                nixchanname = nixchan.name
                self.assertEqual(neochanname, nixchanname)
        nix_units = list(src for src in nixsrc.sources
                         if src.type == "neo.unit")
        self.assertEqual(len(neorcg.units), len(nix_units))
        for neounit in neorcg.units:
            nixunit = nixsrc.sources[neounit.name]
            self.compare_attr(neounit, nixunit)

    def check_refs(self, neoblock, nixblock):
        """
        Checks whether the references between objects that are not nested are
        mapped correctly (e.g., SpikeTrains referenced by a Unit).

        :param neoblock: A Neo block
        :param nixblock: The corresponding NIX block
        """
        for idx, neorcg in enumerate(neoblock.recordingchannelgroups):
            if neorcg.name:
                nixrcg = nixblock.sources[neorcg.name]
            else:
                nixrcg = nixblock.sources[idx]
            # AnalogSignals referencing RCG
            neoasigs = list(sig.name for sig in neorcg.analogsignals)
            nixasigs = list(set(da.metadata.name for da in nixblock.data_arrays
                                if da.type == "neo.analogsignal" and
                                nixrcg in da.sources))

            self.assertEqual(len(neoasigs), len(nixasigs))

            # IrregularlySampledSignals referencing RCG
            neoisigs = list(sig.name for sig in neorcg.irregularlysampledsignals)
            nixisigs = list(set(da.metadata.name for da in nixblock.data_arrays
                                if da.type == "neo.irregularlysampledsignal" and
                                nixrcg in da.sources))
            self.assertEqual(len(neoisigs), len(nixisigs))

            # SpikeTrains referencing RCG and Units
            for sidx, neounit in enumerate(neorcg.units):
                if neounit.name:
                    nixunit = nixrcg.sources[neounit.name]
                else:
                    nixunit = nixrcg.sources[sidx]
                neosts = list(st.name for st in neounit.spiketrains)
                nixsts = list(mt for mt in nixblock.multi_tags
                              if mt.type == "neo.spiketrain" and
                              nixunit.name in mt.sources)
                # SpikeTrains must also reference RCG
                for nixst in nixsts:
                    self.assertIn(nixrcg.name, nixst.sources)
                nixsts = list(st.name for st in nixsts)
                self.assertEqual(len(neosts), len(nixsts))
                for neoname in neosts:
                    if neoname:
                        self.assertIn(neoname, nixsts)

        # Events and Epochs must reference all Signals in the Group (NIX only)
        for nixgroup in nixblock.groups:
            nixevep = list(mt for mt in nixgroup.multi_tags
                           if mt.type in ["neo.event", "neo.epoch"])
            nixsigs = list(da.name for da in nixgroup.data_arrays
                           if da.type in ["neo.analogsignal",
                                          "neo.irregularlysampledsignal"])
            for nee in nixevep:
                for ns in nixsigs:
                    self.assertIn(ns, nee.references)

    def compare_segment_group(self, neoseg, nixgroup):
        self.compare_attr(neoseg, nixgroup)
        neo_signals = neoseg.analogsignals + neoseg.irregularlysampledsignals
        self.compare_signals_das(neo_signals, nixgroup.data_arrays)
        neo_eests = neoseg.epochs + neoseg.events + neoseg.spiketrains
        self.compare_eests_mtags(neo_eests, nixgroup.multi_tags)

    def compare_signals_das(self, neosignals, data_arrays):
        for sig in neosignals:
            if self.io._find_lazy_loaded(sig) is not None:
                sig = self.io.load_lazy_object(sig)
            dalist = list()
            for idx in itertools.count():
                nixname = "{}.{}".format(sig.name, idx)
                if nixname in data_arrays:
                    dalist.append(data_arrays[nixname])
                else:
                    break
            _, nsig = np.shape(sig)
            self.assertEqual(nsig, len(dalist))
            self.compare_signal_dalist(sig, dalist)

    def compare_signal_dalist(self, neosig, nixdalist):
        """
        Check if a Neo Analog or IrregularlySampledSignal matches a list of
        NIX DataArrays.

        :param neosig: Neo Analog or IrregularlySampledSignal
        :param nixdalist: List of DataArrays
        """
        nixmd = nixdalist[0].metadata
        self.assertTrue(all(nixmd == da.metadata for da in nixdalist))
        neounit = str(neosig.dimensionality)
        for sig, da in zip(np.transpose(neosig),
                           sorted(nixdalist, key=lambda d: d.name)):
            self.compare_attr(neosig, da)
            np.testing.assert_almost_equal(sig.magnitude, da)
            self.assertEqual(neounit, da.unit)
            timedim = da.dimensions[0]
            chandim = da.dimensions[1]
            if isinstance(neosig, AnalogSignal):
                self.assertIsInstance(timedim, nixio.SampledDimension)
                self.assertEqual(
                    pq.Quantity(timedim.sampling_interval, timedim.unit),
                    neosig.sampling_period
                )
                self.assertEqual(
                    pq.Quantity(timedim.offset, timedim.unit),
                    neosig.t_start
                )
            elif isinstance(neosig, IrregularlySampledSignal):
                self.assertIsInstance(timedim, nixio.RangeDimension)
                np.testing.assert_almost_equal(neosig.times.magnitude,
                                               timedim.ticks)
                self.assertEqual(timedim.unit,
                                 str(neosig.times.dimensionality))
            self.assertIsInstance(chandim, nixio.SetDimension)

    def compare_eests_mtags(self, eestlist, mtaglist):
        self.assertEqual(len(eestlist), len(mtaglist))
        for eest in eestlist:
            if self.io._find_lazy_loaded(eest) is not None:
                eest = self.io.load_lazy_object(eest)
            mtag = mtaglist[eest.name]
            if isinstance(eest, Epoch):
                self.compare_epoch_mtag(eest, mtag)
            elif isinstance(eest, Event):
                self.compare_event_mtag(eest, mtag)
            elif isinstance(eest, SpikeTrain):
                self.compare_spiketrain_mtag(eest, mtag)

    def compare_epoch_mtag(self, epoch, mtag):
        self.assertEqual(mtag.type, "neo.epoch")
        self.compare_attr(epoch, mtag)
        np.testing.assert_almost_equal(epoch.times.magnitude, mtag.positions)

        np.testing.assert_almost_equal(epoch.durations.magnitude, mtag.extents)
        self.assertEqual(mtag.positions.unit,
                         str(epoch.times.units.dimensionality))
        self.assertEqual(mtag.extents.unit,
                         str(epoch.durations.units.dimensionality))
        for neol, nixl in zip(epoch.labels,
                              mtag.positions.dimensions[0].labels):
            # Dirty. Should find the root cause instead
            if isinstance(neol, bytes):
                neol = neol.decode()
            if isinstance(nixl, bytes):
                nixl = nixl.decode()
            self.assertEqual(neol, nixl)

    def compare_event_mtag(self, event, mtag):
        self.assertEqual(mtag.type, "neo.event")
        self.compare_attr(event, mtag)
        np.testing.assert_almost_equal(event.times.magnitude, mtag.positions)
        self.assertEqual(mtag.positions.unit, str(event.units.dimensionality))
        for neol, nixl in zip(event.labels,
                              mtag.positions.dimensions[0].labels):
            # Dirty. Should find the root cause instead
            # Only happens in 3.2
            if isinstance(neol, bytes):
                neol = neol.decode()
            if isinstance(nixl, bytes):
                nixl = nixl.decode()
            self.assertEqual(neol, nixl)

    def compare_spiketrain_mtag(self, spiketrain, mtag):
        self.assertEqual(mtag.type, "neo.spiketrain")
        self.compare_attr(spiketrain, mtag)
        np.testing.assert_almost_equal(spiketrain.times.magnitude,
                                       mtag.positions)
        if len(mtag.features):
            neowf = spiketrain.waveforms
            nixwf = mtag.features[0].data
            self.assertEqual(np.shape(neowf), np.shape(nixwf))
            self.assertEqual(nixwf.unit, str(neowf.units.dimensionality))
            np.testing.assert_almost_equal(neowf.magnitude, nixwf)
            self.assertIsInstance(nixwf.dimensions[0], nixio.SetDimension)
            self.assertIsInstance(nixwf.dimensions[1], nixio.SetDimension)
            self.assertIsInstance(nixwf.dimensions[2], nixio.SampledDimension)

    def compare_attr(self, neoobj, nixobj):
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

    @classmethod
    def create_nix_file(cls):
        cls.filename = "nixio_testfile.h5"
        nixfile = NixIO(cls.filename, "rw")
        cls.io = nixfile

        nix_block_a = nixfile.nix_file.create_block(cls.rword(10), "neo.block")
        nix_block_a.definition = cls.rsentence(5, 10)
        nix_block_b = nixfile.nix_file.create_block(cls.rword(10), "neo.block")
        nix_block_b.definition = cls.rsentence(3, 3)

        nix_block_a.metadata = nixfile.nix_file.create_section(
            nix_block_a.name, nix_block_a.name+".metadata"
        )

        nix_block_b.metadata = nixfile.nix_file.create_section(
            nix_block_b.name, nix_block_b.name+".metadata"
        )

        nix_blocks = [nix_block_a, nix_block_b]

        for blk in nix_blocks:
            allspiketrains = list()
            allsignalgroups = list()
            for ind in range(2):
                group = blk.create_group(cls.rword(), "neo.segment")
                group.definition = cls.rsentence(10, 15)

                group_md = blk.metadata.create_section(group.name,
                                                       group.name+".metadata")
                group.metadata = group_md

                for n in range(3):
                    siggroup = list()
                    asig_name = "{}_asig{}".format(cls.rword(10), n)
                    asig_definition = cls.rsentence(5, 5)
                    asig_md = group_md.create_section(asig_name,
                                                      asig_name+".metadata")
                    for idx in range(3):
                        da_asig = blk.create_data_array(
                            "{}.{}".format(asig_name, idx),
                            "neo.analogsignal",
                            data=cls.rquant(100, 1)
                        )
                        da_asig.definition = asig_definition
                        da_asig.unit = "mV"

                        da_asig.metadata = asig_md

                        timedim = da_asig.append_sampled_dimension(0.01)
                        timedim.unit = "ms"
                        timedim.label = "time"
                        timedim.offset = 10
                        chandim = da_asig.append_set_dimension()
                        group.data_arrays.append(da_asig)
                        siggroup.append(da_asig)
                    allsignalgroups.append(siggroup)

                for n in range(2):
                    siggroup = list()
                    isig_name = "{}_isig{}".format(cls.rword(10), n)
                    isig_definition = cls.rsentence(12, 12)
                    isig_md = group_md.create_section(isig_name,
                                                      isig_name+".metadata")
                    isig_times = cls.rquant(200, 1, True)
                    for idx in range(10):
                        da_isig = blk.create_data_array(
                            "{}.{}".format(isig_name, idx),
                            "neo.irregularlysampledsignal",
                            data=cls.rquant(200, 1)
                        )
                        da_isig.definition = isig_definition
                        da_isig.unit = "mV"

                        da_isig.metadata = isig_md

                        timedim = da_isig.append_range_dimension(isig_times)
                        timedim.unit = "s"
                        timedim.label = "time"
                        chandim = da_isig.append_set_dimension()
                        group.data_arrays.append(da_isig)
                        siggroup.append(da_isig)
                    allsignalgroups.append(siggroup)

                # SpikeTrains with Waveforms
                for n in range(4):
                    stname = "{}-st{}".format(cls.rword(20), n)
                    times = cls.rquant(400, 1, True)
                    times_da = blk.create_data_array(
                        "{}.times".format(stname),
                        "neo.spiketrain.times",
                        data=times
                    )
                    times_da.unit = "ms"
                    mtag_st = blk.create_multi_tag(stname,
                                                   "neo.spiketrain",
                                                   times_da)
                    group.multi_tags.append(mtag_st)
                    mtag_st.definition = cls.rsentence(20, 30)
                    mtag_st_md = group.metadata.create_section(
                        mtag_st.name, mtag_st.name+".metadata"
                    )
                    mtag_st.metadata = mtag_st_md
                    mtag_st_md.create_property(
                        "t_stop", nixio.Value(max(times_da).item()+1)
                    )

                    waveforms = cls.rquant((40, 10, 35), 1)
                    wfname = "{}.waveforms".format(mtag_st.name)
                    wfda = blk.create_data_array(wfname, "neo.waveforms",
                                                 data=waveforms)
                    wfda.unit = "mV"
                    mtag_st.create_feature(wfda, nixio.LinkType.Indexed)
                    wfda.append_set_dimension()  # spike dimension
                    wfda.append_set_dimension()  # channel dimension
                    wftimedim = wfda.append_sampled_dimension(0.1)
                    wftimedim.unit = "ms"
                    wftimedim.label = "time"
                    wfda.metadata = mtag_st_md.create_section(
                        wfname, "neo.waveforms.metadata"
                    )
                    wfda.metadata.create_property("left_sweep", nixio.Value(20))
                    allspiketrains.append(mtag_st)

                # Epochs
                for n in range(5):
                    epname = "{}-ep{}".format(cls.rword(5), n)
                    times = cls.rquant(5, 1, True)
                    times_da = blk.create_data_array(
                        "{}.times".format(epname),
                        "neo.epoch.times",
                        data=times
                    )
                    times_da.unit = "s"

                    extents = cls.rquant(5, 1)
                    extents_da = blk.create_data_array(
                        "{}.durations".format(epname),
                        "neo.epoch.durations",
                        data=extents
                    )
                    extents_da.unit = "s"

                    mtag_ep = blk.create_multi_tag(
                        epname, "neo.epoch", times_da
                    )
                    group.multi_tags.append(mtag_ep)
                    mtag_ep.definition = cls.rsentence(2)
                    mtag_ep.extents = extents_da
                    label_dim = mtag_ep.positions.append_set_dimension()
                    label_dim.labels = cls.rsentence(5).split(" ")
                    # reference all signals in the group
                    for siggroup in allsignalgroups:
                        mtag_ep.references.extend(siggroup)

                # Events
                for n in range(2):
                    evname = "{}-ev{}".format(cls.rword(5), n)
                    times = cls.rquant(5, 1, True)
                    times_da = blk.create_data_array(
                        "{}.times".format(evname),
                        "neo.event.times",
                        data=times
                    )
                    times_da.unit = "s"

                    mtag_ev = blk.create_multi_tag(
                        evname, "neo.event", times_da
                    )
                    group.multi_tags.append(mtag_ev)
                    mtag_ev.definition = cls.rsentence(2)
                    label_dim = mtag_ev.positions.append_set_dimension()
                    label_dim.labels = cls.rsentence(5).split(" ")
                    # reference all signals in the group
                    for siggroup in allsignalgroups:
                        mtag_ev.references.extend(siggroup)


            # RCG
            nixrcg = blk.create_source(cls.rword(10),
                                       "neo.recordingchannelgroup")
            nixrcg.metadata = nix_blocks[0].metadata.create_section(
                nixrcg.name, "neo.recordingchannelgroup.metadata"
            )
            chantype = "neo.recordingchannel"
            # 3 channels
            for idx in [2, 5, 9]:
                channame = cls.rword(20)
                nixrc = nixrcg.create_source(channame, chantype)
                nixrc.definition = cls.rsentence(13)
                nixrc.metadata = nixrcg.metadata.create_section(
                    nixrc.name, "neo.recordingchannel.metadata"
                )
                nixrc.metadata.create_property("index", nixio.Value(idx))
                dims = tuple(map(nixio.Value, cls.rquant(3, 1)))
                nixrc.metadata.create_property("coordinates", dims)
                nixrc.metadata.create_property("coordinates.units",
                                               nixio.Value("um"))

            nunits = 2
            stsperunit = np.array_split(allspiketrains, nunits)
            for idx in range(nunits):
                unitname = "{}-unit{}".format(cls.rword(5), idx)
                nixunit = nixrcg.create_source(unitname, "neo.unit")
                nixunit.definition = cls.rsentence(4, 10)
                for st in stsperunit[idx]:
                    st.sources.append(nixrcg)
                    st.sources.append(nixunit)

            # pick a few signal groups to reference this RCG
            randsiggroups = np.random.choice(allsignalgroups, 5, False)
            for siggroup in randsiggroups:
                for sig in siggroup:
                    sig.sources.append(nixrcg)
        return nix_blocks

    @classmethod
    def delete_nix_file(cls):
        del cls.io
        os.remove(cls.filename)

    @staticmethod
    def rdate():
        return datetime(year=np.random.randint(1980, 2020),
                        month=np.random.randint(1, 13),
                        day=np.random.randint(1, 29))

    @classmethod
    def populate_dates(cls, obj):
        obj.file_datetime = cls.rdate()
        obj.rec_datetime = cls.rdate()

    @staticmethod
    def rword(n=10):
        return "".join(np.random.choice(list(string.ascii_letters), n))

    @classmethod
    def rsentence(cls, n=3, maxwl=10):
        return " ".join(cls.rword(np.random.randint(1, maxwl))
                        for _ in range(n))

    @classmethod
    def rdict(cls, nitems):
        rd = dict()
        for _ in range(nitems):
            key = cls.rword()
            value = cls.rword() if np.random.choice((0, 1)) \
                else np.random.uniform()
            rd[key] = value
        return rd

    @staticmethod
    def rquant(shape, unit, incr=False):
        try:
            dim = len(shape)
        except TypeError:
            dim = 1
        if incr and dim > 1:
            raise TypeError("Shape of quantity array may only be "
                            "one-dimensional when incremental values are "
                            "requested.")
        arr = np.random.random(shape)
        if incr:
            arr = np.array(np.cumsum(arr))
        return arr*unit

    @classmethod
    def create_all_annotated(cls):
        times = cls.rquant(1, pq.s)
        signal = cls.rquant(1, pq.V)
        blk = Block()
        blk.annotate(**cls.rdict(3))

        seg = Segment()
        seg.annotate(**cls.rdict(4))
        blk.segments.append(seg)

        asig = AnalogSignal(signal=signal, sampling_rate=pq.Hz)
        asig.annotate(**cls.rdict(2))
        seg.analogsignals.append(asig)

        isig = IrregularlySampledSignal(times=times, signal=signal,
                                        time_units=pq.s)
        isig.annotate(**cls.rdict(2))
        seg.irregularlysampledsignals.append(isig)

        epoch = Epoch(times=times, durations=times)
        epoch.annotate(**cls.rdict(4))
        seg.epochs.append(epoch)

        event = Event(times=times)
        event.annotate(**cls.rdict(4))
        seg.events.append(event)

        spiketrain = SpikeTrain(times=times, t_stop=pq.s, units=pq.s)
        spiketrain.annotate(**cls.rdict(6))
        seg.spiketrains.append(spiketrain)

        rcg = RecordingChannelGroup(channel_indexes=[1, 2])
        rcg.annotate(**cls.rdict(5))
        blk.recordingchannelgroups.append(rcg)

        unit = Unit()
        unit.annotate(**cls.rdict(2))
        rcg.units.append(unit)

        return blk


class NixIOWriteTest(NixIOTest):

    def setUp(self):
        self.filename = "nixio_testfile_write.h5"
        self.io = NixIO(self.filename, "ow")

    def tearDown(self):
        del self.io
        os.remove(self.filename)

    def test_block_write(self):
        """
        Write Block test

        Simple Block with basic attributes.
        """
        neo_block = Block(name=self.rword(),
                          description=self.rsentence())
        self.io.write_block(neo_block)
        nix_block = self.io.nix_file.blocks[0]
        self.assertEqual(nix_block.type, "neo.block")
        self.compare_attr(neo_block, nix_block)

    def test_block_cascade_write(self):
        """
        Write Cascade test

        All containers with basic attributes.
        """
        neo_block = Block(name=self.rword(),
                          description=self.rsentence())
        neo_segment = Segment(name=self.rword(),
                              description=self.rsentence(100))
        neo_rcg = RecordingChannelGroup(name=self.rword(30),
                                        description=self.rsentence(4),
                                        channel_indexes=[])
        neo_block.segments.append(neo_segment)
        neo_block.recordingchannelgroups.append(neo_rcg)
        self.io.write_block(neo_block)

        nix_block = self.io.nix_file.blocks[0]
        nix_group = nix_block.groups[0]
        nix_source = nix_block.sources[0]

        # block -> block base attr
        self.assertEqual(nix_block.type, "neo.block")
        self.compare_attr(neo_block, nix_block)

        # segment -> group base attr
        self.assertEqual(nix_group.type, "neo.segment")
        self.compare_attr(neo_segment, nix_group)

        # rcg -> source base attr
        self.assertEqual(nix_source.type, "neo.recordingchannelgroup")
        self.compare_attr(neo_rcg, nix_source)

    def test_container_len_neq_write(self):
        """
        Write: Container length test

        Change length after writing and check for failure.
        """
        neo_block = Block(name=self.rword(20),
                          description=self.rsentence(10, 10))
        neo_segment = Segment(name=self.rsentence(3, 13),
                              description=self.rsentence(10, 23))
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block)
        nix_block = self.io.nix_file.blocks[0]
        neo_segment_new = Segment(name=self.rword(40),
                                  description=self.rsentence(6, 7))
        neo_block.segments.append(neo_segment_new)
        self.assertNotEqual(len(neo_block.segments), len(nix_block.groups))

    def test_block_metadata_write(self):
        """
        Write: Block metadata test

        Test if block's metadata is written correctly.
        """
        neo_block = Block(name=self.rword(44),
                          description=self.rsentence(5))
        neo_block.rec_datetime = self.rdate()
        neo_block.file_datetime = self.rdate()
        neo_block.file_origin = "test_file_origin"
        self.io.write_block(neo_block)
        nix_block = self.io.nix_file.blocks[0]
        self.compare_attr(neo_block, nix_block)

    def test_anonymous_objects_write(self):
        """
        Write full data tree: Anonymous objects

        Create multiple trees that contain all types of objects, with no name or
        data to test the unique name generation.

        Results are not checked. The purpose of this test is to check that the
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

        times = self.rquant(1, pq.s)
        signal = self.rquant(1, pq.V)
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
        nixblocks = self.io.nix_file.blocks
        # Purpose of test is name generation
        #  Comparing everything takes too long
        self.compare_blocks(blocks, nixblocks)

    def test_name_conflict(self):
        """
        Test resolution of naming conflicts from Neo files.

        Object names in Neo may not be unique. The writer should resolve
        naming conflicts.
        """
        block = Block()
        nsegs = 10
        name = "name_conflict"

        times = self.rquant(1, pq.s)
        signal = self.rquant(1, pq.V)

        for n in range(nsegs):
            seg = Segment()
            block.segments.append(seg)
            seg.analogsignals.append(AnalogSignal(name=name,
                                                  signal=signal,
                                                  sampling_rate=pq.Hz))
            seg.irregularlysampledsignals.append(
                IrregularlySampledSignal(name=name,
                                         times=times,
                                         signal=signal,
                                         time_units=pq.s)
            )
            seg.epochs.append(Epoch(name=name, times=times, durations=times))
            seg.events.append(Event(name=name, times=times))
            seg.spiketrains.append(SpikeTrain(times=times, t_stop=pq.s,
                                              units=pq.s))
        self.io.write_block(block)

    def test_annotations_write(self):
        """
        Write full data tree: Annotations only
        """
        blk = self.create_all_annotated()

        self.io.write_block(blk)
        nixblk = self.io.nix_file.blocks[0]

        self.compare_attr(blk, nixblk)

        seg = blk.segments[0]
        self.compare_attr(seg, nixblk.groups[0])

        asig = seg.analogsignals[0]
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.analogsignal"]:
            self.compare_attr(asig, signal)

        isig = seg.irregularlysampledsignals[0]
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.irregularlysampledsignal"]:
            self.compare_attr(isig, signal)

        epoch = seg.epochs[0]
        nixepochs = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.epoch"]
        self.compare_attr(epoch, nixepochs[0])

        event = seg.events[0]
        nixevents = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.event"]
        self.compare_attr(event, nixevents[0])

        spiketrain = seg.spiketrains[0]
        nixspiketrains = [mtag for mtag in nixblk.groups[0].multi_tags
                          if mtag.type == "neo.spiketrain"]
        self.compare_attr(spiketrain, nixspiketrains[0])

        rcg = blk.recordingchannelgroups[0]
        nixrcgs = [src for src in nixblk.sources
                   if src.type == "neo.recordingchannelgroup"]
        self.compare_attr(rcg, nixrcgs[0])

    def test_metadata_structure_write(self):
        """
        Write metadata structure test

        Metadata hierarchy should mirror object hierarchy.
        """
        neoblk = self.create_all_annotated()
        self.io.write_block(neoblk)
        blk = self.io.nix_file.blocks[0]

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

    def test_waveforms_write(self):
        """
        Waveforms write test
        """
        blk = Block()
        seg = Segment()

        # create a spiketrain with some waveforms and attach it to a segment
        wf_array = self.rquant((20, 5, 10), pq.mV)
        times = self.rquant(20, pq.s, incr=True)+0.5*pq.s
        spkt = SpikeTrain(times, waveforms=wf_array,
                          name="spkt_with_waveform", t_stop=100.0,
                          t_start=0.5, left_sweep=5*pq.ms)
        seg.spiketrains.append(spkt)
        blk.segments.append(seg)

        self.io.write_block(blk)
        nix_block = self.io.nix_file.blocks[0]

        nix_spkt = nix_block.multi_tags["spkt_with_waveform"]
        self.assertAlmostEqual(nix_spkt.metadata["t_stop"], 100)
        self.assertAlmostEqual(nix_spkt.metadata["t_start"], 0.5)

        nix_wf = nix_spkt.features[0].data
        self.assertAlmostEqual(nix_wf.metadata["left_sweep"], 0.005)
        np.testing.assert_almost_equal(nix_wf, wf_array.magnitude)

    def test_basic_attr_write(self):
        """
        Write full data tree: Basic attributes test
        """
        times = self.rquant(1, pq.s)
        signal = self.rquant(1, pq.V)
        blk = Block(name=self.rword(5), description=self.rsentence(2))
        blk.file_origin = "/home/user/data/blockfile"
        self.populate_dates(blk)

        seg = Segment(name=self.rword(4),
                      description=self.rsentence(5))
        self.populate_dates(seg)
        seg.file_origin = "/home/user/data/segfile"
        blk.segments.append(seg)

        asig = AnalogSignal(name=self.rword(9),
                            description=self.rsentence(4),
                            signal=signal, sampling_rate=pq.Hz)
        asig.file_origin = "/home/user/data/asigfile"
        seg.analogsignals.append(asig)

        isig = IrregularlySampledSignal(name=self.rword(30),
                                        description=self.rsentence(5, 7),
                                        times=times, signal=signal,
                                        time_units=pq.s)
        isig.file_origin = "/home/user/data/isigfile"
        seg.irregularlysampledsignals.append(isig)

        epoch = Epoch(name=self.rword(14), description=self.rsentence(40, 10),
                      times=times, durations=times)
        epoch.file_origin = "/home/user/data/epochfile"
        seg.epochs.append(epoch)

        event = Event(name=self.rword(),
                      description=self.rsentence(50, 3),
                      times=times)
        event.file_origin = "/home/user/data/eventfile"
        seg.events.append(event)

        spiketrain = SpikeTrain(name=self.rword(20),
                                description=self.rsentence(70, 5),
                                times=times, t_stop=pq.s, units=pq.s)
        spiketrain.file_origin = "/home/user/data/spiketrainfile"
        seg.spiketrains.append(spiketrain)

        rcg = RecordingChannelGroup(
            name=self.rsentence(3, 10),
            description=self.rsentence(10, 8),
            channel_indexes=[1, 2]
        )
        rcg.file_origin = "/home/user/data/rcgfile"
        blk.recordingchannelgroups.append(rcg)

        unit = Unit(name=self.rword(40),
                    description=self.rsentence(30))
        unit.file_origin = "/home/user/data/unitfile"
        rcg.units.append(unit)

        self.io.write_block(blk)
        nixblk = self.io.nix_file.blocks[0]

        self.compare_attr(blk, nixblk)
        self.compare_attr(seg, nixblk.groups[0])
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.analogsignal"]:
            self.compare_attr(asig, signal)
        for signal in [da for da in nixblk.data_arrays
                       if da.type == "neo.irregularlysampledsignal"]:
            self.compare_attr(isig, signal)
        nixepochs = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.epoch"]
        self.compare_attr(epoch, nixepochs[0])
        nixevents = [mtag for mtag in nixblk.groups[0].multi_tags
                     if mtag.type == "neo.event"]
        self.compare_attr(event, nixevents[0])
        nixspiketrains = [mtag for mtag in nixblk.groups[0].multi_tags
                          if mtag.type == "neo.spiketrain"]
        self.compare_attr(spiketrain, nixspiketrains[0])
        nixrcgs = [src for src in nixblk.sources
                   if src.type == "neo.recordingchannelgroup"]
        self.compare_attr(rcg, nixrcgs[0])

    def test_all_write(self):
        """
        Write everything: Integration test with all features

        Test writing of all objects based on examples from the neo docs
        api_reference.html
        """

        neo_block_a = Block(name=self.rword(10),
                            description=self.rsentence(10))

        neo_block_b = Block(name=self.rword(3),
                            description=self.rsentence(7, 20))
        neo_blocks = [neo_block_a, neo_block_b]

        for blk in neo_blocks:
            for ind in range(3):
                seg = Segment(name="segment_{}".format(ind),
                              description="{} segment {}".format(blk.name, ind))
                blk.segments.append(seg)
                asig_data = self.rquant((100, 3), pq.mV)
                asignal = AnalogSignal(asig_data,
                                       name="some_sort_of_signal_{}".format(ind),
                                       t_start=0*pq.s,
                                       sampling_rate=10*pq.kHz)
                seg.analogsignals.append(asignal)

                isig_times = self.rquant(50, pq.ms, True)
                isig_data = self.rquant((50, 10), pq.nA)
                isignal = IrregularlySampledSignal(isig_times, isig_data)
                seg.irregularlysampledsignals.append(isignal)

        # create a spiketrain with some waveforms and attach it to a segment
        wf_array = self.rquant((40, 10, 35), pq.mV)
        seg_train_times = self.rquant(40, pq.s, True)
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

        # RCG with units and an ISS reference
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
        octotrode_rcg.irregularlysampledsignals.append(
            neo_blocks[1].segments[2].irregularlysampledsignals[0]
        )

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
        self.io.write_all_blocks(neo_blocks)
        nix_blocks = self.io.nix_file.blocks

        # ================== TESTING WRITTEN DATA ==================
        self.compare_blocks(neo_blocks, nix_blocks)
        for nixblk, neoblk in zip(nix_blocks, neo_blocks):
            self.assertEqual(nixblk.type, "neo.block")
            self.compare_attr(neoblk, nixblk)

            for nixgrp, neoseg in zip(nixblk.groups, neoblk.segments):
                self.compare_attr(neoseg, nixgrp)
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
                    self.compare_attr(neoseg.analogsignals[0],
                                      nixasig)
                    self.assertEqual(nixasig.unit, "mV")
                    self.assertIs(nixasig.dimensions[0].dimension_type,
                                  nixio.DimensionType.Sample)
                    self.assertIs(nixasig.dimensions[1].dimension_type,
                                  nixio.DimensionType.Set)
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
                    self.compare_attr(neoseg.irregularlysampledsignals[0],
                                      nixisig)
                    self.assertEqual(nixisig.unit, "nA")
                    self.assertIs(nixisig.dimensions[0].dimension_type,
                                  nixio.DimensionType.Range)
                    self.assertIs(nixisig.dimensions[1].dimension_type,
                                  nixio.DimensionType.Set)
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
        self.compare_attr(neo_spiketrain, nix_spiketrain)

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
                      nixio.DimensionType.Set)
        self.assertIs(nix_waveforms.dimensions[1].dimension_type,
                      nixio.DimensionType.Set)
        self.assertIs(nix_waveforms.dimensions[2].dimension_type,
                      nixio.DimensionType.Sample)

        # no time dimension specified when creating - defaults to 1 s
        wf_time_dim = nix_waveforms.dimensions[2].unit
        wf_time_interval = nix_waveforms.dimensions[2].sampling_interval
        self.assertEqual(wf_time_dim, "s")
        self.assertAlmostEqual(wf_time_interval, 1.0)

        # RCGs
        # - Octotrode
        nix_octotrode = nix_blocks[1].sources["octotrode A"]
        self.compare_attr(octotrode_rcg, nix_octotrode)
        nix_channels = list(src for src in nix_octotrode.sources
                            if src.type == "neo.recordingchannel")
        self.assertEqual(len(nix_channels),
                         len(octotrode_rcg.channel_indexes))
        nix_channel_indexes = [c.metadata["index"] for c in nix_channels]
        for nixci, neoci in zip(nix_channel_indexes,
                                octotrode_rcg.channel_indexes):
            self.assertEqual(nixci, neoci)

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
        self.compare_attr(spiketrain_container_rcg, nix_pyram_rcg)
        nix_channels = list(src for src in nix_pyram_rcg.sources
                            if src.type == "neo.recordingchannel")
        self.assertEqual(len(nix_channels),
                         len(spiketrain_container_rcg.channel_indexes))
        nix_channel_indexes = [c.metadata["index"] for c in nix_channels]
        for nixci, neoci in zip(nix_channel_indexes,
                                spiketrain_container_rcg.channel_indexes):
            self.assertEqual(nixci, neoci)

        # - Pyramidal neuron Unit
        nix_pyram_nrn = nix_pyram_rcg.sources["Pyramidal neuron"]
        self.compare_attr(pyram_unit, nix_pyram_nrn)

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
        nix_rcg_a = nix_blocks[0].sources["RCG_1"]

        nix_channels = nix_rcg_a.sources
        nix_channel_indexes = [c.metadata["index"] for c in nix_channels]
        for nixci, neoci in zip(nix_channel_indexes,
                                rcg_a.channel_indexes):
            self.assertEqual(nixci, neoci)

        for sig_idx in range(n_neo_signals):
            nix_name = "{}.{}".format(neo_first_signal.name, sig_idx)
            nix_signal = nix_blocks[0].groups[0].data_arrays[nix_name]
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
        self.compare_attr(evt, nix_event)
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
        self.compare_attr(epc, nix_epoch)
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

    def test_partial_write(self):
        neo_block_a = Block(name=self.rword(),
                            description=self.rsentence())

        neo_block_b = Block(name=self.rword(),
                            description=self.rsentence())
        neo_blocks = [neo_block_a, neo_block_b]

        for blk in neo_blocks:
            for ind in range(5):
                seg = Segment(name="segment_{}".format(ind),
                              description="{} segment {}".format(blk.name, ind))
                blk.segments.append(seg)
                asig_data = self.rquant((100, 3), pq.mV)
                asignal = AnalogSignal(asig_data,
                                       name="some_sort_of_signal_{}".format(ind),
                                       t_start=0*pq.s,
                                       sampling_rate=10*pq.kHz)
                seg.analogsignals.append(asignal)

                isig_times = self.rquant(50, pq.ms, True)
                isig_data = self.rquant((50, 10), pq.nA)
                isignal = IrregularlySampledSignal(
                    isig_times, isig_data,
                    name="an_irregular_signal_{}".format(ind)
                )
                seg.irregularlysampledsignals.append(isignal)

        self.io.write_all_blocks(neo_blocks)
        nix_block = self.io.nix_file.blocks[0]
        ndas = len(nix_block.data_arrays)
        # change signal
        asig = neo_blocks[0].segments[3].analogsignals[0]
        asig[:, 0] = self.rquant(100, pq.mV)

        self.io.write_all_blocks(neo_blocks)

        nix_block = self.io.nix_file.blocks[0]
        self.assertEqual(len(nix_block.data_arrays), ndas)


class NixIOReadTest(NixIOTest):

    nix_blocks = None

    @classmethod
    def setUpClass(cls):
        cls.nix_blocks = cls.create_nix_file()

    @classmethod
    def tearDownClass(cls):
        cls.delete_nix_file()

    def tearDown(self):
        pass

    def test_all_read(self):
        """
        Read everything: Integration test with all features

        Write all objects to a using nix directly, read them using the NixIO
        reader, and check for equality.
        """
        neo_blocks = self.io.read_all_blocks(cascade=True, lazy=False)
        self.compare_blocks(neo_blocks, self.nix_blocks)

    def test_lazyload_fullcascade_read(self):
        """
        Read everything lazily: Lazy integration test with all features
        """
        neo_blocks = self.io.read_all_blocks(cascade=True, lazy=True)
        # data objects should be empty
        for block in neo_blocks:
            for seg in block.segments:
                for asig in seg.analogsignals:
                    self.assertEqual(len(asig), 0)
                for isig in seg.irregularlysampledsignals:
                    self.assertEqual(len(isig), 0)
                for epoch in seg.epochs:
                    self.assertEqual(len(epoch), 0)
                for event in seg.events:
                    self.assertEqual(len(event), 0)
                for st in seg.spiketrains:
                    self.assertEqual(len(st), 0)
        self.compare_blocks(neo_blocks, self.nix_blocks)

    def test_lazyload_lazycascade_read(self):
        """
        Read everything lazily with lazy cascade
        """
        neo_blocks = self.io.read_all_blocks(cascade="lazy", lazy=True)
        self.compare_blocks(neo_blocks, self.nix_blocks)

    def test_fullload_lazycascade_read(self):
        """
        Read everything with lazy cascade
        """
        neo_blocks = self.io.read_all_blocks(cascade="lazy", lazy=False)
        self.compare_blocks(neo_blocks, self.nix_blocks)

    def test_nocascade(self):
        """
        Read a Block without cascading
        """
        nix_block = self.nix_blocks[0]
        blockpath = "/" + nix_block.name
        neo_block = self.io.read_block(blockpath, cascade=False, lazy=False)
        self.assertEqual(len(neo_block.segments), 0)
        self.compare_attr(neo_block, nix_block)


class NixIOHashTest(NixIOTest):

    def setUp(self):
        self.hash = NixIO._hash_object

    def _hash_test(self, objtype, argfuncs):
        attr = {}
        for arg, func in argfuncs.items():
            attr[arg] = func()

        obj_one = objtype(**attr)
        obj_two = objtype(**attr)
        hash_one = self.hash(obj_one)
        hash_two = self.hash(obj_two)
        self.assertEqual(hash_one, hash_two)

        for arg, func in argfuncs.items():
            chattr = attr.copy()
            chattr[arg] = func()
            obj_two = objtype(**chattr)
            hash_two = self.hash(obj_two)
            self.assertNotEqual(
                hash_one, hash_two,
                "Hash test failed with different '{}'".format(arg)
            )

    def test_block_seg_hash(self):
        argfuncs = {"name": self.rword,
                    "description": self.rsentence,
                    "rec_datetime": self.rdate,
                    "file_datetime": self.rdate,
                    # annotations
                    self.rword(): self.rword,
                    self.rword(): lambda: self.rquant((10, 10), pq.mV)}
        self._hash_test(Block, argfuncs)
        self._hash_test(Segment, argfuncs)
        self._hash_test(Unit, argfuncs)

    def test_rcg_hash(self):
        argfuncs = {"name": self.rword,
                    "description": self.rsentence,
                    "channel_indexes": lambda: np.random.random(10).tolist(),
                    "channel_names": lambda: self.rsentence(10).split(" "),
                    # RCG does not store coordinates
                    # "coordinates": lambda: [(np.random.random() * pq.cm,
                    #                          np.random.random() * pq.cm,
                    #                          np.random.random() * pq.cm)]*10,
                    # annotations
                    self.rword(): self.rword,
                    self.rword(): lambda: self.rquant((10, 10), pq.mV)}
        self._hash_test(RecordingChannelGroup, argfuncs)

    def test_analogsignal_hash(self):
        argfuncs = {"name": self.rword,
                    "description": self.rsentence,
                    "signal": lambda: self.rquant((10, 10), pq.mV),
                    "sampling_rate": lambda: np.random.random() * pq.Hz,
                    "t_start": lambda: np.random.random() * pq.sec,
                    "t_stop": lambda: np.random.random() * pq.sec,
                    # annotations
                    self.rword(): self.rword,
                    self.rword(): lambda: self.rquant((10, 10), pq.mV)}
        self._hash_test(AnalogSignal, argfuncs)

    def test_irregularsignal_hash(self):
        argfuncs = {"name": self.rword,
                    "description": self.rsentence,
                    "signal": lambda: self.rquant((10, 10), pq.mV),
                    "times": lambda: self.rquant(10, pq.ms, True),
                    # annotations
                    self.rword(): self.rword,
                    self.rword(): lambda: self.rquant((10, 10), pq.mV)}
        self._hash_test(IrregularlySampledSignal, argfuncs)

    def test_event_hash(self):
        argfuncs = {"name": self.rword,
                    "description": self.rsentence,
                    "times": lambda: self.rquant(10, pq.ms),
                    "durations": lambda: self.rquant(10, pq.ms),
                    "labels": lambda: self.rsentence(10).split(" "),
                    # annotations
                    self.rword(): self.rword,
                    self.rword(): lambda: self.rquant((10, 10), pq.mV)}
        self._hash_test(Event, argfuncs)
        self._hash_test(Epoch, argfuncs)

    def test_spiketrain_hash(self):
        argfuncs = {"name": self.rword,
                    "description": self.rsentence,
                    "times": lambda: self.rquant(10, pq.ms),
                    "t_start": lambda: -np.random.random() * pq.sec,
                    "t_stop": lambda: np.random.random() * pq.sec,
                    "waveforms": lambda: self.rquant((10, 10, 20), pq.mV),
                    # annotations
                    self.rword(): self.rword,
                    self.rword(): lambda: self.rquant((10, 10), pq.mV)}
        self._hash_test(SpikeTrain, argfuncs)


@unittest.skipIf(nomock, "Requires mock module")
class NixIOMockTest(NixIOTest):

    neo_blocks = None

    @classmethod
    def setUpClass(cls):
        # cls.create_nix_file()
        cls.filename = "nixio_testfile.h5"
        nixfile = NixIO(cls.filename, "rw")
        cls.io = nixfile

        nix_block_a = nixfile.nix_file.create_block(cls.rword(10), "neo.block")
        nix_block_a.definition = cls.rsentence(5, 10)

        nix_block_a.metadata = nixfile.nix_file.create_section(
            nix_block_a.name, nix_block_a.name+".metadata"
        )

        nix_block_a.create_group(cls.rword(), "neo.segment")
        cls.neo_blocks = cls.io.read_all_blocks()
        cls.write_attr_original = cls.io._write_attr_annotations

    @classmethod
    def tearDownClass(cls):
        cls.delete_nix_file()

    def tearDown(self):
        self.io._write_attr_annotations = self.write_attr_original

    def _mock_write_attr(self, objclass):
        typestr = str(objclass.__name__).lower()
        self.io._write_attr_annotations = mock.Mock(
            wraps=self.io._write_attr_annotations,
            side_effect=self.check_obj_type("neo.{}".format(typestr))
        )
        neo_blocks = self.neo_blocks
        self.modify_objects(neo_blocks, excludes=[objclass])
        self.io.write_all_blocks(neo_blocks)
        self.io._write_attr_annotations = self.write_attr_original

    def check_obj_type(self, typestring):
        neq = self.assertNotEqual

        def side_effect_func(*args, **kwargs):
            objclass = kwargs.get("nix_object", args[0])
            neq(objclass.type, typestring)
        return side_effect_func

    @classmethod
    def modify_objects(cls, objs, excludes=()):
        excludes = tuple(excludes)
        for obj in objs:
            if not (excludes and isinstance(obj, excludes)):
                obj.description = cls.rsentence()
            for container in getattr(obj, "_child_containers", []):
                children = getattr(obj, container)
                cls.modify_objects(children, excludes)

    def test_partial(self):
        """
        Partial write: All except specific type
        """
        for obj in NixIO.supported_objects:
            self._mock_write_attr(obj)



