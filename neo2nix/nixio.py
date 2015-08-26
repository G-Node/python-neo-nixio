from neo.core import objectlist, objectnames, class_by_name
from neo.core import Block, Event, Epoch, Segment, AnalogSignal
from neo.io.baseio import BaseIO

import quantities as pq
import nix
import os


# -------------------------------------------
# file operations
# -------------------------------------------


def file_transaction(method):
    """
    A decorator that opens the file before and closes after a given I/O method
    execution.

    :param method: a method to execute between opening and closing a file.
    :return:
    """
    def wrapped(*args, **kwargs):
        instance = args[0]
        instance.f.open()

        result = method(*args, **kwargs)
        
        instance.f.close()
        return result

    return wrapped


class FileHandler(object):

    def __init__(self, filename, readonly=False):
        """
        Initialize new IO instance.

        If the file does not exist, it will be created.
        This I/O works in a detached mode.

        :param filename: full path to the file (like '/tmp/foo.h5')
        """
        self.filename = filename
        self.readonly = readonly
        self.handle = None  # future NIX file handle

    def open(self):
        if os.path.exists(self.filename):
            if self.readonly:
                filemode = nix.FileMode.ReadOnly
            else:
                filemode = nix.FileMode.ReadWrite
        else:
            filemode = nix.FileMode.Overwrite

        self.handle = nix.File.open(self.filename, filemode)

    def close(self):
        self.handle.close()


# -------------------------------------------
# NIX I/O helpers
# -------------------------------------------


class NixHelp:

    default_meta_attr_names = ('description', 'file_origin')
    block_meta_attrs = ('file_datetime', 'rec_datetime', 'index')
    segment_meta_attrs = ('file_datetime', 'rec_datetime', 'index')
    analogsignal_meta_attrs = ('channel_index',)
    
    @staticmethod
    def get_or_create_section(root_section, group_name, name):
        try:
            group_sec = root_section.sections[group_name + 's']
        except KeyError:
            group_sec = root_section.create_section(group_name + 's', group_name)

        try:
            target_sec = group_sec.sections[name]
        except KeyError:
            target_sec = group_sec.create_section(name, group_name)

        return target_sec

    @staticmethod
    def get_block(nix_file, block_id):
        try:
            return nix_file.blocks[block_id]
        except KeyError:
            raise NameError('Block with this id %s does not exist' % block_id)

    @staticmethod
    def get_obj_nix_name(obj, parent_id, obj_type):  # pure
        cases = {  # TODO these can be different
            'analogsignal': lambda x: "%s @@ %s" % (x.name, parent_id),
            'spiketrain': lambda x: "%s @@ %s" % (x.name, parent_id),
            'event': lambda x: "%s @@ %s" % (x.name, parent_id),
            'epoch': lambda x: "%s @@ %s" % (x.name, parent_id)
        }
        return cases[obj_type](obj)

    @staticmethod
    def get_obj_neo_name(nix_name, obj_type):  # pure
        cases = {  # TODO these can be different
           'analogsignal': lambda x: x.split('@@')[0][:-1],
           'spiketrain': lambda x: x.split('@@')[0][:-1],
           'event': lambda x: x.split('@@')[0][:-1],
           'epoch': lambda x: x.split('@@')[0][:-1]
        }
        return cases[obj_type](nix_name)

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


class ProxyList(object):
    """ An enhanced list that can load its members on demand. Behaves exactly
    like a regular list for members that are Neo objects.
    """

    def __init__(self, fh, block_id, parent_id, child_type):
        """
        :param io:          IO instance that can load items
        :param child_type:  a type of the children, like 'segment' or 'event'
        :param parent_id:   id of the parent object
        """
        self._fh = fh
        self._block_id = block_id
        self._parent_id = parent_id
        self._child_type = child_type
        self._cache = None

    @property
    def _data(self):
        if self._cache is None:
            should_close = False

            if self._fh.handle is None or not self._fh.handle.is_open():
                self._fh.open()
                should_close = True

            args = (self._fh, self._block_id, self._parent_id, self._child_type)
            self._cache = Reader.read_multiple(*args)

            if should_close:
                self._fh.close()

        return self._cache

    def __getitem__(self, index):
        return self._data.__getitem__(index)

    def __delitem__(self, index):
        self._data.__delitem__(index)

    def __len__(self):
        return self._data.__len__()

    def __setitem__(self, index, value):
        self._data.__setitem__(index, value)

    def insert(self, index, value):
        self._data.insert(index, value)

    def append(self, value):
        self._data.append(value)

    def reverse(self):
        self._data.reverse()

    def extend(self, values):
        self._data.extend(values)

    def remove(self, value):
        self._data.remove(value)

    def __str__(self):
        return '<' + self.__class__.__name__ + '>' + self._data.__str__()

    def __repr__(self):
        return '<' + self.__class__.__name__ + '>' + self._data.__repr__()


