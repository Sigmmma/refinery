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


platform = sys.platform.lower()
curr_dir = get_cwd(__file__)
INF = float("inf")


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

    def load_map(self, map_path, will_be_active=True):
        self.load_maps((map_path, ), will_be_active=will_be_active)

    def save_map(self, save_path=None, engine="<active>", map_name="<active>",
                 *a, **kw):
        meta_data_expansion = kw.pop("meta_data_expansion", 0)
        raw_data_expansion = kw.pop("raw_data_expansion", 0)
        vertex_data_expansion = kw.pop("vertex_data_expansion", 0)
        triangle_data_expansion = kw.pop("triangle_data_expansion", 0)
        assert meta_data_expansion     >= 0
        assert raw_data_expansion      >= 0
        assert vertex_data_expansion   >= 0
        assert triangle_data_expansion >= 0

        maps = self.maps_by_engine.get(engine, {})
        halo_map = maps.get(map_name)
        if halo_map is None:
            return
        elif halo_map.is_resource:
            print("Cannot save resource maps.")
            return
        elif halo_map.engine not in ("halo1ce", "halo1yelo", "halo1pc"):
            print("Cannot save this kind of map.")
            return
        elif not save_path:
            save_path = halo_map.filepath

        save_dir  = os.path.dirname(save_path)
        save_path, ext = os.path.splitext(save_path)
        new_map_name = os.path.basename(save_path)
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
                              vertex_data_expansion + triangle_data_expansion)

            orig_tag_paths = halo_map.orig_tag_paths
            map_magic      = halo_map.map_magic
            index_magic    = halo_map.index_magic
            tag_index      = halo_map.tag_index
            index_offset   = tag_index.tag_index_offset
            index_array    = tag_index.tag_index
            index_header_offset = map_header.tag_index_header_offset

            if index_off_diff:
                index_header_offset += index_off_diff
                map_magic = get_map_magic(map_header)

            func = crc_functions.U
            do_spoof  = halo_map.force_checksum and func is not None

            # copy the map to the new save location
            map_file.seek(0, 2)
            map_size = map_file.tell()
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

            # make sure the user wants to expand the map more if needed
            if strings_size > meta_data_expansion:
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
            if do_spoof:
                func([crc^0xFFffFFff, out_file, index_header_offset + 8])
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

    def deprotect_all(self, e=None):
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

                    self._deprotect(maps[map_name].filepath)
                except Exception:
                    print(format_exc())

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

        active_map = self.active_map
        string = "%s\n" % self.active_map_path

        header     = active_map.map_header
        index      = active_map.tag_index
        orig_index = active_map.orig_tag_index
        if hasattr(active_map.map_data, '__len__'):
            decomp_size = str(len(active_map.map_data))
        elif (hasattr(active_map.map_data, 'seek') and
              hasattr(active_map.map_data, 'tell')):
            curr_pos = active_map.map_data.tell()
            active_map.map_data.seek(0, 2)
            decomp_size = str(active_map.map_data.tell())
            active_map.map_data.seek(curr_pos)
        else:
            decomp_size = "unknown"

        if not active_map.is_compressed:
            decomp_size += "(is already uncompressed)"

        map_type = header.map_type.enum_name
        if map_type == "sp":       map_type = "singleplayer"
        elif map_type == "mp":     map_type = "multiplayer"
        elif map_type == "ui":     map_type = "mainmenu"
        elif map_type == "shared":   map_type = "shared"
        elif map_type == "sharedsp": map_type = "shared single player"
        elif active_map.is_resource: map_type = "resource cache"
        elif "INVALID" in map_type:  map_type = "unknown"

        string += ((
            "Header:\n" +
            "    engine version      == %s\n" +
            "    name                == %s\n" +
            "    build date          == %s\n" +
            "    type                == %s\n" +
            "    decompressed size   == %s\n" +
            "    index header offset == %s\n") %
        (active_map.engine, header.map_name, header.build_date,
         map_type, decomp_size, header.tag_index_header_offset))

        string += ((
            "\nCalculated information:\n" +
            "    index magic    == %s\n" +
            "    map magic      == %s\n") %
        (active_map.index_magic, active_map.map_magic))

        tag_index_offset = index.tag_index_offset
        if active_map.engine == "halo2alpha":
            string += ((
                "\nTag index:\n" +
                "    tag count           == %s\n" +
                "    scenario tag id     == %s\n" +
                "    index array pointer == %s\n") %
            (orig_index.tag_count,
             orig_index.scenario_tag_id & 0xFFff, tag_index_offset))
        elif "halo2" in active_map.engine:
            used_tag_count = 0
            local_tag_count = 0
            for index_ref in index.tag_index:
                if is_reserved_tag(index_ref):
                    continue
                elif index_ref.meta_offset != 0:
                    local_tag_count += 1
                used_tag_count += 1

            string += ((
                "\nTag index:\n" +
                "    tag count           == %s\n" +
                "    used tag count      == %s\n" +
                "    local tag count     == %s\n" +
                "    tag types count     == %s\n" +
                "    scenario tag id     == %s\n" +
                "    globals  tag id     == %s\n" +
                "    index array pointer == %s\n") %
            (orig_index.tag_count, used_tag_count, local_tag_count,
             orig_index.tag_types_count,
             orig_index.scenario_tag_id,
             orig_index.globals_tag_id, tag_index_offset))
        elif active_map.engine == "halo3":
            string += ((
                "\nTag index:\n" +
                "    tag count           == %s\n" +
                "    tag types count     == %s\n" +
                "    root tags count     == %s\n" +
                "    index array pointer == %s\n") %
            (orig_index.tag_count, orig_index.tag_types_count,
             orig_index.root_tags_count,
             tag_index_offset - active_map.map_magic))

            for arr_name, arr in (("Partitions", header.partitions),
                                  ("Sections", header.sections),):
                string += "\n%s:\n" % arr_name
                names = ("debug", "resource", "tag", "locale")\
                        if arr.NAME_MAP else range(len(arr))
                for name in names:
                    section = arr[name]
                    string += ((
                        "    %s:\n" +
                        "        address == %s\n" +
                        "        size    == %s\n" +
                        "        offset  == %s\n") %
                    (name, section[0], section[1], section.file_offset)
                    )
        else:
            string += ((
                "\nTag index:\n" +
                "    tag count           == %s\n" +
                "    scenario tag id     == %s\n" +
                "    index array pointer == %s   non-magic == %s\n" +
                "    model data pointer  == %s\n" +
                "    meta data length    == %s\n" +
                "    vertex parts count  == %s\n" +
                "    index  parts count  == %s\n") %
            (index.tag_count, index.scenario_tag_id & 0xFFff,
             tag_index_offset, tag_index_offset - active_map.map_magic,
             index.model_data_offset, header.tag_data_size,
             index.vertex_parts_count, index.index_parts_count))

            if index.SIZE == 36:
                string += (
                    "    index parts pointer == %s   non-magic == %s\n"
                    % (index.index_parts_offset,
                       index.index_parts_offset - active_map.map_magic))
            else:
                string += ((
                    "    vertex data size    == %s\n" +
                    "    index  data size    == %s\n" +
                    "    model  data size    == %s\n") %
                (index.vertex_data_size,
                 index.model_data_size - index.vertex_data_size,
                 index.model_data_size))

        if active_map.engine == "halo1yelo":
            yelo    = header.yelo_header
            flags   = yelo.flags
            info    = yelo.build_info
            version = yelo.tag_versioning
            cheape  = yelo.cheape_definitions
            rsrc    = yelo.resources
            min_os  = info.minimum_os_build
            string += ((
                "\nYelo information:\n" +
                "    Mod name              == %s\n" +
                "    Memory upgrade amount == %sx\n" +
                "\n    Flags:\n" +
                "        uses memory upgrades       == %s\n" +
                "        uses mod data files        == %s\n" +
                "        is protected               == %s\n" +
                "        uses game state upgrades   == %s\n" +
                "        has compression parameters == %s\n" +
                "\n    Build info:\n" +
                "        build string  == %s\n" +
                "        timestamp     == %s\n" +
                "        stage         == %s\n" +
                "        revision      == %s\n" +
                "\n    Cheape:\n" +
                "        build string      == %s\n" +
                "        version           == %s.%s.%s\n" +
                "        size              == %s\n" +
                "        offset            == %s\n" +
                "        decompressed size == %s\n" +
                "\n    Versioning:\n" +
                "        minimum open sauce     == %s.%s.%s\n" +
                "        project yellow         == %s\n" +
                "        project yellow globals == %s\n" +
                "\n    Resources:\n" +
                "        compression parameters header offset   == %s\n" +
                "        tag symbol storage header offset       == %s\n" +
                "        string id storage header offset        == %s\n" +
                "        tag string to id storage header offset == %s\n"
                ) %
            (yelo.mod_name, yelo.memory_upgrade_multiplier,
             bool(flags.uses_memory_upgrades),
             bool(flags.uses_mod_data_files),
             bool(flags.is_protected),
             bool(flags.uses_game_state_upgrades),
             bool(flags.has_compression_params),
             info.build_string, info.timestamp, info.stage.enum_name,
             info.revision, cheape.build_string,
             info.cheape.maj, info.cheape.min, info.cheape.build,
             cheape.size, cheape.offset, cheape.decompressed_size,
             min_os.maj, min_os.min, min_os.build,
             version.project_yellow, version.project_yellow_globals,
             rsrc.compression_params_header_offset,
             rsrc.tag_symbol_storage_header_offset,
             rsrc.string_id_storage_header_offset,
             rsrc.tag_string_to_id_storage_header_offset,
            ))

        if hasattr(active_map, "bsp_magics"):
            string += "\nSbsp magic and headers:\n"

            for tag_id in active_map.bsp_magics:
                header = active_map.bsp_headers.get(tag_id)
                if header is None: continue

                magic  = active_map.bsp_magics[tag_id]
                string += ((
                    "    %s.structure_scenario_bsp\n" +
                    "        bsp base pointer               == %s\n" +
                    "        bsp magic                      == %s\n" +
                    "        bsp size                       == %s\n" +
                    "        bsp metadata pointer           == %s   non-magic == %s\n"
                    #"        uncompressed lightmaps count   == %s\n" +
                    #"        uncompressed lightmaps pointer == %s   non-magic == %s\n" +
                    #"        compressed   lightmaps count   == %s\n" +
                    #"        compressed   lightmaps pointer == %s   non-magic == %s\n"
                    ) %
                (index.tag_index[tag_id].path,
                 active_map.bsp_header_offsets[tag_id],
                 magic, active_map.bsp_sizes[tag_id],
                 header.meta_pointer, header.meta_pointer - magic,
                 #header.uncompressed_lightmap_materials_count,
                 #header.uncompressed_lightmap_materials_pointer,
                 #header.uncompressed_lightmap_materials_pointer - magic,
                 #header.compressed_lightmap_materials_count,
                 #header.compressed_lightmap_materials_pointer,
                 #header.compressed_lightmap_materials_pointer - magic,
                 ))

        return string
