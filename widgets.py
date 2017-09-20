import tkinter as tk

from os.path import dirname, basename, splitext
from supyr_struct.defs.constants import *
from tkinter import messagebox
from tkinter.filedialog import asksaveasfilename, askdirectory
from traceback import format_exc

from refinery.hashcacher_window import sanitize_filename, HashcacherWindow
from refinery.meta_window import MetaWindow
from refinery.util import is_protected_tag, fourcc, is_reserved_tag

from mozzarilla.tools.shared_widgets import HierarchyFrame
from reclaimer.common_descs import blam_header, QStruct
from supyr_struct.defs.tag_def import TagDef

no_op = lambda *a, **kw: None

# max number of characters long a tag name can be before halo wont accept it
MAX_NAME_LEN = 243


meta_tag_def = TagDef("meta tag",
    blam_header('\xFF\xFF\xFF\xFF'),
    QStruct('tagdata'),
    )

TREE_SORT_METHODS = {0: "name", 4:"pointer", 5:"pointer", 6:"index_id"}
BAD_CLASSES = ("<INVALID>", "NONE")

def ask_extract_settings(parent, def_vars=None, **kwargs):
    if def_vars is None:
        def_vars = {}

    settings_vars = dict(
        recursive=tk.IntVar(parent), overwrite=tk.IntVar(parent),
        show_output=tk.IntVar(parent), accept_rename=tk.IntVar(parent),
        accept_settings=tk.IntVar(parent), out_dir=tk.StringVar(parent),
        extract_mode=tk.StringVar(parent, "tags"), halo_map=parent.active_map,
        rename_string=tk.StringVar(parent), tags_list_path=tk.StringVar(parent)
        )

    settings_vars['rename_string'].set(def_vars.pop('rename_string', ''))

    for k in def_vars:
        if k in settings_vars:
            settings_vars[k].set(def_vars[k].get())

    settings_vars["out_dir"] = def_vars.pop(
        def_vars.get("extract_mode").get() + "_dir")

    w = RefineryActionsWindow(parent, tk_vars=settings_vars, **kwargs)

    # make the parent freeze what it's doing until we're destroyed
    parent.wait_window(w)

    return settings_vars


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

    def sort_index_refs(self, sortable_index_refs):
        new_sorting = {}

        if self.sort_by == "index_id":
            for index_ref in sortable_index_refs:
                key = index_ref[1].id.tag_table_index
                same_list = new_sorting.get(key, [])
                same_list.append(index_ref)
                new_sorting[key] = same_list
        elif self.sort_by == "pointer":
            for index_ref in sortable_index_refs:
                key = index_ref[1].meta_offset
                same_list = new_sorting.get(key, [])
                same_list.append(index_ref)
                new_sorting[key] = same_list
        else:
            # default to sorting by name
            for index_ref in sortable_index_refs:
                key = index_ref[0]
                same_list = new_sorting.get(key, [])
                same_list.append(index_ref)
                new_sorting[key] = same_list

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
            tags_tree.column("class2", minwidth=5, width=15, stretch=False)
            tags_tree.column("class3", minwidth=5, width=15, stretch=False)
            tags_tree.column("magic",  minwidth=5, width=15, stretch=False)
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
        if self.queue_tree is None:
            return

        app_root = self.app_root
        def_tk_vars = {}
        if app_root:
            def_tk_vars = dict(app_root.tk_vars)
            if app_root.running:
                return

        item_name = self.active_map.map_header.map_name

        # ask for extraction settings
        settings = ask_extract_settings(self, def_tk_vars,
                                        title=item_name, renamable=False)

        if settings['accept_settings'].get():
            settings['tag_index_refs'] = self._compile_list_of_selected("")
            settings['title'] = item_name
            self.queue_tree.add_to_queue("%s: map: %s" % (
                settings['extract_mode'].get(), item_name), settings)

    def activate_item(self, e=None):
        tags_tree = self.tags_tree
        tree_id_to_index_ref = self.tree_id_to_index_ref
        if self.queue_tree is None:
            return

        app_root = self.app_root
        def_tk_vars = {}
        if app_root:
            def_tk_vars = dict(app_root.tk_vars)
            if app_root.running:
                return

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

            def_tk_vars['rename_string'] = item_name

            # ask for extraction settings
            settings = ask_extract_settings(self, def_tk_vars, title=item_name,
                                            tag_index_ref=tag_index_ref)

            if settings['accept_rename'].get():
                new_name = splitext(settings['rename_string'].get())[0]
                self.rename_tag_index_refs(tag_index_refs, item_name, new_name)
            elif settings['accept_settings'].get():
                settings['tag_index_refs'] = tag_index_refs
                settings['title'] = item_name
                self.queue_tree.add_to_queue(
                    "%s: %s" % (settings['extract_mode'].get(),
                                item_name), settings)

    def rename_tag_index_refs(self, index_refs, old_basename, new_basename,
                              rename_in_other_trees=True):
        if self.active_map is None: return

        old_basename = old_basename.lower()
        new_basename = new_basename.lower()
        if old_basename == new_basename:
            return

        tags_tree = self.tags_tree
        map_magic = self.active_map.map_magic
        tree_id_to_index_ref = self.tree_id_to_index_ref

        child_items = []
        renamed_index_refs = []
        renaming_multiple = len(index_refs) > 1

        for index_ref in index_refs:
            tag_cls = index_ref.class_1.data
            tag_id  = index_ref.id.tag_table_index
            if not map_magic:
                # resource cache tag
                tag_id += (index_ref.id.table_index << 16)

            if not tags_tree.exists(tag_id):
                continue

            # when renaming only one tag, the basenames COULD BE the full names
            old_name = sanitize_path(index_ref.tag.tag_path.lower())
            if renaming_multiple:
                new_name = old_name.split(old_basename)
                if len(new_name) <= 1:
                    # tag_path doesnt have the base_name in it
                    continue
                elif not new_name[1]:
                    print("Cannot rename '%s' to an empty string." % old_name)
                    continue

                new_name = new_basename + new_name[1]
            else:
                new_name = new_basename

            if index_ref.indexed:
                print("Cannot rename indexed tag: %s" % old_name)
                continue
            elif len(new_name) > MAX_NAME_LEN:
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
                elif tag_cls != sibling_index_ref.class_1.data:
                    # classes are different. no worry
                    continue
                elif sibling_index_ref.tag.tag_path != new_name:
                    # names are different. no worry
                    continue
                already_exists = True
                break

            if already_exists:
                print("'%s' already exists in map. Cannot rename." % new_name)
                continue

            if rename_in_other_trees:
                index_ref.tag.tag_path = new_name

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

        if not rename_in_other_trees:
            return

        for tree in self.sibling_tree_frames.values():
            if tree is not self and hasattr(tree, 'rename_tag_index_refs'):
                tree.rename_tag_index_refs(renamed_index_refs, old_basename,
                                           new_basename, False)

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
                index_refs = index_refs.values()

            check_classes = hasattr(self.valid_classes, "__iter__")
            for b in index_refs:
                if check_classes:
                    if fourcc(b.class_1.data) not in self.valid_classes:
                        continue

                if b.class_1.enum_name not in BAD_CLASSES:
                    ext = ".%s" % b.class_1.enum_name
                else:
                    ext = ".INVALID"

                tag_path = b.tag.tag_path.lower()
                if PATHDIV == "/":
                    tag_path = sanitize_path(tag_path)
                sorted_index_refs.append((tag_path + ext, b))

            sorted_index_refs = self.sort_index_refs(sorted_index_refs)

        # add all the directories before files
        # put the directories in sorted by name
        indices_by_dirpath = {dirname(sorted_index_refs[i][0]): i
                              for i in range(len(sorted_index_refs))}
        for dir_path in sorted(indices_by_dirpath):
            b = sorted_index_refs[indices_by_dirpath[dir_path]][1]
            if is_reserved_tag(b): continue
            if dir_path: dir_path += PATHDIV

            try:
                if not tags_tree.exists(dir_path):
                    self.add_folder_path(dir_path.split(PATHDIV))
            except Exception:
                print(format_exc())

        for index_ref in sorted_index_refs:
            tag_path, b = index_ref
            if is_reserved_tag(b): continue

            dir_path = dirname(tag_path)
            if dir_path:
                dir_path += PATHDIV

            tag_name = basename(tag_path)
            tag_id = b.id.tag_table_index
            map_magic = self.active_map.map_magic

            if b.indexed and map_magic:
                pointer = "not in map"
            elif map_magic is not None:
                pointer = b.meta_offset - map_magic
            else:
                pointer = 0

            if not map_magic:
                # resource cache tag
                tag_id += (b.id.table_index << 16)

            try:
                cls1 = cls2 = cls3 = ""
                if b.class_1.enum_name not in BAD_CLASSES:
                    cls1 = fourcc(b.class_1.data)
                if b.class_2.enum_name not in BAD_CLASSES:
                    cls2 = fourcc(b.class_2.data)
                if b.class_3.enum_name not in BAD_CLASSES:
                    cls3 = fourcc(b.class_3.data)
                tags_tree.insert(
                    # NEED TO DO str OR ELSE THE SCENARIO TAG'S ID WILL
                    # BE INTERPRETED AS NOTHING AND BE CHANGED TO 'I001'
                    dir_path, 'end', iid=str(tag_id), text=tag_name,
                    values=(cls1, cls2, cls3, b.meta_offset, pointer, tag_id))
                tree_id_to_index_ref[tag_id] = b
            except Exception:
                print(format_exc())

    def add_folder_path(self, dir_paths=(), parent_dir=''):
        if not dir_paths:
            return

        this_dir = dir_paths.pop(0)
        if not this_dir:
            return

        abs_dir_path = parent_dir + this_dir
        if abs_dir_path:
            abs_dir_path += PATHDIV

        if not self.tags_tree.exists(abs_dir_path):
            # add the directory to the treeview
            self.tags_tree.insert(
                parent_dir, 'end', iid=abs_dir_path, text=this_dir)

        self.add_folder_path(dir_paths, abs_dir_path)

    open_selected = close_selected = no_op

    set_root_dir = add_root_dir = insert_root_dir = del_root_dir = no_op

    destroy_subitems = no_op

    get_item_tags_dir = highlight_tags_dir = no_op


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
                    if fourcc(b.class_1.data) not in self.valid_classes:
                        continue

                if b.class_1.enum_name not in BAD_CLASSES:
                    tag_cls = fourcc(b.class_1.data)
                    ext = ".%s" % b.class_1.enum_name
                else:
                    tag_cls = "INVALID"
                    ext = ".INVALID"

                tag_path = b.tag.tag_path.lower()
                if PATHDIV == "/":
                    tag_path = sanitize_path(tag_path)
                sorted_index_refs.append(
                    (tag_cls + PATHDIV + tag_path + ext, b))

        sorted_index_refs = self.sort_index_refs(sorted_index_refs)

        # add all the directories before files
        # put the directories in sorted by name
        tag_classes = []
        for index_ref in sorted_index_refs:
            class_enum = index_ref[1].class_1
            class_fcc  = fourcc(class_enum.data)
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
            tag_id = b.id.tag_table_index
            map_magic = self.active_map.map_magic
            tag_cls = "INVALID"
            if b.class_1.enum_name not in BAD_CLASSES:
                tag_cls = fourcc(b.class_1.data)

            if b.indexed and map_magic:
                pointer = "not in map"
            elif map_magic is not None:
                pointer = b.meta_offset - map_magic
            else:
                pointer = 0

            if not map_magic:
                # resource cache tag
                tag_id += (b.id.table_index << 16)

            try:
                cls1 = cls2 = cls3 = ""
                if b.class_1.enum_name not in BAD_CLASSES:
                    cls1 = fourcc(b.class_1.data)
                if b.class_2.enum_name not in BAD_CLASSES:
                    cls2 = fourcc(b.class_2.data)
                if b.class_3.enum_name not in BAD_CLASSES:
                    cls3 = fourcc(b.class_3.data)

                tags_tree.insert(
                    tag_cls + PATHDIV, 'end', iid=str(tag_id), text=tag_path,
                    values=(cls1, cls2, cls3, b.meta_offset, pointer, tag_id))

                tree_id_to_index_ref[tag_id] = b
            except Exception:
                print(format_exc())

    def activate_item(self, e=None):
        tags_tree = self.tags_tree
        tree_id_to_index_ref = self.tree_id_to_index_ref
        if self.queue_tree is None:
            return

        app_root = self.app_root
        def_tk_vars = {}
        if app_root:
            def_tk_vars = dict(app_root.tk_vars)
            if app_root.running:
                return

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
            def_tk_vars['rename_string'] = path_string

            # ask for extraction settings
            settings = ask_extract_settings(self, def_tk_vars, title=title,
                                            tag_index_ref=tag_index_ref)

            if settings['accept_rename'].get():
                if not path_string:
                    # selecting a tag_class
                    print("Cannot rename by tag class.")
                    continue
                new_name = splitext(settings['rename_string'].get())[0]
                self.rename_tag_index_refs(
                    tag_index_refs, path_string, new_name)
            elif settings['accept_settings'].get():
                settings['tag_index_refs'] = tag_index_refs
                self.queue_tree.add_to_queue(
                    "%s: %s" % (settings['extract_mode'].get(),
                                item_name), settings)


