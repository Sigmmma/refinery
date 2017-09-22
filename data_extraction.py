import arbytmap
if not hasattr(arbytmap, "FORMAT_P8"):
    arbytmap.FORMAT_P8 = "P8-BUMP"

    """ADD THE P8 FORMAT TO THE BITMAP CONVERTER"""
    arbytmap.define_format(
        format_id=arbytmap.FORMAT_P8, raw_format=True, channel_count=4,
        depths=(8,8,8,8), offsets=(24,16,8,0),
        masks=(4278190080, 16711680, 65280, 255))

from arbytmap import Arbytmap, TYPE_2D, TYPE_3D, TYPE_CUBEMAP,\
     FORMAT_A8, FORMAT_Y8, FORMAT_AY8, FORMAT_A8Y8,\
     FORMAT_R5G6B5, FORMAT_A1R5G5B5, FORMAT_A4R4G4B4,\
     FORMAT_X8R8G8B8, FORMAT_A8R8G8B8,\
     FORMAT_DXT1, FORMAT_DXT3, FORMAT_DXT5, FORMAT_P8, FORMAT_U8V8,\
     FORMAT_R16G16B16F, FORMAT_A16R16G16B16F,\
     FORMAT_R32G32B32F, FORMAT_A32R32G32B32F
    
from os.path import exists, join
from struct import unpack, pack_into
from traceback import format_exc

from supyr_struct.buffer import BytearrayBuffer
from supyr_struct.defs.constants import *
from supyr_struct.defs.util import *
from supyr_struct.defs.audio.wav import wav_def
from supyr_struct.field_types import FieldType
from refinery.util import is_protected_tag, fourcc, is_reserved_tag
from reclaimer.hek.defs.objs.p8_palette import load_palette

#load the palette for p-8 bump maps
P8_PALETTE = load_palette()

#each sub-bitmap(cubemap face) must be a multiple of 128 bytes
CUBEMAP_PADDING = 128


def get_pad_size(size, mod): return (mod - (size % mod)) % mod


def extract_snd_(meta, tag_index_ref, **kw):
    halo_map = kw['halo_map']
    filepath_base = join(kw['out_dir'], tag_index_ref.tag.tag_path)
    pix_data = meta.processed_pixel_data.STEPTREE


def extract_bitm(meta, tag_index_ref, **kw):
    halo_map = kw['halo_map']
    filepath_base = join(kw['out_dir'], tag_index_ref.tag.tag_path)
    is_padded = "xbox" in halo_map.engine
    pix_data = meta.processed_pixel_data.STEPTREE

    if is_padded:
        # cant extract xbox bitmaps yet
        return True

    arby = Arbytmap()
    tex_infos = []
    bitm_i = 0
    multi_bitmap = len(meta.bitmaps.STEPTREE) > 1
    for bitmap in meta.bitmaps.STEPTREE:
        typ = bitmap.type.enum_name
        fmt = bitmap.format.enum_name
        bpp = 1
        w = bitmap.width
        h = bitmap.height
        d = bitmap.depth
        pix_off = bitmap.pixels_offset

        filepath = filepath_base
        if multi_bitmap:
            filepath += "__%s" % bitm_i
            bitm_i += 1

        tex_block = []
        tex_info = dict(
            width=w, height=h, depth=d, mipmap_count=bitmap.mipmaps,
            sub_bitmap_count=6 if typ == "cubemap" else 1, packed=True,
            swizzled=bitmap.flags.swizzled, filepath=filepath + ".dds"
            )
        tex_infos.append(tex_info)

        if fmt in ("a8", "y8", "ay8", "p8"):
            tex_info["format"] = {"a8": FORMAT_A8,   "y8": FORMAT_Y8,
                                  "ay8": FORMAT_AY8, "p8": FORMAT_A8}[fmt]
        elif fmt == "p8-bump":
            tex_info.update(
                palette=P8_PALETTE.p8_palette_32bit_packed*(bitmap.mipmaps+1),
                palette_packed=True, indexing_size=8, format=FORMAT_P8)
        elif fmt in ("r5g6b5", "a1r5g5b5", "a4r4g4b4",
                     "a8y8", "v8u8", "g8b8"):
            bpp = 2
            tex_info["format"] = {
                "a8y8": FORMAT_A8Y8, "v8u8": FORMAT_U8V8, "g8b8": FORMAT_U8V8,
                "r5g6b5": FORMAT_R5G6B5, "a1r5g5b5": FORMAT_A1R5G5B5,
                "a4r4g4b4": FORMAT_A4R4G4B4}[fmt]
        elif fmt in ("x8r8g8b8", "a8r8g8b8"):
            bpp = 4
            tex_info["format"] = FORMAT_A8R8G8B8
        elif fmt == "rgbfp16":
            bpp = 6
            tex_info["format"] = FORMAT_R16G16B16F
        elif fmt == "rgbfp32":
            bpp = 12
            tex_info["format"] = FORMAT_A16R16G16B16F
        elif fmt == "argbfp32":
            bpp = 16
            tex_info["format"] = FORMAT_A32R32G32B32F
        else:
            tex_info["format"] = {
                "dxt1": FORMAT_DXT1, "dxt3": FORMAT_DXT3, "dxt5": FORMAT_DXT5
                }.get(fmt, FORMAT_A8)

        tex_info["texture_type"] = {
            "texture 2d": TYPE_2D, "texture 3d": TYPE_3D,
            "cubemap":TYPE_CUBEMAP}.get(typ, TYPE_2D)

        for i in range(bitmap.mipmaps + 1):
            if "dxt" in fmt:
                w_texel = w//4
                h_texel = h//4
                if w%4: w_texel += 1
                if h%4: h_texel += 1

                mip_size = w_texel * h_texel * 8  # 8 bytes per texel
                if fmt != "dxt1": mip_size *= 2
            else:
                mip_size = w * h * bpp

            if typ == "cubemap":
                if is_padded:
                    mip_size += get_pad_size(mip_size, CUBEMAP_PADDING)
                for i in range(6):
                    tex_block.append(pix_data[pix_off: pix_off + mip_size])
                    pix_off += mip_size
            else:
                mip_size *= d
                tex_block.append(pix_data[pix_off: pix_off + mip_size])
                pix_off += mip_size

            #if fmt == "p8": mip_size += 256*4
            if w > 1: w = w//2
            if h > 1: h = h//2
            if d > 1: d = d//2

        if not tex_block:
            # nothing to extract
            continue

        arby.load_new_texture(texture_block=tex_block, texture_info=tex_info)
        arby.save_to_file()

    return False


h1_data_extractors = {
    #'mode', 'mod2', 'coll', 'phys', 'antr', 'magy', 'sbsp',
    #'font', 'hmt ', 'str#', 'ustr', 'unic',
    "bitm": extract_bitm, "snd!": extract_snd_,
    }

h2_data_extractors = {
    #'mode', 'coll', 'phmo', 'jmad',
    #'sbsp',

    #'hmt ', 'unic',
    "bitm": extract_bitm, "snd!": extract_snd_,
    }
