import unittest
import os

from .utils import build_fake_block
from neo2nix.nixio import NixIO


class TestBlock(unittest.TestCase):

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.neob = build_fake_block()
        self.neos = self.neob.segments[0]

        self.io = NixIO(self.filename)
        self.io.write_block(self.neob, recursive=True)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_attributes(self):
        b1 = self.io.read_block(self.neob.name)
        s1 = b1.segments[0]

        assert len(s1.analogsignals) > 0

        attrs = NixIO._default_meta_attr_names + NixIO._segment_meta_attrs
        for attr_name in attrs + ('name',):
            v_old = getattr(self.neos, attr_name)
            v_new = getattr(s1, attr_name)
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

        new_name = s1.name + 'foo'
        s1.name = new_name

        self.io.write_block(b1)

        b2 = self.io.read_block(self.neob.name)
        assert len(b2.segments) == len(b1.segments)
        assert new_name in [x.name for x in b2.segments]

    def test_change(self):
        description = 'hello, world!'

        b1 = self.io.read_block(self.neob.name)
        s1 = b1.segments[0]

        s1.description = description  # TODO add more attributes
        self.io.write_block(b1, recursive=True)

        b2 = self.io.read_block(self.neob.name)
        s2 = b2.segments[0]
        assert s2.description == description