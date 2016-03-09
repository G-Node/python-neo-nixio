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
            if verbose:
                print_neo(blocks)
            nixfilename = os.path.splitext(datafilename)[0]+"_nix.h5"
            try:
                print("Writing data to {}".format(nixfilename))
                nixfile = NixIO(nixfilename)
                nixfile.write_all_blocks(blocks)
                print("\tDONE: file converted and saved to {}".
                      format(datafilename, nixfilename))
            except Exception as exc:
                printerr("\tERROR: The following error occurred during "
                         "conversion of file {}.".format(datafilename))
                printerr("\t      - {}".format(exc))


def print_neo(blocks):
    for bidx, block in enumerate(blocks):
        print("> ({}) Block: {}".format(bidx, block.name))
        for sidx, segment in enumerate(block.segments):
            print("     ├─> ({}) Segment: {}".format(sidx, segment.name))
            for asidx, asig in enumerate(segment.analogsignals):
                print("     │    ├─> ({}) AnalogSignal: {}".format(asidx,
                                                                   asig.name))
            for isidx, isig in enumerate(segment.irregularlysampledsignals):
                print("     │    ├─> ({}) IrregularlySampledSignal: {}".
                      format(isidx, isig.name))
            for epidx, ep in enumerate(segment.epochs):
                print("     │    ├─> ({}) Epoch: {}".format(epidx, ep.name))
            for evidx, ev in enumerate(segment.events):
                print("     │    ├─> ({}) Event: {}".format(evidx, ev.name))
            for stidx, st in enumerate(segment.spiketrains):
                print("     │    ├─> ({}) SpikeTrain: {}".format(stidx,
                                                                 st.name))
        for ridx, rcg in enumerate(block.recordingchannelgroups):
            print("     ├─> ({}) RCG: {}".format(ridx, rcg.name))
            for uidx, unit in enumerate(rcg.units):
                print("     │    ├─> ({}) Unit: {}".format(uidx, unit.name))
                for stidx, st in enumerate(unit.spiketrains):
                    print("     │    │    ├─> ({}*) SpikeTrain: {}".
                          format(stidx, st.name))


def printerr(message):
    print(message, file=sys.stderr)


if __name__ == "__main__":
    main()
