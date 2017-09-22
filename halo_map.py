import re

from mmap import mmap
from os.path import dirname, join, splitext, isfile
from struct import unpack
from tkinter.filedialog import asksaveasfilename
from traceback import format_exc

from refinery import halo1_methods, halo2_methods, data_extraction
from refinery.util import is_protected_tag, fourcc
from supyr_struct.buffer import BytearrayBuffer, BytesBuffer, PeekableMmap
from supyr_struct.field_types import FieldType
from supyr_struct.defs.frozen_dict import FrozenDict

from reclaimer.meta.resource import resource_def
from reclaimer.meta.halo_map import get_map_version, get_map_header,\
     get_tag_index, get_index_magic, get_map_magic, get_is_compressed_map,\
     decompress_map, map_header_demo_def, tag_index_pc_def

from reclaimer.hek.defs.sbsp import sbsp_meta_header_def
from reclaimer.os_hek.defs.gelc    import gelc_def
from reclaimer.os_v4_hek.defs.bitm import bitm_def
from reclaimer.os_v4_hek.defs.snd_ import snd__def
from reclaimer.os_v4_hek.defs.font import font_def
from reclaimer.os_v4_hek.defs.hmt_ import hmt__def
from reclaimer.os_v4_hek.defs.ustr import ustr_def
from reclaimer.os_v4_hek.defs.coll import fast_coll_def
from reclaimer.os_v4_hek.defs.sbsp import fast_sbsp_def
from reclaimer.os_v4_hek.handler   import OsV4HaloHandler
from reclaimer.stubbs.defs.mode import mode_def as stubbs_mode_def
from reclaimer.stubbs.defs.mode import pc_mode_def as stubbs_pc_mode_def
from reclaimer.stubbs.defs.sbsp import fast_sbsp_def as stubbs_fast_sbsp_def
from reclaimer.stubbs.defs.coll import fast_coll_def as stubbs_fast_coll_def
from reclaimer.stubbs.handler   import StubbsHandler
from reclaimer.h2.defs.bitm import bitm_meta_def as h2_bitm_meta_def
from reclaimer.h2.defs.snd_ import snd__meta_def as h2_snd__meta_def


__all__ = ("HaloMap", "StubbsMap", "Halo1Map", "Halo1RsrcMap", "Halo2Map")


# Tag classes aren't stored in the cache maps, so we need to
# have a cache of them somewhere. Might as well do it manually
loc_exts = {0:'font', 1:'font', 4:'hud_message_text', 56:'font', 58:'font'}

bitmap_exts = ('bitmap',)*853
sound_exts  = ('sound',)*376
loc_exts    = tuple(loc_exts.get(i, 'unicode_string_list') for i in range(176))
backslash_fix = re.compile(r"\\{2,}")

def h2_to_h1_tag_index(map_header, tag_index):
    new_index = tag_index_pc_def.build()
    old_index_array = tag_index.tag_index
    new_index_array = new_index.tag_index

    # copy information from the h2 index into the h1 index
    new_index.scenario_tag_id[:] = tag_index.scenario_tag_id[:]
    new_index.tag_index_offset = tag_index.tag_index_offset
    new_index.tag_count = tag_index.tag_count

    tag_types = {}
    for typ in tag_index.tag_types:
        tag_types[typ.class_1.data] = [typ.class_1, typ.class_2, typ.class_3]

    for i in range(len(old_index_array)):
        old_index_entry = old_index_array[i]
        new_index_array.append()
        new_index_entry = new_index_array[-1]
        if old_index_entry.tag_class.data not in tag_types:
            new_index_entry.tag.tag_path = "reserved"
            new_index_entry.class_1.data = new_index_entry.class_2.data =\
                                           new_index_entry.class_3.data =\
                                           0xFFFFFFFF
            continue
        else:
            types = tag_types[old_index_entry.tag_class.data]
            new_index_entry.class_1 = types[0]
            new_index_entry.class_2 = types[1]
            new_index_entry.class_3 = types[2]

            #new_index_entry.path_offset = ????
            new_index_entry.tag.tag_path = map_header.strings.\
                                           tag_name_table[i].tag_name

        new_index_entry.id = old_index_entry.id
        new_index_entry.meta_offset = old_index_entry.offset
        if new_index_entry.meta_offset == 0:
            new_index_entry.indexed = 1

    return new_index