class ExplorerHybridTree(ExplorerHierarchyTree):

    def add_tag_index_refs(self, index_refs, presorted=False):
        if presorted:
            ExplorerHierarchyTree.add_tag_index_refs(self, index_refs, True)
            
        sorted_index_refs = []

        check_classes = hasattr(self.valid_classes, "__iter__")
        for b in index_refs:
            if check_classes:
                if fourcc(b.class_1.data) not in self.valid_classes:
                    continue

            if b.class_1.enum_name not in BAD_CLASSES:
                ext = ".%s" % b.class_1.enum_name
            else:
                ext = ".INVALID"

            tag_cls = "INVALID"
            if b.class_1.enum_name not in BAD_CLASSES:
                tag_cls = fourcc(b.class_1.data)

            tag_path = b.tag.tag_path.lower()
            if PATHDIV == "/":
                tag_path = sanitize_path(tag_path)
            sorted_index_refs.append(
                (tag_cls + PATHDIV + tag_path + ext, b))

        sorted_index_refs = self.sort_index_refs(sorted_index_refs)
        ExplorerHierarchyTree.add_tag_index_refs(self, sorted_index_refs, True)

    activate_item = ExplorerClassTree.activate_item


class QueueTree(ExplorerHierarchyTree):
    # keys are the iid's of the items in the queue
    # values are dictionaries containing extraction details
    queue_info = None

    def __init__(self, *args, **kwargs):
        self.queue_info = {}
        kwargs['select_mode'] = 'browse'
        ExplorerHierarchyTree.__init__(self, *args, **kwargs)

        self.tags_tree.bind('<BackSpace>', self.remove_curr_selection)
        self.tags_tree.bind('<Delete>', self.remove_curr_selection)

    def setup_columns(self):
        pass

    def activate_item(self, e=None):
        tags_tree = self.tags_tree
        if not tags_tree.selection():
            return

        # edit queue
        iids = self.tags_tree.selection()

        if len(iids):
            tk_vars = self.queue_info[iids[0]]
            w = RefineryEditActionsWindow(
                self, tk_vars=tk_vars, title=tk_vars.get('title'))
            # make the parent freeze what it's doing until we're destroyed
            w.master.wait_window(self)

    def add_to_queue(self, item_name, new_queue_info):
        self.queue_info[item_name] = new_queue_info

        if self.tags_tree.exists(item_name):
            self.tags_tree.delete(item_name)
        self.tags_tree.insert('', 'end', iid=item_name, text=item_name)

    def remove_items(self, items=None):
        if items is None:
            items = self.tags_tree.get_children()
        if not hasattr(items, "__iter__"):
            items = (items, )

        for item in items:
            self.queue_info.pop(item, None)

        self.tags_tree.delete(*items)

    def remove_curr_selection(self, e=None):
        self.remove_items(self.tags_tree.selection())

    def reload(self, active_map=None):
        self.setup_columns()

        # remove any currently existing children
        self.remove_items()


