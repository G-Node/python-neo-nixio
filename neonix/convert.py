from __future__ import print_function
import os
import neo
from neonix.io.nixio import NixIO


def main():
    for datafilename in [f for f in os.listdir(".") if os.path.isfile(f)]:
        print("- {}".format(datafilename), end="")
        try:
            reader = neo.io.get_io(datafilename)
            data = reader.read()
            reader.close()
        except OSError:
            print("\rX {}\n\tdoes not have an extension known to Neo.".format(
                datafilename
            ))
            continue
        except Exception:
            print("\rX {}\n\tCould not read data.".format(
                datafilename
            ))
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
            print("\r* {}\n\tconverted and saved to {}".format(datafilename,
                                                             nixfilename))


if __name__ == "__main__":
    main()
