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
        neoblock = Block(name="test_block", description="block for testing")
        self.io.write_block(neoblock)
        nixfile = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nixblock = nixfile.blocks[0]
        self.assertEqual(nixblock.name, neoblock.name)
        self.assertEqual(nixblock.type, "neo.block")
        self.assertEqual(nixblock.definition, neoblock.description)
        nixfile.close()

    def test_segment(self):
        neoblock = Block(name="test_block", description="block for testing")
        self.io.write_block(neoblock)
        neosegment = Segment(name="test_segment",
                             description="segment for testing")
        self.io.write_segment(neosegment)
        nixfile = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nixgroup = nixfile.blocks[0].groups[0]
        self.assertEqual(nixgroup.name, neosegment.name)
        self.assertEqual(nixgroup.type, "neo.segment")
        self.assertEqual(nixgroup.definition, neosegment.description)

if __name__ == "__main__":
    unittest.main()
