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


__all__ = (
    "inject_rawdata", "meta_to_tag_data", "load_all_resource_maps",
    "HALO2_MAP_TYPES"
    )

# DO NOT CHANGE THE ORDER OF THESE
HALO2_MAP_TYPES = ("active", "mainmenu", "shared", "single_player_shared")


def split_raw_pointer(ptr):
    return ptr & 0x3FffFFff, HALO2_MAP_TYPES[(ptr>>30)&3]


def inject_rawdata(self, meta, tag_cls, tag_index_ref):
    # get some rawdata that would be pretty annoying to do in the parser
    if tag_cls == "bitm":
        # grab bitmap data correctly from map
        new_pixels = BytearrayBuffer()

        for bitmap in meta.bitmaps.STEPTREE:
            # grab the bitmap data from the correct map
            ptr, map_name = split_raw_pointer(bitmap.lod1_offset)
            map_data = self.maps[map_name].map_data
            if map_data is None:
                # couldn't get pixels from the map
                return

            map_data.seek(ptr)
            new_pixels += zlib.decompressobj().decompress(
                map_data.read(bitmap.lod1_size))

        meta.processed_pixel_data.STEPTREE = new_pixels


def meta_to_tag_data(self, meta, tag_cls, tag_index_ref, **kwargs):
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
                type(self)(self.maps).load_map(map_path, False)
                print("        Finished")
        except Exception:
            print(format_exc())
