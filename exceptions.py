
class RefineryError(Exception): pass
class MapNotLoadedError(RefineryError): pass
class EngineDetectionError(RefineryError): pass
class MapAlreadyLoadedError(RefineryError): pass
class CouldNotGetMetaError(RefineryError): pass
class InvalidTagIdError(RefineryError): pass
class InvalidClassError(RefineryError): pass
class MetaConversionError(RefineryError): pass
class DataExtractionError(RefineryError): pass
