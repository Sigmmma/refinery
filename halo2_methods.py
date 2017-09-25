from arbytmap import Arbytmap
import zlib

from math import pi, sqrt
from os.path import dirname, exists, join
from struct import unpack, pack_into
from tkinter.filedialog import askopenfilename
from traceback import format_exc

from supyr_struct.buffer import BytearrayBuffer, PeekableMmap
from supyr_struct.defs.constants import *
from supyr_struct.defs.util import *
from supyr_struct.field_types import FieldType

from refinery.byteswapping import raw_block_def
from refinery.util_h2 import HALO2_MAP_TYPES


__all__ = (
    "inject_rawdata", "meta_to_tag_data", "load_all_resource_maps",
    )


def inject_rawdata(self, meta, tag_cls, tag_index_ref):
    # get some rawdata that would be pretty annoying to do in the parser
    if tag_cls == "bitm":
        # grab bitmap data correctly from map
        new_pixels = BytearrayBuffer()
        pix_off = 0

        for bitmap in meta.bitmaps.STEPTREE:
            # grab the bitmap data from the correct map
            bitmap.pixels_offset = pix_off

            ptr, map_name = split_raw_pointer(bitmap.lod1_offset)
            halo_map = self
            if map_name != "local":
                halo_map = self.maps.get(map_name)

            if halo_map is None:
                bitmap.lod1_size = 0
                continue

            halo_map.map_data.seek(ptr)
            mip_pixels = zlib.decompress(
                halo_map.map_data.read(bitmap.lod1_size))
            new_pixels += mip_pixels
            bitmap.lod1_size = len(mip_pixels)
            pix_off += bitmap.lod1_size

        meta.processed_pixel_data.STEPTREE = new_pixels


def meta_to_tag_data(self, meta, tag_cls, tag_index_ref, **kwargs):
    engine     = self.engine
    tag_index  = self.tag_index

    if tag_cls == "bitm":
        # set the size of the compressed plate data to nothing
        meta.compressed_color_plate_data.STEPTREE = BytearrayBuffer()

        # to enable compatibility with my bitmap converter we'll set the
        # base address to a certain constant based on the console platform
        is_xbox = engine in ("halo2xbox", )
        new_pixels_offset = 0

        # uncheck the prefer_low_detail flag and
        # set up the lod1_offset correctly.
        for bitmap in meta.bitmaps.STEPTREE:
            bitmap.flags.prefer_low_detail = is_xbox
            bitmap.lod1_offset = new_pixels_offset
            new_pixels_offset += bitmap.lod1_size

            bitmap.lod2_offset = bitmap.lod3_offset = bitmap.lod4_offset =\
                                 bitmap.lod5_offset = bitmap.lod6_offset = 0
            bitmap.lod2_size = bitmap.lod3_size = bitmap.lod4_size =\
                               bitmap.lod5_size = bitmap.lod6_size = 0

    return meta


def load_all_resource_maps(self, maps_dir=""):
    map_paths = {name: None for name in HALO2_MAP_TYPES[1:]}
    if not maps_dir:
        maps_dir = dirname(self.filepath)

    # detect/ask for the map paths for the resource maps
    for map_name in sorted(map_paths.keys()):
        if self.maps.get(map_name) is not None:
            # map already loaded
            continue

        map_path = join(maps_dir, "%s.map" % map_name)

        if not exists(map_path): map_path += ".dtz"

        while map_path and not exists(map_path):
            map_path = askopenfilename(
                initialdir=maps_dir,
                title="Select the %s.map" % map_name,
                filetypes=((map_name, "*.map"),
                           (map_name, "*.map.dtz"),
                           (map_name, "*.*")))

            if map_path:
                maps_dir = dirname(map_path)
            else:
                print("    You wont be able to extract from %s.map" % map_name)

        map_paths[map_name] = map_path

    for map_name in sorted(map_paths.keys()):
        map_path = map_paths[map_name]
        try:
            if self.maps.get(map_name) is None and map_path:
                print("    Loading %s.map..." % map_name)
                type(self)(self.maps).load_map(map_path, will_be_active=False)
                print("        Finished")
        except Exception:
            print(format_exc())
