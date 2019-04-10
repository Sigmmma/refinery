import mmap
import gc
import tkinter as tk
import os
import refinery
import shutil
import sys
import zlib

from refinery.core import *

from struct import unpack
from time import time
from traceback import format_exc

from tkinter.font import Font
from tkinter import messagebox
from tkinter.filedialog import askopenfilename, askopenfilenames,\
     asksaveasfilename


from binilla.about_window import AboutWindow
from binilla.widgets import ScrollMenu

from refinery.defs.config_def import config_def
from refinery.widgets import QueueTree, RefinerySettingsWindow,\
     RefineryRenameWindow, RefineryChecksumEditorWindow,\
     ExplorerHierarchyTree, ExplorerClassTree, ExplorerHybridTree,\
     bitmap_file_formats


default_config_path = os.path.join(curr_dir, 'refinery.cfg')
VALID_DISPLAY_MODES = frozenset(("hierarchy", "class", "hybrid"))
VALID_EXTRACT_MODES = frozenset(("tags", "data"))



class Refinery(tk.Tk, RefineryCore):
    last_dir = curr_dir

    config_path = default_config_path
    config_file = None

    config_version = 2
    app_name = "Refinery"
    version = refinery.__version__

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

    icon_filepath = ""

    about_module_names = (
        "arbytmap",
        "binilla",
        "mozzarilla",
        "reclaimer",
        "refinery",
        "supyr_struct",
        "threadsafe_tkinter",
        )

    about_messages = ()
    tk_vars = ()

    def __init__(self, *args, **kwargs):
        self.app_name = str(kwargs.pop('app_name', self.app_name))

        # we are running a gui based program, so we want errors printed
        # rather than propogated upward(RefineryCore is designed to keep
        # working when an error that would be affected by this would occur)
        self.print_errors = self.do_printout = True

        RefineryCore.__init__(self, *args, **kwargs)
        tk.Tk.__init__(self, *args, **kwargs)
        try:
            with open(os.path.os.path.join(curr_dir, "tad.gsm"[::-1]), 'r', -1, "037") as f:
                setattr(self, 'segassem_tuoba'[::-1], list(l for l in f))
        except Exception:
            pass

        try:
            try:
                icon_filepath = os.path.join(curr_dir, 'refinery.ico')
                self.iconbitmap(icon_filepath)
            except Exception:
                icon_filepath = os.path.join(os.path.join(curr_dir, 'icons', 'refinery.ico'))
                self.iconbitmap(icon_filepath)
        except Exception:
            icon_filepath = ""
            print("Could not load window icon.")

        self.icon_filepath = icon_filepath
        self.title('%s v%s.%s.%s' % ((self.app_name,) + self.version))
        self.minsize(width=500, height=300)

        # make the tkinter variables
        self.extract_mode = tk.StringVar(self, "tags")
        self.show_all_fields = tk.IntVar(self)
        self.edit_all_fields = tk.IntVar(self)
        self.allow_corrupt = tk.IntVar(self)

        self._active_map_path = tk.StringVar(self)
        self._active_map_name = tk.StringVar(self)
        self._active_engine = tk.StringVar(self)

        self._tags_dir = tk.StringVar(self, self.tags_dir)
        self._data_dir = tk.StringVar(self, self.data_dir)
        self._tagslist_path = tk.StringVar(self, self.tagslist_path)

        self._autoload_resources = tk.IntVar(self, 1)
        self._do_printout  = tk.IntVar(self, 1)

        self._force_lower_case_paths = tk.IntVar(self, 1)
        self._extract_cheape = tk.IntVar(self)
        self._rename_duplicates_in_scnr = tk.IntVar(self)
        self._overwrite = tk.IntVar(self)
        self._recursive = tk.IntVar(self)
        self._decode_adpcm = tk.IntVar(self, 1)
        self._generate_uncomp_verts = tk.IntVar(self, 1)
        self._generate_comp_verts = tk.IntVar(self)
        self._use_tag_index_for_script_names = tk.IntVar(self)
        self._use_scenario_names_for_script_names = tk.IntVar(self)
        self._bitmap_extract_keep_alpha = tk.IntVar(self, 1)
        self._bitmap_extract_format = tk.StringVar(self)

        self._fix_tag_classes = tk.IntVar(self, 1)
        self._fix_tag_index_offset = tk.IntVar(self)
        self._use_heuristics = tk.IntVar(self, 1)
        self._valid_tag_paths_are_accurate = tk.IntVar(self, 1)
        self._scrape_tag_paths_from_scripts = tk.IntVar(self, 1)
        self._limit_tag_path_lengths = tk.IntVar(self, 1)
        self._shallow_ui_widget_nesting = tk.IntVar(self, 1)
        self._rename_cached_tags = tk.IntVar(self, 1)
        self._print_heuristic_name_changes = tk.IntVar(self)

        self.tk_vars = dict(
            extract_mode=self.extract_mode,
            show_all_fields=self.show_all_fields,
            edit_all_fields=self.edit_all_fields,
            allow_corrupt=self.allow_corrupt,

            tags_dir=self._tags_dir,
            data_dir=self._data_dir,
            tagslist_path=self._tagslist_path,

            do_printout=self._do_printout,
            autoload_resources=self._autoload_resources,

            force_lower_case_paths=self._force_lower_case_paths,
            extract_cheape=self._extract_cheape,
            rename_duplicates_in_scnr=self._rename_duplicates_in_scnr,
            overwrite=self._overwrite,
            recursive=self._recursive,
            decode_adpcm=self._decode_adpcm,
            generate_uncomp_verts=self._generate_uncomp_verts,
            generate_comp_verts=self._generate_comp_verts,
            use_tag_index_for_script_names=self._use_tag_index_for_script_names,
            use_scenario_names_for_script_names=self._use_scenario_names_for_script_names,
            bitmap_extract_keep_alpha=self._bitmap_extract_keep_alpha,
            bitmap_extract_format=self._bitmap_extract_format,

            fix_tag_classes=self._fix_tag_classes,
            fix_tag_index_offset=self._fix_tag_index_offset,
            use_heuristics=self._use_heuristics,
            valid_tag_paths_are_accurate=self._valid_tag_paths_are_accurate,
            scrape_tag_paths_from_scripts=self._scrape_tag_paths_from_scripts,
            limit_tag_path_lengths=self._limit_tag_path_lengths,
            shallow_ui_widget_nesting=self._shallow_ui_widget_nesting,
            rename_cached_tags=self._rename_cached_tags,
            print_heuristic_name_changes=self._print_heuristic_name_changes,
            )

        if self.config_file is not None:
            pass
        elif os.path.exists(self.config_path):
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
            label="Unload all non-resource maps",
            command=lambda s=self: s.unload_maps_clicked(False, ("<active>",), None))
        self.file_menu.add_command(
            label="Unload all resource maps",
            command=lambda s=self: s.unload_maps_clicked(True, ("<active>",), None))
        self.file_menu.add_command(
            label="Unload all maps",
            command=lambda s=self: s.unload_maps_clicked(None, ("<active>",), None))
        self.file_menu.add_command(
            label="Unload all maps from all engines",
            command=lambda s=self: s.unload_maps_clicked(None, None, None))
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Save map as", command=self.save_map_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.destroy)

        self.bind('<Control-o>', lambda *a, s=self: s.browse_for_maps())

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
        self.menubar.add_command(
            label="About", command=self.show_about_window)
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
        self.deprotect_all_button = tk.Button(
            self.map_action_frame, text="Run mass deprotection",
            command=self.deprotect_all)
        self.deprotect_button = tk.Button(
            self.map_action_frame, text="Run deprotection",
            command=self.deprotect)
        self.begin_button = tk.Button(
            self.map_action_frame, text="Run extraction",
            command=self.start_extraction)


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

        self.engine_select_menu = ScrollMenu(
            self.map_action_frame, str_variable=self._active_engine,
            callback=self.set_active_engine, menu_width=15)
        self.map_select_menu = ScrollMenu(
            self.map_action_frame, str_variable=self._active_map_name,
            callback=self.set_active_map, menu_width=15)
        self.reload_engine_select_options()
        self.reload_map_select_options()

        # pack everything
        self.begin_button.pack(side='right', padx=4, pady=4)
        self.deprotect_button.pack(side='right', padx=4, pady=4)
        #self.deprotect_all_button.pack(side='right', padx=4, pady=4)
        self.engine_select_menu.pack(side='left', padx=4, pady=4, fill='x')
        self.map_select_menu.pack(side='left', padx=(4, 10), pady=4,
                                  fill='x', expand=True)

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

    def __getattribute__(self, attr_name):
        # it would have been a LOT of boilerplate for abstracting the
        # tkinter settings variables if I didn't overload __getattribute__
        try:
            if attr_name in object.__getattribute__(self, "tk_vars",):
                return object.__getattribute__(self, "_" + attr_name).get()
        except AttributeError:
            pass
        return object.__getattribute__(self, attr_name)

    def __setattr__(self, attr_name, new_val):
        # it would have been a LOT of boilerplate for abstracting the
        # tkinter settings variables if I didn't overload __setattr__
        try:
            if attr_name in object.__getattribute__(self, "tk_vars"):
                object.__getattribute__(self, "_" + attr_name).set(new_val)
        except AttributeError:
            pass
        object.__setattr__(self, attr_name, new_val)

    @property
    def running(self):
        return self._running

    def load_config(self, filepath=None):
        if filepath is None:
            filepath = self.config_path
        assert os.path.exists(filepath)

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
        paths      = self.config_file.data.paths
        app_window = self.config_file.data.app_window

        self.geometry("%sx%s+%s+%s" % tuple(app_window[:4]))

        self.tagslist_path = paths.tagslist.path
        self.tags_dir = paths.tags_dir.path
        self.data_dir = paths.data_dir.path
        self.last_dir = paths.last_dir.path

        self._display_mode = header.flags.display_mode.enum_name
        for name in ("do_printout", "autoload_resources"):
            setattr(self, name, bool(getattr(header.flags, name)))

        for flags in (header.extraction_flags, header.deprotection_flags):
            for attr_name in flags.NAME_MAP:
                setattr(self, attr_name, bool(getattr(flags, attr_name)))

        if header.bitmap_extract_format.enum_name in bitmap_file_formats:
            self.bitmap_extract_format = header.bitmap_extract_format.enum_name
        else:
            self.bitmap_extract_format = bitmap_file_formats[0]

    def update_config(self, config_file=None):
        if config_file is None:
            config_file = self.config_file

        header      = config_file.data.header
        paths       = config_file.data.paths
        app_window  = config_file.data.app_window

        header.version = self.config_version

        if self._initialized:
            app_window.app_width    = self.winfo_width()
            app_window.app_height   = self.winfo_height()
            app_window.app_offset_x = self.winfo_x()
            app_window.app_offset_y = self.winfo_y()

        # make sure there are enough entries in the paths
        if len(paths.NAME_MAP) > len(paths):
            paths.extend(len(paths.NAME_MAP) - len(paths))

        paths.tagslist.path = self.tagslist_path
        paths.tags_dir.path = self.tags_dir
        paths.data_dir.path = self.data_dir
        paths.last_dir.path = self.last_dir

        header.flags.display_mode.set_to(self._display_mode)
        for attr_name in ("do_printout", "autoload_resources"):
            setattr(header.flags, attr_name, getattr(self, attr_name))

        for flags in (header.extraction_flags, header.deprotection_flags):
            for attr_name in flags.NAME_MAP:
                setattr(flags, attr_name, getattr(self, attr_name))

        if self.bitmap_extract_format in bitmap_file_formats:
            header.bitmap_extract_format.set_to(self.bitmap_extract_format)
        else:
            header.bitmap_extract_format.set_to(bitmap_file_formats[0])

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
            elif "halo3" in engine:
                valid_classes = h3_data_extractors.keys()
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
        self.unload_maps(None, None, None)
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

    def set_active_engine(self, name_or_index=None, map_name=None,
                          force_reload=False):
        engine_name = None
        engine_names = sorted(n for n in self.maps_by_engine if n != "<active>")
        if isinstance(name_or_index, int):
            if name_or_index in range(len(engine_names)):
                engine_name = engine_names[name_or_index]
        elif name_or_index is None and engine_names:
            engine_name = iter(sorted(engine_names)).__next__()
        elif name_or_index in engine_names:
            engine_name = name_or_index

        if engine_name is None and not force_reload:
            return

        next_maps = self.maps_by_engine.get(engine_name)
        if self.active_maps is next_maps and not force_reload:
            # selected same engine. nothing to change
            return
        elif not next_maps:
            next_map_name = None
        elif map_name in next_maps:
            next_map_name = map_name
        elif next_maps.get("<active>"):
            next_map_name = next_maps.get("<active>").map_header.map_name
        else:
            next_map_name = iter(sorted(next_maps)).__next__()

        # unset any currently active engine and only set
        # it if we have a valid map name to make active
        self.maps_by_engine.pop("<active>", None)
        if next_map_name:
            self.maps_by_engine["<active>"] = next_maps
            next_maps.pop("<active>", None)

        self.active_engine_name = engine_name if next_maps else ""
        self.reload_map_select_options()
        self.set_active_map(next_map_name, True)

    def set_active_map(self, name_or_index=None, force_reload=False):
        map_name = None
        map_names = sorted(n for n in self.active_maps if n != "<active>")
        if name_or_index in range(len(map_names)):
            map_name = map_names[name_or_index]

        prev_map = self.active_map
        RefineryCore.set_active_map(self, map_name)
        if self.active_map is not prev_map or force_reload:
            self.display_map_info()
            self.reload_explorers()

    def reload_engine_select_options(self):
        opts = dict(self.maps_by_engine)
        opts.pop("<active>", None)
        if opts:
            opts = sorted(opts.keys())
        else:
            opts = ("Loaded engines", )

        menu = self.engine_select_menu
        sel_name = self.active_engine_name
        sel_index = opts.index(sel_name) if sel_name in opts else 0
        menu.set_options(opts)
        menu.sel_index = sel_index
        self.reload_map_select_options()

    def reload_map_select_options(self):
        opts = dict(self.active_maps)
        opts.pop("<active>", None)
        if opts:
            opts = sorted(opts.keys())
        else:
            opts = ("Loaded maps", )

        menu = self.map_select_menu
        sel_name = self.active_map_name
        sel_index = opts.index(sel_name) if sel_name in opts else 0
        menu.set_options(opts)
        menu.sel_index = sel_index

    def unload_maps_clicked(self, map_type=False, engines_to_unload=("<active>", ),
                            maps_to_unload=("<active>", )):
        if self._running:
            return
        self._running = True

        try:
            self.unload_maps(map_type, engines_to_unload, maps_to_unload)
        except Exception:
            print(format_exc())
        self._running = False

    def unload_maps(self, map_type=False, engines_to_unload=("<active>", ),
                    maps_to_unload=("<active>", )):
        RefineryCore.unload_maps(self, map_type, engines_to_unload,
                                 maps_to_unload)
        if not self.active_maps:
            self.set_active_engine(force_reload=True)
        else:
            self.set_active_map(force_reload=True)

    def load_resource_maps(self, halo_map=None):
        if halo_map is None:
            halo_map = self.active_map

        if halo_map is None:
            return
        elif self.running:
            return

        self._running = True
        try:
            print("Loading resource maps for: %s" %
                  halo_map.map_header.map_name)
            self.update()
            RefineryCore.load_resource_maps(halo_map)
            self.reload_engine_select_options()
            print("    Finished")
        except Exception:
            print(format_exc())

        self._running = False

    def load_map(self, map_path, make_active=True, ask_close_open=False):
        new_map = None
        try:
            print("Loading %s..." % os.path.basename(map_path))
            new_map = RefineryCore.load_map(
                self, map_path, self.autoload_resources,
                not ask_close_open)
        except MapAlreadyLoadedError:
            if not(ask_close_open and messagebox.askyesno(
                    "A map with that name is already loaded!",
                    ('A map with the name "%s" is already loaded.\n'
                     "Close that map and load this one instead?") %
                    map_name, icon='warning', parent=self)):
                print("    Skipped")
                return
            new_map = RefineryCore.load_map(
                self, map_path, self.autoload_resources, True)
        except Exception:
            try:
                self.unload_maps(None)
            except Exception:
                print(format_exc())
            raise

        if make_active:
            self.set_active_engine(
                new_map.engine, new_map.map_header.map_name, force_reload=True)

        print("    Finished")
        return new_map

    def load_maps(self, map_paths, make_active=True, ask_close_open=False):
        if not map_paths:
            return

        make_active |= self.active_map is None
        new_map = None
        for map_path in map_paths:
            try:
                new_map = self.load_map(map_path, False, ask_close_open)
            except EngineDetectionError:
                print(format_exc(0))
            except Exception:
                self.display_map_info(
                    "Could not load map.\nCheck console window for error.")
                print(format_exc())
                print("Error occurred while attempting to load map.\n"
                      "If this is a PermissionError and the map is located in\n"
                      "a protected location, Refinery may need to run as admin.\n"
                      "    Make sure the map you are accessing is not read-only.\n"
                      "Refinery opens maps in read-write mode in case edits are\n"
                      "made, and opening in this mode fails on read-only files.\n")

        self.reload_engine_select_options()
        if make_active and new_map is not None:
            self.set_active_engine(
                new_map.engine, new_map.map_header.map_name, force_reload=True)

    def display_map_info(self, string=None):
        try:
            self.map_info_text.config(state='normal')
            self.map_info_text.delete('1.0', 'end')
        finally:
            self.map_info_text.config(state='disabled')

        try:
            if string is None:
                string = self.generate_map_info_string()
        except Exception:
            string = ""
            print(format_exc())

        try:
            self.map_info_text.config(state='normal')
            self.map_info_text.insert('end', string)
        finally:
            self.map_info_text.config(state='disabled')

    def deprotect_all(self):
        if self.running: return

        self._running = True
        try:
            RefineryCore.deprotect_all(self)
        except Exception:
            print(format_exc())

        self._running = False

    def deprotect(self, save_path=None):
        if self.active_map is None:
            print("No map loaded.")
            return
        elif self.active_map.is_resource:
            print("Cannot deprotect resource maps.")
            return
        elif self.active_map.engine not in ("halo1ce", "halo1yelo", "halo1pc"):
            print("Cannot deprotect this kind of map.")
            return

        self._running = True
        try:
            if not save_path:
                save_path = asksaveasfilename(
                    initialdir=os.path.dirname(self.active_map_path), parent=self,
                    title="Choose where to save the deprotected map",
                    filetypes=(("Halo mapfile", "*.map"),
                               ("Halo mapfile(extra sauce)", "*.yelo"),
                               ("All", "*")))

            if not save_path:
                print("Deprotection cancelled.")
            else:
                save_path, ext = os.path.splitext(save_path)
                save_path = sanitize_path(save_path + (ext if ext else (
                    '.yelo' if 'yelo' in self.active_map.engine else '.map')))

                start = time()

                RefineryCore.deprotect(self, save_path)
                print("Completed. Took %s seconds." % round(time() - start, 1))
        except Exception:
            print(format_exc())

        self._running = False

    def repair_tag_classes(self):
        print("Repairing tag classes...")
        tag_index_array = self.active_map.tag_index.tag_index
        repaired = RefineryCore.repair_tag_classes(self)

        print("    Finished")
        print("    Deprotected classes of %s of the %s total tags(%s%%)." %
              (len(repaired), len(tag_index_array),
               1000*len(repaired)//len(tag_index_array)/10))

        print()
        if len(repaired) != len(tag_index_array):
            print("The deprotector could not reach these tags:\n"
                  "  (This does not mean they are protected however)\n"
                  "  [ id,  offset,  type,  path ]\n")
            for i in range(len(tag_index_array)):
                if i in repaired:
                    continue
                b = tag_index_array[i]
                try:
                    print("  [ %s, %s, %s, %s ]" % (
                        i, b.meta_offset - self.active_map.map_magic,
                        b.class_1.enum_name, b.path))
                except Exception:
                    print("  [ %s, %s, %s ]" % (
                        i, b.meta_offset - self.active_map.map_magic, "<UNPRINTABLE>"))
            print()

        return repaired

    def sanitize_resource_tag_paths(self):
        print("Renaming tags using resource map tag paths...")
        RefineryCore.sanitize_resource_tag_paths(self)
        print("    Finished")

    def _script_scrape_deprotect(self, tag_path_handler, **kw):
        print("Renaming tags using script strings...")
        RefineryCore._script_scrape_deprotect(self, tag_path_handler, **kw)
        print("    Finished")

    def _heuristics_deprotect(self, tag_path_handler, **kw):
        print("Renaming tags using script strings...")
        RefineryCore._heuristics_deprotect(self, tag_path_handler, **kw)
        print("    Finished")

    def _shorten_tag_handler_paths(self, tag_path_handler, **kw):
        print("Renaming tags using script strings...")
        RefineryCore._shorten_tag_handler_paths(self, tag_path_handler, **kw)
        print("    Finished")

    def save_map_as(self, e=None):
        if not self.map_loaded: return

        halo_map = self.active_map
        if self.running or halo_map is None:
            return ""
        elif halo_map.is_resource:
            print("Cannot save resource maps.")
            return ""
        elif halo_map.engine not in ("halo1ce", "halo1yelo", "halo1pc"):
            print("Cannot save this kind of map.")
            return ""

        save_path = asksaveasfilename(
            initialdir=os.path.dirname(self.active_map_path), parent=self,
            title="Choose where to save the map",
            filetypes=(("Halo mapfile", "*.map"),
                       ("Halo mapfile(extra sauce)", "*.yelo"),
                       ("All", "*")))

        if not save_path:
            return ""

        self._running = True
        try:
            self.save_map(save_path, prompt_strings_expand=True,
                          prompt_internal_rename=True)
        except Exception:
            print(format_exc())
        self._running = False
        return save_path

    def save_map(self, save_path=None, engine="<active>", map_name="<active>", **kw):
        reload_window = kw.pop("reload_window", True)
        prompt_strings_expand = kw.pop("prompt_strings_expand", False)
        prompt_internal_rename = kw.pop("prompt_internal_rename", False)

        maps = self.maps_by_engine.get(engine, {})
        halo_map = maps.get(map_name)
        if halo_map is None:
            return ""
        elif halo_map.is_resource:
            print("Cannot save resource maps.")
            return ""
        elif halo_map.engine not in ("halo1ce", "halo1yelo", "halo1pc"):
            print("Cannot save this kind of map.")
            return ""
        elif not save_path:
            save_path = halo_map.filepath

        new_map_name = os.path.basename(save_path)
        if (prompt_internal_rename and len(new_map_name) < 32 and
            halo_map.map_header.map_name.lower() != new_map_name.lower()):
            if messagebox.askyesno(
                    "Internal name mismatch",
                    ("A maps internal and file names must match for Halo "
                     "to be able to properly load them. Do you want to "
                     "change the internal name to match its filename?"),
                    icon='question', parent=self):
                halo_map.map_header.map_name = new_map_name

        orig_tag_paths = halo_map.orig_tag_paths
        index_array    = halo_map.tag_index.STEPTREE
        new_strings_size = 0
        for i in range(len(index_array)):
            if orig_tag_paths[i].lower() != index_array[i].path.lower():
                new_strings_size += len(index_array[i].path) + 1

        if ((new_strings_size and prompt_strings_expand) and
            not messagebox.askyesno(
                "Tagdata size expansion required",
                ("Tag paths were edited. This maps tag data section "
                 "must be expanded by %s bytes to fit the new strings."
                 "\n\nContinue?") % new_strings_size,
                icon='warning', parent=self)):
            print("    Save cancelled")
            return ""

        print('Saving "%s"' % save_path)
        try:
            save_path = RefineryCore.save_map(self, halo_map=halo_map, **kw)
            print("    Finished")
        except Exception:
            print(format_exc())
            print("    Could not save map")

        if reload_window and save_path:
            print("Reloading map to apply changes...")
            self.load_map(save_path, make_active=True)

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
        start = time()

        queue_info = self.queue_tree.queue_info
        queue_items = queue_tree.get_children()
        total = 0
        cheapes_extracted = set()
        last_map_name = None

        for iid in tuple(queue_items):
            self.update_idletasks()
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
                do_printout    = info['do_printout'].get()
                extract_mode   = info['extract_mode'].get()
                tagslist_path  = info['tagslist_path'].get()
                map_name = curr_map.map_header.map_name
                is_halo1_map = ("halo1"  in curr_map.engine or
                                "stubbs" in curr_map.engine or
                                "shadowrun" in curr_map.engine)
                tags_are_extractable = bool(curr_map.tag_headers)
                recursive &= is_halo1_map

                extract_bitmap_to = info['bitmap_extract_format'].get()
                if extract_bitmap_to not in range(len(bitmap_file_formats)):
                    extract_bitmap_to = 0

                extract_kw = dict(
                    out_dir=out_dir, overwrite=overwrite,
                    decode_adpcm=info['decode_adpcm'].get(),
                    bitmap_ext=bitmap_file_formats[extract_bitmap_to],
                    bitmap_keep_alpha=info["bitmap_extract_keep_alpha"].get(),
                    )

            except Exception:
                print(format_exc())
                continue

            if extract_mode == "tags" and not tags_are_extractable:
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
                try:
                    cheapes_extracted.add(map_name)
                    print(self.extract_cheape_from_halo_map(curr_map))
                except Exception:
                    print(format_exc())
                    print("Error ocurred while extracting cheape.map")

            force_lower_case_paths = self.force_lower_case_paths

            map_magic = curr_map.map_magic
            tag_index = curr_map.tag_index
            tag_index_array = tag_index.tag_index
            tagslist = ""
            extracted = set()
            local_total = 0
            convert_kwargs = dict(
                rename_scnr_dups=self.rename_duplicates_in_scnr,
                generate_uncomp_verts=self.generate_uncomp_verts,
                generate_comp_verts=self.generate_comp_verts,
                force_lower_case_paths=force_lower_case_paths
                )

            extract_kw["hsc_node_strings_by_type"] = hsc_strings_by_type = {}
            if is_halo1_map and curr_map.scnr_meta:
                if self.use_scenario_names_for_script_names:
                    hsc_strings_by_type.update(
                        get_h1_scenario_script_object_type_strings(
                            curr_map.scnr_meta))

                if self.use_tag_index_for_script_names:
                    bipeds = curr_map.scnr_meta.bipeds_palette.STEPTREE
                    strings = {i: tag_index_array[i].path.lower() for
                               i in range(len(tag_index_array))}
                    actors = {i: bipeds[i].name.filepath.split("/")\
                              [-1].split("\\")[-1] for i in range(len(bipeds))}

                    if force_lower_case_paths:
                        strings = {k: v.lower() for k, v in strings.items()}
                        actors  = {k: v.lower() for k, v in actors.items()}

                    # tag reference path strings
                    for i in range(24, 32):
                        hsc_strings_by_type[i] = strings

                    # actor type strings
                    hsc_strings_by_type[35] = actors

            while tag_index_refs:
                next_refs = []

                for tag_index_ref in tag_index_refs:
                    file_path = "<Could not get filepath>"
                    try:
                        self.update()
                        file_path = sanitize_path("%s.%s" %
                            (tag_index_ref.path,
                             tag_index_ref.class_1.enum_name))
                        if force_lower_case_paths:
                            file_path = file_path.lower()

                        tag_id = tag_index_ref.id & 0xFFff
                        if not map_magic:
                            # resource cache tag
                            tag_id = tag_index_ref.id

                        # dont want to re-extract tags
                        if (tag_id, extract_mode) in extracted:
                            continue
                        extracted.add((tag_id, extract_mode))
                        abs_file_path = os.path.join(out_dir, file_path)

                        if tag_index_ref.class_1.enum_name in ("<INVALID>", "NONE"):
                            print(("Unknown tag class for '%s'\n" +
                                   "    Run deprotection to fix this.") %
                                  file_path)
                            continue

                        # determine if not overwriting and we are about to
                        dont_extract = not overwrite and (
                            extract_mode == "tags" and os.path.isfile(abs_file_path))

                        if dont_extract and not recursive:
                            continue

                        tag_cls = fourcc(tag_index_ref.class_1.data)
                        if extract_mode == "tags" and tag_cls not in curr_map.tag_headers:
                            continue

                        if do_printout and not dont_extract:
                            print("%s: %s" % (extract_mode, file_path))

                        meta = curr_map.get_meta(tag_id, True)
                        self.update()
                        if not meta:
                            print("    Could not get meta")
                            continue

                        if tagslist_path:
                            tagslist += "%s: %s\n" % (extract_mode, file_path)

                        tag_refs = ()
                        if recursive or force_lower_case_paths:
                            try:
                                tag_refs = curr_map.get_dependencies(
                                    meta, tag_id, tag_cls)
                            except Exception:
                                print(format_exc())
                                print("    Could not get tag references.")

                        if force_lower_case_paths:
                            # force all tag references to lowercase
                            for ref in tag_refs:
                                ref.filepath = ref.filepath.lower()

                        if recursive:
                            # add dependencies to list to be extracted
                            index_len = len(tag_index_array)
                            extracting = set(extracted)
                            for ref in tag_refs:
                                index = ref.id & 0xFFff
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
                            try:
                                if not os.path.exists(os.path.dirname(abs_file_path)):
                                    os.makedirs(os.path.dirname(abs_file_path))

                                if is_halo1_map: FieldType.force_big()
                                mode = 'r+b' if os.path.isfile(abs_file_path) else 'w+b'
                                with open(abs_file_path, mode) as f:
                                    try:
                                        f.truncate(0)
                                        f.write(curr_map.tag_headers[tag_cls])
                                        f.write(meta.serialize(calc_pointers=False))
                                    except Exception:
                                        print(format_exc())
                                        print("    Failed to serialize tag")
                                        continue
                            except FileNotFoundError:
                                if platform == "win32" and len(abs_file_path) >= 256:
                                    fp, ext = os.path.splitext(abs_file_path)
                                    print(("    Failed to extract. Absolute filepath is over 260 "
                                           "characters. Must be shortened by %s characters. "
                                           "Try extracting to a more shallow tags directory.") % (
                                              len(abs_file_path) - 260))
                                else:
                                    print(format_exc())

                                del meta
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
                for halo_map in curr_map.maps.values():
                    if halo_map.is_resource:
                        halo_map.clear_map_cache()

            FieldType.force_normal()
            try: queue_tree.delete(iid)
            except Exception: pass

            tagslist = "%s tags in: %s\n%s" % (local_total, out_dir, tagslist)
            if tagslist_path:
                if self.write_tagslist(tagslist, tagslist_path):
                    print("Could not create\open tagslist. Either run "
                          "Refinery as admin, or choose a directory "
                          "you have permission to edit/make files in.")

            total += local_total
            local_total = 0
            last_map_name = map_name

        if total == 0:
            print(
                "No tags were extracted. This might be a permissions issue.\n"
                "Close Refinery and run it as admin to potentially fix this.")

        print("Extracted %s tags. Took %s seconds\n" %
              (total, round(time()-start, 1)))

    def reload_explorers(self):
        if self.map_loaded:
            print("Reloading map explorer...")

        for name, tree in self.tree_frames.items():
            if name.startswith(self._display_mode):
                tree.reload(self.active_map)
            else:
                tree.reload()

        if not self.active_maps:
            self.queue_tree.reload()

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
        self.last_dir = os.path.dirname(fps[0])

        self._running = True
        try:
            self.load_maps(fps, self.active_map is None, ask_close_open=True)
        except Exception:
            print(format_exc())
        self._running = False

    def show_about_window(self):
        w = getattr(self, "about_window", None)
        if w is not None:
            try: w.destroy()
            except Exception: pass
            self.about_window = None

        if not hasattr(AboutWindow, "orig_pressed"):
            AboutWindow.orig_pressed = AboutWindow._pressed
            AboutWindow._pressed = self.some_func

        self.about_window = AboutWindow(
            self, module_names=self.about_module_names,
            iconbitmap=self.icon_filepath, app_name=self.app_name,
            messages=self.about_messages)
        self.place_window_relative(self.about_window, 30, 50)

    def some_func(self):
        self.title(self.title().replace(self.app_name, "rotidE paM ehT"[::-1]))
        self.app_name = "rotidE paM ehT"[::-1]
        AboutWindow.orig_pressed(self.about_window)
