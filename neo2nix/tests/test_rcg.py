import unittest
import os

from .utils import build_fake_block
from neo2nix.nixio import NixIO, simple_attrs


class TestRCG(unittest.TestCase):

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.neob = build_fake_block()
        self.rcg = self.neob.recordingchannelgroups[0]

        self.io = NixIO(self.filename)
        self.io.write_block(self.neob, recursive=True)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_attributes(self):
        b1 = self.io.read_block(self.neob.name)
        rcg = [r_i for r_i in b1.recordingchannelgroups if r_i.name == self.rcg.name][0]

        assert len(rcg.analogsignals) > 0

        attrs = simple_attrs['default'] + simple_attrs['recordingchannelgroup']
        for attr_name in attrs + ('name',):
            v_old = getattr(self.rcg, attr_name)
            v_new = getattr(rcg, attr_name)
            assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

    def test_annotations(self):
        """
         Annotations are tested only for Block as the procedure is equal for
         all objects.
        """
        pass

    def test_change_name(self):
        b1 = self.io.read_block(self.neob.name)
        rcg = [r_i for r_i in b1.recordingchannelgroups if r_i.name == self.rcg.name][0]

        new_name = rcg.name + 'foo'
        rcg.name = new_name

        self.io.write_block(b1)

        b2 = self.io.read_block(self.neob.name)
        assert len(b2.recordingchannelgroups) == len(b1.recordingchannelgroups)
        assert new_name in [x.name for x in b2.recordingchannelgroups]

    def test_change(self):
        description = 'hello, world!'

        b1 = self.io.read_block(self.neob.name)
        rcg1 = b1.recordingchannelgroups[0]

        rcg1.description = description  # TODO add more attributes
        self.io.write_block(b1, recursive=True)

        b2 = self.io.read_block(self.neob.name)
        rcg2 = b2.recordingchannelgroups[0]
        assert rcg2.description == description