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

from neonix.io import nixio


class NixIOTest(unittest.TestCase):

    def setUp(self):
        self.filename = "nixio_testfile.hd5"
        self.neo_block = Block(name="test", description="test description")
        self.io = nixio()

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