class RefinerySettingsWindow(tk.Toplevel):
    tk_vars = None

    def __init__(self, *args, **kwargs):
        self.tk_vars = tk_vars = kwargs.pop('tk_vars', {})
        tk.Toplevel.__init__(self, *args, **kwargs)
        self.geometry("340x512")
        self.minsize(width=340, height=512)
        self.resizable(1, 0)
        self.title("Settings")

        self.extract_frame   = tk.LabelFrame(self, text="Extraction settings")
        self.deprotect_frame = tk.LabelFrame(self, text="Deprotection settings")
        self.yelo_frame      = tk.LabelFrame(self, text="Open Sauce settings")
        self.tags_dir_frame = tk.LabelFrame(
            self, text="Default tags extraction folder")
        self.data_dir_frame = tk.LabelFrame(
            self, text="Default data extraction folder")
        self.tags_list_frame = tk.LabelFrame(
            self, text="Tags list log(erase to disable logging)")

        for attr in ("extract_from_ce_resources", "overwrite",
                     "rename_duplicates_in_scnr", "fix_tag_classes",
                     "use_hashcaches", "use_heuristics",
                     "extract_cheape", "show_output", "fix_tag_index_offset"):
            object.__setattr__(self, attr, tk_vars.get(attr, tk.IntVar(self)))

        for attr in ("tags_dir", "data_dir", "tags_list_path"):
            object.__setattr__(self, attr, tk_vars.get(attr, tk.StringVar(self)))

        self.extract_from_ce_resources_checkbutton = tk.Checkbutton(
            self.extract_frame, text="Extract from CE resource maps",
            variable=self.extract_from_ce_resources)
        self.rename_duplicates_in_scnr_checkbutton = tk.Checkbutton(
            self.extract_frame, text=(
                "Rename duplicate camera points, cutscene\n"+
                "flags, and recorded animations in scenario"),
            variable=self.rename_duplicates_in_scnr)
        self.overwrite_checkbutton = tk.Checkbutton(
            self.extract_frame, text="Overwrite tags(not recommended)",
            variable=self.overwrite)
        self.show_output_checkbutton = tk.Checkbutton(
            self.extract_frame, text="Print extracted tag names",
            variable=self.show_output)

        self.fix_tag_classes_checkbutton = tk.Checkbutton(
            self.deprotect_frame, text="Fix tag classes",
            variable=self.fix_tag_classes)
        self.use_hashcaches_checkbutton = tk.Checkbutton(
            self.deprotect_frame, text="Use hashcaches",
            variable=self.use_hashcaches)
        self.use_heuristics_checkbutton = tk.Checkbutton(
            self.deprotect_frame, text="Use heuristics",
            variable=self.use_heuristics)
        self.fix_tag_index_offset_checkbutton = tk.Checkbutton(
            self.deprotect_frame, text=("Fix tag index offset when saving\n" +
                                        "WARNING: Can corrupt certain maps"),
            variable=self.fix_tag_index_offset, justify='left')

        self.extract_cheape_checkbutton = tk.Checkbutton(
            self.yelo_frame, text="Extract cheape.map from yelo maps",
            variable=self.extract_cheape)

        # tags directory
        self.tags_dir_entry = tk.Entry(
            self.tags_dir_frame, state='disabled',
            textvariable=self.tags_dir)
        self.tags_dir_browse_button = tk.Button(
            self.tags_dir_frame, text="Browse",
            command=self.tags_dir_browse, width=6)

        # data directory
        self.data_dir_entry = tk.Entry(
            self.data_dir_frame, state='disabled',
            textvariable=self.data_dir)
        self.data_dir_browse_button = tk.Button(
            self.data_dir_frame, text="Browse",
            command=self.data_dir_browse, width=6)

        # tags list
        self.tags_list_entry = tk.Entry(
            self.tags_list_frame, textvariable=self.tags_list_path)
        self.browse_tags_list_button = tk.Button(
            self.tags_list_frame, text="Browse",
            command=self.tags_list_browse, width=6)

        # pack everything
        self.tags_dir_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.data_dir_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.tags_list_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.extract_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.deprotect_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.yelo_frame.pack(padx=4, pady=2, expand=True, fill="x")

        self.extract_from_ce_resources_checkbutton.pack(padx=4, anchor='w')
        self.rename_duplicates_in_scnr_checkbutton.pack(padx=4, anchor='w')
        self.overwrite_checkbutton.pack(padx=4, anchor='w')
        self.show_output_checkbutton.pack(padx=4, anchor='w')

        self.fix_tag_classes_checkbutton.pack(padx=4, anchor='w')
        self.use_hashcaches_checkbutton.pack(padx=4, anchor='w')
        self.use_heuristics_checkbutton.pack(padx=4, anchor='w')
        self.fix_tag_index_offset_checkbutton.pack(padx=4, anchor='w')

        self.extract_cheape_checkbutton.pack(padx=4, anchor='w')

        self.tags_dir_entry.pack(
            padx=(4, 0), pady=2, side='left', expand=True, fill='x')
        self.tags_dir_browse_button.pack(padx=(0, 4), pady=2, side='left')
        self.data_dir_entry.pack(
            padx=(4, 0), pady=2, side='left', expand=True, fill='x')
        self.data_dir_browse_button.pack(padx=(0, 4), pady=2, side='left')
        self.tags_list_entry.pack(
            padx=(4, 0), pady=2, side='left', expand=True, fill='x')
        self.browse_tags_list_button.pack(padx=(0, 4), pady=2, side='left')

        # make the window not show up on the start bar
        self.transient(self.master)

    def destroy(self):
        try: self.master.settings_window = None
        except AttributeError: pass
        tk.Toplevel.destroy(self)

    def tags_dir_browse(self):
        dirpath = askdirectory(initialdir=self.tags_dir.get(), parent=self,
                               title="Select the tags extraction directory")

        if not dirpath:
            return

        dirpath = sanitize_path(dirpath)
        if not dirpath.endswith(PATHDIV):
            dirpath += PATHDIV

        self.tags_dir.set(dirpath)

    def data_dir_browse(self):
        dirpath = askdirectory(initialdir=self.data_dir.get(), parent=self,
                               title="Select the data extraction directory")

        if not dirpath:
            return

        dirpath = sanitize_path(dirpath)
        if not dirpath.endswith(PATHDIV):
            dirpath += PATHDIV

        self.data_dir.set(dirpath)

    def tags_list_browse(self):
        try:
            init_dir = dirname(self.tags_list_path.get())
        except Exception:
            init_dir = None
        dirpath = asksaveasfilename(
            initialdir=init_dir, parent=self,
            title="Select where to save the tag list log",
            filetypes=(("text log", "*.txt"), ("All", "*")))

        if not dirpath:
            return

        self.tags_list_path.set(sanitize_path(dirpath))


