#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import os

from pathlib import PureWindowsPath
from refinery.constants import INF
from refinery.util import sanitize_win32_path, get_unique_name
from supyr_struct.util import str_to_identifier

from queue import LifoQueue, Empty as EmptyQueueException


class TagPathHandler():
    _path_map = ()
    _index_map = ()
    _priorities = ()
    _priority_mins = ()

    _icon_strings = ()
    _item_strings = ()
    _def_priority = 0.0
    _overwritables = ()

    max_object_str_len = 120  # arbitrary limit. Meant to keep tag paths short

    def __init__(self, tag_index_array, **kwargs):
        self._def_priority = kwargs.get('def_priority', 0)
        self._index_map = list(tag_index_array)
        self._priorities = dict(kwargs.get('priorities', {}))
        self._priority_mins = dict(kwargs.get('priority_mins', {}))
        self._path_map = dict()
        self._overwritables = dict()

        i = 0
        for ref in self._index_map:
            path = (ref.path + '.%s' % ref.class_1.enum_name).lower()
            self._path_map[path] = i
            priority = INF if ref.indexed else self._def_priority
            self._priorities[i] = self._priority_mins[i] = priority
            self._overwritables[i] = False if ref.indexed else True
            i += 1

    @property
    def def_priority(self):
        return self._def_priority

    def get_item_string(self, index):
        if index in range(len(self._item_strings)):
            return self._item_strings[index][: self.max_object_str_len]
        return ""

    def get_icon_string(self, index):
        if index in range(len(self._icon_strings)):
            return self._icon_strings[index][: self.max_object_str_len]
        return ""

    def set_item_strings(self, strings_body):
        new_strings = []
        for b in strings_body.strings.STEPTREE:
            string = str_to_identifier(b.data.lower()).\
                     replace("_", " ").replace(" d ", ' ').\
                     replace("picked up an ", '').replace("picked up a ", '').\
                     replace("picked up the ", '').replace("picked up ", '')

            if string == "need a string entry here":
                string = ""
            elif " for " in string:
                string = string.split(" for ")[-1] + " ammo"
            elif string.startswith("for "):
                string = string.split("for ")[-1] + " ammo"

            new_strings.append(string.strip())

        self._item_strings = new_strings

    def set_icon_strings(self, strings_body):
        new_strings = []
        for b in strings_body.strings.STEPTREE:
            string = str_to_identifier(b.data.lower()).replace("_", " ").strip()
            if string == "need a string entry here":
                string = ""
            new_strings.append(string.strip())

        self._icon_strings = new_strings

    def get_index_ref(self, index):
        if index is None: return
        index &= 0xFFff
        if index not in range(len(self._index_map)): return
        return self._index_map[index]

    def get_path(self, index):
        tag_ref = self.get_index_ref(index)
        if tag_ref:
            return tag_ref.path
        return ""

    def get_ext(self, index):
        tag_ref = self.get_index_ref(index)
        if tag_ref:
            return tag_ref.class_1.enum_name
        return ""

    def get_full_tag_path(self, index):
        tag_path, tag_ext = self.get_path(index), self.get_ext(index)
        if tag_path and tag_ext:
            return "%s.%s" % (tag_path, tag_ext)
        return ""

    def get_priority(self, index, default=-INF):
        if index is None: return default
        return self._priorities.get(index & 0xFFff, default)

    def get_priority_min(self, index, default=INF):
        if index is None: return default
        return self._priority_mins.get(index & 0xFFff, default)

    def get_overwritable(self, index):
        if index is None: return False
        return self._overwritables.get(index & 0xFFff, False)

    def get_sub_dir(self, index, root=""):
        tag_ref = self.get_index_ref(index)
        if not tag_ref:
            return ""
        root_dirs = PureWindowsPath(root).parts
        dirs = PureWindowsPath(tag_ref.path).parts[: -1]
        while (dirs and root_dirs) and dirs[0] == root_dirs[0]:
            dirs.pop(0)
            root_dirs.pop(0)

        if not dirs:
            return ""

        return str(PureWindowsPath(*dirs)) + "\\"

    def get_basename(self, index):
        tag_ref = self.get_index_ref(index)
        if not tag_ref:
            return ""
        return PureWindowsPath(tag_ref.path).name

    def get_will_overwrite(self, index, priority, override=False):
        if index is None:
            return False
        elif priority is None:
            priority = self._def_priority

        if not self.get_overwritable(index):
            return False

        tag_ref = self.get_index_ref(index)
        if self.get_priority(index) > priority:
            return False
        elif (self.get_priority(index) == priority or
              tag_ref.indexed) and not override:
            return False
        return True

    def set_path(self, index, new_path_no_ext, do_printout=False, ensure_unique_name=True):
        if index is None: return
        index &= 0xFFff

        tag_ref = self.get_index_ref(index)
        if tag_ref is None:
            return
        elif not new_path_no_ext or new_path_no_ext[-1] == "\\":
            new_path_no_ext += "protected %s" % index

        ext = "." + tag_ref.class_1.enum_name.lower()
        new_path_no_ext = str(sanitize_win32_path(new_path_no_ext.lower())).strip()

        if ensure_unique_name and self._path_map.get(new_path_no_ext + ext) not in (None, index):
            path_pieces = PureWindowsPath(new_path_no_ext).parts
            path_basename = path_pieces[-1]
            try:
                path_basename_pieces = path_basename.split("#")
                if len(path_basename_pieces) > 1:
                    path_basename = "#".join(path_basename_pieces[: -1])
            except Exception:
                pass

            path_pieces = tuple(path_pieces[: -1]) + (path_basename, )
            new_path_no_ext = get_unique_name(
                self._path_map, str(PureWindowsPath(*path_pieces)), ext, index)

        old_path = tag_ref.path.lower() + ext
        new_path = new_path_no_ext + ext

        if self._path_map.get(new_path, None) not in (None, index):
            raise KeyError(
                'Cannot rename tag to "%s", as that tag already exists.' %
                new_path)

        self._path_map.pop(old_path, None)
        self._path_map[new_path] = index
        tag_ref.path = new_path_no_ext
        if do_printout:
            print(index, self.get_priority(index), sep="\t", end="\t")
            try:
                print(new_path)
            except Exception:
                print("<UNPRINTABLE>")

        return new_path

    def set_path_by_priority(self, index, new_path_no_ext, priority=None,
                             override=False, do_printout=False):
        tag_ref = self.get_index_ref(index)
        if tag_ref is None:
            return -INF

        if priority is None:
            priority = self._def_priority
        assert isinstance(new_path_no_ext, str)

        if not self.get_will_overwrite(index, priority, override):
            return self.get_priority(index)

        self.set_path(index, new_path_no_ext, do_printout)
        self.set_priority(index, priority)
        return priority

    def set_priority(self, index, priority):
        if index is None: return
        index &= 0xFFff
        if index in range(len(self._index_map)):
            self._priorities[index] = float(priority)

    def set_priority_min(self, index, priority):
        if index is None: return
        index &= 0xFFff
        if index in range(len(self._index_map)):
            self._priority_mins[index] = float(priority)

    def set_overwritable(self, index, new_val=True):
        if index is None: return
        index &= 0xFFff
        if index in range(len(self._index_map)):
            self._overwritables[index] = bool(new_val)

    def shorten_paths(self, max_len, **kw):
        paths = {}
        new_paths = {}
        do_printout = kw.pop("do_printout", False)
        print_errors = kw.pop("print_errors", False)

        for tag_path, index in self._path_map.items():
            tag_path = sanitize_win32_path(tag_path.lower())
            if len(str(tag_path.with_suffix(""))) < max_len:
                # don't rename tags below the limit. use None as the key so
                # the tag path is still considered when chosing unique names
                index = None

            tag_path_pieces = tag_path.parts
            curr_dir = paths
            # 1 char for \, 1 for potential ~, 1 for potential number,
            # and 1 for at least one name character
            if (len(tag_path_pieces) - 1)*4 > max_len:
                err_str = "Tag paths too nested to shorten to %s chars." % max_len
                if not print_errors:
                    raise ValueError(err_str)
                print(err_str)
                return

            for dname in tag_path_pieces[: -1]:
                curr_dir = curr_dir.setdefault(dname, {})

            tag_ref = None
            if index is not None:
                tag_ref = self._index_map[index]

            curr_dir[tag_path_pieces[-1]] = tag_ref

        # do a preliminary filepath shortening by removing any
        # words the directories and paths start and end with
        # that the parent directory also starts or ends with.
        stack = LifoQueue()
        parent = ""
        curr_paths = paths
        curr_new_paths = new_paths
        reparent = {}

        while True:
            for name in sorted(curr_paths):
                val = curr_paths[name]
                if not isinstance(val, dict):
                    # reached a filename. move the item and continue.
                    base, ext = os.path.splitext(name)
                    new_base = base
                    if val is not None:
                        new_base = self.shorten_name_to_parent(parent, base)

                    curr_paths.pop(name)
                    if new_base:
                        curr_new_paths[new_base + ext] = val
                    else:
                        # name was simplified to nothing.
                        # schedule it to be put it in the parent
                        reparent.setdefault(parent + ext, []).append(val)

                elif val:
                    # need to go deeper, as this is a non-empty
                    # directory. store the current state to
                    # the stack and jump into this dir.
                    stack.put([parent, curr_paths, curr_new_paths, reparent])
                    new_name = get_unique_name(
                        curr_new_paths,
                        self.shorten_name_to_parent(parent, name)
                        )
                    if new_name:
                        # if the name doesn't get simplified to nothing,
                        # create a new directory to store these items in
                        parent = new_name
                        if new_name not in curr_new_paths:
                            curr_new_paths[new_name] = {}

                        curr_new_paths = curr_new_paths[new_name]

                    curr_paths = val
                    reparent = {}
                    break
                else:
                    # this is an empty directory(already copied all file
                    # and directory entries from it). remove it.
                    curr_paths.pop(name)


            if curr_paths:
                # still have paths to copy.
                continue


            # re-parent any paths that needed to be reparented
            curr_reparent = reparent
            try:
                # exhausted the current paths, get the next ones to do
                parent, curr_paths, curr_new_paths, reparent = stack.get_nowait()
            except EmptyQueueException:
                break

            for name in curr_reparent:
                for item in curr_reparent[name]:
                    no_ext_name, ext = os.path.splitext(name)
                    curr_new_paths[
                        self.get_unique_name(
                            curr_new_paths, no_ext_name, ext) + ext] = item

            curr_reparent.clear()


        # apply the renames
        curr_paths = new_paths
        path_pieces = ()
        while True:
            for name in sorted(curr_paths):
                val = curr_paths.pop(name)
                if isinstance(val, dict):
                    # This is a directory. Need to jump in it, so we'll break
                    if val:
                        # This is a non-empty directory. Store the
                        # current state to the stack and jump in.
                        stack.put([path_pieces, curr_paths])

                        curr_paths = val
                        path_pieces += (name, )
                    break
                elif val is None or val.indexed:
                    continue

                # reached a filename that needs to be renamed. rename the item and continue.
                tag_path = val.path
                new_tag_path = PureWindowsPath(
                    *path_pieces).with_suffix(PureWindowsPath(name).suffix)
                if do_printout:
                    print("%s char filepath shortened to %s chars:\n\t%s\n\t%s\n"%
                          (len(tag_path), len(new_tag_path), tag_path, new_tag_path))
                val.path = new_tag_path

            if not curr_paths:
                # exhausted the current paths, get the next ones to do
                try:
                    path_pieces, curr_paths = stack.get_nowait()
                except EmptyQueueException:
                    break

        # remake the path map
        self._path_map.clear()
        for i in range(len(self._index_map)):
            ref = self._index_map[i]
            tag_path = ref.path
            if do_printout and len(tag_path) > max_len:
                print('WARNING: "%s" is over the length limit.' % tag_path)

            self._path_map[(tag_path + "." + ref.class_1.enum_name).lower()] = i

    def shorten_name_to_parent(self, parent, name):
        join_char = '_' if '_' in name else ' '
        parent_pieces = parent.replace('_', ' ').split(' ')
        name_pieces = name.replace('_', ' ').split(' ')
        start, end = 0, len(name_pieces)
        for i in range(min(len(parent_pieces), len(name_pieces))):
            if parent_pieces[i] != name_pieces[i]:
                break
            start += 1

        for i in range(min(len(parent_pieces), len(name_pieces))):
            if parent_pieces[-1 - i] != name_pieces[-1 - i]:
                break
            end -= 1

        return join_char.join(name_pieces[start: end])
