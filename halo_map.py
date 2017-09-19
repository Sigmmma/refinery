from os.path import dirname, join, splitext
from struct import unpack
from tkinter.filedialog import asksaveasfilename
from traceback import format_exc

from . import halo1_methods, halo2_methods
from .util import is_protected, fourcc
from supyr_struct.buffer import BytearrayBuffer, BytesBuffer, PeekableMmap
from supyr_struct.field_types import FieldType

from reclaimer.meta.resource import resource_def
from reclaimer.meta.halo_map import get_map_version, get_map_header,\
     get_tag_index, get_index_magic, get_map_magic, get_is_compressed_map,\
     decompress_map, map_header_demo_def, tag_index_pc_def

from reclaimer.hek.defs.sbsp import sbsp_meta_header_def
from reclaimer.os_hek.defs.gelc    import gelc_def
from reclaimer.os_v4_hek.defs.sbsp import fast_sbsp_def
from reclaimer.os_v4_hek.defs.coll import fast_coll_def
from reclaimer.os_v4_hek.handler   import OsV4HaloHandler
from reclaimer.stubbs.defs.mode import mode_def as stubbs_mode_def,
from reclaimer.stubbs.defs.mode import pc_mode_def as stubbs_pc_mode_def
from reclaimer.stubbs.defs.sbsp import fast_sbsp_def as stubbs_fast_sbsp_def
from reclaimer.stubbs.defs.coll import fast_coll_def as stubbs_fast_coll_def
from reclaimer.stubbs.handler   import StubbsHandler
from reclaimer.h2.defs.bitm import bitm_meta_def as h2_bitm_meta_def


__all__ = ("HaloMap", "StubbsMap", "Halo1Map", "Halo1RsrcMap", "Halo2Map")


# Tag classes aren't stored in the cache maps, so we need to
# have a cache of them somewhere. Might as well do it manually
loc_exts = {0:'font', 1:'font', 4:'hud_message_text', 56:'font', 58:'font'}

bitmap_exts = ('bitmap',)*853
sound_exts  = ('sound',)*376
loc_exts    = tuple(loc_exts.get(i, 'unicode_string_list') for i in range(176))


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
            new_index_entry.tag.tag_path = "reserved for main map"
            new_index_entry.id.tag_table_index = i
            continue

        types = tag_types[old_index_entry.tag_class.data]
        new_index_entry.class_1 = types[0]
        new_index_entry.class_2 = types[1]
        new_index_entry.class_3 = types[2]

        new_index_entry.id = old_index_entry.id
        new_index_entry.meta_offset = old_index_entry.offset

        #new_index_entry.path_offset = ????
        new_index_entry.tag.tag_path = map_header.strings.\
                                       tag_name_table[i].tag_name

    return new_index


class HaloMap:
    map_data = BytesBuffer()

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
    engine        = ""
    is_resource   = False
    is_compressed = False

    index_magic = 0
    map_magic   = 0

    bsp_magics  = ()
    bsp_sizes   = ()
    bsp_headers = ()
    bsp_header_offsets = ()

    defs = None

    def __init__(self):
        self.bsp_magics = {}
        self.bsp_sizes  = {}
        self.bsp_header_offsets = {}
        self.bsp_headers = {}
        self.orig_tag_paths = ()
        if type(self).defs is None:
            type(self).defs = {}

        self.setup_defs()

    def get_meta_descriptor(self, tag_cls):
        tagdef = self.defs.get(tag_cls)
        if tagdef is not None:
            return tagdef.descriptor[1]

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
        elif self.is_indexed(tag_index_ref) and engine in ("halo1ce",
                                                           "halo1yelo"):
            # tag exists in a resource cache
            return self.get_ce_resource_meta(tag_cls, tag_index_ref)
        elif not reextract:
            if tag_id == tag_index.scenario_tag_id[0] and self.scnr_meta:
                return self.scnr_meta
            elif tag_cls == "matg" and self.matg_meta:
                return self.matg_meta

        h_desc = self.get_meta_descriptor(tag_cls)
        h_block = [None]
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
            h_desc['TYPE'].parser(
                h_desc, parent=h_block, attr_index=0, magic=magic,
                tag_index=tag_index_array, rawdata=map_data, offset=offset)
            FieldType.force_normal()
        except Exception:
            print(format_exc())
            FieldType.force_normal()
            return

        self.inject_rawdata(h_block[0], tag_cls, tag_index_ref)

        return h_block[0]

    def meta_to_tag_data(self, meta, tag_cls, tag_index_ref):
        '''
        Changes anything in a meta data block that needs to be changed for
        it to be a working tag. This includes removing predicted_resource
        references, fetching rawdata for the bitmaps, sounds, and models,
        and byteswapping any rawdata that needs it(animations, bsp, etc).
        '''
        raise NotImplementedError()

    def inject_rawdata(self, meta, tag_cls, tag_index_ref):
        raise NotImplementedError()

    def load_map(self, map_path, will_be_active=True, make_new_map=False):
        with open(map_path, 'rb+') as f:
            comp_data = PeekableMmap(f.fileno(), 0)

        map_header = get_map_header(comp_data, True)
        if map_header is None:
            print("Could not read map header.")
            comp_data.close()
            return

        curr_map = self
        if make_new_map:
            curr_map = type(curr_map)()

        engine = get_map_version(map_header)

        decomp_path = None
        self.is_compressed = get_is_compressed_map(comp_data, map_header)
        if self.is_compressed:
            decomp_path = asksaveasfilename(
                initialdir=dirname(map_path), parent=self,
                title="Choose where to save the decompressed map",
                filetypes=(("mapfile", "*.map"),
                           ("All", "*.*")))
            decomp_path = splitext(decomp_path)[0] + ".map"

        map_data = decompress_map(comp_data, map_header, decomp_path)
        self.map_data = map_data

        if comp_data is not map_data: comp_data.close()

        map_header = get_map_header(map_data)
        tag_index  = self.orig_tag_index = get_tag_index(map_data, map_header)

        if tag_index is None:
            print("Could not read tag index.")
            return

        if will_be_active:
            self.maps["active"] = curr_map

        self.engine      = engine
        self.map_header  = map_header
        self.index_magic = get_index_magic(map_header)
        self.map_magic   = get_map_magic(map_header)
        self.tag_index   = tag_index
        return curr_map

    def load_all_resource_maps(self, maps_dir=""):
        raise NotImplementedError()

    def unload_map(self):
        try: self.map_data.close()
        except Exception: pass
        try: self.maps.pop(self.map_header.map_name)
        except Exception: pass

        if self.maps.get('active') is self:
            self.maps.pop('active', None)


