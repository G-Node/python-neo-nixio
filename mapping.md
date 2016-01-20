# Data model mapping between Neo and NIX

## neo.Block

Maps directly to `nix.Block`.
  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | Block.name(string)            | Block.name(string)                   |
    | Block.description(string)     | Block.definition(string)             |
    | Block.rec_datetime(datetime)  | Block.date(date)                     |
    | Block.file_datetime(datetime) | Block.metadata(**Section**) [[1]](#notes) |
    | Block.file_origin             | Block.metadata(**Section**) [[1]](#notes) |

  - Objects
    - neo.Block.segments(**Segment**[]):  
    Maps directly to nix.Block.groups(**Group**[]).
    See the [neo.Segment](#neosegment) section for details.
    - neo.Block.recordingchannelgroups(**RecordingChannelGroup**[]):  
    Maps to neo.Block.sources(**Source**[]) with `type = "neo.recordingchannelgroup"`.
    See the [neo.RecordingChannelGroup](#neorecordingchannelgroup) section for details.

## neo.Segment

Maps directly to `nix.Group`.
  - Attributes

    | Neo                             | NIX                                  |
    |---------------------------------|--------------------------------------|
    | Segment.name(string)            | Group.name(string)                   |
    | Segment.description(string)     | Group.definition(string)             |
    | Segment.rec_datetime(datetime)  | Group.date(date)                     |
    | Segment.file_datetime(datetime) | Group.metadata(**Section**) [[1]](#notes) |
    | Segment.file_origin             | Group.metadata(**Section**) [[1]](#notes) |

  - Objects
    - Segment.analogsignals(**AnalogSignal**[]) & Segment.irregularlysampledsignals(**IrregularlySampledSignal**[]):  
    For each item in both lists, a `nix.DataArray` is created which holds the signal data and attributes.
    The `type` attribute of the `DataArray` is set to `neo.analogsignal` or `neo.irregularlysampledsignal` accordingly.
    These are stored in the `Group.data_arrays` list.
    See the [neo.AnalogSignal](#neoanalogsignal) and [neo.IrregularlySampledSignal](#neoirregularlysampledsignal) sections for details.
      - Signal objects in Neo can be grouped, e.g., `Segment.analogsignals` is a list of `AnalogSignal` objects, each of which can hold multiple signals.
      In order to be able to reconstruct the original signal groupings, all `DataArray` objects that belong to the same `AnalogSignal` (or `IrregularlySampledSignal`) have their `metadata` attribute point to the same `Section`.
    - Segment.epochs(**Epoch**[]):  
    For each item in `Segment.epochs`, a `nix.MultiTag` is created with `type = neo.epoch`.
    This is stored in the `Group.multi_tags` list.
    See the [neo.Epoch](#neoepoch) section for details.
    - Segment.events(**Event**[]):  
    For each item in `Segment.events`, a `nix.MultiTag` is created with `type = neo.event`.
    This is stored in the `Group.multi_tags` list.
    See the [neo.Event](#neoevent) section for details.
    - Segment.spiketrains(**SpikeTrain**[]):  
    For each item in `Segment.spiketrains`, a `nix.MultiTag` is created with `type = neo.spiketrain`.
    This is stored in the `Group.multi_tags` list.
    See the [neo.SpikeTrain](#neospiketrain) section for details.

## neo.RecordingChannelGroup

Maps to nix.Source with `type = neo.recordingchannelgroup`.

  - Attributes

    | Neo                                       | NIX                                   |
    |-------------------------------------------|---------------------------------------|
    | RecordingChannelGroup.name(string)        | Source.name(string)                   |
    | RecordingChannelGroup.description(string) | Source.definition(string)             |
    | RecordingChannelGroup.file_origin         | Source.metadata(**Section**) [[1]](#notes) |
    | RecordingChannelGroup.coordinates         | Source.metadata(**Section**) [[1]](#notes) |

    - nix.Source requires a date attribute.
    This is inherited from the parent nix.Block.
    - RecordingChannelGroup.channel_indexes:  
    Are not mapped into any NIX object or attribute.
    When converting from NIX to Neo, the channel indexes are reconstructed from the contained `nix.Source` objects [[2]](#notes).

For each object contained in the group lists (`units`, `analogsignals`, `irregularlysampledsignals`), a child nix.Source is created with `type = neo.recordingchannel`.
Each `Source.name` is taken from the `RecordingChannelGroup.channel_names` array.
The sources also inherit the container's `date` and `metadata`.
The `Source.definition` string is constructed by appending the `Source.name` to container's `Source.definition`.

Each of the `nix.Source` objects that are created as children of a `neo.RecordingChannelGroup` are referenced by:
  - The corresponding `DataArray`, in the case of sources which were created from the `analogsignals` and `irregularlysampledsignals` lists.
  - The corresponding `MultiTag`, in the case of sources which were created from the `units` list.
      - These `MultiTag` objects also contain a second `Source` with type `neo.unit`.


## neo.AnalogSignal

Maps to a `nix.DataArray` with `type = neo.analogsignal`.

  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | AnalogSignal.name(string)            | DataArray.name(string)                   |
    | AnalogSignal.description(string)     | DataArray.definition(string)             |
    | AnalogSignal.file_origin             | DataArray.metadata(**Section**) [[1]](#notes) |

  - Objects
    - AnalogSignal.signal(Quantity 2D):  
      - Maps directly to `DataArray.data(DataType[])`.
      - Based on the units of the Quantity, `DataArray.unit(string)` is set.
      - `DataArray.dimensions(Dimension[])` contains two objects, a `Sample` and a `Set` to denote that the first dimension of the data in the array represents regularly sampled data (`AnalogSignal`) and the second dimension simply represents a set of signals.
    - AnalogSignal.sampling_rate(Quantity scalar)
      - Maps to `DataArray.dimensions[0].sampling_interval`.
    - AnalogSignal.t_start(Quantity scalar)
    - AnalogSignal.channel_indexes(


## neo.IrregularlySampledSignal

## neo.Epoch

## neo.Event

## neo.SpikeTrain

## neo.Unit

## Notes:
  1. The NIX objects each hold only one `metadata` attribute.
  Neo attributes such as `file_datetime` and `file_origin` are mapped to properties within the same `nix.Section` to which the `metadata` attribute refers.
  A metadata section is only created for a NIX object if necessary, i.e., it is not created if the Neo object attributes are not set.
  The `Section.name` should match the corresponding NIX object `name`.
  2. The role of `channel_indexes` in `neo.RecordingChannelGroup` is still unclear.
  The mapping is still not complete and is therefore subject to change.
