# Data model mapping between Neo and NIX

## neo.Block
Maps directly to nix.Block.
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
    See the [neo.Segment](#neo.Segment) section for details.
    - neo.Block.recordingchannelgroups(**RecordingChannelGroup**[]):  
    Maps to neo.Block.sources(**Source**[]) with `type = "neo.recordingchannelgroup"`.
    See the [neo.RecordingChannelGroup](#neo.RecordingChannelGroup) section for details.

## neo.Segment
Maps directly to nix.Group.
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
    For each item in both lists, a neo.DataArray is created which holds the signal data and attributes.
    See the [neo.AnalogSignal](#neo.Analogsignal) and [neo.IrregularlySampledSignal](neo.IrregularlySampledSignal) sections for details.
      - Signal objects in Neo can be grouped, e.g., `Segment.analogsignals` is a list of `AnalogSignal` objects, each of which can hold multiple signals.
      In order to be able to reconstruct the original signal groupings, all `DataArray` objects that belong to the same `AnalogSignal` (or `IrregularlySampledSignal`) have their `metadata` attribute point to the same `Section`.
    - Segment.epochs(**Epoch**[]):  
    For each item in Group.epochs, a neo.MultiTag is created with `type = neo.epoch`.
    See the [neo.Epoch](#neo.Epoch) section for details.
    - Segment.events(**Event**[]):  
    For each item in Group.epochs, a neo.MultiTag is created with `type = neo.event`.
    See the [neo.Event](#neo.Event) section for details.
    - Segment.spiketrains(**SpikeTrain**[]):  
    For each item in Group.epochs, a neo.MultiTag is created with `type = neo.spiketrain`.
    See the [neo.SpikeTrain](#neo.SpikeTrain) section for details.

## neo.RecordingChannelGroup


## Notes:
  1. The nix objects each hold only one `metadata` attribute.
  The `file_datetime` and `file_origin` Neo attributes are mapped to two properties within the same `nix.Section`.
  The `Section.name` should match the corresponding NIX object `name`.
