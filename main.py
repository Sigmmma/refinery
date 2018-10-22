print_startup = True  # __name__ == "__main__"
if print_startup:
    print("Refinery is warming up...")

import mmap
import gc
import tkinter as tk
import os
import zlib
import refinery

from os.path import dirname, basename, exists, join, isfile, splitext
from struct import unpack
from time import time
from tkinter.font import Font
from tkinter import messagebox
from tkinter.filedialog import askopenfilename, askopenfilenames,\
     asksaveasfilename
from traceback import format_exc
     

if print_startup:
    print("    Importing supyr_struct modules")

from supyr_struct.buffer import BytearrayBuffer, PeekableMmap
from supyr_struct.defs.constants import *
from supyr_struct.field_types import FieldType


if print_startup:
    print("    Importing refinery modules")


from refinery.util import *
from refinery.widgets import QueueTree,\
     RefinerySettingsWindow, RefineryRenameWindow,\
     ExplorerHierarchyTree, ExplorerClassTree, ExplorerHybridTree
from refinery.defs.config_def import config_def

if print_startup:
    print("    Loading map definitions")

from reclaimer.data_extraction import h1_data_extractors, h2_data_extractors
from reclaimer.meta.objs.halo1_map import Halo1Map
from reclaimer.meta.objs.halo1_rsrc_map import Halo1RsrcMap
from reclaimer.meta.objs.halo2_map import Halo2Map
from reclaimer.meta.objs.stubbs_map import StubbsMap
from reclaimer.meta.objs.shadowrun_map import ShadowrunMap
from reclaimer.meta.halo_map import get_map_header, get_map_version,\
     get_tag_index
from reclaimer.meta.class_repair import class_repair_functions,\
     get_tagc_refs
from reclaimer.meta.rawdata_ref_editing import rawdata_ref_move_functions
from reclaimer.meta.halo1_map_fast_functions import class_bytes_by_fcc

from refinery import crc_functions
from refinery.widgets import QueueTree, RefinerySettingsWindow,\
     RefineryRenameWindow, RefineryChecksumEditorWindow,\
     ExplorerHierarchyTree, ExplorerClassTree, ExplorerHybridTree
from refinery.recursive_rename.tag_path_handler import TagPathHandler
from refinery.recursive_rename.functions import recursive_rename


if print_startup:
    print("    Initializing Refinery")


curr_dir = get_cwd(__file__)
default_config_path = join(curr_dir, 'refinery.cfg')

VALID_DISPLAY_MODES = frozenset(("hierarchy", "class", "hybrid"))
VALID_EXTRACT_MODES = frozenset(("tags", "data"))


def expand_halomap(halo_map, raw_data_expansion=0, meta_data_expansion=0,
                   vertex_data_expansion=0, triangle_data_expansion=0):
    map_file   = halo_map.map_data
    map_header = halo_map.map_header
    tag_index  = halo_map.tag_index
    tag_index_array = tag_index.tag_index
    index_header_offset = map_header.tag_index_header_offset

    raw_data_end    = tag_index.model_data_offset
    vertex_data_end = tag_index.vertex_data_size + raw_data_end
    index_data_end  = tag_index.model_data_size  + raw_data_end
    tag_index.tag_index = tag_index_array

    # seek to the end so we can measure the map
    map_file.seek(0, 2)
    expansions = ((raw_data_end,    raw_data_expansion),
                  (vertex_data_end, vertex_data_expansion),
                  (index_data_end,  triangle_data_expansion),
                  (map_file.tell(), meta_data_expansion))

    # expand the map's sections
    map_end = inject_file_padding(map_file, *expansions)
    diffs_by_offsets, diff = dict(expansions), 0
    for off in sorted(diffs_by_offsets):
        diff += diffs_by_offsets[off]
        diffs_by_offsets[off] = diff

    meta_ptr_diff = diff - meta_data_expansion

    # update the map_header and tag_index_header's offsets and sizes
    tag_index.model_data_offset   += raw_data_expansion
    tag_index.vertex_data_size    += vertex_data_expansion
    tag_index.model_data_size     += (vertex_data_expansion +
                                      triangle_data_expansion)
    halo_map.map_magic                 -= meta_ptr_diff
    map_header.tag_index_header_offset += meta_ptr_diff
    map_header.tag_index_meta_len = map_end - map_header.tag_index_header_offset

    # adjust rawdata pointers in various tags if the index header moved
    if meta_ptr_diff:
        for ref in tag_index_array:
            func = rawdata_ref_move_functions.get(fourcc(ref.class_1.data))
            if func is None or ref.indexed:
                continue
            func(ref.id.tag_table_index, tag_index_array, map_file,
                 halo_map.map_magic, halo_map.engine, diffs_by_offsets)

    map_file.flush()
    return map_end


