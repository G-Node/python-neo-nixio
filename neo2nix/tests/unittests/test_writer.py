import unittest
import os

from neo2nix.nixio import Writer, NixHelp
import nix

from ..utils import build_fake_block


neo_block = build_fake_block()  # to increase speed


class TestWriter(unittest.TestCase):
    """
    run this from cmd:

    python -m unittest neo2nix/tests/unittests/test_writer.py
    """

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.f = nix.File.open(self.filename, nix.FileMode.Overwrite)

    def tearDown(self):
        self.f.close()
        os.remove(self.filename)

    def test_write_block(self):
        assert len(self.f.blocks) == 0

        nix_block = Writer.write_block(self.f, neo_block, True)

        assert len(self.f.blocks) == 1

        assert nix_block.name == neo_block.name
        assert nix_block.metadata is not None

        assert len(neo_block.segments) == len(nix_block.tags)
        assert len(neo_block.recordingchannelgroups) == len(nix_block.sources)

        attrs = NixHelp.default_meta_attr_names + NixHelp.block_meta_attrs
        for attr_name in attrs:
            v_old = getattr(neo_block, attr_name)
            if v_old is not None:
                v_new = nix_block.metadata[attr_name]
                assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

        neo_block.description = 'foo'
        del neo_block.segments[0]
        del neo_block.recordingchannelgroups[0]
        nix_block = Writer.write_block(self.f, neo_block, True)

        assert len(self.f.blocks) == 1
        assert len(neo_block.segments) == len(nix_block.tags)
        assert len(neo_block.recordingchannelgroups) == len(nix_block.sources)

    def test_write_segment(self):
        seg = neo_block.segments[0]

        nix_block = self.f.create_block('foo', 'bar')
        nix_block.metadata = self.f.create_section('foo', 'bar')

        nix_tag = Writer.write_segment(nix_block, seg, True)

        assert len(nix_block.tags) == 1

        assert nix_tag.name == seg.name
        assert nix_tag.metadata is not None

        assert len(seg.analogsignals) == len([x for x in nix_block.data_arrays if x.type == 'analogsignal'])
        assert len(seg.spiketrains) == len([x for x in nix_block.data_arrays if x.type == 'spiketrain'])
        assert len(seg.events) == len([x for x in nix_block.data_arrays if x.type == 'event'])
        assert len(seg.epochs) == len([x for x in nix_block.data_arrays if x.type == 'epoch'])

        attrs = NixHelp.default_meta_attr_names + NixHelp.segment_meta_attrs
        for attr_name in attrs:
            v_old = getattr(seg, attr_name)
            if v_old is not None:
                v_new = nix_tag.metadata[attr_name]
                assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

        seg.description = 'foo'
        del seg.analogsignals[0]
        del seg.spiketrains[0]
        del seg.events[0]
        del seg.epochs[0]
        nix_tag = Writer.write_segment(nix_block, seg, True)

        assert len(nix_block.tags) == 1
        assert len(seg.analogsignals) == len([x for x in nix_block.data_arrays if x.type == 'analogsignal'])
        assert len(seg.spiketrains) == len([x for x in nix_block.data_arrays if x.type == 'spiketrain'])
        assert len(seg.events) == len([x for x in nix_block.data_arrays if x.type == 'event'])
        assert len(seg.epochs) == len([x for x in nix_block.data_arrays if x.type == 'epoch'])

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