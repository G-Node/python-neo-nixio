import unittest
import os

from .utils import build_fake_block
from neo2nix.nixio import NixIO, simple_attrs


class TestBlock(unittest.TestCase):

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.neob = build_fake_block()
        self.neos = self.neob.segments[0]
        self.neost = self.neos.spiketrains[0]

        self.io = NixIO(self.filename)
        self.io.write_block(self.neob, recursive=True)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_attributes(self):
        b1 = self.io.read_block(self.neob.name)
        seg = [s_i for s_i in b1.segments if s_i.name == self.neos.name][0]
        sig = [a_i for a_i in seg.spiketrains if a_i.name == self.neost.name][0]

        attrs = simple_attrs['default'] + simple_attrs['spiketrain']
        for attr_name in attrs:
            v_old = getattr(self.neost, attr_name)
            v_new = getattr(sig, attr_name)
            assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

    def test_annotations(self):
        """
         Annotations are tested only for Block as the procedure is equal for
         all objects.
        """
        pass

    def test_change_data(self):
        b1 = self.io.read_block(self.neob.name)
        s1 = b1.segments[0]
        sig = s1.spiketrains[0]

        nn = (sig.t_stop - sig.t_start)/2.
        sig[0] = nn

        self.io.write_block(b1)

        b2 = self.io.read_block(self.neob.name)
        s2 = b2.segments[0]
        assert len(s2.spiketrains) == len(s1.spiketrains)
        assert nn in [x[0] for x in s2.spiketrains]

    def test_change(self):
        description = 'hello, world!'

        b1 = self.io.read_block(self.neob.name)
        s1 = b1.segments[0]
        sig = s1.spiketrains[0]

        sig.description = description  # TODO add more attributes
        self.io.write_block(b1, recursive=True)

        b2 = self.io.read_block(self.neob.name)
        s2 = b2.segments[0]
        sig = s2.spiketrains[0]
        assert sig.description == description