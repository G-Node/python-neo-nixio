from neo.core import objectlist, objectnames, class_by_name
from neo.core import Block, Event, Epoch, Segment
from neo.io.baseio import BaseIO

from neo2nix.proxy import ProxyList
import nix
import os


def file_transaction(method):
    """
    A decorator that opens the file before and closes after a given method
    execution.

    :param method: a method to execute between opening and closing a file.
    :return:
    """
    def wrapped(*args, **kwargs):
        instance = args[0]
        instance.f = instance._open()
        result = method(*args, **kwargs)
        instance.f.close()
        return result

    return wrapped


class NixIO(BaseIO):
    """
    This I/O can read/write Neo objects into HDF5 format using NIX library.
    """

    is_readable = True
    is_writable = True

    supported_objects = objectlist
    readable_objects = objectlist
    writeable_objects = objectlist

    read_params = dict(zip(objectlist, [] * len(objectlist)))
    write_params = dict(zip(objectlist, [] * len(objectlist)))

    name = 'Nix IO'
    extensions = ['h5']
    mode = 'file'

    # specific to the IO

    _default_meta_attr_names = ('description', 'file_origin')
    _block_meta_attrs = ('file_datetime', 'rec_datetime', 'index')
    _segment_meta_attrs = ('file_datetime', 'rec_datetime', 'index')

    def __init__(self, filename, readonly=False):
        """
        Initialize new IO instance.

        If the file does not exist, it will be created.
        This I/O works in a detached mode.

        :param filename: full path to the file (like '/tmp/foo.h5')
        """
        BaseIO.__init__(self, filename=filename)
        self.readonly = readonly
        self.f = None  # future file handler

    def _open(self):
        if os.path.exists(self.filename):
            if self.readonly:
                filemode = nix.FileMode.ReadOnly
            else:
                filemode = nix.FileMode.ReadWrite
        else:
            filemode = nix.FileMode.Overwrite

        return nix.File.open(self.filename, filemode)

    # -------------------------------------------
    # helpers
    # -------------------------------------------


    @staticmethod
    def _get_or_create_section(entity_with_sec, name, s_type):
        try:
            return entity_with_sec.sections[name]
        except KeyError:
            return entity_with_sec.create_section(name, s_type)

    @staticmethod
    def _get_block(nix_file, block_id):
        try:
            return nix_file.blocks[block_id]
        except KeyError:
            raise NameError('Block with this id %s does not exist' % block_id)

    def _read_multiple(self, nix_file, parent_id, obj_type):
        """
        Reads multiple objects of the same type from a given parent (parent_id).

        :param nix_file:    opened NIX file
        :param parent_id:   source object id
        :param obj_type:    a type of object to fetch, like 'segment' or 'event'
        :return:            a list of fetched objects
        """
        if obj_type == 'block':
            return [self._read_block(nix_file, b.name) for b in nix_file.blocks]

        elif obj_type == 'segment':
            tags = filter(lambda x: x.type == 'neo_segment', nix_file.blocks[parent_id].tags)
            return [self._read_segment(nix_file, parent_id, tag.name) for tag in tags]

    # -------------------------------------------
    # internal I methods
    # -------------------------------------------

    def _read_block(self, nix_file, block_id):
        nix_block = self._get_block(nix_file, block_id)

        b = Block(name=nix_block.name)

        if nix_block.metadata is not None:
            meta_attrs = NixIO._default_meta_attr_names + NixIO._block_meta_attrs
            for attr_name in meta_attrs:
                try:
                    setattr(b, attr_name, nix_block.metadata[attr_name])
                except KeyError:
                    pass  # attr is not present

        setattr(b, 'segments', ProxyList(self, 'segment', nix_block.name))

        # TODO: fetch annotations

        # TODO add more setters for relations

        return b

    def _read_segment(self, nix_file, block_id, seg_id):
        nix_block = self._get_block(nix_file, block_id)

        try:
            nix_tag = nix_block.tags[seg_id]
        except KeyError:
            raise NameError("Segment with this id %s does not exist" % seg_id)

        seg = Segment(name=nix_tag.name)

        if nix_tag.metadata is not None:
            meta_attrs = NixIO._default_meta_attr_names + NixIO._segment_meta_attrs
            for attr_name in meta_attrs:
                try:
                    setattr(seg, attr_name, nix_tag.metadata[attr_name])
                except KeyError:
                    pass  # attr is not present

        # TODO: fetch annotations

        # TODO add more setters for relations

        return seg

    # -------------------------------------------
    # internal O methods
    # -------------------------------------------

    def _write_block(self, nix_file, block, recursive=True):
        """
        Writes the given Neo block to the NIX file.

        :param nix_file:    an open file where to save Block
        :param block:       a Neo block instance to save to NIX
        :param recursive:   write all block contents recursively
        """
        try:
            nix_block = nix_file.blocks[block.name]
        except KeyError:
            nix_block = nix_file.create_block(block.name, 'neo_block')

        # root metadata section for block
        nix_block.metadata = NixIO._get_or_create_section(nix_file, block.name, 'neo_block')

        meta_attrs = NixIO._default_meta_attr_names + NixIO._block_meta_attrs
        for attr_name in meta_attrs:
            value = getattr(block, attr_name, None)
            if value:
                if not type(value) in (list, tuple):
                    value = (value,)
                values = [nix.Value(x) for x in value]

                try:
                    p = nix_block.metadata.props[attr_name]
                except KeyError:
                    p = nix_block.metadata.create_property(attr_name, values)

                if not p.values == values:
                    p.values = values

        # TODO: serialize annotations

        if recursive:
            for segment in block.segments:
                self._write_segment(nix_file, nix_block.name, segment, recursive=recursive)

    def _write_segment(self, nix_file, block_id, segment, recursive=True):
        """
        Writes the given Neo Segment to the NIX file.

        :param nix_file:    an open file where to save Block
        :param block_id:    an id of the block in NIX file where to save segment
        :param recursive:   write all segment contents recursively
        """
        nix_block = self._get_block(nix_file, block_id)

        try:
            nix_tag = nix_block.tags[segment.name]
        except KeyError:
            nix_tag = nix_block.create_tag(segment.name, 'neo_segment', [0.0])

        # root metadata section for block
        nix_tag.metadata = NixIO._get_or_create_section(nix_block.metadata, segment.name, 'neo_block')

        meta_attrs = NixIO._default_meta_attr_names + NixIO._block_meta_attrs
        for attr_name in meta_attrs:
            value = getattr(segment, attr_name, None)
            if value:
                if not type(value) in (list, tuple):
                    value = (value,)
                values = [nix.Value(x) for x in value]

                try:
                    p = nix_tag.metadata.props[attr_name]
                except KeyError:
                    p = nix_tag.metadata.create_property(attr_name, values)

                if not p.values == values:
                    p.values = values

        # TODO: serialize annotations

    # -------------------------------------------
    # I/O methods
    # -------------------------------------------

    @file_transaction
    def read_multiple(self, parent_id, obj_type):
        b = self._read_multiple(self.f, parent_id, obj_type)
        return b

    def read_all_blocks(self):
        return self.read_multiple('whatever', 'block')

    @file_transaction
    def read_block(self, block_id):
        b = self._read_block(self.f, block_id)
        return b

    @file_transaction
    def write_block(self, block, recursive=True):
        self._write_block(self.f, block, recursive=recursive)

