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

    return b