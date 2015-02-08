import unittest
import nix

from neo2nix.block import Block
from utils import build_fake_block


class TestBlock(unittest.TestCase):

    def setUp(self):
        self.neo_block = build_fake_block()

        f = nix.File.open("/tmp/unittest.h5", nix.FileMode.Overwrite)
        Block.write_block(f, self.neo_block, recursive=False)
        f.close()

        self.f = nix.File.open("/tmp/unittest.h5", nix.FileMode.ReadWrite)

    def tearDown(self):
        self.f.close()

    def test_attributes(self):
        b = Block(self.f, self.f.blocks[0])

        assert b.type == 'neo_block'
        assert len(b.segments) == 0

        for name in Block._get_metadata_attr_names() + ('name',):
            v_old = getattr(self.neo_block, name)
            v_new = getattr(b, name)
            assert v_new == v_old, "%s != %s" % (str(v_old), str(v_new))

    def test_change(self):
        description = 'hello, world!'

        b = Block(self.f, self.f.blocks[0])
        b.description = description  # TODO add more attributes


        b1 = Block(self.f, self.f.blocks[0])
        assert b1.description == description