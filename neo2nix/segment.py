from base import NixBase
from analogsignal import AnalogSignal

import nix


class Segment(NixBase):

    def __init__(self, nix_block, nix_tag):
        """
        Builds a Neo-like Segment object attached to the NIX-backend.
        Works only if the 'nix_block' and 'nix_tag' were previously saved using
        'write' methods of this library.

        Note: nix_block would not be necessary as soon as the reference from
        tag to block is implemented in nixpy.

        :param nix_block:   NIX block where the segment is located
        :param nix_tag:     NIX Tag to build the segment from
        :return:            Neo-like Segment object
        """
        super(Segment, self).__init__(nix_tag)
        self._nix_block = nix_block

    @staticmethod
    def _get_metadata_attr_names():
        return Segment._default_metadata_attr_names

    @property
    def block(self):
        return self._nix_block

    @property
    def analogsignals(self):
        signal_filter = lambda x: x.type == 'neo_analogsignal'
        signals = filter(signal_filter, self._nix_object.references)

        return [AnalogSignal(self._nix_block, signal) for signal in signals]

    @property
    def spiketrains(self):
        pass

    @classmethod
    def write_segment(cls, block, segment, recursive=True):
        """
        Writes the given Neo Segment to the given NIX Block.

        :param block:       an instance of the NIX Block
        :param segment:     a Neo segment instance to save to NIX
        :param recursive:   yes/no - write all segment contents recursively
        :return:            an instance of neo2nix.Segment
        """
        nix_tag = block.create_tag(segment.name, 'neo_segment', [0.0])

        # root metadata section for segment
        nix_tag.metadata = block.metadata.create_section(segment.name, 'neo_segment')

        # section for base object metadata - description, file_origin, etc.
        base_meta = nix_tag.metadata.create_section('_base', 'group')

        for attr_name in Segment._get_metadata_attr_names():
            value = getattr(segment, attr_name, None)
            if value:
                base_meta.create_property(attr_name, nix.Value(value))

        result = cls(block, nix_tag)
        result.annotations = segment.annotations

        if recursive:
            create = lambda x: AnalogSignal.write_analogsignal(block, x)
            saved = [create(signal) for signal in segment.analogsignals]

            [nix_tag.references.append(signal._nix_object) for signal in saved]

        return result