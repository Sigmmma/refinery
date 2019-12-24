import os

from pathlib import PureWindowsPath
from supyr_struct.defs.constants import INVALID
from traceback import format_exc

from refinery.constants import BAD_CLASSES
from refinery.util import int_to_fourcc, is_reserved_tag
from refinery.widgets.explorer_hierarchy_tree import ask_extract_settings,\
     ExplorerHierarchyTree


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

    def activate_item(self, e=None):
        tags_tree = self.tags_tree
        tree_id_to_index_ref = self.tree_id_to_index_ref
        if self.active_map is None or self.queue_tree is None:
            return
        elif ("halo2" in self.active_map.engine and
              self.active_map.engine != "halo2vista"):
            print("Cannot interact with Halo 2 Xbox maps.")
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

            path_parts = PureWindowsPath(item_name).parts
            if not path_parts:
                continue

            title, path_string = None, ""
            if len(path_parts) == 1:
                title = path_parts[0]
            else:
                path_string = str(PureWindowsPath(*path_parts[1:]))

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
