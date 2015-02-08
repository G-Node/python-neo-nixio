from base import NixBase
from segment import Segment
import nix


class Block(NixBase):

    def __init__(self, nix_file, nix_block):
        """
        Builds a Neo-like Block object attached to the NIX-backend.
        Works only if the 'nix_block' was previously saved using 'write'
        method of this library.

        Note: nix_file would not be necessary as soon as the reference from
        block to file is implemented in nixpy.

        :param nix_file:    NIX file where the block is located
        :param nix_block:   corresponding NIX block to build the object from
        :return:            Neo-like Block object
        """
        super(Block, self).__init__(nix_block)
        self._nix_file = nix_file

    @staticmethod
    def _get_metadata_attr_names():
        names = ('file_datetime', 'rec_datetime', 'index')
        return names + Block._default_metadata_attr_names

    @property
    def segments(self):
        tags = filter(lambda x: x.type == 'neo_segment', self._nix_object.tags)
        return [Segment(self._nix_object, tag) for tag in tags]

    @classmethod
    def write_block(cls, where, block, recursive=True):
        """
        Writes the given Neo block to the NIX file.

        :param where:       an instance of the NIX file
        :param block:       a Neo block instance to save to NIX
        :param recursive:   yes/no - write all block contents recursively
        :return:            an instance of neo2nix.Block
        """
        nix_block = where.create_block(block.name, 'neo_block')

        # root metadata section for block
        nix_block.metadata = where.create_section(block.name, 'neo_block')

        # section for base object metadata - description, file_origin, etc.
        base_meta = nix_block.metadata.create_section('_base', 'group')

        for attr_name in Block._get_metadata_attr_names():
            value = getattr(block, attr_name, None)
            if value:
                base_meta.create_property(attr_name, nix.Value(value))

        result = cls(where, nix_block)
        result.annotations = block.annotations

        if recursive:
            for segment in block.segments:
                Segment.write_segment(nix_block, segment, recursive=recursive)

        return result