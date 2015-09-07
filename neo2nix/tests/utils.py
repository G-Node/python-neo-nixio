from neo import *
from neo.test.generate_datasets import generate_one_simple_block


def build_fake_block():
    objects = [Block, Segment, RecordingChannelGroup,
               Event, Epoch, Unit, AnalogSignal, SpikeTrain]

    b = generate_one_simple_block(supported_objects=objects)
    b.name = 'foo'
    b.description = 'this is a test block'
    b.file_origin = '/tmp/nonexist.ing'

    b.annotations = {
        'string': 'hello, world!',
        'int': 42,
        'float': 42.0,
        'bool': True
    }

    # FIXME remove this when Neo is fixed (RCG - Unit branch)

    inds = [x for x in range(10)]
    names = ['foo' + str(x) for x in inds]

    rcg1 = RecordingChannelGroup(name='rcg1', channel_indexes=inds, channel_names=names)
    rcg2 = RecordingChannelGroup(name='rcg2', channel_indexes=inds, channel_names=names)

    for sig in b.segments[0].analogsignals:
        rcg1.analogsignals.append(sig)

    for sig in b.segments[1].analogsignals:
        rcg2.analogsignals.append(sig)

    b.recordingchannelgroups = [rcg1, rcg2]

    return b