class Refinery(tk.Tk):
    tk_active_map_name = None
    tk_map_path = None
    tk_tags_dir = None
    tk_data_dir = None
    last_dir = curr_dir

    config_path = default_config_path
    config_file = None

    config_version = 2
    version = (1, 9, 0)

    data_extract_window = None
    settings_window     = None
    rename_window       = None
    checksum_window     = None

    tk_vars = None
    tree_frames = None
    hierarchy_tree = None
    hybrid_tree    = None
    class_tree     = None

    _running = False
    _initialized = False
    _display_mode = "hierarchy"
    stop_processing = False

    # dictionary of all loaded maps by their names
    maps = None

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        try:
            try:
                self.iconbitmap(join(curr_dir, 'refinery.ico'))
            except Exception:
                self.iconbitmap(join(curr_dir, 'icons', 'refinery.ico'))
        except Exception:
            print("Could not load window icon.")

        self.title("Refinery v%s.%s.%s" % self.version)
        self.minsize(width=500, height=300)

        self.maps = {}

        # make the tkinter variables
        self.tk_map_path = tk.StringVar(self)
        self.tk_active_map_name = tk.StringVar(self)
        self.tk_tags_dir = tk.StringVar(
            self, join(curr_dir, "tags", ""))
        self.tk_data_dir = tk.StringVar(
            self, join(curr_dir, "data", ""))
        self.tags_list_path = tk.StringVar(
            self, join(curr_dir, "tags", "tagslist.txt"))
        self.extract_mode = tk.StringVar(self, "tags")
        self.fix_tag_classes = tk.IntVar(self, 1)
        self.fix_tag_index_offset = tk.IntVar(self)
        self.use_hashcaches = tk.IntVar(self)
        self.use_heuristics = tk.IntVar(self)
        self.valid_tag_paths_are_accurate = tk.IntVar(self, 1)
        self.scrape_tag_paths_from_scripts = tk.IntVar(self, 1)
        self.limit_tag_path_lengths = tk.IntVar(self, 1)
        self.extract_cheape = tk.IntVar(self)
        self.show_all_fields = tk.IntVar(self)
        self.extract_from_ce_resources = tk.IntVar(self, 1)
        self.rename_duplicates_in_scnr = tk.IntVar(self)
        self.overwrite = tk.IntVar(self)
        self.recursive = tk.IntVar(self)
        self.autoload_resources = tk.IntVar(self, 1)
        self.show_output  = tk.IntVar(self, 1)
        self.decode_adpcm = tk.IntVar(self, 1)
        self.generate_comp_verts = tk.IntVar(self, 0)
        self.generate_uncomp_verts = tk.IntVar(self, 1)

        self.tk_vars = dict(
            fix_tag_classes=self.fix_tag_classes,
            fix_tag_index_offset=self.fix_tag_index_offset,
            use_hashcaches=self.use_hashcaches,
            use_heuristics=self.use_heuristics,
            valid_tag_paths_are_accurate=self.valid_tag_paths_are_accurate,
            scrape_tag_paths_from_scripts=self.scrape_tag_paths_from_scripts,
            limit_tag_path_lengths=self.limit_tag_path_lengths,
            rename_duplicates_in_scnr=self.rename_duplicates_in_scnr,
            extract_from_ce_resources=self.extract_from_ce_resources,
            overwrite=self.overwrite,
            extract_cheape=self.extract_cheape,
            show_all_fields=self.show_all_fields,
            recursive=self.recursive,
            autoload_resources=self.autoload_resources,
            show_output=self.show_output,
            tags_dir=self.tk_tags_dir,
            data_dir=self.tk_data_dir,
            tags_list_path=self.tags_list_path,
            extract_mode=self.extract_mode,
            decode_adpcm=self.decode_adpcm,
            generate_comp_verts=self.generate_comp_verts,
            generate_uncomp_verts=self.generate_uncomp_verts,
            )

        if self.config_file is not None:
            pass
        elif exists(self.config_path):
            # load the config file
            try:
                self.load_config()
            except Exception:
                self.make_config()
        else:
            # make a config file
            self.make_config()

        # menubar
        self.menubar = tk.Menu(self)
        self.file_menu = tk.Menu(self.menubar, tearoff=False)
        self.edit_menu = tk.Menu(self.menubar, tearoff=False)
        self.file_menu.add_command(
            label="Load maps", command=self.browse_for_maps)
        self.file_menu.add_command(
            label="Load all resource maps", command=self.load_resource_maps)
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Unload active map",
            command=lambda s=self: s.unload_maps_clicked(None))
        self.file_menu.add_command(
            label="Unload all maps",
            command=lambda s=self: s.unload_maps_clicked(False, None))
        self.file_menu.add_command(
            label="Unload resource maps",
            command=lambda s=self: s.unload_maps_clicked(True, None))
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Save map as", command=self.save_map_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.destroy)

        self.edit_menu.add_command(
            label="Rename map", command=self.show_rename)
        self.edit_menu.add_command(
            label="Change map checksum", command=self.show_checksum_edit)

        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.menubar.add_command(label="Settings", command=self.show_settings)
        self.menubar.add_command(
            label="Switch explorer mode", command=self.toggle_display_mode)
        self.menubar.add_command(
            label="Switch extract mode", command=self.toggle_extract_mode)
        self.config(menu=self.menubar)

        # fonts
        self.fixed_font = Font(family="Courier", size=8)
        self.container_title_font = Font(
            family="Courier", size=10, weight='bold')
        self.comment_font = Font(family="Courier", size=9)

        # make the window pane
        self.panes = tk.PanedWindow(self, sashwidth=6,
                                    sashpad=2, sashrelief="raised")

        # make the frames
        self.map_info_frame   = tk.LabelFrame(self, text="Map info")
        self.map_action_frame = tk.LabelFrame(self, text="Actions")

        self.explorer_frame = tk.LabelFrame(self.panes, text="Map contents")
        self.add_del_frame = tk.Frame(self.explorer_frame)
        self.queue_frame = tk.LabelFrame(self.panes, text="Extraction queue")

        self.queue_tree = QueueTree(self.queue_frame, app_root=self)
        self.hierarchy_tree = ExplorerHierarchyTree(
            self.explorer_frame, app_root=self, queue_tree=self.queue_tree)
        self.hybrid_tree = ExplorerHybridTree(
            self.explorer_frame, app_root=self, queue_tree=self.queue_tree)
        self.class_tree = ExplorerClassTree(
            self.explorer_frame, app_root=self, queue_tree=self.queue_tree)

        self.tree_frames = dict(
            hierarchy_tree=self.hierarchy_tree,
            hybrid_tree=self.hybrid_tree,
            class_tree=self.class_tree)

        # give these each reference to each other so they
        # can update each other when one has things renamed
        for tree_frame in self.tree_frames.values():
            tree_frame.sibling_tree_frames = self.tree_frames

        self.panes.add(self.explorer_frame)
        self.panes.add(self.queue_frame)

        # make the entries
        self.fixed_font = Font(family="Courier", size=8)
        self.map_info_text = tk.Text(self.map_info_frame, font=self.fixed_font,
                                     state='disabled', height=8)
        self.map_info_scrollbar = tk.Scrollbar(self.map_info_frame)
        self.map_info_text.config(yscrollcommand=self.map_info_scrollbar.set)
        self.map_info_scrollbar.config(command=self.map_info_text.yview)

        # make the buttons
        self.deprotect_button = tk.Button(
            self.map_action_frame, text="Run deprotection",
            command=self.deprotect)
        self.begin_button = tk.Button(
            self.map_action_frame, text="Run extraction",
            command=self.start_extraction)
        self.cancel_button = tk.Button(
            self.map_action_frame, text="Cancel",
            command=self.cancel_action)


        self.add_button = tk.Button(
            self.add_del_frame, text="Add", width=4,
            command=self.add_pressed)
        self.del_button = tk.Button(
            self.add_del_frame, text="Del", width=4,
            command=self.queue_tree.remove_curr_selection)
        self.add_all_button = tk.Button(
            self.add_del_frame, text="Add\nMap", width=4,
            command=self.queue_add_all)
        self.del_all_button = tk.Button(
            self.add_del_frame, text="Del\nAll", width=4,
            command=self.queue_del_all)

        # pack everything
        self.rebuild_map_select_menu()
        self.cancel_button.pack(side='right', padx=4, pady=4)
        self.begin_button.pack(side='right', padx=4, pady=4)
        self.deprotect_button.pack(side='right', padx=4, pady=4)

        self.map_info_scrollbar.pack(fill='y', side='right', padx=1)
        self.map_info_text.pack(fill='x', side='right', expand=True, padx=1)

        self.add_button.pack(side='top', padx=2, pady=4)
        self.del_button.pack(side='top', padx=2, pady=(0, 20))
        self.add_all_button.pack(side='top', padx=2, pady=(20, 0))
        self.del_all_button.pack(side='top', padx=2, pady=4)

        self.explorer_frame.pack(fill='both', padx=1, expand=True)
        self.add_del_frame.pack(fill='y', side='right', anchor='center')
        self.queue_tree.pack(fill='both', side='right', expand=True)
        self.queue_frame.pack(fill='both', padx=1, expand=True)

        self.panes.pack(fill='both', expand=True, padx=1)
        self.map_action_frame.pack(fill='x', padx=2)
        self.map_info_frame.pack(fill='x', padx=2)

        self.panes.paneconfig(self.explorer_frame, sticky='nsew')
        self.panes.paneconfig(self.queue_frame, sticky='nsew')

        self.set_display_mode()
        self.set_extract_mode()

        self._initialized = True

    @property
    def map_loaded(self):
        return self.active_map is not None

    @property
    def running(self):
        return self._running

    @property
    def tags_dir(self):
        return self.tk_tags_dir.get()

    @property
    def active_map(self):
        return self.maps.get("active")

    def load_config(self, filepath=None):
        if filepath is None:
            filepath = self.config_path
        assert exists(filepath)

        # load the config file
        self.config_file = config_def.build(filepath=filepath)
        if self.config_file.data.header.version != self.config_version:
            raise ValueError(
                "Config version is not what this application is expecting.")

        self.apply_config()

    def make_config(self, filepath=None):
        if filepath is None:
            filepath = self.config_path

        # create the config file from scratch
        self.config_file = config_def.build()
        self.config_file.filepath = filepath

        self.update_config()

    def apply_config(self):
        if self.config_file is None:
            return

        header     = self.config_file.data.header
        app_window = self.config_file.data.app_window
        paths      = self.config_file.data.paths

        self.geometry("%sx%s+%s+%s" % tuple(app_window[:4]))

        self.tags_list_path.set(paths.tags_list.path)
        self.tk_tags_dir.set(paths.tags_dir.path)
        self.tk_data_dir.set(paths.data_dir.path)
        self.last_dir = paths.last_dir.path

        flags = header.flags
        self._display_mode = flags.display_mode.enum_name
        for attr_name in ("show_output", "autoload_resources"):
            getattr(self, attr_name).set(bool(getattr(flags, attr_name)))

        flags = header.extraction_flags
        for attr_name in ("extract_cheape", "overwrite",
                          "extract_from_ce_resources", "recursive",
                          "rename_duplicates_in_scnr", "decode_adpcm",
                          "generate_uncomp_verts", "generate_comp_verts",
                          "show_all_fields",):
            getattr(self, attr_name).set(bool(getattr(flags, attr_name)))

        flags = header.deprotection_flags
        for attr_name in ("fix_tag_classes", "fix_tag_index_offset",
                          "use_hashcaches", "use_heuristics",
                          "valid_tag_paths_are_accurate",
                          "scrape_tag_paths_from_scripts",
                          "limit_tag_path_lengths"):
            getattr(self, attr_name).set(bool(getattr(flags, attr_name)))

    def update_config(self, config_file=None):
        if config_file is None:
            config_file = self.config_file
        config_data = config_file.data

        header     = config_data.header
        paths      = config_data.paths
        app_window = config_data.app_window

        header.version = self.config_version

        if self._initialized:
            app_window.app_width    = self.winfo_width()
            app_window.app_height   = self.winfo_height()
            app_window.app_offset_x = self.winfo_x()
            app_window.app_offset_y = self.winfo_y()

        # make sure there are enough entries in the paths
        if len(paths.NAME_MAP) > len(paths):
            paths.extend(len(paths.NAME_MAP) - len(paths))

        paths.tags_list.path = self.tags_list_path.get()
        paths.tags_dir.path  = self.tk_tags_dir.get()
        paths.data_dir.path  = self.tk_data_dir.get()
        paths.last_dir.path  = self.last_dir
        
        flags = header.flags
        flags.display_mode.set_to(self._display_mode)
        for attr_name in ("show_output", "autoload_resources"):
            setattr(flags, attr_name, getattr(self, attr_name).get())

        flags = header.extraction_flags
        for attr_name in ("extract_cheape", "overwrite",
                          "extract_from_ce_resources", "recursive",
                          "rename_duplicates_in_scnr", "decode_adpcm",
                          "generate_uncomp_verts", "generate_comp_verts",
                          "show_all_fields",):
            setattr(flags, attr_name, getattr(self, attr_name).get())

        flags = header.deprotection_flags
        for attr_name in ("fix_tag_classes", "fix_tag_index_offset",
                          "use_hashcaches", "use_heuristics",
                          "valid_tag_paths_are_accurate",
                          "scrape_tag_paths_from_scripts",
                          "limit_tag_path_lengths"):
            setattr(flags, attr_name, getattr(self, attr_name).get())

    def save_config(self, e=None):
        try:
            self.config_file.data.header.parse(attr_index="date_modified")
        except Exception:
            print(format_exc())
        self.config_file.serialize(temp=0, backup=0, calc_pointers=0)
        self.apply_config()

    def place_window_relative(self, window, x=None, y=None):
        # calculate x and y coordinates for this window
        x_base, y_base = self.winfo_x(), self.winfo_y()
        w, h = window.geometry().split('+')[0].split('x')[:2]
        if w == h and w == '1':
            w = window.winfo_reqwidth()
            h = window.winfo_reqheight()
        if x is None:
            x = self.winfo_width()//2 - int(w)//2
        if y is None:
            y = self.winfo_height()//2 - int(h)//2
        window.geometry(
            '%sx%s+%s+%s' % (w, h, x+x_base, y+y_base))

    def toggle_display_mode(self, e=None):
        if self._display_mode == "hierarchy":
            self.set_display_mode("class")
        elif self._display_mode == "class":
            self.set_display_mode("hybrid")
        elif self._display_mode == "hybrid":
            self.set_display_mode("hierarchy")
        else:
            self.set_display_mode("hierarchy")

    def set_display_mode(self, new_mode=None):
        if new_mode is None:
            new_mode = self._display_mode
            if new_mode not in VALID_DISPLAY_MODES:
                new_mode = "hierarchy"

        if new_mode not in VALID_DISPLAY_MODES:
            return
        elif new_mode == "hierarchy":
            next_mode = "class"
        elif new_mode == "class":
            next_mode = "hybrid"
        else:
            next_mode = "hierarchy"

        for mode in VALID_DISPLAY_MODES:
            tree = self.tree_frames[mode + "_tree"]
            if tree.active_map is None:
                tree.reload(self.active_map)
            if mode == new_mode: continue
            tree.pack_forget()

        tree = self.tree_frames[new_mode + "_tree"]
        tree.pack(side='right', fill='both', expand=True)
        self.menubar.entryconfig(4, label="Switch to %s view" % next_mode)

        self._display_mode = new_mode

    def toggle_extract_mode(self, e=None):
        mode = self.extract_mode.get()
        if mode == "tags":
            self.set_extract_mode("data")
        elif mode == "data":
            self.set_extract_mode("tags")
        else:
            self.set_extract_mode("tags")

    def set_extract_mode(self, new_mode=None):
        if new_mode is None:
            new_mode = self.extract_mode.get()
            if new_mode not in VALID_EXTRACT_MODES:
                new_mode = "tags"

        if new_mode not in VALID_EXTRACT_MODES:
            return
        elif new_mode == "tags" or not self.map_loaded:
            next_mode = "data"
            valid_classes = None
        else:
            next_mode = "tags"
            engine = self.active_map.engine
            if   ("halo1" in engine or "stubbs" in engine or
                  "shadowrun" in engine):
                valid_classes = h1_data_extractors.keys()
            elif "halo2" in engine:
                valid_classes = h2_data_extractors.keys()
            else:
                return

        self.menubar.entryconfig(5, label="Switch to %s extraction" % next_mode)

        self.extract_mode.set(new_mode)

        for tree in self.tree_frames.values():
            tree.active_map = None
            tree.valid_classes = valid_classes
            tree.reload()

        curr_tree = self.tree_frames.get(self._display_mode + "_tree")
        if curr_tree is not None:
            curr_tree.reload(self.active_map)

    def show_settings(self, e=None):
        if self.settings_window is not None or self.running:
            return

        self.settings_window = RefinerySettingsWindow(
            self, settings=self.tk_vars)
        # make sure the window gets a chance to set its size
        self.settings_window.update()
        self.place_window_relative(self.settings_window)

    def show_rename(self, e=None):
        if self.rename_window is not None or not self.map_loaded:
            return
        elif self.running:
            return
        elif self.active_map.is_resource:
            return

        self.rename_window = RefineryRenameWindow(
            self, active_map=self.active_map)
        # make sure the window gets a chance to set its size
        self.rename_window.update()
        self.place_window_relative(self.rename_window)

    def show_checksum_edit(self, e=None):
        if self.checksum_window is not None or not self.map_loaded:
            return
        elif self.running:
            return
        elif self.active_map.is_resource:
            return

        self.checksum_window = RefineryChecksumEditorWindow(
            self, active_map=self.active_map)
        # make sure the window gets a chance to set its size
        self.checksum_window.update()
        self.place_window_relative(self.checksum_window)

    def destroy(self, e=None):
        self._running = False
        self.unload_maps(None, None)
        FieldType.force_normal()
        try:
            self.update_config()
            self.save_config()
        except Exception:
            print(format_exc())

        tk.Tk.destroy(self)

        # I really didn't want to have to call this, but for some
        # reason the program wants to hang and not exit nicely.
        # I've decided to use os._exit until I can figure out the cause.
        os._exit(0)
        #sys.exit(0)

    def add_pressed(self, e=None):
        if not self.map_loaded:
            return

        if self._display_mode == "hierarchy":
            self.hierarchy_tree.activate_item()
        elif self._display_mode == "class":
            self.class_tree.activate_item()
        elif self._display_mode == "hybrid":
            self.hybrid_tree.activate_item()

    def queue_add_all(self, e=None):
        if not self.map_loaded:
            return

        if self._display_mode == "hierarchy":
            tree_frame = self.hierarchy_tree
        elif self._display_mode == "class":
            tree_frame = self.class_tree
        elif self._display_mode == "hybrid":
            tree_frame = self.hybrid_tree
        else:
            return

        tree_frame.activate_all()

    def queue_del_all(self, e=None):
        if not self.map_loaded:
            return

        ans = messagebox.askyesno(
            "Clearing queue", "Are you sure you want to clear\n" +
            "the entire extraction queue?", icon='warning', parent=self)

        if not ans:
            return True

        self.queue_tree.remove_items()

    def set_active_map(self, e=None):
        map_name = self.tk_active_map_name.get()
        if map_name in self.maps:
            curr_map = self.active_map
            next_map = self.maps[map_name]
            if curr_map is next_map:
                return
            elif curr_map is not None and curr_map not in self.maps.values():
                curr_map.unload(False)

            self.tk_map_path.set(next_map.filepath)
            self.maps["active"] = next_map
            self.display_map_info()
            self.reload_explorers()
        else:
            print('"%s" is not loaded.' % map_name)

    def unload_maps_clicked(self, map_type=False, maps_to_unload=("active", )):
        if self._running:
            return
        self._running = True

        try:
            self.unload_maps(map_type, maps_to_unload)
        except Exception:
            print(format_exc())
        self._running = False

    def unload_maps(self, map_type=False, maps_to_unload=("active", )):
        if maps_to_unload is None:
            maps_to_unload = tuple(self.maps.keys())

        active_map = self.active_map
        for map_name in maps_to_unload:
            try:
                curr_map = self.maps[map_name]
                if map_type is None or map_type == curr_map.is_resource:
                    self.maps[map_name].unload_map(False)
                    if curr_map is active_map:
                        self.tk_active_map_name.set("")
            except Exception:
                pass

        self.rebuild_map_select_menu()
        if self.map_loaded: return

        self.stop_processing = True

        self.display_map_info()
        for tree in self.tree_frames.values():
            tree.reload()
        self.queue_tree.reload()
        self.set_extract_mode("tags")

    def load_resource_maps(self, halo_map=None):
        if halo_map is None:
            halo_map = self.active_map
        if halo_map is None:
            return
        elif self.running:
            return

        self._running = True
        try:
            print("Loading resource maps for: %s" % halo_map.map_header.map_name)
            self.update()
            halo_map.load_all_resource_maps()
            self.rebuild_map_select_menu()
            print("    Finished")
        except Exception:
            print(format_exc())

        self._running = False

    def load_map(self, map_path, will_be_active=True):
        self.load_maps((map_path, ), will_be_active=will_be_active)

    def load_maps(self, map_paths, will_be_active=True, ask_close_open=False):
        if not map_paths:
            return

        new_active_map = ''
        for map_path in map_paths:
            try:
                if map_path is None:
                    continue

                print("Loading %s..." % basename(map_path))
                if not exists(map_path):
                    print("    Map does not exist")
                    continue

                with open(map_path, 'r+b') as f:
                    comp_data  = PeekableMmap(f.fileno(), 0)
                    head_sig   = unpack("<I", comp_data.peek(4))[0]
                    map_header = get_map_header(comp_data, True)
                    engine     = get_map_version(map_header)
                    comp_data.close()

                if map_header is None:
                    map_name = {1:"bitmaps", 2:"sounds", 3:"loc"}.get(head_sig)
                else:
                    map_name = map_header.map_name

                do_load = (self.maps.get(map_name) is None or
                           not ask_close_open)

                if not do_load:
                    do_load = messagebox.askyesno(
                        "A map with that name is already loaded!",
                        ('A map with the name "%s" is already loaded.\n'
                         "Close that map and load this one instead?") % map_name,
                        icon='warning', parent=self)

                if not do_load:
                    print("    Skipped")
                    continue
                
                if self.active_map is self.maps.get(map_name):
                    will_be_active = True
                    new_active_map = map_name

                if self.maps.get(map_name) is not None:
                    self.unload_maps(None, (map_name, ))

                if head_sig in (1, 2, 3):
                    new_map = Halo1RsrcMap(self.maps)
                elif map_header is None:
                    print("    Could not read map header.")
                    continue
                elif engine is None:
                    print("    Could not determine map version.")
                    continue
                elif "stubbs" in engine:
                    new_map = StubbsMap(self.maps)
                elif "shadowrun" in engine:
                    new_map = ShadowrunMap(self.maps)
                elif "halo1" in engine:
                    new_map = Halo1Map(self.maps)
                elif "halo2" in engine:
                    new_map = Halo2Map(self.maps)
                else:
                    print("    Cant let you do that.")
                    map_header.pprint(printout=True)
                    continue

                new_map.app = self
                new_map.load_map(map_path, will_be_active=will_be_active,
                                 autoload_resources=self.autoload_resources.get())
                if will_be_active and not new_active_map:
                    new_active_map = map_name
                    self.tk_active_map_name.set(map_name)
                print("    Finished")
            except Exception:
                try:
                    self.display_map_info(
                        "Could not load map.\nCheck console window for error.")
                    self.unload_maps()
                except Exception:
                    print(format_exc())
                print(format_exc())
                print("Error occurred while atempting to load map.\n"
                      "If this is a PermissionError and the map is located in\n"
                      "a protected location, Refinery may need to run as admin.\n"
                      "    Make sure the map you are accessing is not read-only.\n"
                      "Refinery opens maps in read-write mode in case edits are\n"
                      "made, and opening in this mode fails on read-only files.\n")

        self.rebuild_map_select_menu()
        if will_be_active and new_active_map:
            self.maps.pop("active", None)  # self.set_active_map must set this
            self.tk_active_map_name.set(new_active_map)
            self.set_active_map()

    def rebuild_map_select_menu(self):
        if getattr(self, "map_select_menu", None) is not None:
            self.map_select_menu.destroy()

        options = dict(self.maps)
        options.pop("active", None)
        if options:
            options = sorted(options.keys())
        else:
            options = ("Loaded maps", )

        self.map_select_menu = tk.OptionMenu(
            self.map_action_frame, self.tk_active_map_name, *options,
            command=self.set_active_map)
        self.map_select_menu.config(anchor="w")
        self.map_select_menu.pack(side='left', padx=(4, 100), pady=4,
                                  fill='x', expand=True)

    def display_map_info(self, string=None):
        try:
            self.map_info_text.config(state='normal')
            self.map_info_text.delete('1.0', 'end')
        finally:
            self.map_info_text.config(state='disabled')

        if string is None:
            if not self.map_loaded:
                return
            try:
                active_map = self.active_map
                string = "%s\n" % self.tk_map_path.get()

                header     = active_map.map_header
                index      = active_map.tag_index
                orig_index = active_map.orig_tag_index
                if hasattr(active_map.map_data, '__len__'):
                    decomp_size = str(len(active_map.map_data))
                elif (hasattr(active_map.map_data, 'seek') and
                      hasattr(active_map.map_data, 'tell')):
                    curr_pos = active_map.map_data.tell()
                    active_map.map_data.seek(0, 2)
                    decomp_size = str(active_map.map_data.tell())
                    active_map.map_data.seek(curr_pos)
                else:
                    decomp_size = "unknown"

                if not active_map.is_compressed:
                    decomp_size += "(uncompressed)"

                map_type = header.map_type.enum_name
                if active_map.is_resource: map_type = "resource cache"
                elif map_type == "sp":     map_type = "singleplayer"
                elif map_type == "mp":     map_type = "multiplayer"
                elif map_type == "ui":     map_type = "mainmenu"
                elif map_type == "shared":   map_type = "shared"
                elif map_type == "sharedsp": map_type = "shared single player"
                elif "INVALID" in map_type:  map_type = "unknown"

                string += ((
                    "Header:\n" +
                    "    engine version      == %s\n" +
                    "    name                == %s\n" +
                    "    build date          == %s\n" +
                    "    type                == %s\n" +
                    "    decompressed size   == %s\n" +
                    "    index header offset == %s\n") %
                (active_map.engine, header.map_name, header.build_date,
                 map_type, decomp_size, header.tag_index_header_offset))

                string += ((
                    "\nCalculated information:\n" +
                    "    index magic    == %s\n" +
                    "    map magic      == %s\n") %
                (active_map.index_magic, active_map.map_magic))

                tag_index_offset = index.tag_index_offset
                if active_map.engine == "halo2alpha":
                    string += ((
                        "\nTag index:\n" +
                        "    tag count           == %s\n" +
                        "    scenario tag id     == %s\n" +
                        "    index array pointer == %s\n") %
                    (orig_index.tag_count,
                     orig_index.scenario_tag_id[0], tag_index_offset))
                elif "halo2" in active_map.engine:
                    used_tag_count = 0
                    local_tag_count = 0
                    for index_ref in index.tag_index:
                        if is_reserved_tag(index_ref):
                            continue
                        elif index_ref.meta_offset != 0:
                            local_tag_count += 1
                        used_tag_count += 1

                    string += ((
                        "\nTag index:\n" +
                        "    tag count           == %s\n" +
                        "    used tag count      == %s\n" +
                        "    local tag count     == %s\n" +
                        "    tag types count     == %s\n" +
                        "    scenario tag id     == %s\n" +
                        "    globals  tag id     == %s\n" +
                        "    index array pointer == %s\n") %
                    (orig_index.tag_count, used_tag_count, local_tag_count,
                     orig_index.tag_types_count,
                     orig_index.scenario_tag_id[0],
                     orig_index.globals_tag_id[0], tag_index_offset))
                elif active_map.engine == "halo3":
                    string += ((
                        "\nTag index:\n" +
                        "    tag count           == %s\n" +
                        "    tag types count     == %s\n" +
                        "    root tags count     == %s\n" +
                        "    index array pointer == %s\n") %
                    (orig_index.tag_count, orig_index.tag_types_count,
                     orig_index.root_tags_count,
                     tag_index_offset - active_map.map_magic))
                else:
                    string += ((
                        "\nTag index:\n" +
                        "    tag count           == %s\n" +
                        "    scenario tag id     == %s\n" +
                        "    index array pointer == %s   non-magic == %s\n" +
                        "    model data pointer  == %s\n" +
                        "    meta data length    == %s\n" +
                        "    vertex parts count  == %s\n" +
                        "    index  parts count  == %s\n") %
                    (index.tag_count, index.scenario_tag_id[0],
                     tag_index_offset, tag_index_offset - active_map.map_magic,
                     index.model_data_offset, header.tag_index_meta_len,
                     index.vertex_parts_count, index.index_parts_count))

                    if index.SIZE == 36:
                        string += (
                            "    index parts pointer == %s   non-magic == %s\n"
                            % (index.index_parts_offset,
                               index.index_parts_offset - active_map.map_magic))
                    else:
                        string += ((
                            "    vertex data size    == %s\n" +
                            "    index  data size    == %s\n" +
                            "    model  data size    == %s\n") %
                        (index.vertex_data_size,
                         index.model_data_size - index.vertex_data_size,
                         index.model_data_size))

                if active_map.engine == "halo1yelo":
                    yelo    = header.yelo_header
                    flags   = yelo.flags
                    info    = yelo.build_info
                    version = yelo.tag_versioning
                    cheape  = yelo.cheape_definitions
                    rsrc    = yelo.resources
                    min_os  = info.minimum_os_build
                    string += ((
                        "\nYelo information:\n" +
                        "    Mod name              == %s\n" +
                        "    Memory upgrade amount == %sx\n" +
                        "\n    Flags:\n" +
                        "        uses memory upgrades       == %s\n" +
                        "        uses mod data files        == %s\n" +
                        "        is protected               == %s\n" +
                        "        uses game state upgrades   == %s\n" +
                        "        has compression parameters == %s\n" +
                        "\n    Build info:\n" +
                        "        build string  == %s\n" +
                        "        timestamp     == %s\n" +
                        "        stage         == %s\n" +
                        "        revision      == %s\n" +
                        "\n    Cheape:\n" +
                        "        build string      == %s\n" +
                        "        version           == %s.%s.%s\n" +
                        "        size              == %s\n" +
                        "        offset            == %s\n" +
                        "        decompressed size == %s\n" +
                        "\n    Versioning:\n" +
                        "        minimum open sauce     == %s.%s.%s\n" +
                        "        project yellow         == %s\n" +
                        "        project yellow globals == %s\n" +
                        "\n    Resources:\n" +
                        "        compression parameters header offset   == %s\n" +
                        "        tag symbol storage header offset       == %s\n" +
                        "        string id storage header offset        == %s\n" +
                        "        tag string to id storage header offset == %s\n"
                        ) %
                    (yelo.mod_name, yelo.memory_upgrade_multiplier,
                     bool(flags.uses_memory_upgrades),
                     bool(flags.uses_mod_data_files),
                     bool(flags.is_protected),
                     bool(flags.uses_game_state_upgrades),
                     bool(flags.has_compression_params),
                     info.build_string, info.timestamp, info.stage.enum_name,
                     info.revision, cheape.build_string,
                     info.cheape.maj, info.cheape.min, info.cheape.build,
                     cheape.size, cheape.offset, cheape.decompressed_size,
                     min_os.maj, min_os.min, min_os.build,
                     version.project_yellow, version.project_yellow_globals,
                     rsrc.compression_params_header_offset,
                     rsrc.tag_symbol_storage_header_offset,
                     rsrc.string_id_storage_header_offset,
                     rsrc.tag_string_to_id_storage_header_offset,
                    ))

                if active_map.bsp_magics:
                    string += "\nSbsp magic and headers:\n"

                for tag_id in active_map.bsp_magics:
                    header = active_map.bsp_headers.get(tag_id)
                    if header is None: continue

                    magic  = active_map.bsp_magics[tag_id]
                    string += ((
                        "    %s.structure_scenario_bsp\n" +
                        "        bsp base pointer               == %s\n" +
                        "        bsp magic                      == %s\n" +
                        "        bsp size                       == %s\n" +
                        "        bsp metadata pointer           == %s   non-magic == %s\n"
                        #"        uncompressed lightmaps count   == %s\n" +
                        #"        uncompressed lightmaps pointer == %s   non-magic == %s\n" +
                        #"        compressed   lightmaps count   == %s\n" +
                        #"        compressed   lightmaps pointer == %s   non-magic == %s\n"
                        ) %
                    (index.tag_index[tag_id].tag.tag_path,
                     active_map.bsp_header_offsets[tag_id],
                     magic, active_map.bsp_sizes[tag_id],
                     header.meta_pointer, header.meta_pointer - magic,
                     #header.uncompressed_lightmap_materials_count,
                     #header.uncompressed_lightmap_materials_pointer,
                     #header.uncompressed_lightmap_materials_pointer - magic,
                     #header.compressed_lightmap_materials_count,
                     #header.compressed_lightmap_materials_pointer,
                     #header.compressed_lightmap_materials_pointer - magic,
                     ))
            except Exception:
                string = ""
                print(format_exc())
        try:
            self.map_info_text.config(state='normal')
            self.map_info_text.insert('end', string)
        finally:
            self.map_info_text.config(state='disabled')

    def deprotect(self, e=None):
        if not self.map_loaded: return

        if self.running or self.active_map.is_resource:
            return
        elif "halo1" not in self.active_map.engine:
            return

        self._running = True
        try:
            self._deprotect()
        except Exception:
            print(format_exc())

        self._running = False

    def _deprotect(self):
        save_path = asksaveasfilename(
            initialdir=dirname(self.tk_map_path.get()), parent=self,
            title="Choose where to save the deprotected map",
            filetypes=(("Halo mapfile", "*.map"),
                       ("Halo mapfile(extra sauce)", "*.yelo"),
                       ("All", "*")))

        if not save_path:
            print("Deprotection cancelled.")
            return

        save_path, ext = splitext(save_path)
        save_path = sanitize_path(save_path + (ext if ext else (
            '.yelo' if 'yelo' in self.active_map.engine else '.map')))

        if not self.save_map(save_path, prompt_strings_expand=False):
            return

        start = time()
        self.stop_processing = False

        # get the active map AFTER saving because it WILL have changed
        active_map      = self.active_map
        map_data        = active_map.map_data
        map_header      = active_map.map_header
        tag_index       = active_map.tag_index
        tag_index_array = tag_index.tag_index
        engine      = active_map.engine
        index_magic = active_map.index_magic
        map_magic   = active_map.map_magic
        bsp_magics  = active_map.bsp_magics
        bsp_headers = active_map.bsp_headers
        bsp_header_offsets = active_map.bsp_header_offsets

        tag_path_handler = TagPathHandler(tag_index_array)

        if self.fix_tag_classes.get() and not("stubbs" in active_map.engine or
                                              "shadowrun" in active_map.engine):
            print("Repairing tag classes...")

            # locate the tags to start deprotecting with
            repair = {}
            for b in tag_index_array:
                if self.stop_processing:
                    print("    Deprotection stopped by user.")
                    return

                tag_id = b.id.tag_table_index
                if tag_id == tag_index.scenario_tag_id.tag_table_index:
                    tag_cls = "scnr"
                elif b.class_1.enum_name not in ("<INVALID>", "NONE"):
                    tag_cls = fourcc(b.class_1.data)
                else:
                    continue

                if tag_cls in ("scnr", "DeLa"):
                    repair[tag_id] = tag_cls
                elif tag_cls == "matg" and b.tag.tag_path == "globals\\globals":
                    repair[tag_id] = tag_cls
                else:
                    continue

            # scan the tags that need repairing and repair them
            repaired = {}
            tagc_i = 0
            while repair:
                # DEBUG
                # print("Repairing %s tags." % len(repair))

                next_repair = {}
                for tag_id in repair:
                    if tag_id in repaired:
                        continue
                    tag_cls = repair[tag_id]
                    if tag_cls not in class_bytes_by_fcc:
                        # unknown tag class
                        continue
                    repaired[tag_id] = tag_cls

                    if self.stop_processing:
                        print("    Deprotection stopped by user.")
                        return

                    # DEBUG
                    # print('    %s %s' % (tag_id, tag_cls))
                    if (tag_cls not in class_repair_functions or
                            tag_index_array[tag_id].indexed):
                        continue

                    if tag_cls == "sbsp":
                        class_repair_functions[tag_cls](
                            bsp_headers[tag_id].meta_pointer,
                            tag_index_array, map_data,
                            bsp_magics[tag_id] - bsp_header_offsets[tag_id],
                            next_repair, engine, map_magic)
                    else:
                        class_repair_functions[tag_cls](
                            tag_id, tag_index_array, map_data,
                            map_magic, next_repair, engine)

                    # replace meta with the deprotected one
                    if tag_cls == "matg":
                        active_map.matg_meta = active_map.get_meta(tag_id)
                    elif tag_cls == "scnr":
                        active_map.scnr_meta = active_map.get_meta(tag_id)

                # start repairing the newly accumulated tags
                repair = next_repair

                # exhausted tags to repair. try to repair tag colletions now
                if not repair:
                    for b in tag_index_array:
                        if self.stop_processing:
                            print("    Deprotection stopped by user.")
                            return

                        tag_id = b.id.tag_table_index
                        tag_cls = None
                        if tag_id in repaired:
                            continue
                        elif b.class_1.enum_name not in ("<INVALID>", "NONE"):
                            tag_cls = fourcc(b.class_1.data)
                        else:
                            _, reffed_tag_types = get_tagc_refs(
                                b.meta_offset, map_data, map_magic, repaired
                                )
                            if reffed_tag_types:
                                tag_cls = "tagc"

                        if tag_cls is None:
                            # couldn't determine tag class
                            continue

                        if tag_index_array[tag_id].indexed:
                            repaired[tag_id] = tag_cls
                        elif tag_cls in ("Soul", "tagc", "yelo", "gelo", "gelc"):
                            repair[tag_id] = tag_cls

            # try to locate the Soul tag out of all the tags thought to be tagc
            # and(attempt to) determine the names of each tag collection
            map_type = map_header.map_type.enum_name
            tagc_ids_reffed_in_other_tagc = set()
            for b in tag_index_array:
                tag_id = b.id.tag_table_index
                if repaired.get(tag_id) not in ("tagc", "Soul"):
                    continue

                if self.stop_processing:
                    print("    Deprotection stopped by user.")
                    return

                reffed_tag_ids, reffed_tag_types = get_tagc_refs(
                    b.meta_offset, map_data, map_magic, repaired
                    )
                reffed_tag_types = set(reffed_tag_types)
                if reffed_tag_types == set(["DeLa"]):
                    repaired[tag_id] = "Soul"
                    b.tag.tag_path = dict(
                        sp="ui\\shell\\solo",
                        mp="ui\\shell\\multiplayer",
                        ui="ui\\shell\\main_menu"
                        ).get(map_type, b.tag.tag_path)
                    tag_path_handler.set_priority(tag_id, float("inf"))
                elif reffed_tag_types == set(["devc"]):
                    if len(reffed_tag_ids) == 4:
                        b.tag.tag_path = "ui\\ui_default_profiles"
                        tag_path_handler.set_priority(tag_id, float("inf"))
                    elif len(reffed_tag_ids) == 19:
                        b.tag.tag_path = "ui\\ui_input_device_defaults"
                        tag_path_handler.set_priority(tag_id, float("inf"))

                if tag_id not in tagc_ids_reffed_in_other_tagc:
                    tagc_ids_reffed_in_other_tagc.update(reffed_tag_ids)


            for b in tag_index_array:
                if tagc_i >= 2: break

                tag_id = b.id.tag_table_index
                if (repaired.get(tag_id) != "tagc" or
                    tag_id in tagc_ids_reffed_in_other_tagc):
                    continue

                if self.stop_processing:
                    print("    Deprotection stopped by user.")
                    return

                if tagc_i == 0:
                    b.tag.tag_path = "ui\\ui_tags_loaded_all_scenario_types"
                    tag_path_handler.set_priority(tag_id, float("inf"))
                elif tagc_i == 1:
                    b.tag.tag_path = dict(
                        sp="ui\\ui_tags_loaded_solo_scenario_type",
                        mp="ui\\ui_tags_loaded_multiplayer_scenario_type",
                        ui="ui\\ui_tags_loaded_mainmenu_scenario_type"
                        ).get(map_type, b.tag.tag_path)
                    tag_path_handler.set_priority(tag_id, float("inf"))
                tagc_i += 1

            print("    Finished")
            print("    Deprotected classes of %s of the %s total tags(%s%%)." %
                  (len(repaired), len(tag_index_array),
                   1000*len(repaired)//len(tag_index_array)/10))

            print()
            if len(repaired) != len(tag_index_array):
                print("The deprotector could not find these tags:\n"
                      "  (This does not mean they are protected however)\n"
                      "  [ id,  offset,  type,  path ]\n")
                for i in range(len(tag_index_array)):
                    if i not in repaired:
                        b = tag_index_array[i]
                        try:
                            print("  [ %s, %s, %s, %s ]" % (
                                i, b.meta_offset - map_magic,
                                b.class_1.enum_name, b.tag.tag_path))
                        except Exception:
                            print("  [ %s, %s, %s ]" % (
                                i, b.meta_offset - map_magic, "<UNPRINTABLE>"))
                print()

        if self.stop_processing:
            print("    Deprotection stopped by user.")
            return

        # write the deprotected tag classes fourcc's to each
        # tag's header in the tag index in the map buffer
        index_array_offset = tag_index.tag_index_offset - map_magic
        for tag_id, tag_cls in repaired.items():
            tag_index_ref = tag_index_array[tag_id]
            classes_int = int.from_bytes(class_bytes_by_fcc[tag_cls], 'little')
            tag_index_ref.class_1.data = classes_int & 0xFFffFFff
            tag_index_ref.class_2.data = (classes_int >> 32) & 0xFFffFFff
            tag_index_ref.class_3.data = (classes_int >> 64) & 0xFFffFFff


        if self.use_hashcaches.get():
            print("Hashcaches are not implemented.")
            # print("Renaming tags using hashcaches...")
            # print("    Finished")

        if self.valid_tag_paths_are_accurate.get():
            for tag_id in range(len(tag_index_array)):
                tag_index_ref = tag_index_array[tag_id]
                tag_path = tag_index_ref.tag.tag_path
                if not tag_path.startswith("protected"):
                    tag_path_handler.set_priority(tag_id, float("inf"))

        if self.use_heuristics.get():
            print("Renaming tags using heuristics...")
            try:
                self._heuristics_deprotect(tag_path_handler)
            except Exception:
                print(format_exc())
            print("    Finished")

        if self.limit_tag_path_lengths.get():
            print("Limiting tag paths to 254 characters...")
            try:
                tag_path_handler.shorten_paths(254)
            except Exception:
                print(format_exc())
            print("    Finished")

        if self.stop_processing:
            print("    Deprotection stopped by user.")
            return

        # calculate the maps new checksum
        map_header.crc32 = crc_functions.calculate_ce_checksum(map_data, index_magic)

        print("Saving deprotection changes to map...")
        self.save_map(save_path, prompt_strings_expand=False)

        # record the original tag_paths so we know if any were changed
        active_map.orig_tag_paths = tuple(
            b.tag.tag_path for b in active_map.tag_index.tag_index)

        print("Completed. Took %s seconds." % round(time()-start, 1))

    
    def _heuristics_deprotect(self, tag_path_handler):
        active_map = self.active_map
        tag_index_array = active_map.tag_index.tag_index
        matg_meta = active_map.matg_meta
        hudg_id = 0xFFFF if not matg_meta else\
                  matg_meta.interface_bitmaps.STEPTREE[0].hud_globals.id[0]
        hudg_meta = active_map.get_meta(hudg_id, True)

        if hudg_meta:
            block = hudg_meta.messaging_parameters
            items_meta = active_map.get_meta(block.item_message_text.id[0], True)
            icons_meta = active_map.get_meta(block.alternate_icon_text.id[0], True)

            if items_meta: tag_path_handler.set_item_strings(items_meta)
            if icons_meta: tag_path_handler.set_icon_strings(icons_meta)

        vehi_ids = []
        actv_ids = []
        bipd_ids = []
        item_ids = []
        tagc_ids = []
        soul_ids = []
        misc_ids = []
        sbsp_ids = []
        scnr_id = matg_id = None
        for i in range(len(tag_index_array)):
            if self.stop_processing:
                print("    Deprotection stopped by user.")
                return

            tag_type = tag_index_array[i].class_1.enum_name
            if tag_type == "scenario":
                scnr_id = i
            elif tag_type == "globals":
                matg_id = i
            elif tag_type == "vehicle":
                vehi_ids.append(i)
            elif tag_type == "actor_variant":
                actv_ids.append(i)
            elif tag_type == "biped":
                bipd_ids.append(i)
            elif tag_type in ("item", "weapon", "equipment"):
                item_ids.append(i)
            elif tag_type == "tag_collection":
                tagc_ids.append(i)
            elif tag_type == "ui_widget_collection":
                soul_ids.append(i)
            elif tag_type == "scenario_structure_bsp":
                sbsp_ids.append(i)
            else:
                misc_ids.append(i)

        print("\ntag_id\tweight\ttag_path\n")
        for id_list in (sbsp_ids, vehi_ids, item_ids, actv_ids, bipd_ids,
                        soul_ids, (hudg_id, matg_id, scnr_id),
                        tagc_ids, ):#misc_ids):

            if self.stop_processing:
                print("    Deprotection stopped by user.")
                return

            for i in id_list:
                try:
                    recursive_rename(i, active_map, tag_path_handler)
                except Exception:
                    print(format_exc())

        total = 0
        for b in tag_index_array:
            if "\\" not in b.tag.tag_path:
                total += 1

        print('%s%% still "protected":' % round(total * 100 / len(tag_index_array), 2))

    def save_map_as(self, e=None):
        if not self.map_loaded: return

        active_map = self.active_map
        if self.running:
            return
        elif active_map.is_resource:
            print("Cannot save resource maps.")
            return
        elif "halo1" not in active_map.engine:
            print("Cannot save this kind of map.")
            return

        save_path = asksaveasfilename(
            initialdir=dirname(self.tk_map_path.get()), parent=self,
            title="Choose where to save the map",
            filetypes=(("Halo mapfile", "*.map"),
                       ("Halo mapfile(extra sauce)", "*.yelo"),
                       ("All", "*")))

        if not save_path:
            return

        self._running = True
        try:
            self.save_map(save_path)
        except Exception:
            print(format_exc())
        self._running = False

    def save_map(self, save_path=None, map_name="active", *, reload_window=True,
                 meta_data_expansion=0, raw_data_expansion=0,
                 vertex_data_expansion=0, triangle_data_expansion=0,
                 prompt_strings_expand=True):
        assert meta_data_expansion     >= 0
        assert raw_data_expansion      >= 0
        assert vertex_data_expansion   >= 0
        assert triangle_data_expansion >= 0

        halo_map = self.maps.get(map_name)
        if halo_map is None:
            return
        elif halo_map.is_resource:
            print("Cannot save resource maps.")
            return
        elif halo_map.engine not in ("halo1ce", "halo1yelo"):
            print("Cannot save this kind of map.")
            return
        elif not save_path:
            save_path = halo_map.filepath

        save_dir  = dirname(save_path)
        save_path, ext = splitext(save_path)
        save_path = sanitize_path(save_path + (ext if ext else (
            '.yelo' if 'yelo' in halo_map.engine else '.map')))
        if not exists(save_dir):
            os.makedirs(save_dir)

        print("Saving map...")
        print("    %s" % save_path)
        try:
            out_file = map_file = halo_map.map_data
            if save_path.lower() != halo_map.filepath.lower():
                # use r+ mode rather than w if the file exists
                # since it might be hidden. apparently on windows
                # the w mode will fail to open hidden files.
                if isfile(save_path):
                    out_file = open(save_path, 'r+b')
                    out_file.truncate(0)
                else:
                    out_file = open(save_path, 'w+b')

            map_header = halo_map.map_header
            index_off_diff = (raw_data_expansion +
                              vertex_data_expansion + triangle_data_expansion)

            orig_tag_paths = halo_map.orig_tag_paths
            map_magic      = halo_map.map_magic
            index_magic    = halo_map.index_magic
            tag_index      = halo_map.tag_index
            index_offset   = tag_index.tag_index_offset
            index_array    = tag_index.tag_index
            index_header_offset = map_header.tag_index_header_offset

            if index_off_diff:
                index_header_offset += index_off_diff
                map_magic = get_map_magic(map_header)

            func = crc_functions.U
            do_spoof  = halo_map.force_checksum and func is not None

            # copy the map to the new save location
            map_size, chunk = 0, True
            map_file.seek(0)  # DO copy the header(crc calculator reads from it)
            out_file.seek(0)
            while chunk:
                chunk = map_file.read(4*1024**2)  # work with 4Mb chunks
                map_size += len(chunk)
                if map_file is not out_file:
                    out_file.write(chunk)
                gc.collect()

            # recalculate pointers for the strings if they were changed
            strings_size, string_offs = 0, {}
            for i in range(len(index_array)):
                tag_path = index_array[i].tag.tag_path
                if orig_tag_paths[i].lower() == tag_path.lower():
                    # path wasnt changed
                    continue

                # put the new string at the end of the metadata
                string_offs[i] = map_size + map_magic + strings_size
                strings_size += len(tag_path) + 1

            # make sure the user wants to expand the map more if needed
            if strings_size > meta_data_expansion:
                if prompt_strings_expand and not messagebox.askyesno(
                    "Metadata size expansion required",
                    ("Tag paths were edited, requiring the map be expanded to "
                     "accommodate the new strings.\n\nMap must be expanded by "
                     "%s more bytes. Allow this?") % strings_size,
                    icon='warning', parent=self):
                    print("    Save cancelled")
                    if map_file is not out_file:
                        out_file.close()
                    return ""

                # move the new tag_path offsets to the end of the metadata
                for i in string_offs:
                    string_offs[i] += meta_data_expansion

                meta_data_expansion += strings_size

            # change each tag_path's pointer to its new value
            for i, off in string_offs.items():
                index_array[i].path_offset = off

            # move the tag_index array back to where it SHOULD be
            if self.fix_tag_index_offset.get():
                tag_index.tag_index_offset = index_magic + tag_index.get_size()

            # update the map_data and expand the map's sections if necessary
            halo_map.map_data = out_file
            if map_file is not out_file and hasattr(map_file, "close"):
                map_file.close()
            expand_halomap(halo_map, raw_data_expansion, meta_data_expansion,
                           vertex_data_expansion, triangle_data_expansion)

            # get the tag_index_header_offset and map_magic if they changed
            index_header_offset = map_header.tag_index_header_offset
            map_magic = halo_map.map_magic

            # serialize the tag_index_header, tag_index and all the tag_paths
            tag_index.serialize(buffer=out_file, calc_pointers=False,
                                magic=map_magic, offset=index_header_offset)
            out_file.flush()
            if hasattr(out_file, "fileno"):
                os.fsync(out_file.fileno())

            # write the map header so the calculate_ce_checksum can read it
            out_file.seek(0)
            out_file.write(map_header.serialize(calc_pointers=False))
            crc = crc_functions.calculate_ce_checksum(out_file, index_magic)
            if do_spoof:
                func([crc^0xFFffFFff, out_file, index_header_offset + 8])
            else:
                map_header.crc32 = crc

            # write the header to the beginning of the map
            out_file.seek(0)
            out_file.write(map_header.serialize(calc_pointers=False))
            out_file.flush()
            if hasattr(out_file, "fileno"):
                os.fsync(out_file.fileno())
            print("    Finished")
        except Exception:
            print(format_exc())
            print("Could not save map")
            save_path = ""
            if map_file is not out_file:
                out_file.close()

        if reload_window and save_path:
            print("Reloading map to apply changes...")
            self.load_map(save_path, will_be_active=True)

        return save_path

    def start_extraction(self, e=None):
        if self.running:
            return

        queue_tree = self.queue_tree.tags_tree

        if not self.map_loaded:
            return
        elif not queue_tree.get_children():
            self.queue_add_all()
            if not queue_tree.get_children():
                return

        self._running = True
        try:
            self._start_extraction()
        except Exception:
            print(format_exc())
        self._running = False

    def _start_extraction(self):
        queue_tree = self.queue_tree.tags_tree

        print("Starting extraction...")
        self.stop_processing = False
        start = time()

        queue_info = self.queue_tree.queue_info
        queue_items = queue_tree.get_children()
        total = 0
        cheapes_extracted = set()
        last_map_name = None

        for iid in tuple(queue_items):
            self.update_idletasks()
            if self.stop_processing:
                print("Extraction stopped by user\n")
                break

            try:
                info = queue_info.get(iid)
                if not info:
                    # item was removed during processing
                    continue
                curr_map       = info['halo_map']
                tag_index_refs = info['tag_index_refs']

                out_dir        = info['out_dir'].get()
                recursive      = info['recursive'].get()
                overwrite      = info['overwrite'].get()
                show_output    = info['show_output'].get()
                extract_mode   = info['extract_mode'].get()
                tags_list_path = info['tags_list_path'].get()
                map_name = curr_map.map_header.map_name
                is_halo1_tag = ("halo1"  in curr_map.engine or
                                "stubbs" in curr_map.engine or
                                "shadowrun" in curr_map.engine)
                recursive &= is_halo1_tag

                extract_kw = dict(out_dir=out_dir, overwrite=overwrite,
                                  decode_adpcm=info['decode_adpcm'].get())

            except Exception:
                print(format_exc())
                continue

            if extract_mode == "tags" and not is_halo1_tag:
                # cant extract anything other than halo 1 tags yet
                try: queue_tree.delete(iid)
                except Exception: pass
                continue

            if curr_map.is_resource and "halo1pc" in curr_map.engine:
                print("\nCannot extract PC resource caches, as they ONLY"
                      "\ncontain raw data(pixels/sound samples).\n")
                continue

            if last_map_name != map_name:
                print("\nExtracting from %s" % map_name)

            if self.extract_cheape and (curr_map.engine == "halo1yelo" and
                                        map_name not in cheapes_extracted):
                cheapes_extracted.add(map_name)
                filename = map_name + "_cheape.map"

                abs_tag_path = sanitize_path(
                    join(self.tk_tags_dir.get(), filename))

                print(abs_tag_path)
                try:
                    if not exists(dirname(abs_tag_path)):
                        os.makedirs(dirname(abs_tag_path))

                    cheape = curr_map.map_header.yelo_header.cheape_definitions
                    size        = cheape.size
                    decomp_size = cheape.decompressed_size

                    curr_map.map_data.seek(cheape.offset)
                    cheape_data = curr_map.map_data.read(size)
                    mode = 'r+b' if isfile(abs_tag_path) else 'w+b'
                    with open(abs_tag_path, mode) as f:
                        f.truncate(0)
                        if decomp_size and decomp_size != size:
                            cheape_data = zlib.decompress(cheape_data)
                        f.write(cheape_data)

                except Exception:
                    print(format_exc())
                    print("Error ocurred while extracting cheape.map")

            extract_rsrc = curr_map.engine in ("halo1ce", "halo1yelo") and \
                           self.extract_from_ce_resources.get()

            map_magic = curr_map.map_magic
            tag_index = curr_map.tag_index
            tag_index_array = tag_index.tag_index
            tagslist = ""
            extracted = set()
            local_total = 0
            convert_kwargs = dict(
                rename_scnr_dups=self.rename_duplicates_in_scnr.get(),
                generate_uncomp_verts=self.generate_uncomp_verts.get(),
                generate_comp_verts=self.generate_comp_verts.get()
                )

            while tag_index_refs:
                next_refs = []

                for tag_index_ref in tag_index_refs:
                    file_path = "<Could not get filepath>"
                    try:
                        file_path = sanitize_path("%s.%s" %
                            (tag_index_ref.tag.tag_path,
                             tag_index_ref.class_1.enum_name))
                        self.update()
                        if self.stop_processing:
                            break

                        tag_id = tag_index_ref.id.tag_table_index
                        if not map_magic:
                            # resource cache tag
                            tag_id += (tag_index_ref.id.table_index << 16)

                        # dont want to re-extract tags
                        if (tag_id, extract_mode) in extracted:
                            continue
                        elif curr_map.is_indexed(tag_id) and not extract_rsrc:
                            continue
                        extracted.add((tag_id, extract_mode))
                        abs_file_path = join(out_dir, file_path)

                        if tag_index_ref.class_1.enum_name in ("<INVALID>", "NONE"):
                            print(("Unknown tag class for '%s'\n" +
                                   "    Run deprotection to fix this.") %
                                  file_path)
                            continue

                        # determine if not overwriting and we are about to
                        dont_extract = not overwrite and (
                            extract_mode == "tags" and isfile(abs_file_path))

                        if dont_extract and not recursive:
                            continue

                        tag_cls = fourcc(tag_index_ref.class_1.data)

                        if show_output and not dont_extract:
                            print("%s: %s" % (extract_mode, file_path))

                        meta = curr_map.get_meta(tag_id, True)
                        self.update()
                        if not meta:
                            print("    Could not get meta")
                            continue

                        if tags_list_path:
                            tagslist += "%s: %s\n" % (extract_mode, file_path)

                        if recursive:
                            # add dependencies to list to be extracted
                            index_len = len(tag_index_array)
                            refs = ()
                            try:
                                refs = curr_map.get_dependencies(
                                    meta, tag_id, tag_cls)
                            except Exception:
                                print(format_exc())
                                print("    Could not recursively extract.")

                            extracting = set(extracted)
                            for ref in refs:
                                index = ref.id.tag_table_index
                                key = (index, extract_mode)
                                if key not in extracting and index < index_len:
                                    extracting.add(key)
                                    next_refs.append(tag_index_array[index])

                            if dont_extract:
                                continue


                        meta = curr_map.meta_to_tag_data(
                            meta, tag_cls, tag_index_ref, **convert_kwargs)
                        if not meta:
                            print("    Failed to convert meta to tag")
                            continue

                        if extract_mode == "tags":
                            if not exists(dirname(abs_file_path)):
                                os.makedirs(dirname(abs_file_path))

                            if is_halo1_tag: FieldType.force_big()
                            mode = 'r+b' if isfile(abs_file_path) else 'w+b'
                            with open(abs_file_path, mode) as f:
                                try:
                                    f.truncate(0)
                                    f.write(curr_map.tag_headers[tag_cls])
                                    f.write(meta.serialize(calc_pointers=False))
                                except Exception:
                                    print(format_exc())
                                    print("    Failed to serialize tag")
                                    continue
                        elif extract_mode == "data":
                            try:
                                error_str = curr_map.extract_tag_data(
                                    meta, tag_index_ref, **extract_kw)
                            except Exception:
                                error_str = ("%s\nFailed to extract data" %
                                             format_exc())

                            if error_str:
                                print(error_str)
                                continue
                        else:
                            continue

                        local_total += 1
                        del meta
                    except PermissionError:
                        print("Refinery does not have permission to save here.\n"
                              "Try running Refinery as admin to potentially fix this.\n")
                    except Exception:
                        print(format_exc())
                        print("Error ocurred while extracting '%s'" % file_path)

                tag_index_refs = next_refs


            if last_map_name != map_name:
                curr_map.clear_map_cache()
                for halo_map in self.maps.values():
                    if halo_map.is_resource:
                        halo_map.clear_map_cache()

            FieldType.force_normal()
            try: queue_tree.delete(iid)
            except Exception: pass

            if tagslist:
                try:
                    try:
                        f = open(tags_list_path, 'a')
                    except Exception:
                        try:
                            f = open(tags_list_path, 'w')
                        except Exception:
                            try:
                                f = open(tags_list_path, 'r+')
                            except Exception:
                                f = None

                    if f is not None:
                        f.write("%s tags in: %s\n" % (local_total, out_dir))
                        f.write(tagslist)
                        f.write('\n\n')
                        f.close()
                    else:
                        print("Could not create\open tagslist. Either run "
                              "Refinery as admin, or choose a a directory "
                              "you have permission to edit/make files in.")
                except Exception:
                    print(format_exc())
                    print("Could not save tagslist.")

            total += local_total
            local_total = 0
            last_map_name = map_name


        if total == 0:
            print(
                "No tags were extracted. This might be a permissions issue.\n"
                "Close Refinery and run it as admin to potentially fix this.")

        print("Extracted %s tags. Took %s seconds\n" %
              (total, round(time()-start, 1)))

    def cancel_action(self, e=None):
        if not self.map_loaded: return
        self.stop_processing = True

    def reload_explorers(self):
        if not self.map_loaded: return
        print("Reloading map explorer...")

        for name, tree in self.tree_frames.items():
            if name.startswith(self._display_mode):
                tree.reload(self.active_map)
            else:
                tree.reload()

        if not(self.maps):
            self.queue_tree.reload()

        print("    Finished\n")
        self.update()

    def browse_for_maps(self):
        if self.running:
            return
        fps = askopenfilenames(
            initialdir=self.last_dir,
            title="Select map(s) to load", parent=self,
            filetypes=(("Halo mapfile", "*.map"),
                       ("Halo mapfile(extra sauce)", "*.yelo"),
                       ("Halo 2 Vista compressed mapfile", "*.map.dtz"),
                       ("All", "*")))

        if not fps:
            return

        fps = tuple(sanitize_path(fp) for fp in fps)
        self.last_dir = dirname(fps[0])

        self._running = True
        try:
            self.load_maps(fps, self.active_map is None, ask_close_open=True)
        except Exception:
            print(format_exc())
        self._running = False
