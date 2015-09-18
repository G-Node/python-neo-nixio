import unittest
import os

from .utils import build_fake_block
from neo2nix.nixio import NixIO, simple_attrs


class TestUnit(unittest.TestCase):

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.neob = build_fake_block()
        self.rcg = self.neob.recordingchannelgroups[0]
        self.unit = self.rcg.units[0]

        self.io = NixIO(self.filename)
        self.io.write_block(self.neob, recursive=True)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_attributes(self):
        b1 = self.io.read_block(self.neob.name)
        rcg = [r_i for r_i in b1.recordingchannelgroups if r_i.name == self.rcg.name][0]
        unit = [u_i for u_i in rcg.units if u_i.name == self.unit.name][0]

        assert len(unit.spiketrains) > 0

        attrs = simple_attrs['default'] + simple_attrs['unit']
        for attr_name in attrs + ('name',):
            v_old = getattr(self.unit, attr_name)
            v_new = getattr(unit, attr_name)
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
        unit = [u_i for u_i in rcg.units if u_i.name == self.unit.name][0]

        new_name = unit.name + 'foo'
        unit.name = new_name

        self.io.write_block(b1)

        b2 = self.io.read_block(self.neob.name)
        rcg2 = [r_i for r_i in b2.recordingchannelgroups if r_i.name == self.rcg.name][0]
        assert len(rcg2.units) == len(rcg.units)
        assert new_name in [x.name for x in rcg2.units]

    def test_change(self):
        description = 'hello, world!'

        b1 = self.io.read_block(self.neob.name)
        rcg1 = b1.recordingchannelgroups[0]
        unit1 = rcg1.units[0]

        unit1.description = description  # TODO add more attributes
        self.io.write_block(b1, recursive=True)

        b2 = self.io.read_block(self.neob.name)
        rcg2 = b2.recordingchannelgroups[0]
        unit2 = rcg2.units[0]
        assert unit2.description == description