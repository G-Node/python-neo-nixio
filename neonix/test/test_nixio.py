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

from neo.core import Block

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
        neoblock = Block(name="test", description="test description")
        self.io.write_block(neoblock)
        nixfile = nix.File.open(self.filename, nix.FileMode.ReadOnly)
        nixblock = nixfile.blocks[0]
        self.assertEqual(nixblock.name, neoblock.name)
        self.assertEqual(nixblock.type, neoblock.description)
        nixfile.close()


if __name__ == "__main__":
    unittest.main()
