#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import os
import refinery
import tkinter as tk

from pathlib import PureWindowsPath
from traceback import format_exc

from mozzarilla.widgets.directory_frame import HierarchyFrame
from refinery.constants import MAX_TAG_NAME_LEN, BAD_CLASSES,\
     H1_TAG_SUPERCLASSES
from refinery.util import int_to_fourcc, is_reserved_tag
from refinery.windows.actions_window import RefineryActionsWindow

from supyr_struct.defs.frozen_dict import FrozenDict

no_op = lambda *a, **kw: None

TREE_SORT_METHODS = FrozenDict(
    {0: "name", 4:"pointer", 5:"pointer", 6:"index_id"})


class ExplorerHierarchyTree(HierarchyFrame):
    active_map = None
    tags_tree = None
    valid_classes = None

    tree_id_to_index_ref = None

    queue_tree = None
    sibling_tree_frames = None
    sort_by = "name"
    reverse_sorted = False

    def __init__(self, *args, **kwargs):
        self.queue_tree = kwargs.pop('queue_tree', self.queue_tree)
        self.tree_id_to_index_ref = {}
        kwargs.setdefault('select_mode', 'extended')
        self.sibling_tree_frames = kwargs.pop('sibling_tree_frames', {})

        HierarchyFrame.__init__(self, *args, **kwargs)
        self.tags_tree.bind('<Return>', self.activate_item)
        self.tags_tree.bind('<Button-1>', self.set_sort_mode)

    def set_sort_mode(self, event):
        if self.tags_tree.identify_region(event.x, event.y) != "heading":
            return
        column = int(self.tags_tree.identify_column(event.x)[1:])
        new_sort = TREE_SORT_METHODS.get(column)
        if new_sort is None:
            return
        elif new_sort == self.sort_by:
            self.reverse_sorted = not self.reverse_sorted
        else:
            self.reverse_sorted = False

        self.sort_by = new_sort
        self.reload(self.active_map)

    def sort_index_refs(self, index_refs):
        if isinstance(index_refs, dict):
            index_refs = index_refs.keys()

        sortable_index_refs = []
        for b in index_refs:
            tag_path_key = self.get_tag_tree_key(b)
            if tag_path_key is not None:
                sortable_index_refs.append((tag_path_key, b))

        new_sorting = {}
        if self.sort_by == "index_id":
            for index_ref in sortable_index_refs:
                new_sorting.setdefault(
                    index_ref[1].id & 0xFFff, []).append(index_ref)
        elif self.sort_by == "pointer":
            for index_ref in sortable_index_refs:
                new_sorting.setdefault(
                    index_ref[1].meta_offset, []).append(index_ref)
        else:
            # default to sorting by name
            for index_ref in sortable_index_refs:
                new_sorting.setdefault(
                    index_ref[0], []).append(index_ref)

        sorted_index_refs = [None]*len(sortable_index_refs)
        i = 0
        for key in sorted(new_sorting):
            for index_ref in new_sorting[key]:
                sorted_index_refs[i] = index_ref
                i += 1

        if self.reverse_sorted:
            return list(reversed(sorted_index_refs[:i]))

        return sorted_index_refs[:i]

    def setup_columns(self):
        tags_tree = self.tags_tree
        if not tags_tree['columns']:
            # dont want to do this more than once
            tags_tree['columns'] = ('class1', 'class2', 'class3',
                                    'magic', 'pointer', 'index_id')
            tags_tree.heading("#0", text='')
            tags_tree.heading("class1", text='class 1')
            tags_tree.heading("class2", text='class 2')
            tags_tree.heading("class3", text='class 3')
            tags_tree.heading("magic",  text='pointer(memory)')
            tags_tree.heading("pointer", text='pointer(file)')
            tags_tree.heading("index_id",  text='index id')

            tags_tree.column("#0", minwidth=100, width=200)
            tags_tree.column("class1", minwidth=5, width=45, stretch=False)
            tags_tree.column("class2", minwidth=5, width=10, stretch=False)
            tags_tree.column("class3", minwidth=5, width=10, stretch=False)
            tags_tree.column("magic",  minwidth=5, width=12, stretch=False)
            tags_tree.column("pointer", minwidth=5, width=70, stretch=False)
            tags_tree.column("index_id", minwidth=5, width=50, stretch=False)

    def reload(self, active_map=None):
        self.active_map = active_map
        tags_tree = self.tags_tree
        tree_id_to_index_ref = self.tree_id_to_index_ref
        self.setup_columns()

        # remove any currently existing children
        for child in tags_tree.get_children():
            tags_tree.delete(child)
            tree_id_to_index_ref.pop(child, None)

        if active_map is not None:
            # generate the hierarchy
            # TODO: Do a profile of this to determine where the bottleneck
            #       is, as it's taking much longer to reload now.
            self.add_tag_index_refs(active_map.tag_index.tag_index)

    def _compile_list_of_selected(self, parent, selected=None):
        if selected is None:
            selected = []

        tags_tree = self.tags_tree
        tree_id_to_index_ref = self.tree_id_to_index_ref
        for iid in tags_tree.get_children(parent):
            if len(tags_tree.item(iid, 'values')):
                # tag_index_ref
                selected.append(tree_id_to_index_ref[int(iid)])
            else:
                # directory
                self._compile_list_of_selected(iid, selected)

        return selected

    def activate_all(self, e=None):
        tags_tree = self.tags_tree
        if self.active_map is None:
            return

        if self.queue_tree is None:
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

        # ask for extraction settings
        settings, _, __ = self.show_actions_dialog(
            "", renamable=False, title=map_name, defaults=def_settings)

        if settings['accept_settings'].get():
            settings['tag_index_refs'] = self._compile_list_of_selected("")
            settings['title'] = map_name
            self.queue_tree.add_to_queue("%s: %s: %s" % (
                settings['extract_mode'].get(), self.active_map.engine,
                map_name), settings)

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
                tag_index_ref = tree_id_to_index_ref[int(iid)]
                tag_index_refs = (tag_index_ref, )
            else:
                # directory
                item_name = iid
                tag_index_ref = None
                tag_index_refs = self._compile_list_of_selected(iid)

            # ask for extraction settings
            settings, original_name, title = self.show_actions_dialog(
                item_name, defaults=def_settings, tag_index_ref=tag_index_ref)

            if settings['accept_rename'].get():
                item_name = str(PureWindowsPath(
                    tags_tree.parent(iid),
                    tags_tree.item(iid, 'text')).with_suffix(""))

                self.rename_tag_index_refs(
                    tag_index_refs, original_name,
                    settings['rename_string'].get(),
                    settings['newtype_string'].get())
            elif settings['accept_settings'].get():
                settings['tag_index_refs'] = tag_index_refs
                settings['title'] = title
                self.queue_tree.add_to_queue(
                    "%s: map: %s: %s" % (
                        settings['extract_mode'].get(),
                        map_name, item_name), settings)

    def show_actions_dialog(self, item_name, **kwargs):
        defaults = kwargs.pop("defaults", {})

        kwargs.setdefault('title', item_name)

        settings_vars = dict(
            recursive=tk.IntVar(self), overwrite=tk.IntVar(self),
            do_printout=tk.IntVar(self), accept_rename=tk.IntVar(self),
            autoload_resources=tk.IntVar(self), decode_adpcm=tk.IntVar(self),
            bitmap_extract_keep_alpha=tk.IntVar(self),
            generate_comp_verts=tk.IntVar(self), generate_uncomp_verts=tk.IntVar(self),
            accept_settings=tk.IntVar(self), out_dir=tk.StringVar(self),
            extract_mode=tk.StringVar(self, "tags"), halo_map=self.active_map,
            rename_string=tk.StringVar(self), newtype_string=tk.StringVar(self),
            tagslist_path=tk.StringVar(self), allow_corrupt=tk.IntVar(self),
            skip_seen_tags_during_queue_processing=tk.IntVar(self),
            disable_safe_mode=tk.IntVar(self), disable_tag_cleaning=tk.IntVar(self),

            bitmap_extract_format=tk.StringVar(self),
            globals_overwrite_mode=tk.StringVar(self),
            )

        settings_vars['rename_string'].set(
            defaults.pop('name_string', item_name))

        for k in defaults:
            if k in settings_vars:
                settings_vars[k].set(defaults[k].get())

        dir_type = defaults.get("extract_mode").get() + "_dir"
        if dir_type in defaults:
            settings_vars["out_dir"].set(defaults[dir_type].get())

        w = RefineryActionsWindow(self, settings=settings_vars, **kwargs)
        original_name, title = str(w.original_name), w.title()

        # make the tree freeze until the settings ask window is done
        self.wait_window(w)

        return settings_vars, original_name, title

    def rename_tag_index_refs(self, index_refs, old_basename,
                              new_basename, new_cls, rename_other_trees=True):
        if self.active_map is None: return

        old_basename = old_basename.lower()
        new_basename = new_basename.lower()

        tags_tree = self.tags_tree
        map_magic = self.active_map.map_magic
        tree_id_to_index_ref = self.tree_id_to_index_ref

        child_items = []
        renamed_index_refs = []
        renaming_multiple = len(index_refs) > 1
        if renaming_multiple:
            new_cls = None

        if (old_basename == new_basename) and not new_cls:
            return

        for index_ref in index_refs:
            tag_cls_val = index_ref.class_1.data
            tag_id      = index_ref.id & 0xFFff
            if not map_magic:
                # resource cache tag
                tag_id = index_ref.id
            if new_cls:
                try:
                    tag_cls_val = index_ref.class_1.get_value(new_cls)
                except Exception:
                    new_cls = None

            # when renaming only one tag, the basenames COULD BE the full names
            old_name = str(PureWindowsPath(index_ref.path.lower()))
            new_name = old_name.replace(old_basename, new_basename, 1)
            if not old_name.startswith(old_basename):
                # tag_path doesnt have the base_name in it
                continue
            elif not tags_tree.exists(tag_id):
                # tag not in the tree
                continue
            elif not new_name:
                print("Cannot rename '%s' to an empty string." % old_name)
                continue
            elif index_ref.indexed:
                print("Cannot rename indexed tag: %s" % old_name)
                continue
            elif len(new_name) > MAX_TAG_NAME_LEN:
                print("'%s' is too long to use as a tagpath" % new_name)
                continue

            # make sure a tag with that name doesnt already exist
            already_exists = False
            for child_id in tags_tree.get_children(tags_tree.parent(tag_id)):
                try: child_id = int(child_id)
                except ValueError: continue

                sibling_index_ref = tree_id_to_index_ref.get(child_id)
                if not sibling_index_ref:
                    # sibling is being edited. no worry
                    continue
                elif sibling_index_ref is index_ref:
                    # this is the thing we're renaming. no worry
                    continue
                elif tag_cls_val != sibling_index_ref.class_1.data:
                    # classes are different. no worry
                    continue
                elif sibling_index_ref.path != new_name:
                    # names are different. no worry
                    continue
                already_exists = True
                break

            if already_exists:
                print("'%s' already exists in map. Cannot rename." % new_name)
                continue

            if rename_other_trees:
                index_ref.path = new_name
                try:
                    old_cls = index_ref.class_1.enum_name
                except Exception:
                    old_cls = None

                if new_cls and new_cls != old_cls:
                    index_ref.class_1.set_to(new_cls)
                    cls_2, cls_3 = H1_TAG_SUPERCLASSES.get(new_cls, ("NONE", "NONE"))
                    index_ref.class_2.set_to(cls_2)
                    index_ref.class_3.set_to(cls_3)

            # add this child to the list to be removed
            child_items.append(tag_id)
            tree_id_to_index_ref.pop(tag_id, None)
            renamed_index_refs.append(index_ref)

        # remove the highest parent with only 1 child from the tree.
        for child in child_items:
            while len(tags_tree.get_children(tags_tree.parent(child))) <= 1:
                # only one or less children. can be deleted
                child = tags_tree.parent(child)
            tags_tree.delete(child)

        # add the newly named tags back to the tree
        self.add_tag_index_refs(renamed_index_refs)

        if not rename_other_trees:
            return

        for tree in self.sibling_tree_frames.values():
            if tree is not self and hasattr(tree, 'rename_tag_index_refs'):
                tree.rename_tag_index_refs(renamed_index_refs, old_basename,
                                           new_basename, new_cls, False)

    def get_tag_tree_key(self, tag_index_ref):
        if (hasattr(self.valid_classes, "__iter__") and
            int_to_fourcc(tag_index_ref.class_1.data) not in self.valid_classes):
            return None

        if tag_index_ref.class_1.enum_name not in BAD_CLASSES:
            ext = ".%s" % tag_index_ref.class_1.enum_name
        else:
            ext = ".INVALID"

        return str(PureWindowsPath(tag_index_ref.path.lower())) + ext

    def add_tag_index_refs(self, index_refs):
        if self.active_map is None:
            return

        sorted_index_refs = self.sort_index_refs(index_refs)

        # add all the directories before files
        # put the directories in sorted by name
        indices_by_dirpath = {
            os.path.dirname(block[0]): i
            for i, block in enumerate(sorted_index_refs)
            }
        for dir_path in sorted(indices_by_dirpath):
            b = sorted_index_refs[indices_by_dirpath[dir_path]][1]
            if not is_reserved_tag(b):
                self.add_folder_path(PureWindowsPath(dir_path).parts)

        for tag_path, tag_index_ref in sorted_index_refs:
            if is_reserved_tag(tag_index_ref):
                continue

            tag_path = PureWindowsPath(tag_path)
            self.add_tag_index_ref(
                tag_path.parent.parts, tag_path.name, tag_index_ref)

    def add_tag_index_ref(self, parent_dir_parts, tag_path, tag_index_ref):
        tag_id = tag_index_ref.id & 0xFFff
        if not self.active_map.map_magic:
            # resource cache tag
            tag_id = tag_index_ref.id

        pointer_converter = self.active_map.map_pointer_converter
        if hasattr(self.active_map, "bsp_pointer_converters"):
            pointer_converter = self.active_map.bsp_pointer_converters.get(
                tag_id, pointer_converter)

        is_h1_rsrc_map = (self.active_map.is_resource and
                          self.active_map.engine in (
                              "halo1pcdemo", "halo1pc",
                              "halo1ce", "halo1yelo"))

        if tag_index_ref.indexed and pointer_converter and not is_h1_rsrc_map:
            pointer = "not in map"
        elif pointer_converter is not None:
            pointer = pointer_converter.v_ptr_to_f_ptr(
                tag_index_ref.meta_offset)
        else:
            pointer = 0

        try:
            cls1 = cls2 = cls3 = ""
            if tag_index_ref.class_1.enum_name not in BAD_CLASSES:
                cls1 = int_to_fourcc(tag_index_ref.class_1.data)
            if tag_index_ref.class_2.enum_name not in BAD_CLASSES:
                cls2 = int_to_fourcc(tag_index_ref.class_2.data)
            if tag_index_ref.class_3.enum_name not in BAD_CLASSES:
                cls3 = int_to_fourcc(tag_index_ref.class_3.data)

            parent_iid = self.add_folder_path(parent_dir_parts)
            self.tags_tree.insert(
                # NEED TO DO str OR ELSE THE SCENARIO TAG'S ID WILL
                # BE INTERPRETED AS NOTHING AND BE CHANGED TO 'I001'
                parent_iid, 'end', iid=str(tag_id),
                tags=("item", ), text=tag_path,
                values=(cls1, cls2, cls3,
                        tag_index_ref.meta_offset, pointer, tag_id))
            self.tree_id_to_index_ref[tag_id] = tag_index_ref
        except Exception:
            print(format_exc())

    def add_folder_path(self, dir_parts):
        abs_dir_path = str(PureWindowsPath(*dir_parts))
        if abs_dir_path:
            abs_dir_path += "\\"  # directories must end with a backslash.
            #                       this is how we distinguish dirs from files

        if self.tags_tree.exists(abs_dir_path):
            return abs_dir_path

        return self._add_folder_path(list(dir_parts), '')

    def _add_folder_path(self, dir_parts, parent_dir):
        if not dir_parts:
            return parent_dir

        this_dir = dir_parts.pop(0)
        if not this_dir:
            return parent_dir

        abs_dir_path = parent_dir + this_dir
        if abs_dir_path:
            abs_dir_path += "\\"  # directories must end with a backslash.
            #                       this is how we distinguish dirs from files

        if not self.tags_tree.exists(abs_dir_path):
            # add the directory to the treeview
            self.tags_tree.insert(
                parent_dir, 'end', iid=abs_dir_path,
                tags=("item", ), text=this_dir)

        return self._add_folder_path(dir_parts, abs_dir_path)

    open_selected = close_selected = no_op

    set_root_dir = add_root_dir = insert_root_dir = del_root_dir = no_op

    destroy_subitems = no_op

    get_item_tags_dir = highlight_tags_dir = no_op
