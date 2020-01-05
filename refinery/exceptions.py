#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

class RefineryError(Exception): pass
class MapNotLoadedError(RefineryError): pass
class EngineDetectionError(RefineryError): pass
class MapAlreadyLoadedError(RefineryError): pass
class CouldNotGetMetaError(RefineryError): pass
class InvalidTagIdError(RefineryError): pass
class InvalidClassError(RefineryError): pass
class MetaConversionError(RefineryError): pass
class DataExtractionError(RefineryError): pass
