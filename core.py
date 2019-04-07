import mmap
import gc
import os
import refinery
import shutil
import sys
import zlib

from os.path import dirname, basename, exists, join, isfile, splitext
from struct import unpack
from time import time
from traceback import format_exc

from supyr_struct.buffer import BytearrayBuffer, PeekableMmap
from supyr_struct.defs.constants import *
from supyr_struct.field_types import FieldType


from reclaimer.constants import GEN_1_HALO_ENGINES, GEN_2_ENGINES
from reclaimer.data_extraction import h1_data_extractors, h2_data_extractors,\
     h3_data_extractors
from reclaimer.hsc import get_h1_scenario_script_object_type_strings,\
     get_hsc_data_block
from reclaimer.meta.wrappers.halo1_map import Halo1Map
from reclaimer.meta.wrappers.halo1_anni_map import Halo1AnniMap
from reclaimer.meta.wrappers.halo1_rsrc_map import Halo1RsrcMap
from reclaimer.meta.wrappers.halo2_map import Halo2Map
from reclaimer.meta.wrappers.halo3_map import Halo3Map
from reclaimer.meta.wrappers.halo3_beta_map import Halo3BetaMap
from reclaimer.meta.wrappers.halo_reach_map import HaloReachMap
from reclaimer.meta.wrappers.halo_reach_beta_map import HaloReachBetaMap
from reclaimer.meta.wrappers.halo3_odst_map import Halo3OdstMap
from reclaimer.meta.wrappers.halo4_map import Halo4Map
from reclaimer.meta.wrappers.halo4_beta_map import Halo4BetaMap
from reclaimer.meta.wrappers.halo5_map import Halo5Map
from reclaimer.meta.wrappers.stubbs_map import StubbsMap
from reclaimer.meta.wrappers.shadowrun_map import ShadowrunMap

from reclaimer.meta.halo_map import get_map_header, get_map_version,\
     get_tag_index
from reclaimer.meta.class_repair import class_repair_functions,\
     get_tagc_refs
from reclaimer.meta.rawdata_ref_editing import rawdata_ref_move_functions
from reclaimer.meta.halo1_map_fast_functions import class_bytes_by_fcc

from refinery import crc_functions
from refinery.util import *
from refinery.recursive_rename.tag_path_handler import TagPathHandler
from refinery.recursive_rename.functions import recursive_rename


class RefineryError(Exception): pass
class EngineDetectionError(RefineryError): pass
class MapAlreadyLoadedError(RefineryError): pass


platform = sys.platform.lower()
curr_dir = get_cwd(__file__)
INF = float("inf")
        
halo_map_wrappers_by_engine = {
    "stubbs":          StubbsMap,
    "stubbspc":        StubbsMap,
    "shadowrun_proto": ShadowrunMap,
    "halo1anni":       Halo1AnniMap,
    "halo2":           Halo2Map,
    "halo3beta":       Halo3BetaMap,
    "halo3":           Halo3Map,
    "halo3odst":       Halo3OdstMap,
    "haloreachbeta":   HaloReachBetaMap,
    "haloreach":       HaloReachMap,
    "halo4beta":       Halo4BetaMap,
    "halo4":           Halo4Map,
    "halo5":           Halo5Map,
    }
halo_map_wrappers_by_engine.update({e: Halo1Map for e in GEN_1_HALO_ENGINES})
halo_map_wrappers_by_engine.update({e: Halo2Map for e in GEN_2_ENGINES})


class SharedVar:
    __slots__ = ("_val", )
    def __init__(self, val=None): self._val = val
    def get(self): return self._val
    def set(self, new_val): self._val = new_val


def get_halo_map_section_ends(halo_map):
    head  = halo_map.map_header
    index = halo_map.tag_index
    raw_data_end    = index.model_data_offset
    vertex_data_end = index.vertex_data_size + raw_data_end
    index_data_end  = index.model_data_size  + raw_data_end
    meta_data_end   = head.tag_data_size +  head.tag_index_header_offset
    return raw_data_end, vertex_data_end, index_data_end, meta_data_end