class HaloMap:
    map_data = None
    map_data_cache_limit = 50
    _map_cache_byte_count = 0
    _ids_of_tags_read = None

    # these are the different pieces of the map as parsed blocks
    map_header  = None
    rsrc_header = None
    tag_index   = None
    orig_tag_index = None  # the tag index specific to the
    #                        halo version that this map is from

    # the original tag_path of each tag in the map before any deprotection
    orig_tag_paths = None

    # the parsed meta of the root tags in the map
    scnr_meta = None
    matg_meta = None

    # determines how to work with this map
    filepath      = ""
    engine        = ""
    is_resource   = False
    is_compressed = False

    handler = None

    index_magic = 0  # the offset that halo would load the tag index
    #                  header at in virtual memory
    map_magic   = 0  # used to convert pointers in a map into file offsets.
    #                  subtract this from a pointer to convert it to an offset.
    #                      map_magic = index_magic - index_header_offset

    bsp_magics  = ()
    bsp_sizes   = ()
    bsp_headers = ()
    bsp_header_offsets = ()

    defs = None
    maps = None

    def __init__(self, maps=None, map_data_cache_limit=None):
        self.bsp_magics = {}
        self.bsp_sizes  = {}
        self.bsp_header_offsets = {}
        self.bsp_headers = {}
        self.orig_tag_paths = ()
        self.setup_defs()

        self._ids_of_tags_read = set()
        if map_data_cache_limit is not None:
            self.map_data_cache_limit = map_data_cache_limit

        self.maps = {} if maps is None else maps

    def __del__(self):
        self.unload_map(False)

    def is_indexed(self, tag_id):
        if self.engine in ("halo1ce", "halo1yelo"):
            return bool(self.tag_index.tag_index_array[tag_id].indexed)
        return False

    def basic_deprotection(self):
        if self.tag_index is None or self.is_resource:
            return

        i = 0
        found_counts = {}
        for b in self.tag_index.tag_index:
            tag_path = backslash_fix.sub(r'\\', b.tag.tag_path)

            tag_cls  = b.class_1.data
            name_id  = (tag_path, tag_cls)
            if is_protected_tag(tag_path):
                tag_path = "protected_%s" % i
                i += 1
            elif name_id in found_counts:
                tag_path = "%s_%s" % (tag_path, found_counts[name_id])
                found_counts[name_id] += 1
            else:
                found_counts[name_id] = 0

            b.tag.tag_path = tag_path

    def get_meta_descriptor(self, tag_cls):
        tagdef = self.defs.get(tag_cls)
        if tagdef is not None:
            return tagdef.descriptor[1]

    def record_map_cache_read(self, tag_id, size):
        if tag_id in self._ids_of_tags_read: return
        self._ids_of_tags_read.add(tag_id)
        self._map_cache_byte_count += size

    def map_cache_over_limit(self):
        return (self._map_cache_byte_count  >= self.map_data_cache_limit or
                len(self._ids_of_tags_read) >= self.map_data_cache_limit)

    def clear_map_cache(self):
        if not isinstance(self.map_data, mmap) or self.map_data.closed:
            return

        try:
            self.map_data.clear_cache()
        except Exception:
            print(format_exc())

        self._ids_of_tags_read.clear()
        self._map_cache_byte_count = 0

    def meta_to_tag_data(self, meta, tag_cls, tag_index_ref, **kwargs):
        '''
        Changes anything in a meta data block that needs to be changed for
        it to be a working tag. This includes removing predicted_resource
        references, fetching rawdata for the bitmaps, sounds, and models,
        and byteswapping any rawdata that needs it(animations, bsp, etc).
        '''
        raise NotImplementedError()

    def inject_rawdata(self, meta, tag_cls, tag_index_ref):
        raise NotImplementedError()

    def setup_defs(self):
        raise NotImplementedError()

    def get_meta(self, tag_id, reextract=False):
        raise NotImplementedError()

    def load_all_resource_maps(self, maps_dir=""):
        pass

    def load_map(self, map_path, will_be_active=True):
        with open(map_path, 'rb+') as f:
            comp_data = PeekableMmap(f.fileno(), 0)

        map_header = get_map_header(comp_data, True)
        if map_header is None:
            print("    Could not read map header.")
            comp_data.close()
            return

        engine = get_map_version(map_header)

        decomp_path = None
        map_name = map_header.map_name
        self.is_compressed = get_is_compressed_map(comp_data, map_header)
        if self.is_compressed:
            decomp_path = splitext(map_path)
            while decomp_path[1]:
                decomp_path = splitext(decomp_path[0])
            decomp_path = decomp_path[0] + ".map"

            if isfile(decomp_path):
                decomp_path = ''
                while not decomp_path:
                    decomp_path = asksaveasfilename(
                        initialdir=dirname(map_path),
                        title="Decompress '%s' to..." % map_name,
                        filetypes=(("mapfile", "*.map"),
                                   ("All", "*.*")))
            if not(decomp_path.lower().endswith(".map") or
                   isfile(decomp_path + ".map")):
                decomp_path += ".map"

            print("    Decompressing to: %s" % decomp_path)

        map_data = decompress_map(comp_data, map_header, decomp_path)
        if self.is_compressed:
            print("    Decompressed")
        self.map_data = map_data

        if comp_data is not map_data: comp_data.close()

        map_header = get_map_header(map_data)
        tag_index  = self.orig_tag_index = get_tag_index(map_data, map_header)

        if tag_index is None:
            print("    Could not read tag index.")
            return

        self.maps[map_header.map_name] = self
        if will_be_active:
            self.maps["active"] = self

        self.filepath    = map_path
        self.engine      = engine
        self.map_header  = map_header
        self.index_magic = get_index_magic(map_header)
        self.map_magic   = get_map_magic(map_header)
        self.tag_index   = tag_index

    def unload_map(self, keep_resources_loaded=True):
        keep_resources_loaded &= self.is_resource 
        try: map_name = self.map_header.map_name
        except Exception: map_name = None

        if self.maps.get('active') is self:
            self.maps.pop('active')

        if keep_resources_loaded and map_name in self.maps:
            return

        try: self.map_data.close()
        except Exception: pass
        try: self.maps.pop(map_name, None)
        except Exception: pass


