import unittest
import os

from .utils import build_fake_block
from neo2nix.nixio import NixIO


class TestBlock(unittest.TestCase):

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.neob = build_fake_block()
        self.neos = self.neob.segments[0]
        self.neosig = self.neos.analogsignals[0]

        self.io = NixIO(self.filename)
        self.io.write_block(self.neob, recursive=True)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_attributes(self):
        b1 = self.io.read_block(self.neob.name)
        sig = b1.segments[0].analogsignals[0]

        attrs = NixIO._default_meta_attr_names + NixIO._analogsignal_meta_attrs
        for attr_name in attrs:
            v_old = getattr(self.neosig, attr_name)
            v_new = getattr(sig, attr_name)
            assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

    def test_annotations(self):
        """
         Annotations are tested only for Block as the procedure is equal for
         all objects.
        """
        pass

    def test_change_name(self):
        b1 = self.io.read_block(self.neob.name)
        s1 = b1.segments[0]
        sig = s1.analogsignals[0]

        new_name = sig.name + 'foo'
        sig.name = new_name

        self.io.write_block(b1)

        b2 = self.io.read_block(self.neob.name)
        s2 = b2.segments[0]
        assert len(s2.analogsignals) == len(s1.analogsignals)
        assert new_name in [x.name for x in s2.analogsignals]

    def test_change(self):
            description = 'hello, world!'

            b1 = self.io.read_block(self.neob.name)
            s1 = b1.segments[0]
            sig = s1.analogsignals[0]

            sig.description = description  # TODO add more attributes
            self.io.write_block(b1, recursive=True)

            b2 = self.io.read_block(self.neob.name)
            s2 = b2.segments[0]
            sig = s2.analogsignals[0]
            assert sig.description == description