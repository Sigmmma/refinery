#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import mmap
import re
import shutil
import traceback

from pathlib import PureWindowsPath

from reclaimer.util import RESERVED_WINDOWS_FILENAME_MAP, INVALID_PATH_CHARS,\
     is_reserved_tag, is_protected_tag
from supyr_struct.util import is_path_empty, int_to_fourcc, fourcc_to_int


INVALID_WINDOWS_CHAR_SUB = re.compile('[:*?"<>|]')


def inject_file_padding(file, *off_padsize_pairs, padchar=b'\xCA'):
    file.flush()
    file.seek(0, 2)
    map_size = file.tell()
    dcbs = dstoff_cpysize_by_srcoff = dict(off_padsize_pairs)
    assert len(padchar) == 1

    off_diff = 0
    # set up the src offset to dst offset/copysize/padsize mapping
    for srcoff in sorted(dcbs):
        section_padsize = dcbs[srcoff]
        assert section_padsize >= 0
        off_diff += section_padsize  # bump the dst_off by the length
        #                              of the padding we are injecting
        #                     dstoff        cpysize      padsize
        dcbs[srcoff] = [srcoff + off_diff,     0,    section_padsize]

    last_end = map_size
    map_size += off_diff
    # loop over the mapping in reverse to set up the copysize of each section
    for srcoff in sorted(dcbs)[::-1]:
        dcbs[srcoff][1] = max(0, last_end - srcoff)
        last_end = srcoff

    close_mmap = False
    try:
        if not isinstance(file, mmap.mmap):
            file = mmap.mmap(file.fileno(), 0)
            close_mmap = True
    except Exception:
        pass

    try:
        if isinstance(file, mmap.mmap):
            file.resize(map_size)
        else:
            file.truncate(map_size)

        intra_file_move(file, dcbs)
    except Exception:
        if close_mmap:
            try: file.close()
            except Exception: pass
        raise

    return map_size


def intra_file_move(file, dstoff_cpysize_by_srcoff, padchar=b'\xCA'):
    is_mmap = isinstance(file, mmap.mmap)

    for srcoff in sorted(dstoff_cpysize_by_srcoff)[::-1]:
        # copy in chunks starting at the end of the copy section so
        # data doesnt get overwritten if  dstoff < srcoff + cpysize
        dstoff, cpysize, padsize = dstoff_cpysize_by_srcoff[srcoff][:]
        copied = padded = 0
        if not padsize or cpysize < 0 or dstoff == srcoff:
            continue

        if cpysize:
            if is_mmap:
                # mmap.move is much faster than our method below
                file.move(dstoff, srcoff, cpysize)
            else:
                while copied < cpysize:
                    remainder = cpysize - copied
                    chunksize = min(4*1024**2, remainder)  # copy of 4MB chunks

                    file.seek(srcoff + remainder - chunksize)
                    chunk = file.read(chunksize)
                    file.seek(dstoff + remainder - chunksize)
                    file.write(chunk)
                    copied += chunksize

                del chunk

        file.seek(srcoff)
        if padsize >= 1024**2:
            # default to writing padding in 1MB chunks
            padding = padchar * 1024**2

        while padsize > 0:
            if padsize < 1024**2:
                padding = padchar * padsize
            file.write(padding)
            padsize -= len(padding)

    file.flush()


def sanitize_win32_path(name):
    return PureWindowsPath(INVALID_WINDOWS_CHAR_SUB.sub('', name))


def get_unique_name(collection, name="", ext="", curr_value=object()):
    final_name = name
    i = 1
    while collection.get(final_name + ext) not in (None, curr_value):
        final_name = "%s #%s" % (name, i)
        i += 1

    return final_name
