from os.path import join
from struct import unpack, pack_into
from traceback import format_exc

from supyr_struct.buffer import BytearrayBuffer
from supyr_struct.defs.constants import *
from supyr_struct.defs.util import *
from supyr_struct.defs.bitmaps.dds import dds_def
from supyr_struct.defs.audio.wav import wav_def
from supyr_struct.field_types import FieldType
from .util import *

VALID_H1_DATA_TAGS = frozenset((
    #'mode', 'mod2', 'coll', 'phys', 'antr', 'magy', 'sbsp',
    #'font', 'hmt ', 'str#', 'ustr', 'unic',
    'bitm', 'snd!',
    ))

VALID_H2_DATA_TAGS = frozenset((
    #'mode', 'coll', 'phmo', 'jmad',
    #'sbsp',

    #'hmt ', 'unic',
    #'bitm', 'snd!',
    ))


def extract_bitm(settings, meta, tag_index_ref):
    for bitmap in meta.bitmaps.STEPTREE:
        typ = bitmap.type.enum_name
        fmt = bitmap.format.enum_name
        w = bitmap.width
        h = bitmap.height
        d = bitmap.depth
        bitmap_size = 0

        for i in range(bitmap.mipmaps + 1):
            mip_size = w * h
            if fmt in ("r5g6b5", "a1r5g5b5", "a4r4g4b4",
                       "a8y8", "v8u8", "g8b8"):
                mip_size *= 2
            elif fmt in ("x8r8g8b8", "a8r8g8b8"):
                mip_size *= 4
            elif fmt == "rgbfp16":
                mip_size *= 6
            elif fmt == "rgbfp32":
                mip_size *= 12
            elif fmt == "argbfp32":
                mip_size *= 16
            elif "dxt" in fmt:
                w_texel = w//4
                h_texel = h//4
                if w%4: w_texel += 1
                if h%4: h_texel += 1

                mip_size = w_texel * h_texel * 8  # 8 bytes per texel
                if fmt != "dxt1": mip_size *= 2

            if typ == "cubemap":
                mip_size *= 6

            mip_size *= d

            if fmt == "p8":
                # add the size of a 256 color a8r8g8b8 palette
                mip_size += 256*4

            bitmap_size += mip_size
            if w > 1: w = w//2
            if h > 1: h = h//2
            if d > 1: d = d//2

    return ()


def extract_tag_data(app, settings, meta, tag_index_ref):
    data_dir = settings['out_dir'].get()
    base_filepath = join(data_dir, tag_index_ref.path.tagpath)
    tag_cls = fourcc(tag_index_ref.class_1.data)

    extractor = None
    if "halo1" in app.engine or "stubbs" in app.engine:
        extractor = h1_data_extractors.get(tag_cls)
    elif app.engine == "halo2":
        extractor = h2_data_extractors.get(tag_cls)

    if extractor is None: return

    for file in extractor(settings, meta, tag_index_ref):
        if not file.filepath.endswith(file.ext):
            file.filepath += file.ext
        try:
            file.serialize(temp=False, backup=False, calc_pointers=False)
        except Exception:
            print(format_exc())


h1_data_extractors = {
    "bitm": extract_bitm,
    }

h2_data_extractors = {
    "bitm": extract_bitm,
    }