class Halo1Map(HaloMap):
    ce_sound_offsets_by_path = None
    tag_headers = None

    meta_to_tag_data       = halo1_methods.meta_to_tag_data
    inject_rawdata         = halo1_methods.inject_rawdata
    load_all_resource_maps = halo1_methods.load_all_resource_maps

    def __init__(self):
        HaloMap.__init__(self)
        self.ce_sound_offsets_by_path = {}
        if type(self).tag_headers is None:
            type(self).tag_headers = {}

        self.setup_tag_headers()

    def setup_tag_headers(self):
        defs = self.defs
        if self.tag_headers is None:
            self.tag_headers = {}

        tag_headers = self.tag_headers
        for def_id in sorted(defs):
            if def_id in tag_headers or len(def_id) != 4:
                continue
            h_desc = defs[def_id].descriptor[0]

            h_block = [None]
            h_desc['TYPE'].parser(h_desc, parent=h_block, attr_index=0)
            tag_headers[def_id] = bytes(
                h_block[0].serialize(buffer=BytearrayBuffer(),
                                     calc_pointers=False))

    def setup_defs(self):
        self.defs = defs = dict(self.defs)
        return
        defs["sbsp"] = fast_sbsp_def
        defs["coll"] = fast_coll_def

    def basic_deprotection(self):
        if self.tag_index is None or self.is_resource:
            return

        i = 0
        found_counts = {}
        for b in self.tag_index.tag_index:
            tag_path = b.tag.tag_path
            tag_cls  = b.class_1.data
            name_id  = (tag_path, tag_cls)
            if is_protected(tag_path):
                b.tag.tag_path = "protected_%s" % i
                i += 1
            elif name_id in found_counts:
                b.tag.tag_path = "%s_%s" % (tag_path, found_counts[name_id])
                found_counts[name_id] += 1
            else:
                found_counts[name_id] = 0

    def load_resource_map(self, map_path):
        new_map = Halo1RsrcMap()
        new_map.maps = self.maps
        new_map.load_map(map_path, False, True)

    def load_map(self, map_path, will_be_active=True, make_new_map=False):
        curr_map = HaloMap.load_map(self, map_path, will_be_active, make_new_map)

        self.maps[self.map_header.map_name] = curr_map
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
        return curr_map

    def is_indexed(self, tag_index_ref):
        if self.engine in ("halo1ce", "halo1yelo"):
            return bool(tag_index_ref.indexed)
        return False

    def get_ce_resource_meta(self, tag_cls, tag_index_ref):
        '''Returns just the meta of the tag without any raw data.'''
        # read the meta data from the map
        if self.get_meta_descriptor(tag_cls) is None:
            return
        elif self.engine not in ("halo1ce", "halo1yelo"):
            return

        kwargs = dict(parsing_resource=True)

        if self.is_resource:
            # this map is a resource map, not a real map.
            rsrc_map    = self
            rsrc_head   = rsrc_map.rsrc_header
            meta_offset = tag_index_ref.meta_offset
        else:
            if   tag_cls == "snd!": rsrc_map = self.maps.get("sounds")
            elif tag_cls == "bitm": rsrc_map = self.maps.get("bitmaps")
            else:                   rsrc_map = self.maps.get("loc")

            rsrc_head = rsrc_map.rsrc_header

            # resource map not loaded
            if rsrc_head is None:
                return
            elif tag_cls == "snd!":
                sound_mapping = self.ce_sound_offsets_by_path
                tag_path  = tag_index_ref.tag.tag_path
                if sound_mapping is None or tag_path not in sound_mapping:
                    return

                meta_offset = sound_mapping[tag_path]
            else:
                meta_offset = rsrc_head.tag_headers[
                    tag_index_ref.meta_offset].offset

        map_data = rsrc_map.map_data
        if map_data is None:
            # resource map not loaded
            return

        if tag_cls != 'snd!':
            kwargs['magic'] = 0

        h_desc  = self.get_meta_descriptor(tag_cls)
        h_block = [None]

        try:
            FieldType.force_little()
            h_desc['TYPE'].parser(
                h_desc, parent=h_block, attr_index=0, rawdata=map_data,
                tag_index=rsrc_head.tag_paths, root_offset=meta_offset,
                tag_cls=tag_cls, **kwargs)
            FieldType.force_normal()
            self.inject_rawdata(h_block[0], tag_cls, tag_index_ref)
        except Exception:
            print(format_exc())
            return

        return h_block[0]


