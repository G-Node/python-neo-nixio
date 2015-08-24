from neo.core import objectlist, objectnames, class_by_name
from neo.core import Block, Event, Epoch, Segment, AnalogSignal
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


class NixHelp:

    @staticmethod
    def get_or_create_section(entity_with_sec, name, s_type):
        try:
            return entity_with_sec.sections[name]
        except KeyError:
            return entity_with_sec.create_section(name, s_type)

    @staticmethod
    def get_block(nix_file, block_id):
        try:
            return nix_file.blocks[block_id]
        except KeyError:
            raise NameError('Block with this id %s does not exist' % block_id)

    @staticmethod
    def read_attributes(nix_section, attr_names):  # pure
        result = {}

        for attr_name in attr_names:
            if attr_name in nix_section:
                result[attr_name] = nix_section[attr_name]

        return result

    @staticmethod
    def read_annotations(nix_section, exclude_attrs):  # pure
        result = {}

        for prop in nix_section.props:
            key = prop.name
            value = nix_section[key]

            if key not in exclude_attrs:
                result[key] = value

        return result

    @staticmethod
    def write_metadata(nix_section, dict_to_store):
        for attr_name, value in dict_to_store.items():
            if value:
                if not type(value) in (list, tuple):
                    value = (value,)
                values = [nix.Value(x) for x in value]

                try:
                    p = nix_section.props[attr_name]
                except KeyError:
                    p = nix_section.create_property(attr_name, values)

                if not p.values == values:
                    p.values = values


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
    _analogsignal_meta_attrs = ('channel_index',)

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
        nix_block = NixHelp.get_block(nix_file, block_id)

        b = Block(name=nix_block.name)

        nix_section = nix_block.metadata
        direct_attrs = NixIO._default_meta_attr_names + NixIO._block_meta_attrs

        for key, value in NixHelp.read_attributes(nix_section, direct_attrs).items():
            setattr(b, key, value)

        b.annotations = NixHelp.read_annotations(nix_section, direct_attrs)

        setattr(b, 'segments', ProxyList(self, 'segment', nix_block.name))

        # TODO add more setters for relations

        return b

    def _read_segment(self, nix_file, block_id, seg_id):
        nix_block = NixHelp.get_block(nix_file, block_id)
        nix_tag = nix_block.tags[seg_id]

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

    def _read_analogsignal(self, nix_file, block_id, array_id):
        nix_block = NixHelp.get_block(nix_file, block_id)
        nix_da = nix_block.data_arrays[array_id]

        params = {
            'name': nix_da.name,
            'signal': nix_da[:],  # TODO think about lazy data loading
            'units': nix_da.unit,
            'dtype': nix_da.dtype,
            'sampling_period': nix_da.dimensions[0].sampling_interval
        }
        signal = AnalogSignal(**params)

        # fetch t_start from metadata

        if nix_da.metadata is not None:
            meta_attrs = NixIO._default_meta_attr_names + NixIO._analogsignal_meta_attrs
            for attr_name in meta_attrs:
                try:
                    setattr(signal, attr_name, nix_da.metadata[attr_name])
                except KeyError:
                    pass  # attr is not present

        # TODO: fetch annotations

        return signal

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

        # prepare metadata to store
        metadata = dict(block.annotations)

        meta_attrs = NixIO._default_meta_attr_names + NixIO._block_meta_attrs
        for attr_name in meta_attrs:
            if getattr(block, attr_name, None) is not None:
                metadata[attr_name] = getattr(block, attr_name, None)

        nix_block.metadata = NixHelp.get_or_create_section(nix_file, block.name, 'neo_block')
        NixHelp.write_metadata(nix_block.metadata, metadata)

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
        nix_block = NixHelp.get_block(nix_file, block_id)

        try:
            nix_tag = nix_block.tags[segment.name]
        except KeyError:
            nix_tag = nix_block.create_tag(segment.name, 'neo_segment', [0.0])

        # prepare metadata to store
        metadata = dict(segment.annotations)

        meta_attrs = NixIO._default_meta_attr_names + NixIO._segment_meta_attrs
        for attr_name in meta_attrs:
            if getattr(segment, attr_name, None) is not None:
                metadata[attr_name] = getattr(segment, attr_name, None)

        nix_tag.metadata = NixHelp.get_or_create_section(nix_block.metadata, segment.name, 'neo_segment')
        NixHelp.write_metadata(nix_tag.metadata, metadata)

        # TODO: serialize relations

    def _write_analogsignal(self, nix_file, block_id, signal):
        """
        Writes the given Neo AnalogSignal to the NIX file.

        :param nix_file:    an open file where to save Block
        :param block_id:    an id of the block in NIX file where to save segment
        """
        nix_block = NixHelp.get_block(nix_file, block_id)

        try:
            nix_array = nix_block.data_arrays[signal.name]
        except KeyError:
            args = (signal.name, 'neo_analogsignal', signal.dtype, (0,))
            nix_array = nix_block.create_data_array(*args)

        nix_array[:] = signal
        nix_array.unit = signal.units.dimensionality.string

        if not nix_array.dimensions:
            nix_array.append_sampled_dimension(signal.sampling_rate.item())
        nix_array.dimensions[0].unit = signal.sampling_rate.units.dimensionality.string

        # prepare metadata to store
        metadata = dict(signal.annotations)

        meta_attrs = NixIO._default_meta_attr_names + NixIO._analogsignal_meta_attrs
        for attr_name in meta_attrs:
            if getattr(signal, attr_name, None) is not None:
                metadata[attr_name] = getattr(signal, attr_name, None)

        # special t_start serialization
        metadata['t_start'] = nix.Value(signal.t_start.item())
        metadata['t_start__unit'] = nix.Value(signal.t_start.units.dimensionality.string)

        nix_array.metadata = NixHelp.get_or_create_section(nix_block.metadata, signal.name, 'neo_analogsignal')
        NixHelp.write_metadata(nix_array.metadata, metadata)

    # -------------------------------------------
    # I/O methods
    # -------------------------------------------

    @file_transaction
    def read_multiple(self, parent_id, obj_type):
        return self._read_multiple(self.f, parent_id, obj_type)

    def read_all_blocks(self):
        return self.read_multiple('whatever', 'block')

    @file_transaction
    def read_block(self, block_id):
        return self._read_block(self.f, block_id)

    @file_transaction
    def write_block(self, block, recursive=True):
        self._write_block(self.f, block, recursive=recursive)

