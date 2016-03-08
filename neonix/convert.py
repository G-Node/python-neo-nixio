from __future__ import print_function
import os
import sys
import neo
from neonix.io.nixio import NixIO


def main():
    if "-v" in sys.argv:
        verbose = True
    else:
        verbose = False
    for datafilename in [f for f in os.listdir(".") if os.path.isfile(f)]:
        print("Processing {}".format(datafilename))
        try:
            reader = neo.io.get_io(datafilename)
            print("File type: {}".format(reader.name))
            data = reader.read()
        except OSError:
            printerr("\tNOTICE: file {} does not have an extension "
                     "known to Neo.".format(datafilename))
            continue
        except Exception as exc:
            printerr("\tERROR reading file {}.".format(datafilename))
            printerr("\t     - {}".format(exc))
            continue
        blocks = []
        try:
            blkiter = iter(data)
        except TypeError:
            blkiter = iter([data])
        for item in blkiter:
            if isinstance(item, neo.core.Block):
                # filter out non-blocks
                blocks.append(item)
        if blocks:
            nixfilename = os.path.splitext(datafilename)[0]+"_nix.h5"
            nixfile = NixIO(nixfilename)
            nixfile.write_all_blocks(blocks)
            print("\tDONE: file converted and saved to {}".
                  format(datafilename, nixfilename))


if __name__ == "__main__":
    main()
