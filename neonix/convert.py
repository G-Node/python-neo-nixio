import os
import neo
from neonix.io.nixio import NixIO


def main():
    for datafilename in [f for f in os.listdir(".") if os.path.isfile(f)]:
        try:
            reader = neo.io.get_io(datafilename)
        except OSError:
            print("File {} does not have an extension known to Neo.".format(
                datafilename
            ))
            continue
        if neo.core.block.Block in reader.readable_objects:
            blocks = reader.read_all_blocks()
        else:
            print("{} does not support reading blocks.")
            continue
        nixfilename = os.path.splitext(datafilename)[0]+"_nix.h5"
        nixfile = NixIO(nixfilename)
        nixfile.write_all_blocks(blocks)


if __name__ == "__main__":
    main()
