from base import NixBase

import nix
import quantities as pq


class AnalogSignal(NixBase):

    def __init__(self, nix_block, nix_data_array):
        """
        Builds a Neo-like AnalogSignal object attached to the NIX-backend.
        Works only if the 'nix_block' and 'nix_data_array' were previously
        saved using 'write' methods of this library.

        Note: nix_block would not be necessary as soon as the reference from
        data_array to block is implemented in nixpy.

        :param nix_block:       NIX block where the signal is located
        :param nix_data_array:  NIX Data Array to build the segment from
        :return:                Neo-like AnalogSignal object
        """
        super(AnalogSignal, self).__init__(nix_data_array)
        self._nix_block = nix_block

    @staticmethod
    def _get_metadata_attr_names():
        return AnalogSignal._default_metadata_attr_names + ('channel_index',)

    # --------------------------------
    # this "basically" makes it behave like an array
    # --------------------------------

    @property
    def _data(self):
        return self._nix_object.data

    def __iter__(self):
        for value in self._data[:]:
            yield pq.Quantity(value, self._nix_object.unit)

    def __getitem__(self, item):
        return pq.Quantity(self._data[item], self._nix_object.unit)

    # --------------------------------
    # usual attributes
    # --------------------------------

    @property
    def sampling_rate(self):
        dim = self._nix_object.dimensions[0]
        return pq.Quantity(dim.sampling_interval, dim.unit)

    @sampling_rate.setter
    def sampling_rate(self, value):
        assert isinstance(value, pq.Quantity)

        dim = self._nix_object.dimensions[0]
        dim.sampling_interval = value.item()
        dim.unit = value.units.dimensionality.string

    @property
    def t_start(self):
        args = (self._metadata['t_start'], self._metadata['t_start__unit'])
        return pq.Quantity(*args)

    @t_start.setter
    def t_start(self, value):
        assert isinstance(value, pq.Quantity)

        self._metadata['t_start'] = value.item()
        self._metadata['t_start__unit'] = value.units.dimensionality.string

    @property
    def duration(self):
        return self._data.shape[0] / self.sampling_rate

    @property
    def t_stop(self):
        return self.t_start + self.duration

    @property
    def times(self):
        return self.t_start + range(self._data.shape[0]) / self.sampling_rate

    # TODO implement more methods

    @property
    def segment(self):
        # TODO !!! search all the tags which have refs to this signal...?
        pass

    @property
    def recordingchannels(self):
        pass

    # --------------------------------
    # actual serialization
    # --------------------------------

    @classmethod
    def write_analogsignal(cls, block, signal):
        """
        Writes the given Neo AnalogSignal to the given NIX Block/Segment.

        :param block:       an instance of the NIX Block
        :param signal:      a Neo AnalogSignal instance to save to NIX
        :return:            an instance of neo2nix.AnalogSignal
        """
        args = (signal.name, 'neo_analogsignal', signal.dtype, (0,))
        nix_array = block.create_data_array(*args)

        nix_array.data.append(signal)
        nix_array.unit = signal.units.dimensionality.string

        nix_array.append_sampled_dimension(signal.sampling_rate.item())
        nix_array.dimensions[0].unit = signal.sampling_rate.units.dimensionality.string

        # root metadata section for block
        nix_array.metadata = block.metadata.create_section(signal.name, 'neo_segment')

        # special t_start serialization
        t_start = signal.t_start.item()
        t_start__unit = signal.t_start.units.dimensionality.string
        nix_array.metadata.create_property('t_start', nix.Value(t_start))
        nix_array.metadata.create_property('t_start__unit', nix.Value(t_start__unit))

        # section for base object metadata - description, file_origin, etc.
        base_meta = nix_array.metadata.create_section('_base', 'group')

        for attr_name in AnalogSignal._get_metadata_attr_names():
            value = getattr(signal, attr_name, None)
            if value:
                base_meta.create_property(attr_name, nix.Value(value))

        result = cls(block, nix_array)
        result.annotations = signal.annotations

        return result