def expand_halo_map(halo_map, raw_data_expansion=0, meta_data_expansion=0,
                    vertex_data_expansion=0, triangle_data_expansion=0):
    map_file   = halo_map.map_data
    map_header = halo_map.map_header
    tag_index  = halo_map.tag_index
    tag_index_array = tag_index.tag_index
    index_header_offset = map_header.tag_index_header_offset

    raw_data_end, vertex_data_end, index_data_end, meta_data_end = \
                  get_halo_map_section_ends(halo_map)


    expansions = ((raw_data_end,    raw_data_expansion),
                  (vertex_data_end, vertex_data_expansion),
                  (index_data_end,  triangle_data_expansion),
                  (meta_data_end,   meta_data_expansion))

    # expand the map's sections
    map_end = inject_file_padding(map_file, *expansions)
    diffs_by_offsets, diff = dict(expansions), 0
    for off in sorted(diffs_by_offsets):
        diff += diffs_by_offsets[off]
        diffs_by_offsets[off] = diff

    meta_ptr_diff = diff - meta_data_expansion

    # update the map_header and tag_index_header's offsets and sizes
    tag_index.model_data_offset += raw_data_expansion
    tag_index.vertex_data_size  += vertex_data_expansion
    tag_index.model_data_size   += vertex_data_expansion + triangle_data_expansion
    halo_map.map_magic                 -= meta_ptr_diff
    map_header.tag_index_header_offset += meta_ptr_diff
    map_header.decomp_len = map_end
    map_header.tag_data_size += meta_data_expansion

    # adjust rawdata pointers in various tags if the index header moved
    if meta_ptr_diff:
        for ref in tag_index_array:
            func = rawdata_ref_move_functions.get(fourcc(ref.class_1.data))
            if func is None or ref.indexed:
                continue
            func(ref.id & 0xFFff, tag_index_array, map_file,
                 halo_map.map_magic, halo_map.engine, diffs_by_offsets)

    map_file.flush()
    return map_end


