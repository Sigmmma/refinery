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
from supyr_struct.defs.constants import INVALID
from traceback import format_exc

from refinery.constants import BAD_CLASSES
from refinery.util import int_to_fourcc, is_reserved_tag
from refinery.widgets.explorer_hierarchy_tree import ExplorerHierarchyTree


class ExplorerClassTree(ExplorerHierarchyTree):

    def get_tag_tree_key(self, tag_index_ref):
        tag_path_key = ExplorerHierarchyTree.get_tag_tree_key(self, tag_index_ref)
        if tag_path_key is None:
            return None

        if tag_index_ref.class_1.enum_name not in BAD_CLASSES:
            tag_cls = int_to_fourcc(tag_index_ref.class_1.data)
        else:
            tag_cls = INVALID

        return str(PureWindowsPath(tag_cls, tag_path_key))

    def add_tag_index_refs(self, index_refs):
        if self.active_map is None:
            return

        sorted_index_refs = self.sort_index_refs(index_refs)

        # add all the directories before files and have them sorted by name
        tag_classes = set()
        for index_ref in sorted_index_refs:
            class_enum = index_ref[1].class_1
            if class_enum.enum_name not in BAD_CLASSES:
                tag_classes.add(int_to_fourcc(class_enum.data))

        for tag_class in sorted(tag_classes):
            self.add_folder_path([tag_class])

        for tag_path, tag_index_ref in sorted_index_refs:
            if is_reserved_tag(tag_index_ref):
                continue

            tag_cls = INVALID
            if tag_index_ref.class_1.enum_name not in BAD_CLASSES:
                tag_cls = int_to_fourcc(tag_index_ref.class_1.data)

            tag_path = str(PureWindowsPath(
                *PureWindowsPath(tag_path).parts[1:]))
            self.add_tag_index_ref([tag_cls], tag_path, tag_index_ref)

    def show_actions_dialog(self, item_name, **kwargs):
        path_parts = PureWindowsPath(item_name).parts

        kwargs.setdefault("title", item_name)
        kwargs.setdefault("renamable", len(path_parts) > 1)
        kwargs.setdefault("defaults", {})

        kwargs["defaults"]["name_string"] = str(PureWindowsPath(*path_parts[1:]))

        return ExplorerHierarchyTree.show_actions_dialog(
            self, item_name, **kwargs)
