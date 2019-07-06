import tkinter as tk

from refinery.constants import BAD_CLASSES
from refinery.util import sanitize_path, int_to_fourcc
from refinery.widgets.explorer_class_tree import ExplorerClassTree
from refinery.widgets.explorer_hierarchy_tree import ExplorerHierarchyTree

from supyr_struct.defs.constants import PATHDIV, INVALID


class ExplorerHybridTree(ExplorerHierarchyTree):

    def add_tag_index_refs(self, index_refs, presorted=False):
        if presorted:
            ExplorerHierarchyTree.add_tag_index_refs(self, index_refs, True)
            
        sorted_index_refs = []

        check_classes = hasattr(self.valid_classes, "__iter__")
        for b in index_refs:
            if check_classes:
                if int_to_fourcc(b.class_1.data) not in self.valid_classes:
                    continue

            if b.class_1.enum_name not in BAD_CLASSES:
                ext = ".%s" % b.class_1.enum_name
            else:
                ext = ".INVALID"

            tag_cls = INVALID
            if b.class_1.enum_name not in BAD_CLASSES:
                tag_cls = int_to_fourcc(b.class_1.data)

            tag_path = b.path.lower()
            if PATHDIV == "/":
                tag_path = sanitize_path(tag_path)
            sorted_index_refs.append(
                (tag_cls + PATHDIV + tag_path + ext, b))

        sorted_index_refs = self.sort_index_refs(sorted_index_refs)
        ExplorerHierarchyTree.add_tag_index_refs(self, sorted_index_refs, True)

    activate_item = ExplorerClassTree.activate_item