class Halo1Map(HaloMap):
    ce_sound_indexes_by_path = None
    tag_headers = None

    meta_to_tag_data       = halo1_methods.meta_to_tag_data
    inject_rawdata         = halo1_methods.inject_rawdata
    load_all_resource_maps = halo1_methods.load_all_resource_maps

    def __init__(self, maps=None):
        HaloMap.__init__(self, maps)
        self.ce_sound_indexes_by_path = {}
        self.setup_tag_headers()

    def setup_tag_headers(self):
        if Halo1Map.tag_headers is not None:
            return

        tag_headers = Halo1Map.tag_headers = {}
        for def_id in sorted(self.defs):
            if def_id in tag_headers or len(def_id) != 4:
                continue
            h_desc, h_block = self.defs[def_id].descriptor[0], [None]
            h_desc['TYPE'].parser(h_desc, parent=h_block, attr_index=0)
            tag_headers[def_id] = bytes(
                h_block[0].serialize(buffer=BytearrayBuffer(),
                                     calc_pointers=False))

    def setup_defs(self):
        if Halo1Map.defs is None:
            print("Loading Halo 1 OSv4 tag definitions...")
            Halo1Map.handler = OsV4HaloHandler(build_reflexive_cache=False,
                                               build_raw_data_cache=False)
            Halo1Map.defs = FrozenDict(Halo1Map.handler.defs)
            print("    Finished")

        # make a shallow copy for this instance to manipulate
        self.defs = dict(self.defs)

        self.defs["sbsp"] = fast_sbsp_def
        self.defs["coll"] = fast_coll_def
        self.defs["gelc"] = gelc_def

    def load_resource_map(self, map_path):
        Halo1RsrcMap(self.maps).load_map(map_path, False)

    def load_map(self, map_path, will_be_active=True):
        HaloMap.load_map(self, map_path, will_be_active)

        tag_index = self.tag_index
        tag_index_array = tag_index.tag_index

        # record the original halo 1 tag_paths so we know if they change
        self.orig_tag_paths = tuple(b.tag.tag_path for b in tag_index_array)

        # make all contents of the map parasble
        self.basic_deprotection()

        # get the scenario meta
        try:
            self.scnr_meta = self.get_meta(tag_index.scenario_tag_id[0])

            if self.scnr_meta is not None:
                bsp_sizes   = self.bsp_sizes
                bsp_magics  = self.bsp_magics
                bsp_offsets = self.bsp_header_offsets
                for b in self.scnr_meta.structure_bsps.STEPTREE:
                    bsp = b.structure_bsp
                    bsp_offsets[bsp.id.tag_table_index] = b.bsp_pointer
                    bsp_magics[bsp.id.tag_table_index]  = b.bsp_magic
                    bsp_sizes[bsp.id.tag_table_index]   = b.bsp_size

                # read the sbsp headers
                for tag_id, offset in bsp_offsets.items():
                    header = sbsp_meta_header_def.build(rawdata=self.map_data,
                                                        offset=offset)
                    self.bsp_headers[tag_id] = header
                    if header.sig != header.get_desc("DEFAULT", "sig"):
                        print("Sbsp header is invalid for '%s'" %
                              tag_index_array[tag_id].tag.tag_path)
            else:
                print("Could not read scenario tag")

        except Exception:
            print(format_exc())
            print("Could not read scenario tag")

        # get the globals meta
        try:
            matg_id = None
            for b in tag_index_array:
                if fourcc(b.class_1.data) == "matg":
                    matg_id = b.id.tag_table_index
                    break

            self.matg_meta = self.get_meta(matg_id)
            if self.matg_meta is None:
                print("Could not read globals tag")
        except Exception:
            print(format_exc())
            print("Could not read globals tag")

        self.load_all_resource_maps(dirname(map_path))
        self.map_data.clear_cache()

    def extract_tag_data(self, meta, tag_index_ref, **kw):
        extractor = data_extraction.h1_data_extractors.get(
            fourcc(tag_index_ref.class_1.data))
        if extractor is None:
            return True
        return extractor(meta, tag_index_ref, halo_map=self,
                         out_dir=kw['out_dir'].get(),
                         overwrite=kw['overwrite'].get())

    def get_meta(self, tag_id, reextract=False):
        '''
        Takes a tag reference id as the sole argument.
        Returns that tags meta data as a parsed block.
        '''
        if tag_id is None: return
        magic     = self.map_magic
        engine    = self.engine
        map_data  = self.map_data
        tag_index = self.tag_index
        tag_index_array = tag_index.tag_index

        # if we are given a 32bit tag id, mask it off
        tag_id &= 0xFFFF

        tag_index_ref = tag_index_array[tag_id]

        if tag_id != tag_index.scenario_tag_id[0] or self.is_resource:
            tag_cls = None
            if tag_index_ref.class_1.enum_name not in ("<INVALID>", "NONE"):
                tag_cls = fourcc(tag_index_ref.class_1.data)
        else:
            tag_cls = "scnr"

        # if we dont have a defintion for this tag_cls, then return nothing
        if self.get_meta_descriptor(tag_cls) is None:
            return

        if tag_cls is None:
            # couldn't determine the tag class
            return
        elif self.is_indexed(tag_id):
            # tag exists in a resource cache
            tag_id = tag_index_ref.meta_offset

            if tag_cls == "snd!":
                rsrc_map = self.maps.get("sounds")
                sound_mapping = self.ce_sound_indexes_by_path
                tag_path = tag_index_ref.tag.tag_path
                if sound_mapping is None or tag_path not in sound_mapping:
                    return

                tag_id = sound_mapping[tag_path]//2
            elif tag_cls == "bitm":
                rsrc_map = self.maps.get("bitmaps")
                tag_id = tag_id//2
            else:
                rsrc_map = self.maps.get("loc")
                if tag_id >= len(loc_exts):
                    # this resource tag is in a yelo loc.map, which means
                    # we will need to set its tag class to what this map
                    # specifies it as or else the resource map wont know
                    # what type of tag to extract it as.
                    rsrc_map.tag_index.tag_index[tag_id].class_1.set_to(
                        tag_index_ref.class_1.enum_name)

            if rsrc_map is None:
                return

            return rsrc_map.get_meta(tag_id)
        elif not reextract:
            if tag_id == tag_index.scenario_tag_id[0] and self.scnr_meta:
                return self.scnr_meta
            elif tag_cls == "matg" and self.matg_meta:
                return self.matg_meta

        desc = self.get_meta_descriptor(tag_cls)
        block = [None]
        offset = tag_index_ref.meta_offset - magic
        if tag_cls == "sbsp":
            # bsps use their own magic because they are stored in
            # their own section of the map, directly after the header
            magic  = (self.bsp_magics[tag_id] -
                      self.bsp_header_offsets[tag_id])
            offset = self.bsp_headers[tag_id].meta_pointer - magic

        try:
            # read the meta data from the map
            FieldType.force_little()
            desc['TYPE'].parser(
                desc, parent=block, attr_index=0, magic=magic,
                tag_index=tag_index_array, rawdata=map_data, offset=offset)
            FieldType.force_normal()
        except Exception:
            print(format_exc())
            FieldType.force_normal()
            return

        self.record_map_cache_read(tag_id, 0)  # cant get size quickly enough
        if self.map_cache_over_limit():
            self.clear_map_cache()

        self.inject_rawdata(block[0], tag_cls, tag_index_ref)

        return block[0]


