#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

from pathlib import PureWindowsPath

from refinery.constants import BAD_CLASSES
from refinery.util import int_to_fourcc
from refinery.widgets.explorer_class_tree import ExplorerClassTree
from refinery.widgets.explorer_hierarchy_tree import ExplorerHierarchyTree

from supyr_struct.defs.constants import INVALID


class ExplorerHybridTree(ExplorerHierarchyTree):

    def get_tag_tree_key(self, tag_index_ref):
        tag_path_key = ExplorerHierarchyTree.get_tag_tree_key(self, tag_index_ref)
        if tag_path_key is None:
            return None

        tag_cls = INVALID
        if tag_index_ref.class_1.enum_name not in BAD_CLASSES:
            tag_cls = int_to_fourcc(tag_index_ref.class_1.data)

        return str(PureWindowsPath(tag_cls, tag_path_key))

    show_actions_dialog = ExplorerClassTree.show_actions_dialog
