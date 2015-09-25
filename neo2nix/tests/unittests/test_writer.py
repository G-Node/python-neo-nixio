import unittest
import os

from neo2nix.nixio import Writer, simple_attrs
import numpy as np
import nix

from ..utils import build_fake_block


class TestWriter(unittest.TestCase):
    """
    run this from cmd:

    python -m unittest neo2nix/tests/unittests/test_writer.py
    """

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.f = nix.File.open(self.filename, nix.FileMode.Overwrite)
        self.b = build_fake_block()  # to increase speed

    def tearDown(self):
        self.f.close()
        os.remove(self.filename)

    @staticmethod
    def _validate_attrs(neo_obj, nix_obj):
        obj_type = Writer.Help.get_classname(neo_obj)

        for attr_name in simple_attrs['default'] + simple_attrs[obj_type]:
            v_old = getattr(neo_obj, attr_name)
            if v_old is not None:
                v_new = nix_obj.metadata[attr_name]
                assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

    def test_write_block(self):
        assert len(self.f.blocks) == 0

        nix_block = Writer.write_block(self.f, self.b, True)

        assert len(self.f.blocks) == 1

        assert nix_block.name == Writer.Help.get_obj_nix_name(self.b)
        assert nix_block.metadata is not None

        assert len(self.b.segments) == len(nix_block.tags)
        assert len(self.b.recordingchannelgroups) == len(nix_block.sources)

        TestWriter._validate_attrs(self.b, nix_block)

        del self.b.segments[0]
        del self.b.recordingchannelgroups[0]
        nix_block = Writer.write_block(self.f, self.b, True)

        assert len(self.f.blocks) == 1
        assert len(self.b.segments) == len(nix_block.tags)
        assert len(self.b.recordingchannelgroups) == len(nix_block.sources)

    def test_write_recordingchannelgroup(self):
        rcg = self.b.recordingchannelgroups[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')

        nix_source = Writer.write_recordingchannelgroup(nix_block, rcg, True)

        assert len(nix_block.sources) == 1

        assert nix_source.name == Writer.Help.get_obj_nix_name(rcg)
        assert nix_source.metadata is not None

        assert len(rcg.analogsignals) == len([x for x in nix_block.data_arrays if x.type == 'analogsignal'])
        assert len(rcg.irregularlysampledsignals) == len([x for x in nix_block.data_arrays if x.type == 'irregularlysampledsignal'])
        assert len(rcg.units) == len([x for x in nix_source.sources if x.type == 'unit'])

        TestWriter._validate_attrs(rcg, nix_source)

        del rcg.analogsignals[0]
        del rcg.irregularlysampledsignals[0]
        del rcg.units[0]
        nix_source = Writer.write_recordingchannelgroup(nix_block, rcg, True)

        assert len(nix_block.sources) == 1
        assert len(rcg.analogsignals) == len([x for x in nix_block.data_arrays if x.type == 'analogsignal'])
        assert len(rcg.irregularlysampledsignals) == len([x for x in nix_block.data_arrays if x.type == 'irregularlysampledsignal'])
        assert len(rcg.units) == len([x for x in nix_source.sources if x.type == 'unit'])

    def test_write_unit(self):
        rcg = self.b.recordingchannelgroups[0]
        unit = rcg.units[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')
        nix_rcg = nix_block.create_source('rcg', 'bar')
        nix_rcg.metadata = self.f.create_section('rcg', 'bar')

        nix_source = Writer.write_unit(nix_block, nix_rcg.name, unit, True)

        assert len(nix_rcg.sources) == 1
        assert nix_source.name == Writer.Help.get_obj_nix_name(unit)
        assert nix_source.metadata is not None

        assert len(unit.spiketrains) == len([x for x in nix_block.data_arrays if x.type == 'spiketrain'])

        TestWriter._validate_attrs(unit, nix_source)

        del unit.spiketrains[0]
        nix_source = Writer.write_unit(nix_block, nix_rcg.name, unit, True)

        assert len(nix_rcg.sources) == 1
        assert len(unit.spiketrains) == len([x for x in nix_block.data_arrays if x.type == 'spiketrain'])

    def test_write_segment(self):
        seg = self.b.segments[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')

        nix_tag = Writer.write_segment(nix_block, seg, True)

        assert len(nix_block.tags) == 1

        assert nix_tag.name == Writer.Help.get_obj_nix_name(seg)
        assert nix_tag.metadata is not None

        assert len(seg.analogsignals) == len([x for x in nix_block.data_arrays if x.type == 'analogsignal'])
        assert len(seg.irregularlysampledsignals) == len([x for x in nix_block.data_arrays if x.type == 'irregularlysampledsignal'])
        assert len(seg.spiketrains) == len([x for x in nix_block.data_arrays if x.type == 'spiketrain'])
        assert len(seg.events) == len([x for x in nix_block.data_arrays if x.type == 'event'])
        assert len(seg.epochs) == len([x for x in nix_block.data_arrays if x.type == 'epoch'])

        TestWriter._validate_attrs(seg, nix_tag)

        del seg.analogsignals[0]
        del seg.irregularlysampledsignals[0]
        del seg.spiketrains[0]
        del seg.events[0]
        del seg.epochs[0]
        nix_tag = Writer.write_segment(nix_block, seg, True)

        assert len(nix_block.tags) == 1
        assert len(seg.analogsignals) == len([x for x in nix_block.data_arrays if x.type == 'analogsignal'])
        assert len(seg.irregularlysampledsignals) == len([x for x in nix_block.data_arrays if x.type == 'irregularlysampledsignal'])
        assert len(seg.spiketrains) == len([x for x in nix_block.data_arrays if x.type == 'spiketrain'])
        assert len(seg.events) == len([x for x in nix_block.data_arrays if x.type == 'event'])
        assert len(seg.epochs) == len([x for x in nix_block.data_arrays if x.type == 'epoch'])

    def test_write_analogsignal(self):
        seg = self.b.segments[0]
        signal = seg.analogsignals[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')

        nix_array = Writer.write_analogsignal(nix_block, signal)

        assert len(nix_block.data_arrays) == 1

        assert nix_array.name == Writer.Help.get_obj_nix_name(signal)
        assert nix_array.metadata is not None
        assert 't_start' in nix_array.metadata
        assert 't_start__unit' in nix_array.metadata
        assert all(nix_array[:] == np.array(signal))

        TestWriter._validate_attrs(signal, nix_array)

    def test_write_irregularlysampledsignal(self):
        seg = self.b.segments[0]
        signal = seg.irregularlysampledsignals[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')

        nix_array = Writer.write_irregularlysampledsignal(nix_block, signal)

        assert len(nix_block.data_arrays) == 1

        assert nix_array.name == Writer.Help.get_obj_nix_name(signal)
        assert nix_array.metadata is not None
        assert all(nix_array[:] == np.array(signal))
        assert all(np.array(nix_array.dimensions[0].ticks) == signal.times)

        TestWriter._validate_attrs(signal, nix_array)

    def test_write_spiketrain(self):
        seg = self.b.segments[0]
        st = seg.spiketrains[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')

        nix_array = Writer.write_spiketrain(nix_block, st)

        assert len(nix_block.data_arrays) == 1

        assert nix_array.name == Writer.Help.get_obj_nix_name(st)
        assert nix_array.metadata is not None
        assert 't_start' in nix_array.metadata
        assert 't_start__unit' in nix_array.metadata
        assert 't_stop' in nix_array.metadata
        assert 't_stop__unit' in nix_array.metadata
        assert all(nix_array[:] == st.times)

        TestWriter._validate_attrs(st, nix_array)

    def test_write_event(self):
        seg = self.b.segments[0]
        event = seg.events[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')

        nix_array = Writer.write_event(nix_block, event)

        assert len(nix_block.data_arrays) == 1

        assert nix_array.name == Writer.Help.get_obj_nix_name(event)
        assert nix_array.metadata is not None
        assert all(nix_array[:] == event.times)

        for i, value in enumerate(event.labels):
            assert nix_array.dimensions[0].labels[i].encode('UTF-8') == value

        TestWriter._validate_attrs(event, nix_array)

    def test_write_epoch(self):
        seg = self.b.segments[0]
        epoch = seg.epochs[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')

        nix_array = Writer.write_epoch(nix_block, epoch)

        assert len(nix_block.data_arrays) == 1

        assert nix_array.name == Writer.Help.get_obj_nix_name(epoch)
        assert nix_array.metadata is not None
        assert all(nix_array[0] == epoch.times)
        assert all(nix_array[1] == epoch.durations)

        for i, value in enumerate(epoch.labels):
            assert nix_array.dimensions[0].labels[i].encode('UTF-8') == value

        TestWriter._validate_attrs(epoch, nix_array)

    def test_clean(self):
        nix_block = self.f.create_block('foo', 'bar')

        d1 = nix_block.create_data_array('d1', 'data', data=[1, 2, 3])
        d2 = nix_block.create_data_array('d2', 'data', data=[1, 2, 3])
        d3 = nix_block.create_data_array('d3', 'data', data=[1, 2, 3])
        d4 = nix_block.create_data_array('d4', 'data', data=[1, 2, 3])

        source = nix_block.create_source('foo', 'bar')
        d1.sources.append(source)
        d2.sources.append(source)

        tag = nix_block.create_tag('foo', 'bar', [0.0])
        tag.references.append(d2)
        tag.references.append(d3)

        assert len(nix_block.data_arrays) == 4

        Writer.Help.clean(nix_block)

        assert len(nix_block.data_arrays) == 3
        assert d4 not in nix_block.data_arrays