# -------------------------------------------
# Reader / Writer
# -------------------------------------------


class Reader:

    # -------------------------------------------
    # read multiple
    # -------------------------------------------

    @staticmethod
    def read_multiple(fh, block_id, parent_id, obj_type):
        """
        Reads multiple objects of the same type from a given parent (parent_id).

        :param fh:          handler with opened NIX file
        :param block_id:    block id from where to read
        :param parent_id:   source object id
        :param obj_type:    a type of object to fetch, like 'segment' or 'event'
        :return:            a list of fetched objects
        """
        nix_file = fh.handle
        results = []

        # TODO some refactoring here (group all NIX DAs and all Sources)

        if obj_type == 'block':
            results = [Reader.read_block(fh, b.name) for b in nix_file.blocks]

        elif obj_type == 'segment':
            tags = filter(lambda x: x.type == 'neo_segment', nix_file.blocks[block_id].tags)
            results = [Reader.read_segment(fh, block_id, tag.name) for tag in tags]

        elif obj_type == 'analogsignal':
            nix_tag = nix_file.blocks[block_id].tags[parent_id]
            signals = filter(lambda x: x.type == 'neo_analogsignal', nix_tag.references)
            results = [Reader.read_analogsignal(fh, block_id, da.name) for da in signals]

        return results

    # -------------------------------------------
    # read single
    # -------------------------------------------

    @staticmethod
    def read_block(fh, block_id):
        nix_block = NixHelp.get_block(fh.handle, block_id)

        b = Block(name=nix_block.name)

        nix_section = nix_block.metadata
        direct_attrs = NixHelp.default_meta_attr_names + NixHelp.block_meta_attrs

        for key, value in NixHelp.read_attributes(nix_section, direct_attrs).items():
            setattr(b, key, value)

        b.annotations = NixHelp.read_annotations(nix_section, direct_attrs)

        setattr(b, 'segments', ProxyList(fh, nix_block.name, nix_block.name, 'segment'))

        # TODO add more setters for relations

        return b

    @staticmethod
    def read_segment(fh, block_id, seg_id):
        nix_block = NixHelp.get_block(fh.handle, block_id)
        nix_tag = nix_block.tags[seg_id]

        seg = Segment(name=nix_tag.name)

        if nix_tag.metadata is not None:
            meta_attrs = NixHelp.default_meta_attr_names + NixHelp.segment_meta_attrs
            for attr_name in meta_attrs:
                try:
                    setattr(seg, attr_name, nix_tag.metadata[attr_name])
                except KeyError:
                    pass  # attr is not present

        # TODO: fetch annotations

        setattr(seg, 'analogsignals', ProxyList(fh, nix_block.name, nix_tag.name, 'analogsignal'))

        # TODO add more setters for relations

        return seg

    @staticmethod
    def read_analogsignal(fh, block_id, array_id):
        nix_block = NixHelp.get_block(fh.handle, block_id)
        nix_da = nix_block.data_arrays[array_id]

        params = {
            'name': NixHelp.get_obj_neo_name(nix_da.name, 'analogsignal'),
            'signal': nix_da[:],  # TODO think about lazy data loading
            'units': nix_da.unit,
            'dtype': nix_da.dtype,
            }

        s_dim = nix_da.dimensions[0]
        sampling = s_dim.sampling_interval * getattr(pq, s_dim.unit)
        if 'hz' in s_dim.unit.lower():
            params['sampling_rate'] = sampling
        else:
            params['sampling_period'] = sampling

        signal = AnalogSignal(**params)

        # fetch t_start from metadata

        if nix_da.metadata is not None:
            meta_attrs = NixHelp.default_meta_attr_names + NixHelp.analogsignal_meta_attrs
            for attr_name in meta_attrs:
                try:
                    setattr(signal, attr_name, nix_da.metadata[attr_name])
                except KeyError:
                    pass  # attr is not present

        # TODO: fetch annotations

        return signal


