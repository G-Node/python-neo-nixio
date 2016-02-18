from __future__ import print_function
import os
import neo
from neonix.io.nixio import NixIO


def main():
    for datafilename in [f for f in os.listdir(".") if os.path.isfile(f)]:
        print("Processing {}".format(datafilename))
        try:
            reader = neo.io.get_io(datafilename)
            print("Filetype: {}".format(reader.name))
            data = reader.read()
            reader.close()
        except OSError:
            print("NOTICE: file does not have an extension known to Neo.".
                  format(datafilename))
            continue
        except Exception as exc:
            print("ERROR: Could not read data.".format(datafilename))
            print(exc)
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
            print("DONE: file converted and saved to {}".
                  format(datafilename, nixfilename))


if __name__ == "__main__":
    main()
