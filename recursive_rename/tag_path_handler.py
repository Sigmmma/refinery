from refinery.recursive_rename.constants import *
from refinery.recursive_rename.functions import sanitize_path
from supyr_struct.defs.util import str_to_identifier

from os.path import splitext
from queue import LifoQueue, Empty as EmptyQueueException


class TagPathHandler():
    _path_map = ()
    _index_map = ()
    _shared_by = ()
    _priorities = ()

    _icon_strings = ()
    _item_strings = ()
    _def_priority = 0.0

    max_object_str_len = 120


    def __init__(self, tag_index_array, **kwargs):
        self._def_priority = kwargs.get('def_priority', 0)
        self._index_map = list(tag_index_array)
        self._shared_by = {i: [] for i in range(len(tag_index_array))}
        self._priorities = dict(kwargs.get('priorities', {}))
        self._path_map = dict()

        i = 0
        for ref in self._index_map:
            path = (ref.tag.tag_path + '.%s' % ref.class_1.enum_name).lower()
            self._path_map[path] = i
            if ref.indexed:
                self._priorities[i] = INF
            else:
                self._priorities[i] = self._def_priority
            i += 1

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
        if index is None or index not in range(len(self._index_map)):
            return
        return self._index_map[index]

    def get_path(self, index):
        tag_ref = self.get_index_ref(index)
        if tag_ref:
            return tag_ref.tag.tag_path
        return ""

    def get_shared_by(self, index):
        return self._shared_by.get(index, ())

    def get_priority(self, index):
        return self._priorities.get(index, float("-inf"))

    def get_sub_dir(self, index, root=""):
        tag_ref = self.get_index_ref(index)
        if not tag_ref:
            return ""
        root_dirs = root.split("\\")
        dirs = tag_ref.tag.tag_path.split("\\")[: -1]
        while (dirs and root_dirs) and dirs[0] == root_dirs[0]:
            dirs.pop(0)
            root_dirs.pop(0)

        if not dirs:
            return ""

        return '\\'.join(dirs) + "\\"

    def get_basename(self, index):
        tag_ref = self.get_index_ref(index)
        if not tag_ref:
            return ""
        return tag_ref.tag.tag_path.split("\\")[-1]

    def set_path(self, index, new_path_no_ext, priority=None, override=False):
        if index is None:
            return ""
        elif priority is None:
            priority = self._def_priority
        assert isinstance(new_path_no_ext, str)

        tag_ref = self.get_index_ref(index)
        ext = "." + tag_ref.class_1.enum_name
        new_path_no_ext, ext = sanitize_path(new_path_no_ext), ext.lower()
        old_path = tag_ref.tag.tag_path.lower() + ext

        if (not self.get_priority(index) < priority) or tag_ref.indexed:
            return old_path
        elif self.get_priority(index) == priority and not override:
            return old_path

        if not new_path_no_ext or new_path_no_ext[-1] == "\\":
            new_path_no_ext += "protected"

        if self._path_map.get(new_path_no_ext + ext, None) not in (None, index):
            i = 1
            while (self._path_map.get(
                    "%s %s%s" % (new_path_no_ext, i, ext), None)
                    not in (None, index)):
                i += 1

            new_path_no_ext += " %s" % i

        new_path = new_path_no_ext + ext

        self._priorities[index] = priority

        self._path_map.pop(old_path, None)
        self._path_map[new_path] = index
        tag_ref.tag.tag_path = new_path_no_ext
        ############# DEBUG #############
        print(index, priority, new_path_no_ext, sep="\t")
        return new_path

    def set_priority(self, index, priority):
        self._priorities[index] = float(priority)

    def shorten_paths(self, max_len):
        paths = {}
        new_paths = {}

        for tag_path, index in self._path_map.items():
            curr_dir = paths
            tag_path_pieces = tag_path.split("\\")
            # 1 char for \, 1 for potential ~, 1 for potential number,
            # and 1 for at least one name character
            if (len(tag_path_pieces) - 1)*4 > max_len:
                raise ValueError("Tag paths too nested to shorten to %s chars."
                                 % max_len)
                return

            for dirname in tag_path_pieces[: -1]:
                curr_dir = curr_dir.setdefault(dirname, {})

            curr_dir[tag_path_pieces[-1]] = self._index_map[index]

        # do a preliminary filepath shortening by removing any
        # words the directories and paths start and end with
        # that the parent directory also starts or ends with.
        stack = LifoQueue()
        parent = ""
        curr_paths = paths
        curr_new_paths = new_paths
        reparent = {}



        # TODO: FINISH THIS SHIT


        while True:
            for name in sorted(curr_paths):
                val = curr_paths[name]
                if not isinstance(val, dict):
                    # reached a filename. move the item and continue.
                    basename, ext = splitext(name)
                    new_basename = self.shorten_name_to_parent(parent, basename)
                    curr_paths.pop(name)
                    if new_basename:
                        curr_new_paths[new_basename + ext] = val
                    else:
                        # name was simplified to nothing.
                        # schedule it to be put it in the parent
                        reparent.setdefault(parent, []).append(val)

                elif val:
                    # need to go deeper, as this is a non-empty
                    # directory. store the current state to
                    # the stack and jump into this dir.
                    stack.put([parent, curr_paths, curr_new_paths, reparent])
                    new_name = self.get_unique_name(
                        curr_new_paths,
                        self.shorten_name_to_parent(parent, name)
                        )
                    if new_name:
                        # if the name doesn't get simplified to nothing,
                        # create a new directory to store these items in
                        # CANNOT SIMPLIFY THIS TO THIS
                        #    curr_new_paths = curr_new_paths[name] = {}
                        parent = name
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
            for name in reparent:
                for item in reparent[name]:
                    curr_new_paths[
                        self.get_unique_name(curr_new_paths,
                                             *splitext(name))] = item


            reparent.clear()
            try:
                # exhausted the current paths, get the next ones to do
                parent, curr_paths, curr_new_paths, reparent = stack.get_nowait()
            except EmptyQueueException:
                break


        # apply the renames
        curr_paths = new_paths
        path_pieces = ()
        while True:
            for name in sorted(curr_paths):
                val = curr_paths.pop(name)
                if not isinstance(val, dict):
                    # reached a filename. rename the item and continue.
                    if not val.indexed:
                        val.tag.tag_path = "\\".join(
                            path_pieces + splitext(name)[: 1])

                    continue
                elif val:
                    # This is a non-empty directory. Need to go
                    # deeper, so store the current state to the
                    # stack and jump into this dir.
                    stack.put([path_pieces, curr_paths])

                    curr_paths = val
                    path_pieces += (name, )

                break

            if curr_paths:
                # still have paths to modify.
                continue

            try:
                # exhausted the current paths, get the next ones to do
                path_pieces, curr_paths = stack.get_nowait()
            except EmptyQueueException:
                break


        # remake the path map
        self._path_map.clear()
        for i in range(len(self._index_map)):
            ref = self._index_map[i]
            self._path_map[('%s.%s' % (
                ref.tag.tag_path, ref.class_1.enum_name)).lower()] = i

    def shorten_name_to_parent(self, parent, name):
        join_char = '_' if '_' in name else ' '
        parent_pieces = parent.replace('_', ' ').split(' ')
        name_pieces = name.replace('_', ' ').split(' ')
        start, end = 0, len(name_pieces)
        for i in range(min(len(parent_pieces), len(name_pieces))):
            if parent_pieces[i] == name_pieces[i]:
                start += 1

        for i in range(min(len(parent_pieces), len(name_pieces))):
            if parent_pieces[-1 - i] == name_pieces[-1 - i]:
                end -= 1

        return join_char.join(name_pieces[start: end])

    def get_unique_name(self, collection, name, ext=""):
        if name + ext not in collection:
            return name + ext

        i = 1
        while "%s %s%s" % (name, i, ext) in collection:
            i += 1
        return "%s %s%s" % (name, i, ext)
