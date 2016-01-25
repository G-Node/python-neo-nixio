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
        self.assertEqual(nix_block.name, neo_block.name)
        self.assertEqual(nix_block.type, "neo.block")
        self.assertEqual(nix_block.definition, neo_block.description)
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

if __name__ == "__main__":
    unittest.main()
