#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import os
import shutil
import sys
import zlib

from pathlib import Path, PureWindowsPath
from struct import unpack
from time import time
from traceback import format_exc

from supyr_struct.buffer import get_rawdata_context, PeekableMmap
from supyr_struct.defs import constants as supyr_constants
from supyr_struct.field_types import FieldType
from supyr_struct.util import path_normalize


from reclaimer.constants import GEN_1_HALO_ENGINES, GEN_2_ENGINES
from reclaimer.halo_script.hsc import get_hsc_data_block, HSC_IS_GLOBAL,\
     get_h1_scenario_script_object_type_strings
from reclaimer.hek import hardcoded_ce_tag_paths
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
     get_tag_index, get_map_magic
from reclaimer.meta.class_repair import class_repair_functions,\
     get_tagc_refs
from reclaimer.meta.rawdata_ref_editing import rawdata_ref_move_functions
from reclaimer.meta.halo1_map_fast_functions import class_bytes_by_fcc

from refinery.constants import INF, ACTIVE_INDEX, MAP_TYPE_ANY,\
     MAP_TYPE_REGULAR, MAP_TYPE_RESOURCE
from refinery import crc_functions
from refinery import editor_constants as e_c
from refinery.exceptions import RefineryError, MapNotLoadedError,\
     EngineDetectionError, MapAlreadyLoadedError, CouldNotGetMetaError,\
     InvalidTagIdError, InvalidClassError, MetaConversionError,\
     DataExtractionError
from refinery.queue_item import RefineryQueueItem
from refinery.heuristic_deprotection.constants import VERY_HIGH_PRIORITY
from refinery.heuristic_deprotection.functions import heuristic_deprotect
from refinery.tag_index.tag_path_handler import TagPathHandler
from refinery.tag_index.tag_path_detokenizer import TagPathDetokenizer
from refinery.util import inject_file_padding, int_to_fourcc

from supyr_struct.util import is_path_empty


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


def get_halo_map_section_ends(halo_map):
    head  = halo_map.map_header
    index = halo_map.tag_index
    raw_data_end    = index.model_data_offset
    vertex_data_end = index.vertex_data_size + raw_data_end
    index_data_end  = index.model_data_size  + raw_data_end
    meta_data_end   = head.tag_data_size +  head.tag_index_header_offset
    return raw_data_end, vertex_data_end, index_data_end, meta_data_end


def expand_halo_map(halo_map, raw_data_expansion=0, vertex_data_expansion=0,
                    triangle_data_expansion=0, meta_data_expansion=0):
    map_file   = halo_map.get_writable_map_data()
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
            func = rawdata_ref_move_functions.get(int_to_fourcc(ref.class_1.data))
            if func is None or ref.indexed:
                continue
            func(ref.id & 0xFFff, tag_index_array, map_file,
                 halo_map.map_magic, halo_map.engine, diffs_by_offsets)

    map_file.flush()
    return map_end