class StubbsMap(Halo1Map):

    def setup_tag_headers(self):
        if StubbsMap.tag_headers is not None:
            return

        Halo1Map.setup_tag_headers(self)
        tag_headers = StubbsMap.tag_headers = dict(Halo1Map.tag_headers)

        for b_def in (stubbs_antr_def, stubbs_coll_def, stubbs_mode_def,
                      stubbs_soso_def):
            def_id , h_desc, h_block = b_def.def_id, b_def.descriptor[0], [None]
            h_desc['TYPE'].parser(h_desc, parent=h_block, attr_index=0)
            self.tag_headers[def_id] = bytes(
                h_block[0].serialize(buffer=BytearrayBuffer(),
                                     calc_pointers=False))

    def setup_defs(self):
        Halo1Map.setup_defs(self)
        if StubbsMap.defs is None:
            print("Loading Stubbs tag definitions...")
            StubbsMap.handler = StubbsHandler(build_reflexive_cache=False,
                                              build_raw_data_cache=False)
            StubbsMap.defs = FrozenDict(StubbsMap.handler.defs)
            print("    Finished")

        if self.engine == "stubbspc":
            self.defs["mode"] = stubbs_pc_mode_def
        else:
            self.defs["mode"] = stubbs_mode_def
        self.defs["sbsp"] = stubbs_fast_sbsp_def
        self.defs["coll"] = stubbs_fast_coll_def


