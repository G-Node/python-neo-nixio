import unittest
import os
import numpy as np

from neo2nix.nixio import NixIO
from .utils import build_fake_block


class TestBlock(unittest.TestCase):

    def setUp(self):
        self.filename = "/tmp/unittest.h5"
        self.io = NixIO(self.filename)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_write_all(self):

        def validate(block):
            assert block.name == neo_block.name
            assert len(block.segments) == len(neo_block.segments)

            s1 = block.segments[0]
            s2 = neo_block.segments[0]
            assert s1.name == s2.name
            """
            assert len(s1.analogsignals) == len(s2.analogsignals)

            a1 = s1.analogsignals[0]
            a2 = s2.analogsignals[0]
            equals = [x == y for x, y in zip([e1 for e1 in a1[:]], [e2 for e2 in a2[:]])]
            assert np.array(equals).all()
            """

        neo_block = build_fake_block()

        self.io.write_block(neo_block)
        validate(self.io.read_all_blocks()[0])
        validate(self.io.read_block(neo_block.name))

        # TODO tests for proxy list, descrete file opening