class RefineryCore:
    # active map settings
    active_engine_name = ""
    active_map_name = ""
    _active_map_path = ""

    # default directories and tagslist path
    _tags_dir = Path("")
    _data_dir = Path("")
    _tagslist_path = Path("")

    # settings
    autoload_resources = True
    do_printout = False
    print_errors = False

    # extraction settings
    force_lower_case_paths = True
    rename_scnr_dups = False
    overwrite = False
    recursive = False
    decode_adpcm = True
    generate_uncomp_verts = True
    generate_comp_verts = False
    use_tag_index_for_script_names = True
    use_scenario_names_for_script_names = True
    bitmap_extract_keep_alpha = True
    bitmap_extract_format = "dds"
    globals_overwrite_mode = 0

    skip_seen_tags_during_queue_processing = True
    disable_safe_mode = False
    disable_tag_cleaning = False

    # deprotection settings
    fix_tag_classes = True
    fix_tag_index_offset = False
    use_minimum_priorities = True
    use_heuristics = True
    valid_tag_paths_are_accurate = True
    scrape_tag_paths_from_scripts = True
    limit_tag_path_lengths = True
    shallow_ui_widget_nesting = True
    rename_cached_tags = True
    print_heuristic_name_changes = True

    # dictionary of all loaded map collections by their engine id strings
    _maps_by_engine = ()
    _extract_queue = ()

    def __init__(self, *args, **kwargs):
        self.tags_dir = Path.cwd().joinpath("tags")
        self.data_dir = Path.cwd().joinpath("data")
        self.tagslist_path = self.tags_dir.joinpath("tagslist.txt")
        self._maps_by_engine = {}
        self._extract_queue = []

    @property
    def active_map_path(self):
        return self._active_map_path
    @active_map_path.setter
    def active_map_path(self, new_val):
        if not isinstance(new_val, Path):
            new_val = Path(new_val)
        self._active_map_path = new_val

    @property
    def tags_dir(self):
        return self._tags_dir
    @tags_dir.setter
    def tags_dir(self, new_val):
        if not isinstance(new_val, Path):
            new_val = Path(new_val)
        self._tags_dir = new_val

    @property
    def data_dir(self):
        return self._data_dir
    @data_dir.setter
    def data_dir(self, new_val):
        if not isinstance(new_val, Path):
            new_val = Path(new_val)
        self._data_dir = new_val

    @property
    def tagslist_path(self):
        return self._tagslist_path
    @tagslist_path.setter
    def tagslist_path(self, new_val):
        if not isinstance(new_val, Path):
            new_val = Path(new_val)
        self._tagslist_path = new_val

    @property
    def maps_by_engine(self): return self._maps_by_engine
    @property
    def extract_queue(self): return self._extract_queue

    @property
    def map_loaded(self):  return self.active_map is not None
    @property
    def active_maps(self): return self.maps_by_engine.get(ACTIVE_INDEX, {})
    @property
    def active_map(self):  return self.active_maps.get(ACTIVE_INDEX)

    def enqueue(self, operation="extract_tags", **kwargs):
        if isinstance(operation, RefineryQueueItem):
            self._extract_queue.append(operation)
            return
        kwargs.setdefault("engine", ACTIVE_INDEX)
        kwargs.setdefault("map_name", ACTIVE_INDEX)
        self._extract_queue.append(RefineryQueueItem(operation, **kwargs))

    def dequeue(self, index=0):
        if index in range(len(self._extract_queue)):
            return self._extract_queue.pop(index)

    def set_active_engine(self, name=None, map_name=None):
        if name == ACTIVE_INDEX and map_name == ACTIVE_INDEX:
            return

        engine = None
        if name is None and self.maps_by_engine:
            engine = iter(self.maps_by_engine).__next__()
        elif name in self.maps_by_engine:
            engine = name

        next_maps = self.maps_by_engine.get(engine)
        if not next_maps:
            next_map_name = None
        elif map_name in next_maps:
            next_map_name = map_name
        elif next_maps.get(ACTIVE_INDEX):
            next_map_name = next_maps[ACTIVE_INDEX].map_name
        else:
            next_map_name = iter(sorted(next_maps)).__next__()

        # unset any currently active engine and only set
        # it if we have a valid map name to make active
        self.maps_by_engine.pop(ACTIVE_INDEX, None)
        if next_map_name:
            self.maps_by_engine[ACTIVE_INDEX] = next_maps
            next_maps.pop(ACTIVE_INDEX, None)

        self.active_engine_name = engine if next_maps else ""
        self.set_active_map(next_map_name)

    def set_active_map(self, name=None):
        if name == ACTIVE_INDEX:
            return

        map_name = None
        if name is None and self.active_maps:
            map_name = iter(self.active_maps).__next__()
        elif name in self.active_maps:
            map_name = name

        next_map = self.active_maps.get(map_name)
        self.active_maps.pop(ACTIVE_INDEX, None)
        if next_map:
            self.active_maps[ACTIVE_INDEX] = next_map

        self.active_map_path = next_map.filepath if next_map else ""
        self.active_map_name = map_name if next_map else ""

    def unload_maps(self, map_type=MAP_TYPE_REGULAR,
                    engines_to_unload=(ACTIVE_INDEX, ),
                    maps_to_unload=(ACTIVE_INDEX, )):
        if engines_to_unload is None:
            engines_to_unload = tuple(self.maps_by_engine.keys())

        for engine in engines_to_unload:
            maps = self.maps_by_engine.get(engine, {})
            map_names = maps_to_unload
            if map_names is None:
                map_names = tuple(maps.keys())

            active_map = self.active_map
            for map_name in map_names:
                halo_map = maps.get(map_name)
                if not halo_map:
                    continue

                is_rsrc = getattr(halo_map, "is_resource", False)
                if (map_type == MAP_TYPE_ANY or
                    (map_type == MAP_TYPE_RESOURCE and is_rsrc) or
                    (map_type == MAP_TYPE_REGULAR and not is_rsrc)):
                    self.unload_map(map_name, engine)

        for engine in tuple(self.maps_by_engine):
            # remove any engine maps without loaded maps.
            if not self.maps_by_engine[engine]:
                self.maps_by_engine.pop(engine, None)

        if not self.active_maps:
            self.set_active_engine()
        elif not self.active_map:
            self.set_active_map()

    def unload_map(self, map_name=ACTIVE_INDEX, engine=ACTIVE_INDEX, **kw):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        if halo_map is None:
            return

        if halo_map is self.active_map:
            self.active_map_name = ""

        halo_map.unload_map()

    def save_map(self, save_path=None, map_name=ACTIVE_INDEX,
                 engine=ACTIVE_INDEX, **kw):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)

        raw_data_expansion = kw.pop("raw_data_expansion", 0)
        meta_data_expansion = kw.pop("meta_data_expansion", 0)
        vertex_data_expansion = kw.pop("vertex_data_expansion", 0)
        triangle_data_expansion = kw.pop("triangle_data_expansion", 0)
        assert raw_data_expansion      >= 0
        assert meta_data_expansion     >= 0
        assert vertex_data_expansion   >= 0
        assert triangle_data_expansion >= 0

        fix_tag_index_offset = kw.pop(
            "fix_tag_index_offset", self.fix_tag_index_offset)

        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        if halo_map is None:
            raise KeyError("No map loaded and none provided.")
        elif halo_map.is_resource:
            raise TypeError("Cannot save resource maps.")
        elif halo_map.engine not in ("halo1ce", "halo1yelo",
                                     "halo1pc", "halo1vap"):
            raise TypeError("Cannot save this kind of map.")
        elif is_path_empty(save_path):
            save_path = halo_map.filepath

        save_path = Path(save_path)
        if not save_path.suffix:
            save_path = save_path.with_suffix(
                '.yelo' if 'yelo' in halo_map.engine else '.map')

        save_dir = save_path.parent
        save_dir.mkdir(exist_ok=True, parents=True)

        try:
            map_file = halo_map.map_data
            if save_path == halo_map.filepath:
                out_file = map_file = halo_map.get_writable_map_data()
            else:
                # use r+ mode rather than w if the file os.path.exists
                # since it might be hidden. apparently on windows
                # the w mode will fail to open hidden files.
                if save_path.is_file():
                    tmp_file = save_path.open('r+b')
                    tmp_file.truncate(0)
                else:
                    tmp_file = save_path.open('w+b')

                map_file.seek(0) # need to seek to 0 as shutil.copyfileobj uses
                tmp_file.seek(0) # the current file offsets for copying to/from
                shutil.copyfileobj(map_file, tmp_file)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                tmp_file.close()

                with save_path.open('r+b') as f:
                    out_file = PeekableMmap(f.fileno(), 0)

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
            if fix_tag_index_offset:
                tag_index.tag_index_offset = index_magic + tag_index.get_size()

            # update the map_data
            halo_map.map_data = out_file
            if map_file is not out_file:
                map_file.close()

            # expand the map's sections if necessary
            expansions = (raw_data_expansion, vertex_data_expansion,
                          triangle_data_expansion, meta_data_expansion)
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

            # set the size of the map in the header to 0 to fix a bug where
            # halo will leak file handles for very large maps. Also removes
            # the map size limitation so halo can load stupid big maps.
            if halo_map.engine in ("halo1ce", "halo1yelo", "halo1vap"):
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

            halo_map.filepath = halo_map.decomp_filepath = save_path
        except Exception:
            if halo_map.map_data is not out_file:
                out_file.close()
            raise

        return save_path

    def load_map(self, map_path, replace_if_same_name=False, **kw):
        make_active        = kw.pop("make_active", None)
        do_printout        = kw.get("do_printout", self.do_printout)
        autoload_resources = kw.pop("autoload_resources", self.autoload_resources)

        if do_printout:
            print("Loading %s..." % map_path.name)

        with get_rawdata_context(filepath=map_path, writable=False) as f:
            head_sig   = unpack("<I", f.peek(4))[0]
            map_header = get_map_header(f, True)
            engine     = get_map_version(map_header)

        is_halo1_rsrc = False
        if engine is None and head_sig in (1, 2, 3):
            # gotta do some hacky shit to figure out this engine
            rsrc_map = Halo1RsrcMap({})
            rsrc_map.load_map(map_path)
            engine = rsrc_map.engine
            is_halo1_rsrc = True

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

        if make_active is None and (
                maps.get(ACTIVE_INDEX) is None or
                maps.get(ACTIVE_INDEX, object()) is maps.get(map_name)):
            # only make active if unspecified and no map currently active
            # or the active map is being replaced when this one is loaded
            make_active = True

        if maps.get(map_name) is not None:
            self.unload_maps(None, (engine, ), (map_name, ))

        if is_halo1_rsrc:
            new_map = Halo1RsrcMap(maps)
        elif engine in halo_map_wrappers_by_engine:
            new_map = halo_map_wrappers_by_engine[engine](maps)
        else:
            raise EngineDetectionError(
                'Could not determine map engine for "%s"' % map_path)

        new_map.load_map(map_path, **kw)

        if make_active:
            maps[ACTIVE_INDEX] = new_map
            self.active_map_name = map_name
            self.active_map_path = new_map.filepath

        if not self.maps_by_engine.get(ACTIVE_INDEX):
            self.maps_by_engine[ACTIVE_INDEX] = maps
            self.active_engine_name = engine

        if autoload_resources:
            self.load_resource_maps(new_map)

        return new_map

    def load_resource_maps(self, halo_map=None, maps_dir="", map_paths=(), **kw):
        if halo_map is None:
            halo_map = self.active_map

        if not halo_map:
            return set()

        return halo_map.load_resource_maps(maps_dir, map_paths, **kw)

    def deprotect_all(self, **kw):
        for engine in self.maps_by_engine:
            if engine not in ("halo1ce", "halo1yelo", "halo1pc", "halo1vap"):
                continue

            maps = self.maps_by_engine[engine]
            for map_name in sorted(maps):
                try:
                    halo_map = maps.get(map_name)
                    if halo_map is not None and (map_name != ACTIVE_INDEX and
                                                 not halo_map.is_resource):
                        self.deprotect(halo_map.filepath, map_name, engine, **kw)
                except Exception:
                    print(format_exc())

    def deprotect(self, save_path=None, map_name=ACTIVE_INDEX,
                  engine=ACTIVE_INDEX, **kw):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)

        if not self.map_loaded:
            raise KeyError("No map loaded.")
        elif halo_map.is_resource:
            raise TypeError("Cannot deprotect resource maps.")
        elif halo_map.engine not in ("halo1ce", "halo1yelo",
                                     "halo1pc", "halo1vap"):
            raise TypeError("Cannot deprotect this kind of map.")

        if is_path_empty(save_path):
            save_path = halo_map.filepath

        save_path = Path(save_path)

        do_printout  = kw.pop("do_printout", self.do_printout)
        print_errors = kw.pop("print_errors", self.print_errors)

        use_heuristics = kw.pop(
            "use_heuristics", self.use_heuristics)
        fix_tag_classes = kw.pop(
            "fix_tag_classes", self.fix_tag_classes)
        limit_tag_path_lengths = kw.pop(
            "limit_tag_path_lengths", self.limit_tag_path_lengths)
        scrape_tag_paths_from_scripts = kw.pop(
            "scrape_tag_paths_from_scripts", self.scrape_tag_paths_from_scripts)
        rename_cached_tags = kw.pop(
            "rename_cached_tags", self.rename_cached_tags)
        valid_tag_paths_are_accurate = kw.pop(
            "valid_tag_paths_are_accurate", self.valid_tag_paths_are_accurate)
        spoof_checksum = halo_map.force_checksum
        if is_path_empty(self.save_map(
                save_path, map_name, engine,
                prompt_strings_expand=False,
                prompt_internal_rename=False)):
            return

        # get the active map AFTER saving because it WILL have changed
        halo_map        = self.active_map
        map_type        = halo_map.map_header.map_type.enum_name
        tag_index_array = halo_map.tag_index.tag_index

        halo_map.force_checksum = spoof_checksum

        if fix_tag_classes:
            try:
                self.repair_tag_classes(map_name, engine)
            except Exception:
                if not print_errors:
                    raise
                print(format_exc())

        tag_path_handler = TagPathHandler(tag_index_array)

        tag_path_handler.set_path_by_priority(
            halo_map.tag_index.scenario_tag_id & 0xFFff,
            "levels\\%s\\%s" % (halo_map.map_header.map_name,
                                halo_map.map_header.map_name), INF, True)

        # rename cached tags using tag paths found in resource maps
        if rename_cached_tags:
            try:
                self.sanitize_resource_tag_paths(tag_path_handler,
                                                 map_name, engine)
            except Exception:
                if not print_errors:
                    raise
                print(format_exc())

        tag_paths_to_not_rename = set()
        ignore_filepath = e_c.REFINERYLIB_DIR.joinpath(
            "tag_paths_to_never_rename.txt")
        try:
            with ignore_filepath.open("r") as file:
                for line in file:
                    line = str(PureWindowsPath(line.split(";")[0])).lower()
                    if line:
                        tag_paths_to_not_rename.add(line)
        except Exception:
            print("Could not read from '%s'" % ignore_filepath)

        # never want to overwrite these as they are seekd out by name and class
        for i in range(len(tag_index_array)):
            tag_path  = tag_path_handler.get_full_tag_path(i).lower()
            tag_class = tag_path_handler.get_ext(i).lower()

            if (tag_path in hardcoded_ce_tag_paths.HARDCODED_TAG_PATHS or
                tag_path in tag_paths_to_not_rename):

                tag_path_handler.set_overwritable(i, False)
                tag_path_handler.set_priority(i, INF)
                if tag_class in (
                        "actor", "bitmap", "camera_track", "color_table",
                        "hud_message_text", "input_device_defaults",
                        "physics", "point_physics", "sound_environment",
                        "string_list", "unicode_string_list", "wind"):
                    # these tags dont have dependencies, so we can
                    # set their minimum priority to infinite
                    tag_path_handler.set_priority_min(i, INF)

        if valid_tag_paths_are_accurate:
            for b in tag_index_array:
                if not b.path.lower().startswith("protected"):
                    tag_path_handler.set_overwritable(b.id, False)
                    tag_path_handler.set_priority(b.id, VERY_HIGH_PRIORITY)

        try:
            tagc_names = self.detect_tag_collection_names(map_name, engine)
            if do_printout:
                print("Renaming tag collections\n"
                      "tag_id\ttag_path\n")

            for tag_id, tag_path in tagc_names.items():
                if do_printout:
                    print(tag_id, tag_path, sep="\t")
                tag_path_handler.set_path_by_priority(
                    tag_id, tag_path, VERY_HIGH_PRIORITY, True, False)

        except Exception:
            if not print_errors:
                raise
            print(format_exc())

        if scrape_tag_paths_from_scripts:
            try:
                self._script_scrape_deprotect(
                    tag_path_handler, map_name, engine,
                    do_printout=do_printout, print_errors=print_errors)
            except Exception:
                if not print_errors:
                    raise
                print(format_exc())

        if use_heuristics:
            try:
                self._heuristics_deprotect(
                    tag_path_handler, map_name, engine,
                    do_printout=do_printout, print_errors=print_errors)
            except Exception:
                if not print_errors:
                    raise
                print(format_exc())

        if limit_tag_path_lengths:
            try:
                tag_path_handler.shorten_paths(254, do_printout=do_printout,
                                               print_errors=print_errors)
            except Exception:
                if not print_errors:
                    raise
                print(format_exc())

        # calculate the maps new checksum
        if not halo_map.force_checksum:
            halo_map.map_header.crc32 = crc_functions.calculate_ce_checksum(
                halo_map.get_writable_map_data(), halo_map.index_magic)

        self.save_map(save_path, map_name, engine,
                      prompt_strings_expand=False,
                      prompt_internal_rename=False)

        # record the original tag_paths so we know if any were changed
        halo_map.cache_original_tag_paths()

    def detect_tag_collection_names(self, map_name=ACTIVE_INDEX, engine=ACTIVE_INDEX):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        tag_type_names = {}
        if not halo_map:
            return tag_type_names

        map_type        = halo_map.map_header.map_type.enum_name
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
                tag_classes_by_id, tag_index_array)

            reffed_tag_types = set(reffed_tag_types)
            tag_path = None
            if reffed_tag_types == set(["devc"]):
                tag_path = "ui\\ui_input_device_defaults"
            elif reffed_tag_types == set(["DeLa"]):
                if   map_type == "sp": tag_path = "ui\\shell\\solo"
                elif map_type == "mp": tag_path = "ui\\shell\\multiplayer"
                elif map_type == "ui": tag_path = "ui\\shell\\main_menu"

            tag_id = b.id & 0xFFff
            if tag_path is not None:
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

            tag_name = None
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

    def repair_tag_classes(self, map_name=ACTIVE_INDEX, engine=ACTIVE_INDEX):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        repaired = {}
        if not halo_map:
            return repaired

        if halo_map.engine not in ("halo1ce", "halo1yelo",
                                   "halo1pc", "halo1vap"):
            raise TypeError('Cannot repair tag classes in "%s" maps' %
                            halo_map.engine)

        tag_index_array = halo_map.tag_index.tag_index

        # locate the tags to start deprotecting with
        repair = {}
        for b in tag_index_array:
            if b.id == halo_map.tag_index.scenario_tag_id:
                tag_cls = "scnr"
            elif b.indexed or b.class_1.enum_name in (
                    supyr_constants.INVALID, "NONE"):
                continue
            else:
                tag_cls = int_to_fourcc(b.class_1.data)

            tag_id = b.id & 0xFFff
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

                try:
                    if tag_cls != "sbsp":
                        class_repair_functions[tag_cls](
                            tag_id, tag_index_array, halo_map.get_writable_map_data(),
                            halo_map.map_magic, next_repair, halo_map.engine,
                            not self.disable_safe_mode)

                        # replace meta with the deprotected one
                        if tag_cls == "matg":
                            halo_map.matg_meta = halo_map.get_meta(tag_id)
                        elif tag_cls == "scnr":
                            halo_map.scnr_meta = halo_map.get_meta(tag_id)
                    elif tag_id in halo_map.bsp_headers:
                        class_repair_functions[tag_cls](
                            halo_map.bsp_headers[tag_id].meta_pointer,
                            tag_index_array, halo_map.get_writable_map_data(),
                            halo_map.bsp_magics[tag_id] - halo_map.bsp_header_offsets[tag_id],
                            next_repair, halo_map.engine, halo_map.map_magic,
                            not self.disable_safe_mode)
                except Exception:
                    print(format_exc())

            # start repairing the newly accumulated tags
            repair = next_repair

            # exhausted tags to repair. try to repair tag colletions now
            if not repair:
                for b in tag_index_array:
                    tag_id = b.id & 0xFFff
                    tag_cls = None
                    if tag_id in repaired:
                        continue
                    elif b.class_1.enum_name not in (supyr_constants.INVALID,
                                                     "NONE"):
                        tag_cls = int_to_fourcc(b.class_1.data)
                    else:
                        _, reffed_tag_types = get_tagc_refs(
                            b.meta_offset, halo_map.get_writable_map_data(),
                            halo_map.map_magic, repaired, tag_index_array
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

        # try to find the ui_widget_collection tag based on what tags it contains
        for b in tag_index_array:
            tag_id = b.id & 0xFFff
            if b.class_1.enum_name in ("tag_collection", "ui_widget_collection"):
                reffed_tag_ids, reffed_tag_types = get_tagc_refs(
                    b.meta_offset, halo_map.get_writable_map_data(),
                    halo_map.map_magic, repaired, tag_index_array)
                if set(reffed_tag_types) == set(["DeLa"]):
                    repaired[tag_id] = "Soul"

        # write the deprotected tag classes fourcc's to each
        # tag's header in the tag index in the map buffer
        index_array_offset = halo_map.tag_index.tag_index_offset - halo_map.map_magic
        for tag_id, tag_cls in repaired.items():
            tag_index_ref = tag_index_array[tag_id]
            classes_int = int.from_bytes(class_bytes_by_fcc[tag_cls], 'little')
            tag_index_ref.class_1.data = classes_int & 0xFFffFFff
            tag_index_ref.class_2.data = (classes_int >> 32) & 0xFFffFFff
            tag_index_ref.class_3.data = (classes_int >> 64) & 0xFFffFFff

        return repaired

    def sanitize_resource_tag_paths(self, path_handler, map_name=ACTIVE_INDEX,
                                    engine=ACTIVE_INDEX):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        if not halo_map:
            return

        engine_maps = halo_map.maps
        for b in halo_map.tag_index.tag_index:
            tag_id = b.id & 0xFFff
            rsrc_tag_id = b.meta_offset
            rsrc_map = None
            if not b.indexed:
                continue
            elif b.class_1.enum_name == "bitmap":
                rsrc_map = engine_maps.get("~bitmaps", engine_maps.get("bitmaps"))
            elif b.class_1.enum_name == "sound":
                rsrc_map = engine_maps.get("~sounds", engine_maps.get("sounds"))
            elif b.class_1.enum_name in ("font", "hud_message_text",
                                         "unicode_string_list"):
                rsrc_map = engine_maps.get("~loc", engine_maps.get("loc"))

            rsrc_tag_index = getattr(rsrc_map, "orig_tag_index", ())
            if rsrc_tag_id not in range(len(rsrc_tag_index)):
                continue

            path_handler.set_path(tag_id, rsrc_tag_index[rsrc_tag_id].tag.path)
            path_handler.set_overwritable(tag_id, False)

    def _script_scrape_deprotect(self, path_handler, map_name=ACTIVE_INDEX,
                                 engine=ACTIVE_INDEX, **kw):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        if not halo_map:
            return

        scnr_meta = halo_map.get_meta(halo_map.tag_index.scenario_tag_id)
        if not scnr_meta:
            raise ValueError("Could not get scenario data for script scraping.")

        do_printout = kw.pop("do_printout", self.do_printout)

        string_data = scnr_meta.script_string_data.data.decode("latin-1")
        syntax_data = get_hsc_data_block(raw_syntax_data=scnr_meta.script_syntax_data.data)

        seen = set()
        for node in syntax_data.nodes:
            if node.type not in range(24, 32) or (node.flags & HSC_IS_GLOBAL):
                # node does NOT reference a tag. if HSC_IS_GLOBAL is set, the
                # node actually refers to a tag stored in a script globals.
                continue

            # make sure the tag id points to a valid tag
            tag_id = node.data & 0xFFff
            if tag_id in seen or path_handler.get_index_ref(tag_id) is None:
                continue

            seen.add(tag_id)

            string_end = string_data.find("\x00", node.string_offset)
            new_tag_path = string_data[node.string_offset: string_end]
            if new_tag_path:
                path_handler.set_path_by_priority(
                    tag_id, new_tag_path, INF, True, do_printout)

    def _heuristics_deprotect(self, path_handler, map_name=ACTIVE_INDEX,
                              engine=ACTIVE_INDEX, **kw):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        if not halo_map:
            return

        ids_to_deprotect_by_class = {class_name: [] for class_name in (
            "scenario", "globals", "hud_globals", "project_yellow", "vehicle",
            "actor_variant", "biped", "weapon", "equipment", "tag_collection",
            "ui_widget_collection", "ui_widget_definition", "scenario_structure_bsp"
            )}

        do_printout = kw.pop("do_printout", self.do_printout)
        print_errors = kw.pop("print_errors", self.print_errors)
        use_minimum_priorities = kw.pop(
            "use_minimum_priorities", self.use_minimum_priorities)
        shallow_ui_widget_nesting = kw.pop(
            "shallow_ui_widget_nesting", self.shallow_ui_widget_nesting)
        print_name_changes = do_printout and kw.pop(
            "print_heuristic_name_changes", self.print_heuristic_name_changes)

        if halo_map is None:
            halo_map = self.active_map

        if not halo_map:
            return

        tag_index_array = halo_map.tag_index.tag_index
        matg_meta = halo_map.matg_meta
        hudg_id = 0xFFFF if not matg_meta else\
                  matg_meta.interface_bitmaps.STEPTREE[0].hud_globals.id & 0xFFff
        hudg_meta = halo_map.get_meta(hudg_id, True)

        if hudg_meta:
            block = hudg_meta.messaging_parameters
            items_meta = halo_map.get_meta(block.item_message_text.id & 0xFFff, True)
            icons_meta = halo_map.get_meta(block.alternate_icon_text.id & 0xFFff, True)

            if items_meta: path_handler.set_item_strings(items_meta)
            if icons_meta: path_handler.set_icon_strings(icons_meta)

        # reset the name of each tag with a default priority and that
        # currently resides in the tags directory root to "protected_XXXX"
        for i in range(len(tag_index_array)):
            if ((path_handler.get_priority(i) == path_handler.def_priority)
                and not path_handler.get_sub_dir(i)):
                path_handler.set_path_by_priority(
                    i, "protected_%s" % i, override=True, do_printout=False)

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
                "actor_variant", "biped",
                "ui_widget_collection", "ui_widget_definition", "hud_globals",
                "project_yellow", "globals", "scenario", "tag_collection"):
            if do_printout:
                print("Renaming %s tags" % tag_type)
                if print_name_changes:
                    print("tag_id\tweight\ttag_path\n")

            for tag_id in ids_to_deprotect_by_class[tag_type]:
                if tag_id is None:
                    continue

                try:
                    depth = 0 if tag_type == "ui_widget_collection" else INF
                    heuristic_deprotect(
                        tag_id, halo_map, path_handler,
                        do_printout=print_name_changes, depth=depth,
                        shallow_ui_widget_nesting=shallow_ui_widget_nesting,
                        use_minimum_priorities=use_minimum_priorities)
                except Exception:
                    if not print_errors:
                        raise
                    print(format_exc())

        if do_printout:
            print("Final actor_variant rename pass")
            if print_name_changes:
                print("tag_id\tweight\ttag_path\n")

        for tag_id in ids_to_deprotect_by_class["actor_variant"]:
            if tag_id is None: continue
            try:
                depth = INF if (path_handler.get_priority(tag_id) ==
                                path_handler.def_priority) else 1
                heuristic_deprotect(tag_id, halo_map, path_handler, depth=depth,
                                 do_printout=print_name_changes)
            except Exception:
                if not print_errors:
                    raise
                print(format_exc())

        if do_printout:
            print("Final scenery rename pass")
            if print_name_changes:
                print("tag_id\tweight\ttag_path\n")

        for tag_id in scen_ids:
            if tag_id is None: continue
            try:
                depth = INF if (path_handler.get_priority(tag_id) ==
                                path_handler.def_priority) else 0
                heuristic_deprotect(tag_id, halo_map, path_handler, depth=depth,
                                 do_printout=print_name_changes)
            except Exception:
                if not print_errors:
                    raise
                print(format_exc())

    def extract_cheape(self, filepath=Path(""), map_name=ACTIVE_INDEX,
                       engine=ACTIVE_INDEX):
        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        if not halo_map or halo_map.engine != "halo1yelo":
            return Path("")

        filepath = Path(filepath)
        if is_path_empty(filepath):
            filepath = self.tags_dir.joinpath(
                halo_map.map_header.map_name + "_cheape.map")

        filepath.parent.mkdir(exist_ok=True, parents=True)

        cheape = halo_map.map_header.yelo_header.cheape_definitions
        size        = cheape.size
        decomp_size = cheape.decompressed_size

        halo_map.map_data.seek(cheape.offset)
        cheape_data = halo_map.map_data.read(size)
        mode = 'r+b' if filepath.is_file() else 'w+b'
        with filepath.open(mode) as f:
            f.truncate(0)
            if decomp_size and decomp_size != size:
                cheape_data = zlib.decompress(cheape_data)
            f.write(cheape_data)

        return filepath

    def process_queue(self, **kw):
        tags_extracted_by_map = {}
        data_extracted_by_map = {}
        cheapes_extracted = set()

        start = time()
        extract_kw = dict(tags_extracted_by_map=tags_extracted_by_map,
                          data_extracted_by_map=data_extracted_by_map,
                          cheapes_extracted=cheapes_extracted)

        item = self.dequeue()
        while item:
            if kw.get("do_printout", self.do_printout):
                engine = getattr(item, "engine", None)
                map_name = getattr(item, "map_name", None)

                halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
                print("%s: " % item.operation, end="")
                if halo_map:
                    print("%s: %s" % (halo_map.engine, halo_map.map_name))
                elif engine:
                    print(item.engine)
                elif map_name:
                    print(item.map_name)

            try:
                self.process_queue_item(item, **extract_kw)
                if kw.get("do_printout", self.do_printout):
                    print()  # print a new line to separate operations
            except RefineryError:
                print(format_exc(0)) # only last line for RefineryErrors
            except Exception:
                print(format_exc())

            item = self.dequeue(0)

        if kw.get("do_printout", self.do_printout) and (tags_extracted_by_map or
                                                        data_extracted_by_map):
            tags_extracted = data_extracted = 0
            for tag_ids in tags_extracted_by_map.values():
                tags_extracted += len(tag_ids)

            for tag_ids in data_extracted_by_map.values():
                data_extracted += len(tag_ids)

            print("Extracted %s tags and %s data. Took %s seconds.\n" %
                  (tags_extracted, data_extracted, round(time() - start, 1)))

        return tags_extracted_by_map, data_extracted_by_map

    def process_queue_item(self, queue_item, **kw):
        tags_by_map = kw.pop("tags_extracted_by_map", {})
        data_by_map = kw.pop("data_extracted_by_map", {})
        cheapes_extracted = kw.pop("cheapes_extracted", set())

        op = queue_item.operation
        kw.update(queue_item.operation_kwargs)

        engine = kw.pop("engine", ACTIVE_INDEX)
        map_name = kw.pop("map_name", ACTIVE_INDEX)
        tag_ids = kw.pop("tag_ids", ())
        tag_id = kw.pop("tag_id", 0xFFff)

        dir_path = Path(kw.get("dir_path", ""))
        filepath = Path(kw.pop("filepath", ""))

        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        engine = getattr(halo_map, "engine", None)
        map_name = getattr(halo_map, "map_name", None)
        if not halo_map and op not in ("load_map", "set_vars"):
            return

        skip_seen = kw.get("skip_seen_tags_during_queue_processing",
                           self.skip_seen_tags_during_queue_processing)

        if op in ("extract_tags", "extract_data"):
            if op == "extract_tags":
                kw["extract_mode"] = "tags"
                ignore = tags_by_map.setdefault((engine, map_name), set())
            else:
                kw["extract_mode"] = "data"
                ignore = data_by_map.setdefault((engine, map_name), set())

            if skip_seen:
                kw.update(tags_to_ignore=ignore)

            ignore.update(self.extract_tags(
                TagPathDetokenizer(tag_ids).get_filtered_tag_ids(halo_map),
                map_name, engine, **kw))
        elif op == "extract_tag":
            tag_ids = TagPathDetokenizer((tag_id,)).get_filtered_tag_ids(halo_map)
            if len(tag_ids) == 0:
                return
            elif filepath:
                kw["filepath"] = filepath

            kw["extract_mode"] = "tags"
            ignore = tags_by_map.setdefault((engine, map_name), set())

            if tag_ids[0] not in ignore:
                self.extract_tag(tag_ids[0], map_name, engine, **kw)
                ignore.add(tag_ids[0])
        elif op == "extract_cheape":
            if map_name not in cheapes_extracted:
                if is_path_empty(filepath):
                    filepath = Path(kw.pop("out_dir", self.tags_dir)).joinpath(
                        map_name + "_cheape.map")

                cheapes_extracted.add(map_name)
                self.extract_cheape(filepath, map_name, engine)
        elif op == "deprotect_map":
            self.deprotect(filepath, map_name, engine, **kw)
        elif op == "load_map":
            self.load_map(filepath, **kw)
        elif op == "unload_map":
            self.unload_map(map_name, engine, **kw)
        elif op == "save_map":
            self.save_map(filepath, map_name, engine, **kw)
        elif op == "rename_map":
            halo_map.map_header.map_name = queue_item.new_name
        elif op == "spoof_crc":
            halo_map.map_header.crc32 = queue_item.new_crc & 0xFFffFFff
            halo_map.force_checksum = True
        elif op == "set_vars":
            for i in range(len(queue_item.names)):
                name = queue_item.names[i]
                value = queue_item.values[i]
                if not hasattr(self, name):
                    raise ValueError(
                        '%s has no attribute "%s"' % (type(self), name))
                setattr(self, name, value)
        elif op == "rename_tag_by_id":
            tag_ids = TagPathDetokenizer((tag_id,)).get_filtered_tag_ids(halo_map)
            if len(tag_ids) == 0:
                return
            halo_map.rename_tag_by_id(tag_ids[0], queue_item.new_path)
        elif op == "print_dir":
            kw.setdefault("do_printout", True)
            halo_map.print_tag_index(**kw)
        elif op == "print_files":
            kw.setdefault("do_printout", True)
            halo_map.print_tag_index_files(**kw)
        elif op == "print_dir_ct":
            if kw.get("total"):
                print(halo_map.get_total_dir_count(dir_path))
            else:
                print(halo_map.get_dir_count(dir_path))
        elif op == "print_file_ct":
            if kw.get("total"):
                print(halo_map.get_total_file_count(dir_path))
            else:
                print(halo_map.get_file_count(dir_path))
        elif op == "print_dir_names":
            print(halo_map.get_dir_names(dir_path))
        elif op == "print_file_names":
            print(halo_map.get_file_names(dir_path))
        elif op == "print_map_info":
            print(halo_map.generate_map_info_string())
        elif op == "rename_tag":
            halo_map.rename_tag(queue_item.tag_path, queue_item.new_path)
        elif op == "rename_dir":
            halo_map.rename_dir(queue_item.dir_path, queue_item.new_path)
        elif op == "switch_map_by_filepath":
            engine = map_name = None
            for curr_engine in sorted(self.maps_by_engine):
                maps = self.maps_by_engine[curr_engine]
                for curr_map_name in sorted(maps):
                    curr_halo_map = maps[curr_map_name]
                    map_filepath = Path(getattr(curr_halo_map, "filepath", ""))
                    if path_normalize(filepath) == path_normalize(map_filepath):
                        engine = curr_engine
                        map_name = curr_map_name
                        break

                if engine is not None: break

            if engine is not None and map_name is not None:
                self.set_active_engine(engine, map_name)
        elif op == "switch_map":
            self.set_active_map(map_name)
        elif op == "switch_engine":
            self.set_active_engine(engine)
        else:
            raise ValueError('Unknown queue operation "%s"' % op)

    def extract_tags(self, tag_ids, map_name=ACTIVE_INDEX, engine=ACTIVE_INDEX, **kw):
        '''
        Extracts multiple tags from the specified map as either a tag or data.
        If recursive == True and extract_mode == "tags", all dependent tags
        will be extracted as well. Returns a set() of all tag ids extracted.
        '''
        extract_mode = kw.setdefault("extract_mode", "tags")
        assert extract_mode in ("tags", "data")

        tags_to_ignore = set(kw.pop("tags_to_ignore", ()))
        recursive     = kw.pop("recursive", self.recursive)
        do_printout   = kw.get("do_printout", self.do_printout)
        tagslist_path = Path(kw.pop("tagslist_path", self.tagslist_path))

        if isinstance(tag_ids, int):
            tag_ids = (tag_ids, )

        if extract_mode == "tags":
            out_dir = Path(kw.setdefault("out_dir", self.tags_dir))
        else:
            out_dir = Path(kw.setdefault("out_dir", self.data_dir))

        extracted = set()
        tagslist = ""

        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        if halo_map is None:
            raise MapNotLoadedError(
                '"%s" is not loaded under engine "%s".' % (map_name, engine))
        elif halo_map.is_resource and halo_map.engine == "halo1pc":
            raise RefineryError(
                "Cannot extract tags directly from Halo PC resource maps")

        is_gen1 = ("halo1" in halo_map.engine or
                   "stubbs" in halo_map.engine or
                   "shadowrun" in halo_map.engine)
        recursive &= is_gen1 and (extract_mode == "tags")

        curr_tag_ids = set(tag_ids)
        while curr_tag_ids:
            next_tag_ids = set()
            if recursive:
                kw["dependency_ids"] = next_tag_ids

            for tag_id in sorted(curr_tag_ids):
                if tag_id in tags_to_ignore:
                    continue

                try:
                    if self.extract_tag(tag_id, map_name, engine, **kw):
                        extracted.add(tag_id)
                        if is_path_empty(tagslist_path):
                            continue

                        tag_index_ref = halo_map.tag_index.tag_index[tag_id]
                        tag_path = "%s.%s" % (PureWindowsPath(tag_index_ref.path),
                                              tag_index_ref.class_1.enum_name)
                        tagslist += "%s: %s\n" % (extract_mode, tag_path)
                except RefineryError:
                    print(format_exc(0)) # only last line for RefineryErrors
                except Exception:
                    print(format_exc())

            tags_to_ignore.update(curr_tag_ids)
            curr_tag_ids = next_tag_ids

        for rsrc_map in halo_map.maps.values():
            if rsrc_map.is_resource or rsrc_map is halo_map:
                rsrc_map.clear_map_cache()

        if not is_path_empty(tagslist_path):
            tagslist = "%s tags in: %s\n%s" % (
                len(extracted), out_dir, tagslist)
            if self.write_tagslist(tagslist, tagslist_path):
                if do_printout:
                    print("Could not create/open tagslist. Either run "
                          "Refinery as admin, or choose a directory "
                          "you have permission to edit/make files in.")

        return extracted

    def extract_tag(self, tag_id, map_name=ACTIVE_INDEX, engine=ACTIVE_INDEX, **kw):
        '''
        Extracts a single tag from the specified map as either a tag or data.
        If dependency_ids is provided as a set(), it will be filled with the
        tag index ids of any dependencies of this tag.

        Returns either True or False, indicating whether or not the
        tag was extracted. True indicates extraction success, with False
        indicating extraction was skipped to not overwrite existing files.
        '''
        extract_mode = kw.pop("extract_mode", "tags")
        assert extract_mode in ("tags", "data")

        do_printout = kw.pop("do_printout", self.do_printout)
        overwrite = kw.pop("overwrite", self.overwrite)
        force_lower_case_paths = kw.pop(
            "force_lower_case_paths", self.force_lower_case_paths)
        use_scenario_names_for_script_names = kw.pop(
            "use_scenario_names_for_script_names",
            self.use_scenario_names_for_script_names)
        use_tag_index_for_script_names = kw.pop(
            "use_tag_index_for_script_names",
            self.use_tag_index_for_script_names)
        disable_safe_mode = kw.pop(
            "disable_safe_mode", self.disable_safe_mode)
        disable_tag_cleaning = kw.pop(
            "disable_tag_cleaning", self.disable_tag_cleaning)


        dependency_ids = kw.pop("dependency_ids", None)

        get_dependencies = isinstance(dependency_ids, set)

        halo_map = self.maps_by_engine.get(engine, {}).get(map_name)
        if halo_map is None:
            raise MapNotLoadedError(
                '"%s" is not loaded under engine "%s".' % (map_name, engine))
        elif halo_map.is_resource and halo_map.engine == "halo1pc":
            raise RefineryError(
                "Cannot extract tags directly from Halo PC resource maps")

        tag_index_array = halo_map.tag_index.tag_index
        if tag_id not in range(len(tag_index_array)):
            raise InvalidTagIdError('tag_id "%s" is not in the tag index.' % tag_id)

        tag_index_ref = tag_index_array[tag_id]
        tag_path = Path(PureWindowsPath(tag_index_ref.path))
        if tag_index_ref.class_1.enum_name in (supyr_constants.INVALID,
                                               "NONE"):
            raise InvalidClassError(
                'Unknown class for "%s". Run deprotection to fix.' % tag_path)

        if extract_mode == "data" and not halo_map.is_data_extractable(tag_index_ref):
            return False

        full_tag_class = tag_index_ref.class_1.enum_name
        tag_path = str(tag_path) + "." + full_tag_class
        if force_lower_case_paths:
            tag_path = tag_path.lower()

        tag_cls = int_to_fourcc(tag_index_ref.class_1.data)
        if extract_mode == "tags":
            out_dir = Path(kw.get("out_dir", self.tags_dir))
            filepath = Path(kw.pop("filepath", out_dir.joinpath(tag_path)))
            do_extract = ((overwrite or not filepath.is_file())
                          and tag_cls in halo_map.tag_headers)

            if not(do_extract or get_dependencies):
                return False
        else:
            out_dir = Path(kw.get("out_dir", self.data_dir))
            filepath = Path("")
            do_extract = True
            get_dependencies = False # it makes no sense to fill out
            #                          dependencies in data extraction

        is_gen1 = ("halo1" in halo_map.engine or
                   "stubbs" in halo_map.engine or
                   "shadowrun" in halo_map.engine)

        if tag_cls == "matg" and filepath.is_file() and is_gen1:
            # determine if we should overwrite the globals tag
            mode = self.globals_overwrite_mode
            prompt = (mode == 0)
            overwrite = (mode == 1)
            map_type = halo_map.map_header.map_type.enum_name
            if mode == 3 and map_type in ("sp", "ui"):
                prompt = True
            elif mode in (3, 4) and map_type == "mp":
                overwrite = True

            if prompt:
                overwrite = self.prompt_globals_overwrite(halo_map, tag_id)

            if not overwrite:
                return

        if do_printout:
            print("%s: %s" % (extract_mode, tag_path))

        meta = halo_map.get_meta(
            tag_id, True, disable_safe_mode=disable_safe_mode,
            disable_tag_cleaning=disable_tag_cleaning,)

        if not meta:
            raise CouldNotGetMetaError('Could not get meta for "%s"' % tag_path)

        extract_kw = dict(
            hsc_node_strings_by_type={}, out_dir=out_dir, overwrite=overwrite,
            bitmap_ext=kw.pop("bitmap_extract_format", self.bitmap_extract_format),
            bitmap_keep_alpha=kw.pop("bitmap_extract_keep_alpha", self.bitmap_extract_keep_alpha),
            decode_adpcm=kw.pop("decode_adpcm", self.decode_adpcm),
            rename_scnr_dups=kw.pop("rename_scnr_dups", self.rename_scnr_dups),
            generate_uncomp_verts=kw.pop("generate_uncomp_verts", self.generate_uncomp_verts),
            generate_comp_verts=kw.pop("generate_comp_verts", self.generate_comp_verts),
            )

        if is_gen1 and full_tag_class == "scenario" and extract_mode == "data":
            if use_scenario_names_for_script_names:
                extract_kw["hsc_node_strings_by_type"].update(
                    get_h1_scenario_script_object_type_strings(meta))

            if use_tag_index_for_script_names:
                bipeds = meta.bipeds_palette.STEPTREE
                actors = {i: PureWindowsPath(bipeds[i].name.filepath).stem
                          for i in range(len(bipeds))}
                strings = {i: tag_index_array[i].path
                           for i in range(len(tag_index_array))}

                if force_lower_case_paths:
                    actors  = {k: v.lower() for k, v in actors.items()}
                    strings = {k: v.lower() for k, v in strings.items()}

                # actor type strings
                extract_kw["hsc_node_strings_by_type"][35] = actors

                # tag reference path strings
                for i in range(24, 32):
                    extract_kw["hsc_node_strings_by_type"][i] = strings

        tag_refs = () if not (get_dependencies or force_lower_case_paths) else\
                   halo_map.get_dependencies(meta, tag_id, tag_cls)

        if force_lower_case_paths:
            # force all tag references to lowercase
            for ref in tag_refs:
                ref.filepath = ref.filepath.lower()

        if get_dependencies:
            # add dependencies to list to be extracted
            index_len = len(tag_index_array)
            dependency_ids.update(ref.id & 0xFFff for ref in tag_refs if
                                  ref.id & 0xFFff in range(index_len))

            if not do_extract:
                return False

        meta = halo_map.meta_to_tag_data(
            meta, tag_cls, tag_index_ref, **extract_kw)
        if not meta:
            raise MetaConversionError("Failed to convert meta to tag")

        if extract_mode == "data":
            error_str = halo_map.extract_tag_data(meta, tag_index_ref, **extract_kw)
            if error_str:
                raise DataExtractionError(error_str)
            return True

        try:
            filepath.parent.mkdir(exist_ok=True, parents=True)
            with filepath.open('r+b' if filepath.is_file() else 'w+b') as f:
                f.truncate(0)
                f.write(halo_map.tag_headers[tag_cls])
                if is_gen1:
                    with FieldType.force_big:
                        f.write(meta.serialize(calc_pointers=False))
                else:
                    with FieldType.force_normal:
                        f.write(meta.serialize(calc_pointers=False))
        except PermissionError:
            raise RefineryError(
                "Refinery does not have permission to save here. "
                "Running Refinery as admin could potentially fix this.")
        except FileNotFoundError:
            if not e_c.IS_WIN or len(str(filepath)) < 260:
                raise
            raise RefineryError("Filepath is over the Windows 260 character limit.")

        return True

    def prompt_globals_overwrite(self, halo_map, tag_id):
        map_name = halo_map.map_name
        tag_name = halo_map.tag_index.tag_index[tag_id & 0xFFff].path
        return input(
            ('The tag "%s.globals" already exists in the extraction directory. '
             'Do you want to overwrite it with the globals from the map "%s"?'
             '\nType "y" for yes. Anything else means no: ') %
            (tag_name, map_name)
            ).lower().strip() == "y"

    def write_tagslist(self, tagslist, tagslist_path):
        tagslist_path = Path(tagslist_path)
        try:
            f = tagslist_path.open('a')
        except Exception:
            try:
                f = tagslist_path.open('w')
            except Exception:
                try:
                    f = tagslist_path.open('r+')
                except Exception:
                    f = None

        if f is None:
            return True

        f.write(tagslist)
        f.write('\n\n')
        f.close()
        return False

    def generate_map_info_string(self):
        if not self.map_loaded:
            return ""

        return self.active_map.generate_map_info_string()
