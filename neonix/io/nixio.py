# Copyright (c) 2014, German Neuroinformatics Node (G-Node)
#                     Achilleas Koutsou <achilleas.k@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the BSD License. See
# LICENSE file in the root of the Project.

from __future__ import absolute_import

from datetime import datetime
import numpy as np
import quantities as pq

from neo.io.baseio import BaseIO
from neo.core import (Block, Segment, RecordingChannelGroup, AnalogSignal,
                      IrregularlySampledSignal, Epoch, Event, SpikeTrain, Unit)

try:
    import nix
except ImportError:  # pragma: no cover
    raise ImportError("Failed to import NIX (NIXPY not found). "
                      "The NixIO requires the Python bindings for NIX.")


def calculate_timestamp(dt):
    return int((dt - datetime.fromtimestamp(0)).total_seconds())

# TODO: Copy neo annotations for all objects into metadata segments

class NixIO(BaseIO):
    """
    Class for reading and writing NIX files.
    """

    is_readable = False  # for now
    is_writable = True

    supported_objects = [Block, Segment, RecordingChannelGroup]
    readable_objects = []
    writeable_objects = [Block, Segment, RecordingChannelGroup]

    name = "NIX"
    extensions = ["h5"]
    mode = "file"

    def __init__(self, filename):
        """
        Initialise IO instance and NIX file.

        :param filename: Full path to the file
        """
        BaseIO.__init__(self, filename=None)
        self.filename = filename
        if self.filename:
            self.nix_file = nix.File.open(self.filename, nix.FileMode.Overwrite)

    def __del__(self):
        self.nix_file.close()

    def write_block(self, neo_block, cascade=True):
        """
        Convert ``neo_block`` to the NIX equivalent and write it to the file.
        If ``cascade`` is True, write all the block's child objects as well.

        :param neo_block: Neo block to be written
        :param cascade: Save all child objects (default: True)
        :return: The new NIX Block
        """
        nix_name = neo_block.name
        nix_type = "neo.block"
        nix_definition = neo_block.description
        nix_block = self.nix_file.create_block(nix_name, nix_type)
        nix_block.definition = nix_definition
        object_path = [("block", nix_name)]
        if neo_block.rec_datetime:
            # Truncating timestamp to seconds
            nix_block.force_created_at(
                    calculate_timestamp(neo_block.rec_datetime))
        if neo_block.file_datetime:
            block_metadata = self._get_or_init_metadata(nix_block)
            # Truncating timestamp to seconds
            block_metadata.create_property(
                    "file_datetime",
                    nix.Value(
                            calculate_timestamp(neo_block.file_datetime)))
        if neo_block.file_origin:
            block_metadata = self._get_or_init_metadata(nix_block)
            block_metadata.create_property("file_origin",
                                           nix.Value(neo_block.file_origin))
        if cascade:
            for segment in neo_block.segments:
                self.write_segment(segment, object_path)
            for rcg in neo_block.recordingchannelgroups:
                self.write_recordingchannelgroup(rcg, object_path)
        return nix_block

    def write_all_blocks(self, neo_blocks, cascade=True):
        """
        Convert all ``neo_blocks`` to the NIX equivalent and write them to the
        file. If ``cascade`` is True, write all child objects as well.

        :param neo_blocks: List (or iterable) containing Neo blocks
        :param cascade: Save all child objects (default: True)
        :return: A list containing the new NIX Blocks
        """
        nix_blocks = []
        for nb in neo_blocks:
            nix_blocks.append(self.write_block(nb, cascade))
        return nix_blocks

    def write_segment(self, segment, parent_path):
        """
        Convert the provided ``segment`` to a NIX Group and write it to the NIX
        file at the location defined by ``parent_path``.

        :param segment: Neo segment to be written
        :param parent_path: Path to the parent of the new segment
        :return: The newly created NIX Group
        """
        parent_block = self.get_object_at(parent_path)
        nix_name = segment.name
        nix_type = "neo.segment"
        nix_definition = segment.description
        nix_group = parent_block.create_group(nix_name, nix_type)
        nix_group.definition = nix_definition
        object_path = parent_path + [("group", nix_name)]
        if segment.rec_datetime:
            # Truncating timestamp to seconds
            nix_group.force_created_at(calculate_timestamp(segment.rec_datetime))
        if segment.file_datetime:
            group_metadata = self._get_or_init_metadata(nix_group, object_path)
            # Truncating timestamp to seconds
            group_metadata .create_property(
                    "file_datetime",
                    nix.Value(calculate_timestamp(segment.file_datetime)))
        if segment.file_origin:
            group_metadata = self._get_or_init_metadata(nix_group, object_path)
            group_metadata.create_property("file_origin",
                                           nix.Value(segment.file_origin))
        for anasig in segment.analogsignals:
            self.write_analogsignal(anasig, object_path)
        for irsig in segment.irregularlysampledsignals:
            self.write_irregularlysampledsignal(irsig, object_path)
        for ep in segment.epochs:
            self.write_epoch(ep, object_path)
        for ev in segment.events:
            self.write_event(ev, object_path)
        for sptr in segment.spiketrains:
            self.write_spiketrain(sptr, object_path)

        return nix_group

    def write_recordingchannelgroup(self, rcg, parent_path):
        """
        Convert the provided ``rcg`` (RecordingChannelGroup) to a NIX Source
        and write it to the NIX file at the location defined by ``parent_path``.

        :param rcg: The Neo RecordingChannelGroup to be written
        :param parent_path: Path to the parent of the new segment
        :return: The newly created NIX Source
        """
        parent_block = self.get_object_at(parent_path)
        nix_name = rcg.name
        nix_type = "neo.recordingchannelgroup"
        nix_definition = rcg.description
        nix_source = parent_block.create_source(nix_name, nix_type)
        nix_source.definition = nix_definition
        object_path = parent_path + [("source", nix_name)]
        if rcg.file_origin:
            source_metadata = self._get_or_init_metadata(nix_source,
                                                         object_path)
            source_metadata.create_property("file_origin",
                                            nix.Value(rcg.file_origin))
        if hasattr(rcg, "coordinates"):
            source_metadata = self._get_or_init_metadata(nix_source,
                                                         object_path)
            nix_coordinates = NixIO._copy_coordinates(rcg.coordinates)
            source_metadata.create_property("coordinates",
                                            nix_coordinates)
        return nix_source

    def write_analogsignal(self, anasig, parent_path):
        """
        Convert the provided ``anasig`` (AnalogSignal) to a group of NIX
        DataArray objects and write them to the NIX file at the location defined
        by ``parent_path``. All DataArray objects created from the same
        AnalogSignal have their metadata section point to the same object.

        :param anasig: The Neo AnalogSignal to be written
        :param parent_path: Path to the parent of the new segment
        :return: A list containing the newly created NIX DataArrays
        """
        parent_group = self.get_object_at(parent_path)
        parent_block = self.get_object_at(parent_path[0])
        nix_name = anasig.name
        nix_type = "neo.analogsignal"
        nix_definition = anasig.description
        parent_metadata = self._get_or_init_metadata(parent_group, parent_path)
        anasig_group_segment = parent_metadata.create_section(nix_name,
                                                              nix_type)

        # common properties
        data_units = str(anasig.units)
        time_units = str(anasig.sampling_period.units)
        offset = anasig.t_start.rescale(time_units).item()
        sampling_interval = anasig.sampling_period.item()

        nix_data_arrays = []
        for idx, sig in enumerate(anasig.signal):
            nix_data_array = parent_block.create_data_array(
                "{}{}".format(nix_name, idx),
                nix_type,
                data=sig.magnitude
            )
            nix_data_array.definition = nix_definition
            nix_data_array.unit = data_units

            timedim = nix_data_array.append_sampled_dimension(sampling_interval)
            timedim.unit = time_units
            timedim.label = "time"
            timedim.offset = offset
            chandim = nix_data_array.append_set_dimension()
            parent_group.data_arrays.append(nix_data_array)
            # point metadata to common section
            nix_data_array.metadata = anasig_group_segment
            nix_data_arrays.append(nix_data_array)
        return nix_data_arrays

    def write_irregularlysampledsignal(self, irsig, parent_path):
        """
        Convert the provided ``irsig`` (IrregularlySampledSignal) to a NIX
        Source and write it to the NIX file at the location defined by
        ``parent_path``.

        :param irsig: The Neo IrregularlySampledSignal to be written
        :param parent_path: Path to the parent of the new Source
        :return: The newly created NIX DataArray
        """
        parent_group = self.get_object_at(parent_path)
        parent_block = self.get_object_at(parent_path[0])
        nix_name = irsig.name
        nix_type = "neo.irregularlysampledsignal"
        nix_definition = irsig.description
        parent_metadata = self._get_or_init_metadata(parent_group, parent_path)
        irsig_group_segment = parent_metadata.create_section(nix_name,
                                                             nix_type)

        # common properties
        data_units = str(irsig.units)
        time_units = str(irsig.times.units)
        times = irsig.times.magnitude.tolist()

        nix_data_arrays = []
        for idx, sig in enumerate(irsig.signal):
            nix_data_array = parent_block.create_data_array(
                "{}{}".format(nix_name, idx),
                nix_type,
                data=sig.magnitude
            )
            nix_data_array.definition = nix_definition
            nix_data_array.unit = data_units

            timedim = nix_data_array.append_range_dimension(times)
            timedim.unit = time_units
            timedim.label = "time"
            chandim = nix_data_array.append_set_dimension()
            parent_group.data_arrays.append(nix_data_array)
            # point metadata to common section
            nix_data_array.metadata = irsig_group_segment
            nix_data_arrays.append(nix_data_array)
        return nix_data_arrays

    def write_epoch(self, ep, parent_path):
        """
        Convert the provided ``ep`` (Epoch) to a NIX MultiTag and write it to
        the NIX file at the location defined by ``parent_path``.

        :param ep: The Neo Epoch to be written
        :param parent_path: Path to the parent of the new MultiTag
        :return: The newly created NIX MultiTag
        """
        parent_group = self.get_object_at(parent_path)
        parent_block = self.get_object_at(parent_path[0])
        nix_name = ep.name
        nix_type = "neo.epoch"
        nix_definition = ep.description
        nix_multi_tag = parent_block.create_multi_tag(nix_name, nix_type)
        parent_group.multi_tags.append(nix_multi_tag)
        nix_multi_tag.definition = nix_definition
        object_path = parent_path + [("multi_tag", nix_name)]
        if ep.file_origin:
            mtag_metadata = self._get_or_init_metadata(nix_multi_tag,
                                                       object_path)
            mtag_metadata.create_property("file_origin",
                                          nix.Value(ep.file_origin))
        # TODO: labels
        # times -> positions
        times = ep.times.magnitude  # .tolist()
        time_units = str(ep.times.units)

        times_da = parent_block.create_data_array("times",
                                                  "neo.epoch.times",
                                                  data=times)
        times_da.unit = time_units
        nix_multi_tag.positions = times_da

        # durations -> extents
        durations = ep.durations.magnitude  # .tolist()
        duration_units = str(ep.durations.units)

        durations_da = parent_block.create_data_array("durations",
                                                      "neo.epoch.durations",
                                                      data=durations)
        durations_da.unit = duration_units
        nix_multi_tag.extents = durations_da
        return nix_multi_tag

    def write_event(self, ev, parent_path):
        """
        Convert the provided ``ev`` (Event) to a NIX MultiTag and write it to
        the NIX file at the location defined by ``parent_path``.

        :param ev: The Neo Event to be written
        :param parent_path: Path to the parent of the new MultiTag
        :return: The newly created NIX MultiTag
        """
        parent_group = self.get_object_at(parent_path)
        parent_block = self.get_object_at(parent_path[0])
        nix_name = ev.name
        nix_type = "neo.event"
        nix_definition = ev.description
        nix_multi_tag = parent_block.create_multi_tag(nix_name, nix_type)
        parent_group.multi_tags.append(nix_multi_tag)
        nix_multi_tag.definition = nix_definition
        object_path = parent_path + [("multi_tag", nix_name)]
        if ev.file_origin:
            mtag_metadata = self._get_or_init_metadata(nix_multi_tag,
                                                       object_path)
            mtag_metadata.create_property("file_origin",
                                          nix.Value(ev.file_origin))

        # TODO: labels
        # times -> positions
        times = ev.times.magnitude  # .tolist()
        time_units = str(ev.times.units)

        times_da = parent_block.create_data_array("times",
                                                  "neo.event.times",
                                                  data=times)
        times_da.unit = time_units
        nix_multi_tag.positions = times_da
        return nix_multi_tag

    def write_spiketrain(self, sptr, parent_path):
        """
        Convert the provided ``sptr`` (SpikeTrain) to a NIX MultiTag and write
         it to the NIX file at the location defined by ``parent_path``.

        :param sptr: The Neo SpikeTrain to be written
        :param parent_path: Path to the parent of the new MultiTag
        :return: The newly created NIX MultiTag
        """
        parent_group = self.get_object_at(parent_path)
        parent_block = self.get_object_at(parent_path[0])
        nix_name = sptr.name
        nix_type = "neo.spiketrain"
        nix_definition = sptr.description
        nix_multi_tag = parent_block.create_multi_tag(nix_name, nix_type)
        parent_group.multi_tags.append(nix_multi_tag)
        nix_multi_tag.definition = nix_definition
        object_path = parent_path + [("multi_tag", nix_name)]
        if sptr.file_origin:
            mtag_metadata = self._get_or_init_metadata(nix_multi_tag,
                                                       object_path)
            mtag_metadata.create_property("file_origin",
                                          nix.Value(sptr.file_origin))

        # TODO: t_start, t_stop (required), left_sweep, times, waveforms, units
        return nix_multi_tag

    def write_unit(self, ut, parent_path):
        """
        Convert the provided ``ut`` (Unit) to a NIX MultiTag and write it to the
        NIX file at the location defined by ``parent_path``.

        :param ut: The Neo Unit to be written
        :param parent_path: Path to the parent of the new MultiTag
        :return: The newly created NIX Source
        """
        parent_group = self.get_object_at(parent_path)
        parent_block = self.get_object_at(parent_path[0])
        nix_name = ut.name
        nix_type = "neo.unit"
        nix_definition = ut.description
        nix_multi_tag = parent_block.create_multi_tag(nix_name, nix_type)
        parent_group.multi_tags.append(nix_multi_tag)
        nix_multi_tag.definition = nix_definition
        object_path = parent_path + [("multi_tag", nix_name)]
        if ut.file_origin:
            mtag_metadata = self._get_or_init_metadata(nix_multi_tag,
                                                       object_path)
            mtag_metadata.create_property("file_origin",
                                          nix.Value(ut.file_origin))

        return nix_multi_tag

    def _get_or_init_metadata(self, nix_obj, obj_path=[]):
        """
        Creates a metadata Section for the provided NIX object if it doesn't
        have one already. Returns the new or existing metadata section.

        :param nix_obj: The object to which the Section is attached
        :param obj_path: Path to nix_obj
        :return: The metadata section of the provided object
        """
        if nix_obj.metadata is None:
            if len(obj_path) <= 1:  # nix_obj is root block
                parent_metadata = self.nix_file
            else:
                obj_parent = self.get_object_at(obj_path[:-1])
                parent_metadata = self._get_or_init_metadata(obj_parent,
                                                             obj_path[:-1])
            nix_obj.metadata = parent_metadata.create_section(
                    nix_obj.name, nix_obj.type+".metadata")
        return nix_obj.metadata

    def get_object_at(self, path):
        """
        Returns the object at the location defined by the path. ``path`` is a
        list of tuples. Each tuple contains the NIX type of each object as a
        string and the name of the object at the location in the path.
        Valid object type strings are: block, group, source, data_array, tag,
        multi_tag, feature.

        :param path: List of tuples that define a location in the file
        :return: The object at the location defined by the path
        """
        # NOTE: Should this be simplified to:
        #   return parent.__getattribute__(obj_type+"s")[obj_name] ?
        parent = self.nix_file
        for obj_type, obj_name in path:
            if obj_type == "block":
                return parent.blocks[obj_name]
            elif obj_type == "group":
                return parent.groups[obj_name]
            elif obj_type == "source":
                return parent.sources[obj_name]
            elif obj_type == "data_array":
                return parent.data_arrays[obj_name]
            elif obj_type == "tag":
                return parent.tags[obj_name]
            elif obj_type == "multi_tag":
                return parent.multi_tags[obj_name]
            elif obj_type == "feature":
                return parent.features[obj_name]
            else:
                # TODO: Raise error
                return None

    @staticmethod
    def _equals(neo_obj, nix_obj, cascade=True):
        """
        Returns ``True`` if the attributes of ``neo_obj`` match the attributes
        of the ``nix_obj``.

        :param neo_obj: A Neo object (block, segment, etc.)
        :param nix_obj: A NIX object to compare to (block, group, etc.)
        :param cascade: test all child objects for equivalence recursively
                        (default: True)
        :return: True if the attributes and child objects (if cascade=True)
         of the two objects, as defined in the object mapping, are equal
        """
        if not NixIO._equals_attr(neo_obj, nix_obj):
            return False
        if cascade:
            return NixIO._equals_child_objects(neo_obj, nix_obj)
        else:
            return True

    @staticmethod
    def _equals_attr(neo_obj, nix_obj):
        if neo_obj.name != nix_obj.name:
            return False
        if neo_obj.description != nix_obj.definition:
            return False
        if hasattr(neo_obj, "rec_datetime") and neo_obj.rec_datetime and\
                (neo_obj.rec_datetime !=
                 datetime.fromtimestamp(nix_obj.created_at)):
            return False
        if hasattr(neo_obj, "file_datetime") and neo_obj.file_datetime and\
                (neo_obj.file_datetime !=
                 datetime.fromtimestamp(nix_obj.metadata["file_datetime"])):
            return False
        if neo_obj.file_origin and\
                neo_obj.file_origin != nix_obj.metadata["file_origin"]:
            return False
        if isinstance(neo_obj, RecordingChannelGroup):
            if not NixIO._equals_coordinates(neo_obj.coordinates,
                                             nix_obj.metadata["coordinates"]):
                return False
        if isinstance(neo_obj, SpikeTrain):
            # TODO: t_start, t_stop (required), left_sweep
            pass

        return True

    @staticmethod
    def _equals_child_objects(neo_obj, nix_obj):
        if isinstance(neo_obj, Block):
            for neo_seg, nix_grp in zip(neo_obj.segments, nix_obj.groups):
                if not NixIO._equals(neo_seg, nix_grp):
                    return False
            for neo_rcg, nix_src in zip(neo_obj.recordingchannelgroups,
                                        nix_obj.sources):
                if not NixIO._equals(neo_rcg, nix_src):
                    return False
        return True

    @staticmethod
    def _equals_coordinates(neo_coords, nix_coords):
        return True

    @staticmethod
    def _copy_coordinates(neo_coords):
        nix_coords = nix.Value(0)
        return nix_coords

    @staticmethod
    def _convert_signal_data(signal):
        data = []
        for chan in signal:
            data.append(chan.magnitude)
        return np.array(data)