class RefineryActionsWindow(tk.Toplevel):
    app_root = None
    tk_vars = None
    renamable = True
    accept_rename = None
    accept_settings = None
    tag_index_ref = None

    rename_string = None
    recursive_rename = None

    def __init__(self, *args, **kwargs):
        title = kwargs.pop('title', None)
        self.renamable = kwargs.pop('renamable', self.renamable)
        self.tk_vars = tk_vars = kwargs.pop('tk_vars', {})
        self.tag_index_ref = kwargs.pop('tag_index_ref', self.tag_index_ref)
        tk.Toplevel.__init__(self, *args, **kwargs)
        self.bind('<Escape>', lambda e=None, s=self, *a, **kw: s.destroy())

        height = 270
        if self.tag_index_ref is not None:
            height += 25
        self.geometry("300x%s" % height)
        self.minsize(width=300, height=height)

        if self.app_root is None and hasattr(self.master, 'app_root'):
            self.app_root = self.master.app_root

        self.accept_rename   = tk_vars.get('accept_rename', tk.IntVar(self))
        self.accept_settings = tk_vars.get('accept_settings', tk.IntVar(self))
        self.rename_string   = tk_vars.get('rename_string', tk.StringVar(self))
        self.extract_to_dir  = tk_vars.get('out_dir', tk.StringVar(self))
        self.tags_list_path  = tk_vars.get('tags_list_path', tk.StringVar(self))
        self.extract_mode    = tk_vars.get('extract_mode', tk.StringVar(self))
        self.recursive_rename = tk.IntVar(self)
        self.resizable(1, 0)

        if title is None:
            title = self.rename_string.get()
            if not title:
                title = "Options"
        self.title(title)

        self.rename_string.set(splitext(self.rename_string.get())[0])

        self.accept_rename.set(0)
        self.accept_settings.set(0)

        # frames
        self.rename_frame     = tk.LabelFrame(self, text="Rename to")
        self.tags_list_frame  = tk.LabelFrame(
            self, text="Tags list log(erase to disable logging)")
        self.extract_to_frame = tk.LabelFrame(self, text="Directory to extract to")
        self.settings_frame   = tk.LabelFrame(self, text="Extract settings")

        self.button_frame = tk.Frame(self)
        self.accept_frame = tk.Frame(self.button_frame)
        self.cancel_frame = tk.Frame(self.button_frame)

        # rename
        self.rename_entry = tk.Entry(
            self.rename_frame, textvariable=self.rename_string)
        self.rename_button = tk.Button(
            self.rename_frame, text="Rename", command=self.rename, width=6)
        self.recursive_rename_checkbutton = tk.Checkbutton(
            self.rename_frame, text="Recursive", variable=self.recursive_rename)

        # tags list
        self.tags_list_entry = tk.Entry(
            self.tags_list_frame, textvariable=self.tags_list_path)
        self.browse_tags_list_button = tk.Button(
            self.tags_list_frame, text="Browse", command=self.tags_list_browse)

        # extract to dir
        self.extract_to_entry = tk.Entry(
            self.extract_to_frame, textvariable=self.extract_to_dir)
        self.browse_extract_to_button = tk.Button(
            self.extract_to_frame, text="Browse",
            command=self.extract_to_browse)

        # settings
        self.recursive_checkbutton = tk.Checkbutton(
            self.settings_frame, text="Recursive extraction",
            variable=tk_vars.get("recursive", tk.IntVar(self)))
        self.overwrite_checkbutton = tk.Checkbutton(
            self.settings_frame, text="Overwrite tags(not recommended)",
            variable=tk_vars.get("overwrite", tk.IntVar(self)))
        self.show_output_checkbutton = tk.Checkbutton(
            self.settings_frame, text="Print extracted tag names",
            variable=tk_vars.get("show_output", tk.IntVar(self)))

        # accept/cancel
        self.accept_button = tk.Button(
            self.accept_frame, text="Add to queue",
            command=self.add_to_queue, width=14)
        self.cancel_button = tk.Button(
            self.cancel_frame, text="Cancel",
            command=self.destroy, width=14)
        self.show_meta_button = tk.Button(
            self, text="Display metadata", command=self.show_meta)

        # pack everything
        # frames
        if self.renamable:
            self.rename_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.tags_list_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.extract_to_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.settings_frame.pack(padx=4, pady=2, expand=True, fill="x")

        self.button_frame.pack(pady=2, expand=True, fill="x")
        self.accept_frame.pack(padx=4, side='left',  fill='x', expand=True)
        self.cancel_frame.pack(padx=4, side='right', fill='x', expand=True)

        # rename
        self.rename_entry.pack(padx=4, side='left', fill='x', expand=True)
        self.rename_button.pack(padx=4, side='left', fill='x')
        #self.recursive_rename_checkbutton.pack(padx=4, side='left', fill='x')

        # extract to
        self.extract_to_entry.pack(padx=4, side='left', fill='x', expand=True)
        self.browse_extract_to_button.pack(padx=4, side='left', fill='x')

        # tags list
        self.tags_list_entry.pack(padx=4, side='left', fill='x', expand=True)
        self.browse_tags_list_button.pack(padx=4, side='left', fill='x')

        # settings
        # WONT DO ANYTHING YET
        #self.recursive_checkbutton.pack(padx=4, anchor='w')
        self.overwrite_checkbutton.pack(padx=4, anchor='w')
        self.show_output_checkbutton.pack(padx=4, anchor='w')

        # accept/cancel
        self.accept_button.pack(side='right')
        self.cancel_button.pack(side='left')
        if self.tag_index_ref is not None:
            self.show_meta_button.pack(padx=4, pady=4, expand=True, fill='x')

        # make the window not show up on the start bar
        self.transient(self.master)
        self.grab_set()

        try:
            self.update()
            self.app_root.place_window_relative(self)
            # I would use focus_set, but it doesn't seem to always work
            self.accept_button.focus_force()
        except AttributeError:
            pass

    def add_to_queue(self, e=None):
        self.accept_settings.set(1)
        self.destroy()

    def rename(self, e=None):
        new_name = self.rename_string.get()
        new_name = sanitize_path(new_name).lower().strip(PATHDIV).strip('.')
        if self.tag_index_ref is not None:
            new_name.rstrip(PATHDIV)
        elif new_name and not new_name.endswith(PATHDIV):
            # directory of tags
            new_name += PATHDIV

        self.rename_string.set(new_name)
        new_name = splitext(new_name)[0]
        str_len = len(new_name)
        if str_len > MAX_NAME_LEN:
            messagebox.showerror(
                "Max name length exceeded",
                ("The max length for a tag is limited to %s characters\n" +
                 "Remove %s characters(excluding extension).") %
                (MAX_NAME_LEN, str_len - MAX_NAME_LEN), parent=self)
            return
        elif is_protected_tag(new_name):
            messagebox.showerror(
                "Invalid name",
                "The entered string is not a valid filename.", parent=self)
            return
        elif not str_len and self.tag_index_ref is not None:
            messagebox.showerror(
                "Invalid name",
                "The entered string cannot be empty.", parent=self)
            return
        self.accept_rename.set(1)
        self.destroy()

    def tags_list_browse(self):
        try:
            init_dir = dirname(self.tags_list_path.get())
        except Exception:
            init_dir = None
        dirpath = asksaveasfilename(
            initialdir=init_dir, parent=self,
            title="Select where to save the tag list log",
            filetypes=(("text log", "*.txt"), ("All", "*")))

        if not dirpath:
            return

        self.tags_list_path.set(sanitize_path(dirpath))

    def extract_to_browse(self):
        dirpath = askdirectory(
            initialdir=self.extract_to_dir.get(), parent=self,
            title="Select the directory to extract tags to")

        if not dirpath:
            return

        self.extract_to_dir.set(sanitize_path(dirpath))

    def show_meta(self):
        index_ref = self.tag_index_ref
        if not index_ref:
            return

        try:
            # make sure it's re-extracted
            meta = self.app_root.active_map.get_meta(
                index_ref.id.tag_table_index, True)
            if meta is None:
                print("Could not get meta.")
                return

            meta_tag = meta_tag_def.build()
            meta_tag.data.tagdata = meta
            tag_path = index_ref.tag.tag_path
            if index_ref.class_1.enum_name not in BAD_CLASSES:
                ext = ".%s" % index_ref.class_1.enum_name
            else:
                ext = ".INVALID"

            w = MetaWindow(self.app_root, meta_tag, tag_path=tag_path + ext)
            self.destroy()
            w.focus_set()
        except Exception:
            print(format_exc())
            return