class Halo1RsrcMap(Halo1Map):
    tag_classes = None

    def __init__(self, maps=None):
        Halo1Map.__init__(self, maps)

    def setup_tag_headers(self):
        if Halo1RsrcMap.tag_headers is not None:
            return

        tag_headers = Halo1RsrcMap.tag_headers = {}
        for def_id in ("bitm", "snd!", "font", "hmt ", "ustr"):
            h_desc, h_block = self.defs[def_id].descriptor[0], [None]
            h_desc['TYPE'].parser(h_desc, parent=h_block, attr_index=0)
            tag_headers[def_id] = bytes(
                h_block[0].serialize(buffer=BytearrayBuffer(),
                                     calc_pointers=False))

    def setup_defs(self):
        self.defs = {
            "bitm": bitm_def, "snd!": snd__def,
            "font": font_def, "hmt ": hmt__def, "ustr": ustr_def
            }

    def load_map(self, map_path, will_be_active=True):
        with open(map_path, 'rb+') as f:
            map_data = PeekableMmap(f.fileno(), 0)

        resource_type = unpack("<I", map_data.read(4))[0]; map_data.seek(0)

        rsrc_head = resource_def.build(rawdata=map_data)

        # check if this is a pc or ce cache. cant rip pc ones
        pth = rsrc_head.tag_paths[0].tag_path
        self.filepath    = map_path
        self.engine = "halo1ce"
        if resource_type < 3 and not (pth.endswith('__pixels') or
                                      pth.endswith('__permutations')):
            self.engine = "halo1pc"

        # so we don't have to redo a lot of code, we'll make a
        # fake tag_index and map_header and just fill in info
        self.map_header = head = map_header_demo_def.build()
        self.tag_index  = tags = tag_index_pc_def.build()
        self.map_magic  = 0
        self.map_data   = map_data
        self.rsrc_header = rsrc_head
        self.is_resource = True

        head.version.set_to(self.engine)
        self.index_magic = 0

        index_mul = 2
        if self.engine == "halo1pc" or resource_type == 3:
            index_mul = 1

        head.map_name, tag_classes, def_cls = {
            1: ("bitmaps", bitmap_exts, 'bitmap'),
            2: ("sounds",  sound_exts,  'sound'),
            3: ("loc",     loc_exts,    'NONE')
            }[resource_type]

        # allow an override to be specified before the map is loaded
        if self.tag_classes is None:
            self.tag_classes = tag_classes

        self.maps[head.map_name] = self
        if will_be_active:
            self.maps["active"] = self

        rsrc_tag_count = len(rsrc_head.tag_paths)//index_mul
        self.tag_classes += (def_cls,)*(rsrc_tag_count - len(self.tag_classes))
        tags.tag_index.extend(rsrc_tag_count)
        tags.scenario_tag_id[:] = (0, 0)

        tags.tag_count = rsrc_tag_count
        # fill in the fake tag_index
        for i in range(rsrc_tag_count):
            j = i*index_mul
            if index_mul != 1:
                j += 1

            tag_ref = tags.tag_index[i]
            tag_ref.class_1.set_to(self.tag_classes[i])
            tag_ref.id[:] = (i, 0)

            tag_ref.meta_offset  = rsrc_head.tag_headers[j].offset
            tag_ref.indexed      = 1
            tag_ref.tag.tag_path = rsrc_head.tag_paths[j].tag_path
            tagid = (tag_ref.id[0], tag_ref.id[1])

        self.map_data.clear_cache()

    def get_meta(self, tag_id, reextract=False):
        '''Returns just the meta of the tag without any raw data.'''

        # if we are given a 32bit tag id, mask it off
        tag_id &= 0xFFFF
        tag_index_ref = self.tag_index.tag_index[tag_id]
        tag_cls = dict(
            sound="snd!", bitmap="bitm", font="font",
            unicode_string_list="ustr", hud_message_text="hmt ").get(
                tag_index_ref.class_1.enum_name)

        kwargs = dict(parsing_resource=True)
        desc = self.get_meta_descriptor(tag_cls)
        if desc is None or self.engine not in ("halo1ce", "halo1yelo"):
            return
        elif tag_cls != 'snd!':
            kwargs['magic'] = 0

        block = [None]

        self.record_map_cache_read(tag_id, 0)  # cant get size quickly enough
        if self.map_cache_over_limit():
            self.clear_map_cache()

        try:
            FieldType.force_little()
            desc['TYPE'].parser(
                desc, parent=block, attr_index=0, rawdata=self.map_data,
                tag_index=self.rsrc_header.tag_paths, tag_cls=tag_cls,
                root_offset=tag_index_ref.meta_offset, **kwargs)
            FieldType.force_normal()
            self.inject_rawdata(block[0], tag_cls, tag_index_ref)
        except Exception:
            print(format_exc())
            return

        return block[0]


