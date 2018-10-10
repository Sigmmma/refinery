from refinery.recursive_rename.constants import *
from supyr_struct.defs.util import str_to_identifier


class TagPathHandler():
    _path_map = ()
    _index_map = ()
    _shared_by = ()
    _priorities = ()

    _icon_strings = ()
    _item_strings = ()
    _def_priority = 0.0


    def __init__(self, tag_index_array, **kwargs):
        self._def_priority = kwargs.get('def_priority', 0)
        self._index_map = list(tag_index_array)
        self._shared_by = [[] for i in range(len(tag_index_array))]
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

    def set_item_strings(self, strings_body):
        new_strings = []
        for b in strings_body.strings.STEPTREE:
            string = str_to_identifier(b.data.lower())
            string = string.lstrip("picked_up_").lstrip("the_").lstrip("an_").\
                     lstrip("%a_").lstrip("%d_")
            new_strings.append(sanitize_name(string).strip("_"))

        self._item_strings = new_strings

    def set_icon_strings(self, strings_body):
        new_strings = []
        for b in strings_body.strings.STEPTREE:
            string = str_to_identifier(b.data.lower())
            new_strings.append(sanitize_name(string).strip("_"))

        self._icon_strings = new_strings

    def get_index_ref(self, index):
        return self._index_map[index]

    def get_path(self, index):
        return self.get_index_ref(index).tag.tag_path

    def get_shared_by(self, index):
        return self._shared_by[index]

    def get_priority(self, index):
        return self._priorities[index]

    def set_path(self, index, new_path, priority=None, parent=None):
        if priority is None:
            priority = self._def_priority
        assert isinstance(new_path, str)
        new_path = sanitize_name(new_path)
        new_path_no_ext, ext = splitext(new_path)
        new_path_no_ext, ext = new_path_no_ext.lower(), ext.lower()

        tag_ref = self.get_index_ref(index)
        old_path = "%s.%s" % (tag_ref.tag.tag_path.lower(), ext)
        if self.get_priority(index) > priority or tag_ref.indexed:
            return old_path

        i = 0
        new_path = new_path_no_ext
        while new_path in self._path_map:
            new_path = "%s_%s%s" % (new_path_no_ext, i, ext)
            i += 1

        if i > 0:
            new_path_no_ext = "%s_%s" % (new_path_no_ext, i)

        if len(new_path_no_ext) > MAX_TAG_NAME_LEN:
            print("'%s' is too long to use as a tagpath" % new_path_no_ext)
            return

        self._priorities[index] = priority
        if parent:
            self._shared_by[index].append(parent)

        self._path_map.pop(old_path, None)
        self._path_map[new_path] = index
        tag_ref.tag.tag_path = new_path_no_ext
        return new_path

    def set_priority(self, index, priority):
        self._priorities[index] = float(priority)
