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

    def test_write_block(self):
        assert len(self.f.blocks) == 0

        nix_block = Writer.write_block(self.f, self.b, True)

        assert len(self.f.blocks) == 1

        assert nix_block.name == Writer.Help.get_obj_nix_name(self.b)
        assert nix_block.metadata is not None

        assert len(self.b.segments) == len(nix_block.tags)
        assert len(self.b.recordingchannelgroups) == len(nix_block.sources)

        for attr_name in simple_attrs['default'] + simple_attrs['block']:
            v_old = getattr(self.b, attr_name)
            if v_old is not None:
                v_new = nix_block.metadata[attr_name]
                assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

        del self.b.segments[0]
        del self.b.recordingchannelgroups[0]
        nix_block = Writer.write_block(self.f, self.b, True)

        assert len(self.f.blocks) == 1
        assert len(self.b.segments) == len(nix_block.tags)
        assert len(self.b.recordingchannelgroups) == len(nix_block.sources)

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

        for attr_name in simple_attrs['default'] + simple_attrs['segment']:
            v_old = getattr(seg, attr_name)
            if v_old is not None:
                v_new = nix_tag.metadata[attr_name]
                assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

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

        for attr_name in simple_attrs['default'] + simple_attrs['analogsignal']:
            v_old = getattr(signal, attr_name)
            if v_old is not None:
                v_new = nix_array.metadata[attr_name]
                assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

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

        for attr_name in simple_attrs['default'] + simple_attrs['irregularlysampledsignal']:
            v_old = getattr(signal, attr_name)
            if v_old is not None:
                v_new = nix_array.metadata[attr_name]
                assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

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

        for attr_name in simple_attrs['default'] + simple_attrs['analogsignal']:
            v_old = getattr(st, attr_name)
            if v_old is not None:
                v_new = nix_array.metadata[attr_name]
                assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

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