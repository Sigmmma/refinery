from refinery.recursive_rename.constants import *
from refinery.recursive_rename.functions import sanitize_name
from supyr_struct.defs.util import str_to_identifier


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

    def set_path(self, index, new_path_no_ext, priority=None, parent=None):
        if index is None:
            return ""
        elif priority is None:
            priority = self._def_priority
        assert isinstance(new_path_no_ext, str)

        tag_ref = self.get_index_ref(index)
        ext = "." + tag_ref.class_1.enum_name
        new_path_no_ext, ext = sanitize_name(new_path_no_ext), ext.lower()
        old_path = tag_ref.tag.tag_path.lower() + ext

        if self.get_priority(index) >= priority or tag_ref.indexed:
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
        #if len(new_path_no_ext) > MAX_TAG_NAME_LEN:
        #    print("'%s' is too long to use as a tagpath" % new_path_no_ext)
        #    return old_path

        self._priorities[index] = priority
        if parent:
            self._shared_by[index].append(parent)

        self._path_map.pop(old_path, None)
        self._path_map[new_path] = index
        tag_ref.tag.tag_path = new_path_no_ext
        ############# DEBUG #############
        print(index, priority, new_path_no_ext)
        return new_path

    def set_priority(self, index, priority):
        self._priorities[index] = float(priority)