class RefineryCore:
    active_engine_name = ""
    active_map_name = ""
    active_map_path = ""

    # dictionary of all loaded map collections by their engine id strings
    maps_by_engine = None

    def __init__(self, *args, **kwargs):
        self.maps_by_engine = {}

    @property
    def map_loaded(self): return self.active_map is not None

    @property
    def active_maps(self): return self.maps_by_engine.get("<active>", {})
    @property
    def active_map(self):  return self.active_maps.get("<active>")

    def set_active_engine(self, name=None, map_name=None):
        if name == "<active>":
            return

        engine_name = None
        if name is None and self.maps_by_engine:
            engine_name = iter(self.maps_by_engine).__next__()
        elif name in self.maps_by_engine:
            engine_name = name

        next_maps = self.maps_by_engine.get(engine_name)
        if not next_maps:
            next_map_name = None
        elif map_name in next_maps:
            next_map_name = map_name
        elif next_maps.get("<active>"):
            next_map_name = next_maps.get("<active>").map_header.map_name
        else:
            next_map_name = iter(sorted(next_maps)).__next__()

        # unset any currently active engine and only set
        # it if we have a valid map name to make active
        self.maps_by_engine.pop("<active>", None)
        if next_map_name:
            self.maps_by_engine["<active>"] = next_maps
            next_maps.pop("<active>", None)

        self.active_engine_name = engine_name if next_maps else ""
        self.set_active_map(next_map_name)

    def set_active_map(self, name=None):
        if name == "<active>":
            return

        map_name = None
        if name is None and self.active_maps:
            map_name = iter(self.active_maps).__next__()
        elif name in self.active_maps:
            map_name = name

        next_map = self.active_maps.get(map_name)
        self.active_maps.pop("<active>", None)
        if next_map:
            self.active_maps["<active>"] = next_map

        self.active_map_path = next_map.filepath if next_map else ""
        self.active_map_name = map_name if next_map else ""

    def unload_maps(self, map_type=False, engines_to_unload=("<active>", ),
                    maps_to_unload=("<active>", )):
        if engines_to_unload is None:
            engines_to_unload = tuple(self.maps_by_engine.keys())

        for engine in engines_to_unload:
            maps = self.maps_by_engine.get(engine, {})
            map_names = maps_to_unload
            if map_names is None:
                map_names = tuple(maps.keys())

            active_map = self.active_map
            for map_name in map_names:
                try:
                    curr_map = maps[map_name]
                    if map_type is None or map_type == curr_map.is_resource:
                        maps[map_name].unload_map(False)
                        if curr_map is active_map:
                            self.active_map_name = ""
                except Exception:
                    pass

        for engine in tuple(self.maps_by_engine):
            # remove any engine maps without loaded maps.
            if not self.maps_by_engine[engine]:
                self.maps_by_engine.pop(engine, None)

        if not self.active_maps:
            self.set_active_engine()
        else:
            self.set_active_map()

    def load_resource_maps(self, halo_map=None):
        if halo_map is None:
            halo_map = self.active_map

        if halo_map:
            halo_map.load_all_resource_maps()

    def save_map(self, save_path=None, halo_map=None, **kw):
        if halo_map is None:
            halo_map = self.active_map

        meta_data_expansion = kw.pop("meta_data_expansion", 0)
        raw_data_expansion = kw.pop("raw_data_expansion", 0)
        vertex_data_expansion = kw.pop("vertex_data_expansion", 0)
        triangle_data_expansion = kw.pop("triangle_data_expansion", 0)
        assert meta_data_expansion     >= 0
        assert raw_data_expansion      >= 0
        assert vertex_data_expansion   >= 0
        assert triangle_data_expansion >= 0

        if halo_map is None:
            raise KeyError("No map loaded and none provided.")
        elif halo_map.is_resource:
            raise TypeError("Cannot save resource maps.")
        elif halo_map.engine not in ("halo1ce", "halo1yelo", "halo1pc"):
            raise TypeError("Cannot save this kind of map.")
        elif not save_path:
            save_path = halo_map.filepath

        save_dir  = os.path.dirname(save_path)
        save_path, ext = os.path.splitext(save_path)
        save_path = sanitize_path(save_path + (ext if ext else (
            '.yelo' if 'yelo' in halo_map.engine else '.map')))
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        try:
            out_file = map_file = halo_map.map_data
            if save_path.lower() != sanitize_path(halo_map.filepath).lower():
                # use r+ mode rather than w if the file os.path.exists
                # since it might be hidden. apparently on windows
                # the w mode will fail to open hidden files.
                if os.path.isfile(save_path):
                    out_file = open(save_path, 'r+b')
                    out_file.truncate(0)
                else:
                    out_file = open(save_path, 'w+b')

            map_header = halo_map.map_header
            index_off_diff = (raw_data_expansion +
                              vertex_data_expansion +
                              triangle_data_expansion)

            if index_off_diff:
                map_header.tag_index_header_offset += index_off_diff
                halo_map.map_magic = get_map_magic(map_header)

            orig_tag_paths = halo_map.orig_tag_paths
            map_magic      = halo_map.map_magic
            index_magic    = halo_map.index_magic
            tag_index      = halo_map.tag_index
            index_offset   = tag_index.tag_index_offset
            index_array    = tag_index.tag_index
            index_header_offset = map_header.tag_index_header_offset

            # copy the map to the new save location
            map_file.seek(0) # need to seek to 0 as shutil.copyfileobj uses
            out_file.seek(0) # the current file offsets for copying to/from
            if map_file is not out_file:
                shutil.copyfileobj(map_file, out_file)

            # recalculate pointers for the strings if they were changed
            # NOTE: Can't optimize this by writing changed paths back to
            # any existing path pointers, as we cannot assume they point
            # to areas reserved for tag paths(map might be damaged and
            # the pointers are actually pointing into tag data.)
            strings_size, string_offs = 0, {}
            meta_data_end = map_header.tag_data_size + index_header_offset
            for i in range(len(index_array)):
                tag_path = index_array[i].path
                if orig_tag_paths[i].lower() == tag_path.lower():
                    # path wasnt changed
                    continue

                # put the new string at the end of the metadata
                string_offs[i] = meta_data_end + map_magic + strings_size
                strings_size += len(tag_path) + 1

            # move the new tag_path offsets to the end of the metadata
            for i in string_offs:
                string_offs[i] += meta_data_expansion

            meta_data_expansion += strings_size

            # change each tag_path's pointer to its new value
            for i, off in string_offs.items():
                index_array[i].path_offset = off

            # move the tag_index array back to where it SHOULD be
            if self.fix_tag_index_offset.get():
                tag_index.tag_index_offset = index_magic + tag_index.get_size()

            # update the map_data and expand the map's sections if necessary
            halo_map.map_data = out_file
            if map_file is not out_file and hasattr(map_file, "close"):
                map_file.close()

            expansions = (raw_data_expansion, meta_data_expansion,
                          vertex_data_expansion, triangle_data_expansion)
            section_ends = get_halo_map_section_ends(halo_map)

            expand_halo_map(halo_map, *expansions)

            # move the cheape.map pointer
            if halo_map.engine == "halo1yelo":
                cheape = map_header.yelo_header.cheape_definitions
                move_amount = 0
                for end, exp in zip(section_ends, expansions):
                    if end <= cheape.offset:
                        move_amount += exp
                cheape.offset += move_amount

            # get the tag_index_header_offset and map_magic if they changed
            index_header_offset = map_header.tag_index_header_offset
            map_magic = halo_map.map_magic

            # serialize the tag_index_header, tag_index and all the tag_paths
            tag_index.serialize(buffer=out_file, calc_pointers=False,
                                magic=map_magic, offset=index_header_offset)
            out_file.flush()
            if hasattr(out_file, "fileno"):
                os.fsync(out_file.fileno())

            # set the size of the map in the header to 0 to fix a bug where
            # halo will leak file handles for very large maps. Also removes
            # the map size limitation so halo can load stupid big maps.
            if halo_map.engine in ("halo1ce", "halo1yelo"):
                map_header.decomp_len = 0

            # write the map header so the calculate_ce_checksum can read it
            out_file.seek(0)
            out_file.write(map_header.serialize(calc_pointers=False))
            crc = crc_functions.calculate_ce_checksum(out_file, index_magic)
            if halo_map.force_checksum:
                crc_functions.E.__defaults__[0][:] = [
                    0, 0x800000000 - map_header.crc32, map_header.crc32]
                crc_functions.U([crc^0xFFffFFff, out_file,
                                 index_header_offset + 8])
            else:
                map_header.crc32 = crc

            # write the header to the beginning of the map
            out_file.seek(0)
            out_file.write(map_header.serialize(calc_pointers=False))
            out_file.flush()
            if hasattr(out_file, "fileno"):
                os.fsync(out_file.fileno())
        except Exception:
            if map_file is not out_file:
                out_file.close()
            raise

        return save_path

    def load_map(self, map_path, load_resource_maps=True,
                 replace_if_same_name=False):
        with open(map_path, 'r+b') as f:
            comp_data  = PeekableMmap(f.fileno(), 0)
            head_sig   = unpack("<I", comp_data.peek(4))[0]
            map_header = get_map_header(comp_data, True)
            engine     = get_map_version(map_header)
            comp_data.close()

        if engine is None and head_sig in (1, 2, 3):
            # gotta do some hacky shit to figure out this engine
            rsrc_map = Halo1RsrcMap({})
            rsrc_map.load_map(map_path)
            engine = rsrc_map.engine

            map_name = {1: "bitmaps", 2: "sounds", 3: "loc"}[head_sig]
        elif engine in halo_map_wrappers_by_engine:
            map_name = map_header.map_name
        else:
            raise EngineDetectionError(
                'Could not determine map engine for "%s"' % map_path)

        maps = self.maps_by_engine.setdefault(engine, {})
        if not(maps.get(map_name) is None or replace_if_same_name):
            raise MapAlreadyLoadedError(
                ('A map with the name "%s" is already loaded '
                 'under the "%s" engine.' ) % (map_name, engine))

        if maps.get(map_name) is not None:
            self.unload_maps(None, (engine, ), (map_name, ))

        if engine in halo_map_wrappers_by_engine:
            new_map = halo_map_wrappers_by_engine[engine](maps)
        else:
            new_map = Halo1RsrcMap(maps)

        new_map.load_map(map_path, autoload_resources=load_resource_maps)
        return new_map

    def deprotect_all(self):
        for engine_name in self.maps_by_engine:
            if engine_name not in ("halo1ce", "halo1yelo", "halo1pc"):
                continue

            engine_set = False
            maps = self.maps_by_engine[engine_name]
            for map_name in sorted(maps):
                try:
                    if map_name == "<active>" or maps[map_name].is_resource:
                        continue
                    elif not engine_set:
                        self.set_active_engine(engine_name, map_name)
                        engine_set = True
                    else:
                        self.set_active_map(map_name)

                    self.deprotect(maps[map_name].filepath)
                except Exception:
                    print(format_exc())

    def deprotect(self, save_path):
        if self.active_map is None:
            raise KeyError("No map loaded.")
        elif self.active_map.is_resource:
            raise TypeError("Cannot deprotect resource maps.")
        elif self.active_map.engine not in ("halo1ce", "halo1yelo", "halo1pc"):
            raise TypeError("Cannot deprotect this kind of map.")

        spoof_checksum = self.active_map.force_checksum
        if not self.save_map(save_path, prompt_strings_expand=False,
                             prompt_internal_rename=False):
            return

        # get the active map AFTER saving because it WILL have changed
        active_map      = self.active_map
        map_type        = active_map.map_header.map_type.enum_name
        tag_index_array = active_map.tag_index.tag_index

        self.active_map.force_checksum = spoof_checksum

        # rename cached tags using tag paths found in resource maps
        try:
            if self.rename_cached_tags:
                self.sanitize_resource_tag_paths()
        except Exception:
            print(format_exc())

        try:
            if self.fix_tag_classes:
                self.repair_tag_classes()
        except Exception:
            print(format_exc())
        

        tag_path_handler = TagPathHandler(tag_index_array)

        if self.valid_tag_paths_are_accurate.get():
            for tag_id in range(len(tag_index_array)):
                if not (tag_index_array[tag_id].path.lower().
                        startswith("protected")):
                    tag_path_handler.set_priority(tag_id, INF)

        try:
            tagc_names = detect_tag_collection_names(self.active_map)
        except Exception:
            tagc_names = {}

        for tag_id, tag_path in tagc_names.items():
            tag_path_handler.set_path(tag_id, tag_path, INF, True, False)

        try:
            if self.scrape_tag_paths_from_scripts:
                self._script_scrape_deprotect(tag_path_handler)
        except Exception:
            print(format_exc())

        try:
            if self.use_heuristics:
                self._heuristics_deprotect(tag_path_handler)
        except Exception:
            print(format_exc())

        try:
            if self.limit_tag_path_lengths:
                tag_path_handler.shorten_paths(254)
        except Exception:
            print(format_exc())

        # calculate the maps new checksum
        if not self.active_map.force_checksum:
            active_map.map_header.crc32 = crc_functions.calculate_ce_checksum(
                active_map.map_data, active_map.index_magic)

        self.save_map(save_path, prompt_strings_expand=False,
                      prompt_internal_rename=False)

        # record the original tag_paths so we know if any were changed
        active_map.orig_tag_paths = tuple(
            b.path for b in active_map.tag_index.tag_index)

    def detect_tag_collection_names(self, halo_map):
        tag_type_names = {}

        map_type        = active_map.map_header.map_type.enum_name
        tag_index_array = halo_map.tag_index.tag_index

        tag_classes_by_id = {i: tag_index_array[i].class_1.data.
                             to_bytes(4, "big").decode('latin-1')
                             for i in range(len(tag_index_array))}


        # try to locate the Soul tag out of all the tags thought to be tagc
        # and(attempt to) determine the names of each tag collection
        tagc_ids_reffed_in_other_tagc = set()
        for b in tag_index_array:
            if b.class_1.enum_name not in ("tag_collection", "ui_widget_collection"):
                continue

            reffed_tag_ids, reffed_tag_types = get_tagc_refs(
                b.meta_offset, halo_map.map_data, halo_map.map_magic,
                tag_classes_by_id)

            reffed_tag_types = set(reffed_tag_types)
            tag_path = None
            if reffed_tag_types == set(["devc"]):
                tag_path = "ui\\ui_input_device_defaults"
            elif reffed_tag_types == set(["DeLa"]):
                if   map_type == "sp": tag_path = "ui\\shell\\solo"
                elif map_type == "mp": tag_path = "ui\\shell\\multiplayer"
                elif map_type == "ui": tag_path = "ui\\shell\\main_menu"

            tag_id = b.id & 0xFFff
            if tag_name is not None:
                tag_type_names[tag_id] = tag_path

            if tag_id not in tagc_ids_reffed_in_other_tagc:
                tagc_ids_reffed_in_other_tagc.update(reffed_tag_ids)


        # find out if there are any explicit scenario refs in the yelo tag
        ui_all_scnr_idx = 0
        for tag_id, tag_cls in tag_classes_by_id.items():
            if tag_cls != "yelo": continue

            yelo_meta = halo_map.get_meta(tag_id)
            if not yelo_meta: continue

            if (yelo_meta.scenario_explicit_references.id & 0xFFff) != 0xFFff:
                ui_all_scnr_idx += 1


        # rename tag collections based on what order they're found
        # first one will will always be the yelo explicit refs(if it exists)
        # next will be ui_tags_loaded_all_scenario_types
        # last will be ui_tags_loaded_XXXX_scenario_type
        tagc_i = 0
        for b in tag_index_array:
            tag_id = b.id & 0xFFff
            if (tag_classes_by_id.get(tag_id) != "tagc" or
                tag_id in tagc_ids_reffed_in_other_tagc):
                continue

            tag_path = None
            if tagc_i == ui_all_scnr_idx:
                tag_name = "all_scenario_types"
            elif tagc_i == ui_all_scnr_idx + 1:
                if   map_type == "sp": tag_name = "solo_scenario_type"
                elif map_type == "mp": tag_name = "multiplayer_scenario_type"
                elif map_type == "ui": tag_name = "mainmenu_scenario_type"

            if tag_name is not None:
                tag_type_names[tag_id] = "ui\\ui_tags_loaded_" + tag_name

            tagc_i += 1

        return tag_type_names

    def repair_tag_classes(self):
        if active_map.engine not in ("halo1ce", "halo1yelo", "halo1pc"):
            raise TypeError('Cannot repair tag classes in "%s" maps' %
                            active_map.engine)

        active_map      = self.active_map
        tag_index_array = active_map.tag_index.tag_index

        # locate the tags to start deprotecting with
        repair = {}
        repaired = {}
        for b in tag_index_array:
            tag_id = b.id & 0xFFff
            if tag_id == tag_index.scenario_tag_id & 0xFFff:
                tag_cls = "scnr"
            elif b.class_1.enum_name not in ("<INVALID>", "NONE"):
                tag_cls = fourcc(b.class_1.data)
            else:
                continue

            if tag_cls in ("scnr", "DeLa"):
                repair[tag_id] = tag_cls
            elif tag_cls == "matg" and b.path == "globals\\globals":
                repair[tag_id] = tag_cls

        # scan the tags that need repairing and repair them
        while repair:
            next_repair = {}
            for tag_id in repair:
                if tag_id in repaired:
                    continue
                tag_cls = repair[tag_id]
                if tag_cls not in class_bytes_by_fcc:
                    # unknown tag class
                    continue
                repaired[tag_id] = tag_cls

                if (tag_cls not in class_repair_functions or
                        tag_index_array[tag_id].indexed):
                    continue

                if tag_cls != "sbsp":
                    class_repair_functions[tag_cls](
                        tag_id, tag_index_array, active_map.map_data,
                        active_map.map_magic, next_repair, active_map.engine)

                    # replace meta with the deprotected one
                    if tag_cls == "matg":
                        active_map.matg_meta = active_map.get_meta(tag_id)
                    elif tag_cls == "scnr":
                        active_map.scnr_meta = active_map.get_meta(tag_id)
                elif tag_id not in active_map.bsp_headers:
                    print("    Bsp header missing for tag %s" % tag_id)
                    continue
                else:
                    class_repair_functions[tag_cls](
                        active_map.bsp_headers[tag_id].meta_pointer,
                        tag_index_array, active_map.map_data,
                        active_map.bsp_magics[tag_id] - active_map.bsp_header_offsets[tag_id],
                        next_repair, active_map.engine, active_map.map_magic)

            # start repairing the newly accumulated tags
            repair = next_repair

            # exhausted tags to repair. try to repair tag colletions now
            if not repair:
                for b in tag_index_array:
                    tag_id = b.id & 0xFFff
                    tag_cls = None
                    if tag_id in repaired:
                        continue
                    elif b.class_1.enum_name not in ("<INVALID>", "NONE"):
                        tag_cls = fourcc(b.class_1.data)
                    else:
                        _, reffed_tag_types = get_tagc_refs(
                            b.meta_offset, active_map.map_data,
                            active_map.map_magic, repaired
                            )
                        if reffed_tag_types:
                            tag_cls = "tagc"

                    if tag_cls is None:
                        # couldn't determine tag class
                        continue

                    if tag_index_array[tag_id].indexed:
                        repaired[tag_id] = tag_cls
                    elif tag_cls in ("Soul", "tagc", "yelo", "gelo", "gelc"):
                        repair[tag_id] = tag_cls

        for b in tag_index_array:
            tag_id = b.id & 0xFFff
            if b.class_1.enum_name in ("tag_collection", "ui_widget_collection"):
                reffed_tag_ids, reffed_tag_types = get_tagc_refs(
                    b.meta_offset, active_map.map_data,
                    active_map.map_magic, repaired)
                if set(reffed_tag_types) == set(["DeLa"]):
                    repaired[tag_id] = "Soul"

        # write the deprotected tag classes fourcc's to each
        # tag's header in the tag index in the map buffer
        index_array_offset = tag_index.tag_index_offset - active_map.map_magic
        for tag_id, tag_cls in repaired.items():
            tag_index_ref = tag_index_array[tag_id]
            classes_int = int.from_bytes(class_bytes_by_fcc[tag_cls], 'little')
            tag_index_ref.class_1.data = classes_int & 0xFFffFFff
            tag_index_ref.class_2.data = (classes_int >> 32) & 0xFFffFFff
            tag_index_ref.class_3.data = (classes_int >> 64) & 0xFFffFFff

        return repaired

    def sanitize_resource_tag_paths(self):
        for b in tag_index_array:
            tag_id = b.id & 0xFFff
            rsrc_tag_id = b.meta_offset
            rsrc_map = None
            if not b.indexed:
                continue
            elif b.class_1.enum_name == "bitmap":
                rsrc_map = self.active_maps.get("bitmaps")
            elif b.class_1.enum_name == "sound":
                rsrc_map = self.active_maps.get("sounds")
            elif b.class_1.enum_name in ("font", "hud_message_text",
                                         "unicode_string_list"):
                rsrc_map = self.active_maps.get("loc")

            rsrc_tag_index = getattr(rsrc_map, "orig_tag_index", ())
            if rsrc_tag_id not in range(len(rsrc_tag_index)):
                continue

            tag_path = rsrc_tag_index[rsrc_tag_id].tag.path

    def _script_scrape_deprotect(self, path_handler):
        scnr_meta = self.active_map.scnr_meta

        string_data = scnr_meta.script_string_data.data.decode("latin-1")
        syntax_data = get_hsc_data_block(raw_syntax_data=scnr_meta.script_syntax_data.data)

        seen = set()
        for i in range(min(syntax_data.last_node, len(syntax_data.nodes))):
            node = syntax_data.nodes[i]
            # make sure the node references some kind of tag
            if node.type not in range(24, 32):
                continue

            # make sure the tag id points to a valid tag
            tag_id = node.data & 0xFFff
            if tag_id in seen or path_handler.get_index_ref(tag_id) is None:
                continue

            seen.add(tag_id)

            string_end = string_data.find("\x00", node.string_offset)
            new_tag_path = string_data[node.string_offset: string_end]
            if new_tag_path:
                path_handler.set_path(tag_id, new_tag_path, INF, True)

    def _heuristics_deprotect(self, path_handler,
                              do_printout=False, print_name_changes=False,
                              shallow_ui_widget_nesting=True):
        ids_to_deprotect_by_class = {class_name: [] for class_name in (
            "scenario", "globals", "hud_globals", "project_yellow", "vehicle",
            "actor_variant", "biped", "weapon", "equipment", "tag_collection",
            "ui_widget_collection", "scenario_structure_bsp"
            )}
        active_map = self.active_map
        tag_index_array = active_map.tag_index.tag_index
        matg_meta = active_map.matg_meta
        hudg_id = 0xFFFF if not matg_meta else\
                  matg_meta.interface_bitmaps.STEPTREE[0].hud_globals.id & 0xFFff
        hudg_meta = active_map.get_meta(hudg_id, True)

        if hudg_meta:
            block = hudg_meta.messaging_parameters
            items_meta = active_map.get_meta(block.item_message_text.id & 0xFFff, True)
            icons_meta = active_map.get_meta(block.alternate_icon_text.id & 0xFFff, True)

            if items_meta: path_handler.set_item_strings(items_meta)
            if icons_meta: path_handler.set_icon_strings(icons_meta)

        # reset the name of each tag with a default priority and that
        # currently resides in the tags directory root to "protected_XXXX"
        for i in range(len(tag_index_array)):
            if ((path_handler.get_priority(i) == path_handler.def_priority)
                and not path_handler.get_sub_dir(i)):
                path_handler.set_path(i, "protected_%s" % i, override=True,
                                      print_new_name=False)

        scen_ids = []
        for i in range(len(tag_index_array)):
            tag_type = tag_index_array[i].class_1.enum_name
            if tag_type == "scenery":
                scen_ids.append(i)

            if tag_type in ids_to_deprotect_by_class:
                ids_to_deprotect_by_class[tag_type].append(i)

        # NOTE: These are ordered in this way to allow the most logical sorting
        for tag_type in (
                "scenario_structure_bsp", "vehicle", "weapon", "equipment",
                "actor_variant", "biped", "ui_widget_collection", "hud_globals",
                "project_yellow", "globals", "scenario", "tag_collection"):
            if do_printout:
                print("\nRenaming %s tags" % tag_type, end="")

            if print_name_changes:
                print("\ntag_id\tweight\ttag_path\n")

            for tag_id in ids_to_deprotect_by_class[tag_type]:
                if tag_id is None:
                    continue

                try:
                    recursive_rename(
                        tag_id, active_map, path_handler,
                        shallow_ui_widget_nesting=shallow_ui_widget_nesting,
                        print_new_name=print_name_changes)
                except Exception:
                    print(format_exc())

        if do_printout:
            print("\nFinal actor_variant rename pass", end="")
            print("\ntag_id\tweight\ttag_path\n" if
                  print_name_changes else "")
    
        for tag_id in ids_to_deprotect_by_class["actor_variant"]:
            if tag_id is None: continue
            try:
                recursive_rename(tag_id, active_map, path_handler, depth=1)
            except Exception:
                print(format_exc())

        if do_printout:
            print("\nFinal scenery rename pass", end="")
            print("\ntag_id\tweight\ttag_path\n" if
                  print_name_changes else "")

        for tag_id in scen_ids:
            if tag_id is None: continue
            try:
                recursive_rename(tag_id, active_map, path_handler, depth=0)
            except Exception:
                print(format_exc())

    def extract_cheape_from_halo_map(self, halo_map, output_path=""):
        if halo_map.engine != "halo1yelo":
            return ""

        if not output_path:
            output_path = sanitize_path(
                os.path.join(self.tk_tags_dir.get(),
                     halo_map.map_header.map_name + "_cheape.map"))

        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))

        cheape = halo_map.map_header.yelo_header.cheape_definitions
        size        = cheape.size
        decomp_size = cheape.decompressed_size

        halo_map.map_data.seek(cheape.offset)
        cheape_data = halo_map.map_data.read(size)
        mode = 'r+b' if os.path.isfile(output_path) else 'w+b'
        with open(output_path, mode) as f:
            f.truncate(0)
            if decomp_size and decomp_size != size:
                cheape_data = zlib.decompress(cheape_data)
            f.write(cheape_data)

        return output_path

    def generate_map_info_string(self):
        if not self.map_loaded:
            return ""

        return self.active_map.generate_map_info_string()
