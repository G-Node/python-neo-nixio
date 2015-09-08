from neo.core import objectlist, objectnames, class_by_name
from neo.core import Block, Event, Epoch, Segment, AnalogSignal, RecordingChannelGroup
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
    analogsignal_meta_attrs = ('name',)
    recordingchannelgroup_meta_attrs = ('name', 'channel_indexes', 'channel_names')

    @staticmethod
    def get_classname(neo_obj):
        return neo_obj.__class__.__name__.lower()

    @staticmethod
    def get_block(nix_file, block_id):
        try:
            return nix_file.blocks[block_id]
        except KeyError:
            raise NameError('Block with this id %s does not exist' % block_id)

    @staticmethod
    def get_obj_nix_name(obj):  # pure

        # FIXME make for all objects

        cases = {  # TODO these can be different
            'analogsignal': lambda x: str(hash(x.tostring())),
        }
        return cases[NixHelp.get_classname(obj)](obj)

    @staticmethod
    def get_obj_neo_name(nix_obj):  # pure
        cases = {  # TODO these can be different
           'analogsignal': lambda x: x.metadata['name'],
        }
        return cases[nix_obj.type](nix_obj)

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
    def extract_metadata(neo_obj):  # pure
        metadata = dict(neo_obj.annotations)

        custom_attrs = getattr(NixHelp, NixHelp.get_classname(neo_obj) + '_meta_attrs')
        for attr_name in NixHelp.default_meta_attr_names + custom_attrs:
            if getattr(neo_obj, attr_name, None) is not None:
                metadata[attr_name] = getattr(neo_obj, attr_name)

        return metadata


