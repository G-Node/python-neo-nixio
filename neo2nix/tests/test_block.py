import unittest
import os

from .utils import build_fake_block
from neo2nix.nixio import NixIO, simple_attrs


class TestBlock(unittest.TestCase):

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.neob = build_fake_block()

        self.io = NixIO(self.filename)
        self.io.write_block(self.neob, recursive=False)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_attributes(self):
        b1 = self.io.read_block(self.neob.name)

        assert len(b1.segments) == 0

        attrs = simple_attrs['default'] + simple_attrs['block']
        for attr_name in attrs + ('name',):
            v_old = getattr(self.neob, attr_name)
            v_new = getattr(b1, attr_name)
            assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

    def test_annotations(self):
        annotations = self.io.read_block(self.neob.name).annotations

        assert type(annotations) == dict
        assert type(annotations['string']) == str
        assert type(annotations['int']) == int
        assert type(annotations['float']) == float
        assert type(annotations['bool']) == bool

    def test_change_name(self):
        b1 = self.io.read_block(self.neob.name)

        b1.name += 'foo'

        self.io.write_block(b1)

        assert self.io.read_block(b1.name).name == b1.name
        assert len(self.io.read_all_blocks()) == 2

    def test_change(self):
        description = 'hello, world!'

        b1 = self.io.read_block(self.neob.name)
        b1.description = description  # TODO add more attributes
        self.io.write_block(b1, recursive=False)

        b2 = self.io.read_block(self.neob.name)
        assert b2.description == description