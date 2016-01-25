# Copyright (c) 2014, German Neuroinformatics Node (G-Node)
#                     Achilleas Koutsou <achilleas.k@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the BSD License. See
# LICENSE file in the root of the Project.

import os
import unittest

from neo.core import Block, Segment

from neonix.io.nixio import NixIO
import nix


class NixIOTest(unittest.TestCase):
    # TODO: Simplify tests - lots of code duplication could go in setUp/tearDown

    def setUp(self):
        self.filename = "nixio_testfile.hd5"
        self.io = NixIO(self.filename)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_block(self):
        neo_block = Block(name="test_block", description="block for testing")
        self.io.write_block(neo_block)
        nix_file = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nix_block = nix_file.blocks[0]
        self.assertTrue(NixIO._equals(neo_block, nix_block))
        nix_file.close()

    def test_block_cascade(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block, cascade=True)
        nix_file = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nix_block = nix_file.blocks[0]
        self.assertEqual(nix_block.name, neo_block.name)
        self.assertEqual(nix_block.type, "neo.block")
        self.assertEqual(nix_block.definition, neo_block.description)
        nix_group = nix_block.groups[0]
        self.assertEqual(nix_group.name, neo_segment.name)
        self.assertEqual(nix_group.type, "neo.segment")
        self.assertEqual(nix_group.definition, neo_segment.description)
        self.assertTrue(NixIO._equals(neo_block, nix_block))
        nix_file.close()

    def test_segment(self):
        neo_block = Block(name="test_block", description="block for testing")
        self.io.write_block(neo_block)
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        self.io.write_segment(neo_segment, neo_block)
        nix_file = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nix_group = nix_file.blocks[0].groups[0]
        self.assertEqual(nix_group.name, neo_segment.name)
        self.assertEqual(nix_group.type, "neo.segment")
        self.assertEqual(nix_group.definition, neo_segment.description)
        self.assertTrue(NixIO._equals(neo_segment, nix_group))
        nix_file.close()

    def test_missing_block(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        with self.assertRaises(LookupError):
            self.io.write_segment(neo_segment, neo_block)

    def test_block_neq(self):
        neo_block = Block(name="test_block_neq",
                          description="block for testing neq")
        self.io.write_block(neo_block)
        nix_file = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nix_block = nix_file.blocks[0]
        neo_block.name = "foo"  # changing neo block name
        self.assertFalse(NixIO._equals(neo_block, nix_block))
        nix_file.close()

    def test_segment_neq(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment_neq",
                              description="segment for testing neq")
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block, cascade=True)
        nix_file = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nix_block = nix_file.blocks[0]
        neo_segment.name = "foo"  # changing neo segment (child) name
        self.assertFalse(NixIO._equals(neo_block, nix_block))
        nix_file.close()

    def test_container_len_neq(self):
        neo_block = Block(name="test_block", description="block for testing")
        neo_segment = Segment(name="test_segment",
                              description="segment for testing")
        neo_block.segments.append(neo_segment)
        self.io.write_block(neo_block, cascade=True)
        nix_file = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nix_block = nix_file.blocks[0]
        neo_segment_new = Segment(name="test_segment_2",
                                  description="second segment for testing")
        neo_block.segments.append(neo_segment_new)
        self.assertFalse(NixIO._equals(neo_block, nix_block))
        nix_file.close()

if __name__ == "__main__":
    unittest.main()