class StubbsMap(Halo1Map):

    def setup_tag_headers(self):
        defs = self.defs
        if self.tag_headers is None:
            self.tag_headers = {}

        for block_def in (stubbs_antr_def, stubbs_coll_def, stubbs_mode_def,
                          stubbs_soso_def):
            h_block = [None]
            def_id = block_def.def_id
            h_desc = block_def.descriptor[0]
            h_desc['TYPE'].parser(h_desc, parent=h_block, attr_index=0)
            self.tag_headers[def_id + "_halo"]   = self.tag_headers[def_id]
            self.tag_headers[def_id + "_stubbs"] = bytes(
                h_block[0].serialize(buffer=BytearrayBuffer(), calc_pointers=0))

    def setup_defs(self):
        self.defs = defs = dict(self.defs)
        return
        if self.engine == "stubbspc":
            defs["mode"] = stubbs_pc_mode_def
        else:
            defs["mode"] = stubbs_mode_def
        defs["sbsp"] = stubbs_fast_sbsp_def
        defs["coll"] = stubbs_fast_coll_def


class Halo1RsrcMap(Halo1Map):
    tag_classes = None

    def __init__(self):
        Halo1Map.__init__(self)

    def load_map(self, map_path, will_be_active=True, make_new_map=False):
        with open(map_path, 'rb+') as f:
            map_data = PeekableMmap(f.fileno(), 0)

        resource_type = unpack("<I", map_data.read(4))[0]; map_data.seek(0)

        rsrc_head = resource_def.build(rawdata=map_data)
        curr_map = self
        if make_new_map:
            curr_map = Halo1RsrcMap()

        # check if this is a pc or ce cache. cant rip pc ones
        pth = rsrc_head.tag_paths[0].tag_path
        curr_map.engine = "halo1ce"
        if resource_type < 3 and not (pth.endswith('__pixels') or
                                      pth.endswith('__permutations')):
            curr_map.engine = "halo1pc"

        # so we don't have to redo a lot of code, we'll make a
        # fake tag_index and map_header and just fill in info
        curr_map.map_header = head = map_header_demo_def.build()
        curr_map.tag_index  = tags = tag_index_pc_def.build()
        curr_map.map_magic  = 0
        curr_map.map_data   = map_data
        curr_map.rsrc_header = rsrc_head
        curr_map.is_resource = True

        head.version.set_to(curr_map.engine)
        curr_map.index_magic = 0

        index_mul = 2
        if curr_map.engine == "halo1pc" or resource_type == 3:
            index_mul = 1

        head.map_name, tag_classes, def_cls = {
            1: ("bitmaps", bitmap_exts, 'bitmap'),
            2: ("sounds",  sound_exts,  'sound'),
            3: ("loc",     loc_exts,    'unicode_string_list')
            }[resource_type]

        # allow an override to be specified before the map is loaded
        if self.tag_classes is None:
            self.tag_classes = tag_classes

        self.maps[head.map_name] = curr_map
        if will_be_active:
            self.maps["active"] = curr_map

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


class Halo2Map(HaloMap):
    def __init__(self):
        HaloMap.__init__(self)

    meta_to_tag_data       = halo2_methods.meta_to_tag_data
    inject_rawdata         = halo2_methods.inject_rawdata
    load_all_resource_maps = halo2_methods.load_all_resource_maps

    def setup_defs(self):
        '''Switch definitions based on which game the map is for'''
        pass

    def load_map(self, map_path, will_be_active=True, make_new_map=False):
        curr_map = HaloMap.load_map(self, map_path, will_be_active, make_new_map)
        tag_index = self.tag_index
        self.tag_index = h2_to_h1_tag_index(self.map_header, tag_index)

        map_type = self.map_header.map_type.data - 1
        if map_type > 0 and map_type < 4:
            self.maps[halo2_methods.HALO2_MAP_TYPES[map_type]] = self

        self.load_all_resource_maps(dirname(map_path))