class Writer:

    @staticmethod
    def write_block(nix_file, block, recursive=True):
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

        meta_attrs = NixHelp.default_meta_attr_names + NixHelp.block_meta_attrs
        for attr_name in meta_attrs:
            if getattr(block, attr_name, None) is not None:
                metadata[attr_name] = getattr(block, attr_name, None)

        try:
            nix_block.metadata = nix_file.sections[block.name]
        except KeyError:
            nix_block.metadata = nix_file.create_section(block.name, 'block')

        NixHelp.write_metadata(nix_block.metadata, metadata)

        if recursive:
            existing = filter(lambda x: x.type == 'neo_segment', nix_block.tags)
            to_remove = set([x.name for x in existing]) - set([x.name for x in block.segments])

            for segment in block.segments:
                Writer.write_segment(nix_file, nix_block.name, segment, recursive=recursive)

            for name in to_remove:
                del nix_block.tags[name]

        return nix_block

    @staticmethod
    def write_segment(nix_file, block_id, segment, recursive=True):
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

        meta_attrs = NixHelp.default_meta_attr_names + NixHelp.segment_meta_attrs
        for attr_name in meta_attrs:
            if getattr(segment, attr_name, None) is not None:
                metadata[attr_name] = getattr(segment, attr_name, None)

        nix_tag.metadata = NixHelp.get_or_create_section(nix_block.metadata, 'segment', segment.name)
        NixHelp.write_metadata(nix_tag.metadata, metadata)

        if recursive:
            convert = lambda x: NixHelp.get_obj_nix_name(x, nix_tag.name, 'analogsignal')
            existing = list(filter(lambda x: x.type == 'neo_analogsignal', nix_tag.references))
            to_remove = set([x.name for x in existing]) - set([convert(x) for x in segment.analogsignals])
            to_append = set([convert(x) for x in segment.analogsignals]) - set([x.name for x in existing])

            for signal in segment.analogsignals:
                Writer.write_analogsignal(nix_file, nix_block.name, nix_tag.name, signal)

            names = [da.name for da in nix_tag.references if da.name in to_remove]
            for da_name in names:
                del nix_tag.references[da_name]

                # FIXME really delete unused arrays?

                del nix_block.data_arrays[da_name]

            for name in to_append:
                nix_tag.references.append(nix_block.data_arrays[name])

        return nix_tag

    @staticmethod
    def write_analogsignal(nix_file, block_id, tag_id, signal):
        """
        Writes the given Neo AnalogSignal to the NIX file.

        :param nix_file:    an open file where to save Block
        :param block_id:    an id of the block in NIX file where to save segment
        """
        nix_block = NixHelp.get_block(nix_file, block_id)
        obj_name = NixHelp.get_obj_nix_name(signal, tag_id, 'analogsignal')

        try:
            nix_array = nix_block.data_arrays[obj_name]

            # TODO update data?

        except KeyError:
            args = (obj_name, 'neo_analogsignal', signal.dtype, (0,))
            nix_array = nix_block.create_data_array(*args)
            nix_array.append(signal)

        nix_array.unit = signal.units.dimensionality.string

        if not nix_array.dimensions:
            nix_array.append_sampled_dimension(signal.sampling_rate.item())
        nix_array.dimensions[0].unit = signal.sampling_rate.units.dimensionality.string

        # prepare metadata to store
        metadata = dict(signal.annotations)

        meta_attrs = NixHelp.default_meta_attr_names + NixHelp.analogsignal_meta_attrs
        for attr_name in meta_attrs:
            if getattr(signal, attr_name, None) is not None:
                metadata[attr_name] = getattr(signal, attr_name, None)

        # special t_start serialization
        metadata['t_start'] = signal.t_start.item()
        metadata['t_start__unit'] = signal.t_start.units.dimensionality.string

        nix_array.metadata = NixHelp.get_or_create_section(nix_block.metadata, 'analogsignal', obj_name)
        NixHelp.write_metadata(nix_array.metadata, metadata)

        return nix_array
    

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

    def __init__(self, filename, readonly=False):
        """
        Initialize new IO instance.

        If the file does not exist, it will be created.
        This I/O works in a detached mode.

        :param filename: full path to the file (like '/tmp/foo.h5')
        """
        BaseIO.__init__(self, filename=filename)
        self.f = FileHandler(filename)
        self.readonly = readonly

    @file_transaction
    def read_all_blocks(self):
        return Reader.read_multiple(self.f, 'whatever', 'whatever', 'block')

    @file_transaction
    def read_block(self, block_id):
        return Reader.read_block(self.f, block_id)

    @file_transaction
    def write_block(self, block, recursive=True):
        Writer.write_block(self.f.handle, block, recursive=recursive)

