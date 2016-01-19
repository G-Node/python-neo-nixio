# Data model mapping between Neo and NIX

## neo.Block

Maps directly to `nix.Block`.
  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | Block.name(string)            | Block.name(string)                   |
    | Block.description(string)     | Block.definition(string)             |
    | Block.rec_datetime(datetime)  | Block.date(date)                     |
    | Block.file_datetime(datetime) | Block.metadata(**Section**) [Note 1] |
    | Block.file_origin             | Block.metadata(**Section**) [Note 1] |

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
    | Segment.file_datetime(datetime) | Group.metadata(**Section**) [Note 1] |
    | Segment.file_origin             | Group.metadata(**Section**) [Note 1] |

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
    | RecordingChannelGroup.file_origin         | Source.metadata(**Section**) [Note 1] |
    | RecordingChannelGroup.coordinates(Quantity2D) | Source.metadata(**Section**) [Note 1] |
    | RecordingChannelGroup.channel_names(np.ndarray) | Source.metadata(**Section**) [Note 1] |
    | RecordingChannelGroup.channel_indexes(np.ndarray) | Source.metadata(**Section**) [Note 1] |

  - Objects
      - RecordingChannelGroup.units(**Unit**[]):  
      For each item in `RecordingChannelGroup.units`, a `nix.Source` is created with `type = neo.unit`.
      This is stored in the `Source.sources` list.
      See the [neo.Unit](#neounit) section for details.
      - RecordingChannelGroup.analogsignals(**AnalogSignal**[]):  
      For each item in `RecordingChannelGroup.analogsignals`, a `nix.Source` is created with `type = neo.recordingchannelgroup`.
      This is stored in the `Source.sources` list.
      The child Source object contains a metadata (**Section**) reference which is also referenced by the relevant `DataArray`.
      - RecordingChannelGroup.irregularlysampledsignals(**IrregularlySampledSignal**[]):  
      For each item in `RecordingChannelGroup.IrregularlySampledSignal`, a `nix.Source` is created with `type = neo.irregularlysampledsignals`.
      This is stored in the `Source.sources` list.
      The child Source object contains a metadata (**Section**) reference which is also referenced by the relevant `DataArray`.

## neo.AnalogSignal

When it is a child of a `neo.Segment`, maps to a `nix.DataArray` with `type = neo.analogsignal`.

When it is a child of a `neo.RecordingChannelGroup`, maps to a `nix.Source` with `type = neo.analogsignal`.
The `nix.Source` object references a `nix.Section` in its `metadata` attribute, which is also referenced by the corresponding `nix.DataArray` [Note 2].




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
  2. It may be useful if nix.Source objects which are used to refer to DataArrays have a suffix which denotes they are references.
  For example, a nix.Source which is created to refer to a DataArray with type `neo.analogsignal`, would have a type attribute with value `neo.analogsignal_ref`.
  The same rule could be applied to metadata sections.