class RefineryRenameWindow(tk.Toplevel):

    def __init__(self, *args, **kwargs):
        tk.Toplevel.__init__(self, *args, **kwargs)

        self.geometry("300x80")
        self.title("Rename map")
        self.resizable(0, 0)

        self.rename_string = tk.StringVar(self)
        self.rename_string.set(self.master.map_header.map_name)

        # frames
        self.rename_frame = tk.LabelFrame(self, text="Rename to")

        self.button_frame = tk.Frame(self)
        self.button_frame_l = tk.Frame(self.button_frame)
        self.button_frame_r = tk.Frame(self.button_frame)

        # rename
        self.rename_entry = tk.Entry(
            self.rename_frame, textvariable=self.rename_string)

        # accept/cancel
        self.rename_button = tk.Button(
            self.button_frame_l, text="Rename", command=self.rename, width=10)
        self.cancel_button = tk.Button(
            self.button_frame_r, text="Cancel", command=self.destroy, width=10)

        # pack everything
        self.rename_frame.pack(padx=4, expand=True, fill="x", pady=2)
        self.button_frame.pack(pady=2, expand=True, fill="x")

        self.button_frame_l.pack(padx=4, side='left',  fill='x', expand=True)
        self.button_frame_r.pack(padx=4, side='right', fill='x', expand=True)

        self.rename_entry.pack(padx=4, side='left', fill='x', expand=True)
        self.rename_button.pack(side='right')
        self.cancel_button.pack(side='left')

        # make the window not show up on the start bar
        self.transient(self.master)

    def destroy(self):
        try: self.master.rename_window = None
        except AttributeError: pass
        tk.Toplevel.destroy(self)

    def rename(self, e=None):
        MAX_LEN = 31
        new_name = self.rename_string.get()
        self.rename_string.set(new_name)
        if len(new_name) > MAX_LEN:
            messagebox.showerror(
                "Max name length exceeded",
                "The max length for a map is limited to %s characters.\n" %
                MAX_LEN, parent=self)
        elif is_protected_tag(new_name) or "/" in new_name or "\\" in new_name:
            messagebox.showerror(
                "Invalid name",
                "The entered string is not a valid map name.", parent=self)
        elif not new_name:
            messagebox.showerror(
                "Invalid name",
                "The entered string cannot be empty.", parent=self)
        else:
            self.master.map_header.map_name = new_name
            self.master.display_map_info()
            self.destroy()


class RefineryEditActionsWindow(RefineryActionsWindow):

    def __init__(self, *args, **kwargs):
        RefineryActionsWindow.__init__(self, *args, **kwargs)
        self.rename_frame.pack_forget()
        self.button_frame.pack_forget()

        self.geometry("300x200")
        self.minsize(width=300, height=200)
        self.title("Edit: %s" % self.title())
