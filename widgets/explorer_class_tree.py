import os
import tkinter as tk

from supyr_struct.defs.constants import PATHDIV, INVALID
from traceback import format_exc

from refinery.constants import BAD_CLASSES
from refinery.util import sanitize_path, int_to_fourcc, is_reserved_tag
from refinery.widgets.explorer_hierarchy_tree import ask_extract_settings,\
     ExplorerHierarchyTree


class ExplorerClassTree(ExplorerHierarchyTree):

    def add_tag_index_refs(self, index_refs, presorted=False):
        if self.active_map is None: return

        map_magic = self.active_map.map_magic
        tags_tree = self.tags_tree
        tree_id_to_index_ref = self.tree_id_to_index_ref

        if presorted:
            sorted_index_refs = index_refs
        else:
            sorted_index_refs = []

            # sort the index_refs
            if isinstance(index_refs, dict):
                index_refs = index_refs.keys()

            check_classes = hasattr(self.valid_classes, "__iter__")
            for b in index_refs:
                if check_classes:
                    if int_to_fourcc(b.class_1.data) not in self.valid_classes:
                        continue

                if b.class_1.enum_name not in BAD_CLASSES:
                    tag_cls = int_to_fourcc(b.class_1.data)
                    ext = ".%s" % b.class_1.enum_name
                else:
                    tag_cls = INVALID
                    ext = ".INVALID"

                tag_path = b.path.lower()
                if PATHDIV == "/":
                    tag_path = sanitize_path(tag_path)
                sorted_index_refs.append(
                    (tag_cls + PATHDIV + tag_path + ext, b))

        sorted_index_refs = self.sort_index_refs(sorted_index_refs)

        if self.sort_by != "name":
            # add all the directories before files and have them sorted by name
            tag_classes = []
            for index_ref in sorted_index_refs:
                class_enum = index_ref[1].class_1
                class_fcc  = int_to_fourcc(class_enum.data)
                if class_enum.enum_name in BAD_CLASSES:     continue
                elif tags_tree.exists(class_fcc + PATHDIV): continue
                elif class_fcc in tag_classes:              continue

                tag_classes.append(class_fcc)

            for tag_class in sorted(tag_classes):
                self.add_folder_path([tag_class])

        for index_ref in sorted_index_refs:
            tag_path, b = index_ref
            if is_reserved_tag(b): continue

            tag_path = tag_path.split(PATHDIV, 1)[1]
            tag_id = b.id & 0xFFff
            map_magic = self.active_map.map_magic
            tag_cls = INVALID
            if b.class_1.enum_name not in BAD_CLASSES:
                tag_cls = int_to_fourcc(b.class_1.data)

            pointer_converter = self.active_map.map_pointer_converter
            if hasattr(self.active_map, "bsp_pointer_converters"):
                pointer_converter = self.active_map.bsp_pointer_converters.get(
                    tag_id, pointer_converter)

            if b.indexed and pointer_converter:
                pointer = "not in map"
            elif pointer_converter is not None:
                pointer = pointer_converter.v_ptr_to_f_ptr(b.meta_offset)
            else:
                pointer = 0

            if not self.active_map.map_magic:
                # resource cache tag
                tag_id = b.id

            try:
                if not self.tags_tree.exists(tag_cls + PATHDIV):
                    self.add_folder_path([tag_cls])

                cls1 = cls2 = cls3 = ""
                if b.class_1.enum_name not in BAD_CLASSES:
                    cls1 = int_to_fourcc(b.class_1.data)
                if b.class_2.enum_name not in BAD_CLASSES:
                    cls2 = int_to_fourcc(b.class_2.data)
                if b.class_3.enum_name not in BAD_CLASSES:
                    cls3 = int_to_fourcc(b.class_3.data)

                tags_tree.insert(
                    tag_cls + PATHDIV, 'end', iid=str(tag_id),
                    tags=("item", ), text=tag_path,
                    values=(cls1, cls2, cls3, b.meta_offset, pointer, tag_id))

                tree_id_to_index_ref[tag_id] = b
            except Exception:
                print(format_exc())

    def activate_item(self, e=None):
        tags_tree = self.tags_tree
        tree_id_to_index_ref = self.tree_id_to_index_ref
        if self.queue_tree is None:
            return

        def_settings = {}
        if self.app_root:
            def_settings = dict(self.app_root.tk_vars)
            if self.app_root.running:
                return

        map_name = self.active_map.map_header.map_name
        # add selection to queue
        for iid in tags_tree.selection():
            if len(tags_tree.item(iid, 'values')):
                # tag_index_ref
                item_name = tags_tree.parent(iid) + tags_tree.item(iid, 'text')
                tag_index_ref  = tree_id_to_index_ref[int(iid)]
                tag_index_refs = (tag_index_ref, )
            else:
                # directory
                item_name = iid
                tag_index_ref  = None
                tag_index_refs = self._compile_list_of_selected(iid)

            title, path_string = item_name.split(PATHDIV, 1)
            if path_string:
                title = None
            def_settings['rename_string'] = path_string

            # ask for extraction settings
            settings = ask_extract_settings(self, def_settings, title=title,
                                            tag_index_ref=tag_index_ref)

            if settings['accept_rename'].get():
                if not path_string:
                    # selecting a tag_class
                    print("Cannot rename by tag class.")
                    continue
                #new_name = os.path.splitext(settings['rename_string'].get())[0]
                new_name = settings['rename_string'].get()
                new_type = settings['newtype_string'].get()
                self.rename_tag_index_refs(
                    tag_index_refs, os.path.splitext(path_string)[0],
                    new_name, new_type)
            elif settings['accept_settings'].get():
                settings['tag_index_refs'] = tag_index_refs
                self.queue_tree.add_to_queue(
                    "%s: map: %s: %s" % (settings['extract_mode'].get(),
                                         map_name, item_name), settings)