class ProxyList(object):
    """ An enhanced list that can load its members on demand. Behaves exactly
    like a regular list for members that are Neo objects.
    """

    def __init__(self, fh, fetch_func):
        """
        :param io:          IO instance that can load items
        :param child_type:  a type of the children, like 'segment' or 'event'
        :param parent_id:   id of the parent object
        """
        self._fh = fh
        self._fetch_func = fetch_func
        self._cache = None

    @property
    def _data(self):
        if self._cache is None:
            should_close = False

            if self._fh.handle is None or not self._fh.handle.is_open():
                self._fh.open()
                should_close = True

            self._cache = self._fetch_func(self._fh.handle)

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
    # read single
    # -------------------------------------------

    @staticmethod
    def read_block(fh, block_id):
        def read_segments(nix_file):
            tags = filter(lambda x: x.type == 'segment', nix_file.blocks[block_id].tags)
            return [Reader.read_segment(fh, block_id, tag.name) for tag in tags]

        def read_recordingchannelgroups(nix_file):
            sources = filter(lambda x: x.type == 'recordingchannelgroup', nix_file.blocks[block_id].sources)
            return [Reader.read_RCG(fh, block_id, src.name) for src in sources]

        nix_block = NixHelp.get_block(fh.handle, block_id)

        b = Block(name=nix_block.name)

        nix_section = nix_block.metadata
        direct_attrs = NixHelp.default_meta_attr_names + NixHelp.block_meta_attrs

        for key, value in NixHelp.read_attributes(nix_section, direct_attrs).items():
            setattr(b, key, value)

        b.annotations = NixHelp.read_annotations(nix_section, direct_attrs)

        setattr(b, 'segments', ProxyList(fh, read_segments))
        setattr(b, 'recordingchannelgroups', ProxyList(fh, read_recordingchannelgroups))

        # TODO add more setters for relations

        return b

    @staticmethod
    def read_segment(fh, block_id, seg_id):
        def read_analogsignals(nix_file):
            nix_tag = nix_file.blocks[block_id].tags[seg_id]
            signals = filter(lambda x: x.type == 'analogsignal', nix_tag.references)
            return [Reader.read_analogsignal(fh, block_id, da.name) for da in signals]

        nix_block = NixHelp.get_block(fh.handle, block_id)
        nix_tag = nix_block.tags[seg_id]

        seg = Segment(name=nix_tag.name)

        nix_section = nix_tag.metadata
        direct_attrs = NixHelp.default_meta_attr_names + NixHelp.segment_meta_attrs

        for key, value in NixHelp.read_attributes(nix_section, direct_attrs).items():
            setattr(seg, key, value)

        seg.annotations = NixHelp.read_annotations(nix_tag.metadata, direct_attrs)

        setattr(seg, 'analogsignals', ProxyList(fh, read_analogsignals))

        # TODO add more setters for relations

        return seg

    @staticmethod
    def read_RCG(fh, block_id, rcg_id):
        def read_analogsignals(nix_file):
            signals = filter(lambda x: x.type == 'analogsignal', nix_file.blocks[block_id].data_arrays)
            signals = [x for x in signals if nsn in [y.name for y in x.sources]]
            return [Reader.read_analogsignal(fh, block_id, da.name) for da in signals]

        nix_block = NixHelp.get_block(fh.handle, block_id)
        nix_source = nix_block.sources[rcg_id]
        nsn = nix_source.name

        params = {
            'name': nix_source.name,
            'channel_indexes': nix_source.metadata['channel_indexes']
        }
        rcg = RecordingChannelGroup(**params)

        nix_section = nix_source.metadata
        direct_attrs = NixHelp.default_meta_attr_names + NixHelp.recordingchannelgroup_meta_attrs

        for key, value in NixHelp.read_attributes(nix_section, direct_attrs).items():
            setattr(rcg, key, value)

        rcg.annotations = NixHelp.read_annotations(nix_section, direct_attrs)

        setattr(rcg, 'analogsignals', ProxyList(fh, read_analogsignals))

        # TODO add more setters for relations

        return rcg

    @staticmethod
    def read_analogsignal(fh, block_id, array_id):
        nix_block = NixHelp.get_block(fh.handle, block_id)
        nix_da = nix_block.data_arrays[array_id]

        params = {
            'name': NixHelp.get_obj_neo_name(nix_da),
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

        t_start = nix_da.metadata['t_start']
        t_start__unit = nix_da.metadata['t_start__unit']
        signal.t_start = pq.quantity.Quantity(float(t_start), t_start__unit)

        nix_section = nix_da.metadata
        direct_attrs = NixHelp.default_meta_attr_names + NixHelp.recordingchannelgroup_meta_attrs

        for key, value in NixHelp.read_attributes(nix_section, direct_attrs).items():
            setattr(signal, key, value)

        signal.annotations = NixHelp.read_annotations(nix_section, direct_attrs)

        return signal


class Writer:

    @staticmethod
    def get_or_create_section(root_section, group_name, name):
        if not isinstance(root_section, nix.Section):
            group_sec = root_section  # file is a root section for Blocks
        else:
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
    def write_metadata(nix_section, dict_to_store):
        for attr_name, value in dict_to_store.items():
            if value is not None:
                if not type(value) in (list, tuple):
                    value = (value,)
                values = [nix.Value(x) for x in value]

                try:
                    p = nix_section.props[attr_name]
                except KeyError:
                    p = nix_section.create_property(attr_name, values)

                if not p.values == values:
                    p.values = values

    @staticmethod
    def write_block(nix_file, block, recursive=True):
        """
        Writes the given Neo block to the NIX file.

        :param nix_file:    an open file where to save Block
        :param block:       a Neo block instance to save to NIX
        :param recursive:   write all block contents recursively
        """
        def write_multiple(neo_objs, nix_objs, obj_type):
            existing = filter(lambda x: x.type == obj_type, nix_objs)
            to_remove = set([x.name for x in existing]) - set([x.name for x in neo_objs])

            func = getattr(Writer, 'write_' + obj_type)
            for obj in neo_objs:
                func(nix_file, nix_block.name, obj, recursive=recursive)

            for name in to_remove:
                del nix_objs[name]

        try:
            nix_block = nix_file.blocks[block.name]
        except KeyError:
            nix_block = nix_file.create_block(block.name, 'block')

        nix_block.metadata = Writer.get_or_create_section(nix_file, 'block', block.name)
        Writer.write_metadata(nix_block.metadata, NixHelp.extract_metadata(block))

        if recursive:
            write_multiple(block.segments, nix_block.tags, 'segment')
            write_multiple(block.recordingchannelgroups, nix_block.sources, 'recordingchannelgroup')

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
            nix_tag = nix_block.create_tag(segment.name, 'segment', [0.0])

        nix_tag.metadata = Writer.get_or_create_section(nix_block.metadata, 'segment', segment.name)
        Writer.write_metadata(nix_tag.metadata, NixHelp.extract_metadata(segment))

        if recursive:
            convert = lambda x: NixHelp.get_obj_nix_name(x)
            existing = list(filter(lambda x: x.type == 'analogsignal', nix_tag.references))
            to_remove = set([x.name for x in existing]) - set([convert(x) for x in segment.analogsignals])
            to_append = set([convert(x) for x in segment.analogsignals]) - set([x.name for x in existing])

            for signal in segment.analogsignals:
                Writer.write_analogsignal(nix_file, nix_block.name, signal)

            names = [da.name for da in nix_tag.references if da.name in to_remove]
            for da_name in names:
                del nix_tag.references[da_name]

            for name in to_append:
                nix_tag.references.append(nix_block.data_arrays[name])

        return nix_tag


    @staticmethod
    def write_recordingchannelgroup(nix_file, block_id, rcg, recursive=True):
        """
        Writes the given Neo RecordingChannelGroup to the NIX file.

        :param nix_file:    an open file where to save Block
        :param block_id:    an id of the block in NIX file where to save segment
        :param recursive:   write all RCG contents recursively
        """
        nix_block = NixHelp.get_block(nix_file, block_id)

        try:
            nix_source = nix_block.sources[rcg.name]
        except KeyError:
            nix_source = nix_block.create_source(rcg.name, 'recordingchannelgroup')

        nix_source.metadata = Writer.get_or_create_section(nix_block.metadata, 'recordingchannelgroup', rcg.name)
        Writer.write_metadata(nix_source.metadata, NixHelp.extract_metadata(rcg))

        if recursive:
            convert = lambda x: NixHelp.get_obj_nix_name(x)

            existing = filter(lambda x: x.type == 'analogsignal', nix_block.data_arrays)
            existing = [x for x in existing if nix_source in x.sources]
            to_remove = set([x.name for x in existing]) - set([convert(x) for x in rcg.analogsignals])
            to_append = set([convert(x) for x in rcg.analogsignals]) - set([x.name for x in existing])

            for signal in rcg.analogsignals:
                Writer.write_analogsignal(nix_file, nix_block.name, signal)

            for nix_da in to_remove:
                del nix_block.data_arrays[nix_da].sources[nix_source.name]

            for nix_da in to_append:
                nix_block.data_arrays[nix_da].sources.append(nix_source)

        return nix_source

    @staticmethod
    def write_analogsignal(nix_file, block_id, signal):
        """
        Writes the given Neo AnalogSignal to the NIX file.

        :param nix_file:    an open file where to save Block
        :param block_id:    an id of the block in NIX file where to save segment
        """
        nix_block = NixHelp.get_block(nix_file, block_id)
        obj_name = NixHelp.get_obj_nix_name(signal)

        try:
            nix_array = nix_block.data_arrays[obj_name]

            # TODO update data?

        except KeyError:
            args = (obj_name, 'analogsignal', signal.dtype, (0,1))
            nix_array = nix_block.create_data_array(*args)
            nix_array.append(signal)

        nix_array.unit = signal.units.dimensionality.string

        if not nix_array.dimensions:
            nix_array.append_sampled_dimension(signal.sampling_rate.item())
        nix_array.dimensions[0].unit = signal.sampling_rate.units.dimensionality.string

        metadata = NixHelp.extract_metadata(signal)

        # special t_start serialization
        metadata['t_start'] = signal.t_start.item()
        metadata['t_start__unit'] = signal.t_start.units.dimensionality.string

        nix_array.metadata = Writer.get_or_create_section(nix_block.metadata, 'analogsignal', obj_name)
        Writer.write_metadata(nix_array.metadata, metadata)

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
        return [Reader.read_block(self.f, blk.name) for blk in self.f.handle.blocks]

    @file_transaction
    def read_block(self, block_id):
        return Reader.read_block(self.f, block_id)

    @file_transaction
    def write_block(self, block, recursive=True):
        Writer.write_block(self.f.handle, block, recursive=recursive)

        # FIXME really delete unused arrays?

        # implement clean up
        # del all arrays with no tag/source
        #del nix_block.data_arrays[da_name]