class Halo2Map(HaloMap):
    def __init__(self, maps=None):
        HaloMap.__init__(self, maps)

    meta_to_tag_data       = halo2_methods.meta_to_tag_data
    inject_rawdata         = halo2_methods.inject_rawdata
    load_all_resource_maps = halo2_methods.load_all_resource_maps

    def setup_defs(self):
        self.defs = {
            "bitm": h2_bitm_meta_def, "snd!": h2_snd__meta_def,
            }

    def get_meta_descriptor(self, tag_cls):
        tagdef = self.defs.get(tag_cls)
        if tagdef is not None:
            return tagdef.descriptor

    def load_map(self, map_path, will_be_active=True):
        HaloMap.load_map(self, map_path, will_be_active)
        tag_index = self.tag_index
        self.tag_index = h2_to_h1_tag_index(self.map_header, tag_index)

        map_type = self.map_header.map_type.data - 1
        if map_type > 0 and map_type < 4:
            self.is_resource = True
            self.maps[halo2_methods.HALO2_MAP_TYPES[map_type]] = self

        if will_be_active or not self.is_resource:
            self.load_all_resource_maps(dirname(map_path))

        self.map_data.clear_cache()

    def extract_tag_data(self, meta, tag_index_ref, **kw):
        extractor = data_extraction.h2_data_extractors.get(
            fourcc(tag_index_ref.class_1.data))
        if extractor is None:
            return True
        return extractor(meta, tag_index_ref, halo_map=self,
                         out_dir=kw['out_dir'].get(),
                         overwrite=kw['overwrite'].get())

    def get_meta(self, tag_id, reextract=False):
        if tag_id is None: return
        scnr_id = self.orig_tag_index.scenario_tag_id[0]
        matg_id = self.orig_tag_index.globals_tag_id[0]
        tag_index_array = self.tag_index.tag_index
        shared_map    = self.maps.get("shared")
        sp_shared_map = self.maps.get("single_player_shared")

        # if we are given a 32bit tag id, mask it off
        tag_id &= 0xFFFF
        if tag_id >= 10000 and shared_map is not self:
            if shared_map is None: return
            return shared_map.get_meta(tag_id, reextract)
        elif tag_id >= len(tag_index_array) and sp_shared_map is not self:
            if sp_shared_map is None: return
            return sp_shared_map.get_meta(tag_id, reextract)

        tag_index_ref = tag_index_array[tag_id]

        tag_cls = None
        if   tag_id == scnr_id: tag_cls = "scnr"
        elif tag_id == matg_id: tag_cls = "matg"
        elif tag_index_ref.class_1.enum_name not in ("<INVALID>", "NONE"):
            tag_cls = fourcc(tag_index_ref.class_1.data)

        desc = self.get_meta_descriptor(tag_cls)
        if desc is None or tag_cls is None:        return
        elif reextract:                            pass
        elif tag_id == scnr_id and self.scnr_meta: return self.scnr_meta
        elif tag_id == matg_id and self.matg_meta: return self.matg_meta

        block = [None]
        offset = tag_index_ref.meta_offset - self.map_magic

        try:
            # read the meta data from the map
            desc['TYPE'].parser(
                desc, parent=block, attr_index=0, magic=self.map_magic,
                tag_index=tag_index_array, rawdata=self.map_data, offset=offset)
        except Exception:
            print(format_exc())
            return

        self.record_map_cache_read(tag_id, 0)  # cant get size quickly enough
        if self.map_cache_over_limit():
            self.clear_map_cache()

        self.inject_rawdata(block[0], tag_cls, tag_index_ref)

        return block[0]
