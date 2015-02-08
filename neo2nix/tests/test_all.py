import unittest
import nix
import numpy as np

from neo2nix.block import Block
from utils import build_fake_block


class TestBlock(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        if hasattr(self, 'f1') and self.f1.is_open():
            self.f1.close()

        if hasattr(self, 'f2') and self.f2.is_open():
            self.f2.close()

    def test_write_all(self):

        def validate(block):
            assert block.name == neo_block.name
            assert len(block.segments) == len(neo_block.segments)

            s1 = block.segments[0]
            s2 = neo_block.segments[0]
            assert s1.name == s2.name
            assert len(s1.analogsignals) == len(s2.analogsignals)

            a1 = s1.analogsignals[0]
            a2 = s2.analogsignals[0]
            equals = [x == y for x, y in zip([e1 for e1 in a1[:]], [e2 for e2 in a2[:]])]
            assert np.array(equals).all()

        neo_block = build_fake_block()

        self.f1 = nix.File.open("/tmp/unittest.h5", nix.FileMode.Overwrite)
        validate(Block.write_block(self.f1, neo_block))
        self.f1.close()

        self.f2 = nix.File.open("/tmp/unittest.h5", nix.FileMode.ReadWrite)
        validate(Block(self.f2, self.f2.blocks[0]))
        self.f2.close()