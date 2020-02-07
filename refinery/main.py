#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import refinery
import tkinter as tk
import os
import sys
import webbrowser

from refinery.core import RefineryCore

from pathlib import Path
from time import time
from tkinter import messagebox
from traceback import format_exc

from binilla.windows.about_window import AboutWindow
from binilla.widgets.binilla_widget import BinillaWidget
from binilla.windows.filedialog import askopenfilename, askopenfilenames,\
     asksaveasfilename
from binilla.widgets.scroll_menu import ScrollMenu

from refinery import editor_constants as e_c
from refinery.constants import ACTIVE_INDEX, MAP_TYPE_ANY,\
     MAP_TYPE_REGULAR, MAP_TYPE_RESOURCE
from refinery.exceptions import MapAlreadyLoadedError, EngineDetectionError
from refinery.defs.config_def import config_def, bitmap_file_formats
from refinery.widgets.explorer_hierarchy_tree import ExplorerHierarchyTree
from refinery.widgets.explorer_class_tree import ExplorerClassTree
from refinery.widgets.explorer_hybrid_tree import ExplorerHybridTree
from refinery.widgets.queue_tree import QueueTree
from refinery.windows.settings_window import RefinerySettingsWindow
from refinery.windows.rename_window import RefineryRenameWindow
from refinery.windows.crc_window import RefineryChecksumEditorWindow
from refinery.util import is_path_empty

from supyr_struct.defs import constants as supyr_constants
from supyr_struct.field_types import FieldType


VALID_DISPLAY_MODES = frozenset(("hierarchy", "class", "hybrid"))
VALID_EXTRACT_MODES = frozenset(("tags", "data"))


class Refinery(tk.Tk, BinillaWidget, RefineryCore):
    config_file = None
    _config_path = Path(e_c.SETTINGS_DIR, "refinery.cfg")

    _last_dir = e_c.WORKING_DIR

    path_property_names = frozenset((
        "tags_dir", "data_dir", "tagslist_dir", "active_map_path",
        "last_dir", "config_path", "config_path",
        "icon_filepath", "app_bitmap_filepath",
        ))

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
    _window_geometry_initialized = False
    _display_mode = "hierarchy"

    font_names = e_c.font_names

    icon_filepath = Path("")
    app_bitmap_filepath = Path("")

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

    issue_tracker_url = refinery.__website__ + "/issues"

    def __init__(self, *args, **kwargs):
        self.app_name = str(kwargs.pop('app_name', self.app_name))

        # we are running a gui based program, so we want errors printed
        # rather than propogated upward(RefineryCore is designed to keep
        # working when an error that would be affected by this would occur)
        self.print_errors = self.do_printout = True

        tk.Tk.__init__(self, *args, **kwargs)
        self._tags_dir = tk.StringVar(self)
        self._data_dir = tk.StringVar(self)
        self._tagslist_path = tk.StringVar(self)

        RefineryCore.__init__(self, *args, **kwargs)
        BinillaWidget.__init__(self, *args, **kwargs)
        try:
            with Path(e_c.MOZZLIB_DIR, "tad.gsm"[::-1]).open('r', -1, "037") as f:
                setattr(self, 'segassem_tuoba'[::-1], list(l for l in f))
        except Exception:
            pass

        self.app_bitmap_filepath = e_c.REFINERY_BITMAP_PATH
        if not e_c.IS_LNX:
            self.icon_filepath = e_c.REFINERY_ICON_PATH
            if self.icon_filepath:
                self.iconbitmap(str(self.icon_filepath))

        if is_path_empty(self.icon_filepath):
            print("Could not load window icon.")

        self.title('%s v%s.%s.%s' % ((self.app_name,) + self.version))
        self.minsize(width=500, height=300)

        # make the tkinter variables
        self.extract_mode = tk.StringVar(self, "tags")
        self.show_all_fields = tk.IntVar(self)
        self.show_structure_meta = tk.IntVar(self)
        self.edit_all_fields = tk.IntVar(self)
        self.allow_corrupt = tk.IntVar(self)

        self._active_map_name = tk.StringVar(self)
        self._active_engine_name = tk.StringVar(self)

        self._autoload_resources = tk.IntVar(self, 1)
        self._do_printout  = tk.IntVar(self, 1)

        self._force_lower_case_paths = tk.IntVar(self, 1)
        self._extract_yelo_cheape = tk.IntVar(self)
        self._rename_scnr_dups = tk.IntVar(self)
        self._overwrite = tk.IntVar(self)
        self._recursive = tk.IntVar(self)
        self._decode_adpcm = tk.IntVar(self, 1)
        self._generate_uncomp_verts = tk.IntVar(self, 1)
        self._generate_comp_verts = tk.IntVar(self)
        self._use_tag_index_for_script_names = tk.IntVar(self)
        self._use_scenario_names_for_script_names = tk.IntVar(self)
        self._bitmap_extract_keep_alpha = tk.IntVar(self, 1)
        self._skip_seen_tags_during_queue_processing = tk.IntVar(self, 1)
        self._disable_safe_mode = tk.IntVar(self, 0)
        self._disable_tag_cleaning = tk.IntVar(self, 0)
        self._globals_overwrite_mode = tk.IntVar(self, 0)

        self._bitmap_extract_format = tk.StringVar(self)

        self._fix_tag_classes = tk.IntVar(self, 1)
        self._fix_tag_index_offset = tk.IntVar(self)
        self._use_minimum_priorities = tk.IntVar(self, 1)
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
            show_structure_meta=self.show_structure_meta,
            edit_all_fields=self.edit_all_fields,
            allow_corrupt=self.allow_corrupt,

            tags_dir=self._tags_dir,
            data_dir=self._data_dir,
            tagslist_path=self._tagslist_path,

            do_printout=self._do_printout,
            autoload_resources=self._autoload_resources,

            force_lower_case_paths=self._force_lower_case_paths,
            extract_yelo_cheape=self._extract_yelo_cheape,
            rename_scnr_dups=self._rename_scnr_dups,
            overwrite=self._overwrite,
            recursive=self._recursive,
            decode_adpcm=self._decode_adpcm,
            generate_uncomp_verts=self._generate_uncomp_verts,
            generate_comp_verts=self._generate_comp_verts,
            use_tag_index_for_script_names=self._use_tag_index_for_script_names,
            use_scenario_names_for_script_names=self._use_scenario_names_for_script_names,
            bitmap_extract_keep_alpha=self._bitmap_extract_keep_alpha,
            skip_seen_tags_during_queue_processing=self._skip_seen_tags_during_queue_processing,
            disable_safe_mode=self._disable_safe_mode,
            disable_tag_cleaning=self._disable_tag_cleaning,
            globals_overwrite_mode=self._globals_overwrite_mode,

            bitmap_extract_format=self._bitmap_extract_format,

            fix_tag_classes=self._fix_tag_classes,
            fix_tag_index_offset=self._fix_tag_index_offset,
            use_minimum_priorities=self._use_minimum_priorities,
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
        elif self.config_path.is_file():
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
            label="Load all resource maps", command=self.load_resource_maps_clicked)
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Unload active map",
            command=lambda s=self: s.unload_maps_clicked(MAP_TYPE_ANY))
        self.file_menu.add_command(
            label="Unload all non-resource maps",
            command=lambda s=self: s.unload_maps_clicked(MAP_TYPE_REGULAR, (ACTIVE_INDEX,), None))
        self.file_menu.add_command(
            label="Unload all resource maps",
            command=lambda s=self: s.unload_maps_clicked(MAP_TYPE_RESOURCE, (ACTIVE_INDEX,), None))
        self.file_menu.add_command(
            label="Unload all maps",
            command=lambda s=self: s.unload_maps_clicked(MAP_TYPE_ANY, (ACTIVE_INDEX,), None))
        self.file_menu.add_command(
            label="Unload all maps from all engines",
            command=lambda s=self: s.unload_maps_clicked(MAP_TYPE_ANY, None, None))
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Save map as", command=self.save_map_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.destroy)

        self.bind('<Control-o>', lambda *a, s=self: s.browse_for_maps())
        self.bind('<Control-s>', lambda *a, s=self: s.save_map_as())

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
        self.menubar.add_command(label="Report Bug", command=self.open_issue_tracker)
        self.config(menu=self.menubar)

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
        self.reload_fonts()
        self.map_info_text = tk.Text(
            self.map_info_frame, font=self.get_font("console"),
            state='disabled', height=8)
        self.map_info_text.font_type = "console"
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
            self.map_action_frame, str_variable=self._active_engine_name,
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

        app_window = self.config_file.data.app_window
        self.apply_style()

        self._initialized = True

    @property
    def tags_dir(self):
        return Path(self._tags_dir.get())
    @tags_dir.setter
    def tags_dir(self, new_val):
        self._tags_dir.set(new_val)

    @property
    def data_dir(self):
        return Path(self._data_dir.get())
    @data_dir.setter
    def data_dir(self, new_val):
        self._data_dir.set(new_val)

    @property
    def tagslist_path(self):
        return Path(self._tagslist_path.get())
    @tagslist_path.setter
    def tagslist_path(self, new_val):
        self._tagslist_path.set(new_val)

    @property
    def config_path(self):
        return self._config_path
    @config_path.setter
    def config_path(self, new_val):
        if not isinstance(new_val, Path):
            new_val = Path(new_val)
        self._config_path = new_val

    @property
    def last_dir(self):
        return self._last_dir
    @last_dir.setter
    def last_dir(self, new_val):
        if not isinstance(new_val, Path):
            new_val = Path(new_val)
        self._last_dir = new_val

    @property
    def running(self):
        return self._running

    def apply_style(self, seen=None):
        super(Refinery, self).apply_style(seen)
        if not self._window_geometry_initialized:
            app_window = self.config_file.data.app_window
            self._window_geometry_initialized = True

            if app_window.app_offset_x not in range(0, self.winfo_screenwidth()):
                app_window.app_offset_x = 0

            if app_window.app_offset_y not in range(0, self.winfo_screenheight()):
                app_window.app_offset_y = 0

            self.geometry("%sx%s+%s+%s" %
                          (app_window.app_width, app_window.app_height,
                           app_window.app_offset_x, app_window.app_offset_y))

        column_widths = self.config_file.data.column_widths
        for tree_frame in self.tree_frames.values():
            tree = tree_frame.tags_tree
            column_names = ("#0", ) + tree['columns']
            for name, width in zip(column_names, column_widths):
                tree.column(name, width=width)

        self.update_ttk_style()

    def __getattribute__(self, attr_name):
        # it would have been a LOT of boilerplate for abstracting the
        # tkinter settings variables if I didn't overload __getattribute__
        try:
            if attr_name in object.__getattribute__(self, "tk_vars",):
                val = object.__getattribute__(self, "_" + attr_name).get()
                if attr_name in self.path_property_names:
                    val = Path(val)

                return val
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

    def enqueue(self, operation="extract_tags", **kwargs):
        if operation in ("extract_tags", "extract_cheape"):
            kwargs.setdefault("out_dir", self.tags_dir)
        elif operation == "extract_data":
            kwargs.setdefault("out_dir", self.data_dir)
        RefineryCore.enqueue(self, operation, **kwargs)

    def load_config(self, filepath=None):
        if filepath is None:
            filepath = self.config_path

        filepath = Path(filepath)
        assert filepath.is_file()

        # load the config file
        self.config_file = config_def.build(filepath=filepath)
        if self.config_file.data.header.version != self.config_version:
            raise ValueError(
                "Config version is not what this application is expecting.")

        self.apply_config()

    def make_config(self, filepath=None):
        if filepath is None:
            filepath = self.config_path

        filepath = Path(filepath)

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
        fonts      = self.config_file.data.fonts

        self.tagslist_path = paths.tagslist.path
        self.tags_dir = paths.tags_dir.path
        self.data_dir = paths.data_dir.path
        self.last_dir = paths.last_dir.path

        self._display_mode = header.flags.display_mode.enum_name
        for name in ("do_printout", "autoload_resources"):
            setattr(self, name, bool(getattr(header.flags, name)))

        for attr_name in header.preview_flags.NAME_MAP:
            getattr(self, attr_name).set(
                bool(getattr(header.preview_flags, attr_name)))

        for flags in (header.extraction_flags, header.deprotection_flags):
            for attr_name in flags.NAME_MAP:
                setattr(self, attr_name, bool(getattr(flags, attr_name)))

        self.bitmap_extract_format = bitmap_file_formats[0]
        self.globals_overwrite_mode = header.globals_overwrite_mode.data

        try:
            self.panes.sash_place(0, app_window.sash_position, 1)
        except Exception:
            pass

        if header.bitmap_extract_format.enum_name in bitmap_file_formats:
            self.bitmap_extract_format = header.bitmap_extract_format.enum_name

        if header.globals_overwrite_mode.enum_name == supyr_constants.INVALID:
            self.globals_overwrite_mode = 0

        for i in range(len(fonts)):
            try:
                self.set_font_config(
                    self.font_names[i], family=fonts[i].family,
                    size=fonts[i].size, weight=("bold" if fonts[i].flags.bold
                                                else "normal"),
                    )
            except IndexError:
                pass

    def update_config(self, config_file=None):
        if config_file is None:
            config_file = self.config_file

        header        = config_file.data.header
        paths         = config_file.data.paths
        app_window    = config_file.data.app_window
        column_widths = config_file.data.column_widths
        fonts         = config_file.data.fonts

        header.version = self.config_version

        if self._initialized:
            w, geom = self.geometry().split("x")
            h, x, y = geom.split("+")
            app_window.app_width = int(w)
            app_window.app_height = int(h)
            app_window.app_offset_x = int(x)
            app_window.app_offset_y = int(y)

        # make sure there are enough entries in the paths
        if len(paths.NAME_MAP) > len(paths):
            paths.extend(len(paths.NAME_MAP) - len(paths))

        paths.tagslist.path = "" if is_path_empty(self.tagslist_path) else str(self.tagslist_path)
        paths.tags_dir.path = "" if is_path_empty(self.tags_dir) else str(self.tags_dir)
        paths.data_dir.path = "" if is_path_empty(self.data_dir) else str(self.data_dir)
        paths.last_dir.path = "" if is_path_empty(self.last_dir) else str(self.last_dir)

        header.flags.display_mode.set_to(self._display_mode)
        for attr_name in ("do_printout", "autoload_resources"):
            setattr(header.flags, attr_name, getattr(self, attr_name))

        for attr_name in header.preview_flags.NAME_MAP:
            setattr(header.preview_flags, attr_name,
                    getattr(self, attr_name).get())

        for flags in (header.extraction_flags, header.deprotection_flags):
            for attr_name in flags.NAME_MAP:
                setattr(flags, attr_name, getattr(self, attr_name))

        header.bitmap_extract_format.set_to(bitmap_file_formats[0])
        header.globals_overwrite_mode.data = self.globals_overwrite_mode

        if self.bitmap_extract_format in bitmap_file_formats:
            header.bitmap_extract_format.set_to(self.bitmap_extract_format)

        if header.globals_overwrite_mode.enum_name == supyr_constants.INVALID:
            header.globals_overwrite_mode.data = 0

        try:
            active_tree = self.tree_frames[self._display_mode + "_tree"]
            tree = active_tree.tags_tree
            widths = [tree.column(name)["width"] for name in
                      (("#0", ) + tree['columns'])]
        except Exception:
            widths = [200, 45, 10, 10, 12, 70, 50]

        del column_widths[:]
        for width in widths:
            column_widths.append(width)

        config_file.data.set_size(None, "column_widths")

        try:
            # idk if this value can ever be negative, so i'm using abs
            app_window.sash_position = abs(self.panes.sash_coord(0)[0])
        except Exception:
            app_window.sash_position = sum(widths)

        for i in range(len(self.font_names)):
            try:
                font_block = fonts[i]
            except IndexError:
                fonts.append()
                try:
                    font_block = fonts[i]
                except IndexError:
                    continue

            try:
                font_cfg = self.get_font_config(self.font_names[i])
                font_block.family = font_cfg.family
                font_block.size = font_cfg.size
                font_block.flags.bold = font_cfg.weight == "bold"
            except IndexError:
                pass

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

        valid_classes = None
        if new_mode == "tags":
            next_mode = "data"
        elif new_mode == "data":
            next_mode = "tags"
            if self.active_map is not None:
                valid_classes = self.active_map.data_extractors.keys()
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
        engine = None
        engines = sorted(n for n in self._maps_by_engine if n != ACTIVE_INDEX)

        if isinstance(name_or_index, int):
            if name_or_index in range(len(engines)):
                engine = engines[name_or_index]
        elif name_or_index is None and engines:
            engine = iter(sorted(engines)).__next__()
        elif name_or_index in engines:
            engine = name_or_index

        if engine is None and not force_reload:
            return

        next_maps = self._maps_by_engine.get(engine)
        if self.active_maps is next_maps and not force_reload:
            # selected same engine. nothing to change
            return
        elif not next_maps:
            next_map_name = None
        elif map_name in next_maps:
            next_map_name = map_name
        elif next_maps.get(ACTIVE_INDEX):
            next_map_name = next_maps[ACTIVE_INDEX].map_name
        else:
            next_map_name = iter(sorted(next_maps)).__next__()

        # unset any currently active engine and only set
        # it if we have a valid map name to make active
        self._maps_by_engine.pop(ACTIVE_INDEX, None)
        if next_map_name:
            self._maps_by_engine[ACTIVE_INDEX] = next_maps
            next_maps.pop(ACTIVE_INDEX, None)

        self.active_engine_name = engine if next_maps else ""
        # set the active map BEFORE reloading the options. this ensures
        # the active map name is properly displayed in the scroll menu
        self.set_active_map(next_map_name, True)
        self.reload_map_select_options()

    def set_active_map(self, name_or_index=None, force_reload=False):
        map_name = None
        map_names = sorted(n for n in self.active_maps if n != ACTIVE_INDEX)
        if name_or_index in range(len(map_names)):
            map_name = map_names[name_or_index]
        elif name_or_index in map_names:
            map_name = name_or_index

        prev_map = self.active_map
        RefineryCore.set_active_map(self, map_name)
        if self.active_map is not prev_map or force_reload:
            self.display_map_info()
            valid_classes = None
            if self.active_map is not None and self.extract_mode.get() == "data":
                valid_classes = self.active_map.data_extractors.keys()

            for tree in self.tree_frames.values():
                tree.valid_classes = valid_classes

            self.reload_explorers()

    def reload_engine_select_options(self):
        opts = dict(self._maps_by_engine)
        opts.pop(ACTIVE_INDEX, None)
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
        opts.pop(ACTIVE_INDEX, None)
        if opts:
            opts = sorted(opts.keys())
        else:
            opts = ("Loaded maps", )

        menu = self.map_select_menu
        sel_name = self.active_map_name
        sel_index = opts.index(sel_name) if sel_name in opts else 0
        menu.set_options(opts)
        menu.sel_index = sel_index

    def unload_maps_clicked(self, map_type=MAP_TYPE_REGULAR,
                            engines_to_unload=(ACTIVE_INDEX, ),
                            maps_to_unload=(ACTIVE_INDEX, )):
        if self._running:
            return
        self._running = True

        try:
            self.unload_maps(map_type, engines_to_unload, maps_to_unload)
        except Exception:
            print(format_exc())
        self._running = False

    def unload_maps(self, map_type=False, engines_to_unload=(ACTIVE_INDEX, ),
                    maps_to_unload=(ACTIVE_INDEX, )):
        RefineryCore.unload_maps(self, map_type, engines_to_unload,
                                 maps_to_unload)

        self.reload_map_select_options()
        if not self.active_maps:
            self.set_active_engine(force_reload=True)
        elif not self.active_map:
            self.set_active_map(force_reload=True)

    def load_map(self, map_path, make_active=True, ask_close_open=False, **kw):
        autoload_resources = kw.pop("autoload_resources", self.autoload_resources)
        new_map = prev_active_engine = prev_active_map = None
        try:
            new_map = RefineryCore.load_map(
                self, map_path, not ask_close_open, make_active=False,
                autoload_resources=False, decompress_overwrite=True)
        except MapAlreadyLoadedError:
            if not(ask_close_open and messagebox.askyesno(
                    "A map with that name is already loaded!",
                    ('A map with the same name as "%s" is already loaded. '
                     "Close that map and load this one instead?") %
                    Path(map_path).stem, icon='warning', parent=self)):
                print("    Skipped")
                return

            prev_active_engine = self.active_engine_name
            prev_active_map = self.active_map_name
            new_map = RefineryCore.load_map(
                self, map_path, True, make_active=False,
                autoload_resources=False)

            if (new_map.engine == prev_active_engine and
                new_map.map_name == prev_active_map):
                # if the map was active before we closed it, make the
                # newly loaded map active in its place.
                make_active = True
        except Exception:
            try:
                self.unload_maps(None)
            except Exception:
                print(format_exc())
            raise

        if autoload_resources:
            self.load_resource_maps(new_map)

        if make_active:
            self.set_active_engine(
                new_map.engine, new_map.map_name, force_reload=True)

        return new_map

    def load_maps(self, map_paths, make_active=False, ask_close_open=False, **kw):
        if not map_paths:
            return

        first_map = None
        for map_path in map_paths:
            try:
                new_map = self.load_map(map_path, False, ask_close_open, **kw)

                if new_map is not None and first_map is None:
                    first_map = new_map
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
        if make_active and first_map is not None:
            self.set_active_engine(
                first_map.engine, first_map.map_name, force_reload=True)

    def load_resource_maps_clicked(self):
        if self.active_map is None:
            return
        elif self.running:
            return

        self._running = True
        try:
            self.update()
            self.load_resource_maps()
        except Exception:
            print(format_exc())
            self.reload_engine_select_options()

        self._running = False

    def load_resource_maps(self, halo_map=None, maps_dir=Path(""), map_paths=(), **kw):
        if halo_map is None:
            halo_map = self.active_map

        if not halo_map:
            return

        nothing_to_load = True
        for name in halo_map.get_resource_map_paths():
            if name not in halo_map.maps:
                nothing_to_load = False

        if nothing_to_load:
            return

        print("Loading resource maps for: %s" % halo_map.map_name)
        kw.setdefault("do_printout", True)
        if is_path_empty(maps_dir):
            maps_dir = halo_map.filepath.parent

        not_loaded = RefineryCore.load_resource_maps(
            self, halo_map, maps_dir, (), **kw)

        asked = set()
        for map_name in sorted(not_loaded):
            if map_name in asked or halo_map.maps.get(map_name) is not None:
                continue

            asked.add(map_name)
            map_path = askopenfilename(
                initialdir=maps_dir, title="Select the %s.map" % map_name,
                filetypes=((map_name, "*.map"), (map_name, "*.map.dtz"),
                           ("All", "*.*")))

            map_path = Path(map_path)
            if is_path_empty(map_path):
                print("You wont be able to extract from %s.map" % map_name)
                continue

            RefineryCore.load_resource_maps(self, halo_map, map_path.parent,
                                            {map_name: map_path}, **kw)

        print("    Finished loading resource maps")
        self.reload_engine_select_options()

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

    def deprotect(self, save_path=None, map_name=ACTIVE_INDEX,
                  engine=ACTIVE_INDEX, **kw):
        halo_map = self._maps_by_engine.get(engine, {}).get(map_name)

        if halo_map is None:
            if engine != ACTIVE_INDEX and map_name != ACTIVE_INDEX:
                print('No map named "%s" under engine "%s" is loaded.' %
                      (map_name, engine))
            return
        elif halo_map.is_resource:
            print("Cannot deprotect resource maps.")
            return
        elif halo_map.engine not in ("halo1ce", "halo1yelo",
                                     "halo1pc", "halo1vap"):
            print("Cannot deprotect this kind of map.")
            return

        if is_path_empty(save_path):
            filetypes = [("All", "*")]
            if halo_map.engine == "halo1vap":
                filetypes.insert(0, ("Halo mapfile(chimerified)", "*.vap"))
            elif halo_map.engine == "halo1yelo":
                filetypes.insert(0, ("Halo mapfile(extra sauce)", "*.yelo"))
            else:
                filetypes.insert(0, ("Halo mapfile", "*.map"))

            save_path = asksaveasfilename(
                initialdir=halo_map.filepath.parent, parent=self,
                title="Choose where to save the deprotected map",
                filetypes=filetypes)

        save_path = Path(save_path)

        if is_path_empty(save_path):
            print("Deprotection cancelled.")
            return

        self._running = True
        try:
            if not save_path.suffix:
                save_path = save_path.with_suffix(
                    '.yelo' if 'yelo' in halo_map.engine else '.map')

            start = time()

            RefineryCore.deprotect(self, save_path, map_name, engine, **kw)
            print("Completed. Took %s seconds." % round(time() - start, 1))
        except Exception:
            print(format_exc())

        self._running = False

    def repair_tag_classes(self, map_name=ACTIVE_INDEX, engine=ACTIVE_INDEX):
        print("Repairing tag classes...")
        halo_map = self._maps_by_engine.get(engine, {}).get(map_name)
        if not halo_map:
            return {}

        tag_index_array = halo_map.tag_index.tag_index
        repaired = RefineryCore.repair_tag_classes(self, map_name, engine)

        print("    Deprotected classes of %s of the %s total tags(%s%%)." %
              (len(repaired), len(tag_index_array),
               1000*len(repaired)//len(tag_index_array)/10))

        print()
        if len(repaired) != len(tag_index_array):
            print("The deprotector could not reach these tags:\n"
                  "  (This does not mean they are protected. It could just\n"
                  "   mean that they aren't actually used in any way)\n"
                  "  [ id,  offset,  type,  path ]\n")
            for i in range(len(tag_index_array)):
                if i in repaired:
                    continue
                b = tag_index_array[i]
                try:
                    print("  [ %s, %s, %s, %s ]" % (
                        i, b.meta_offset - halo_map.map_magic,
                        b.class_1.enum_name, b.path))
                except Exception:
                    print("  [ %s, %s, %s ]" % (
                        i, b.meta_offset - halo_map.map_magic,
                        supyr_constants.UNPRINTABLE))
            print()

        return repaired

    def sanitize_resource_tag_paths(self, path_handler, map_name=ACTIVE_INDEX,
                                    engine=ACTIVE_INDEX):
        print("Renaming tags using resource map tag paths...")
        RefineryCore.sanitize_resource_tag_paths(self, path_handler,
                                                 map_name, engine)

    def _script_scrape_deprotect(self, tag_path_handler, map_name=ACTIVE_INDEX,
                                 engine=ACTIVE_INDEX, **kw):
        print("Renaming tags using script strings...")
        RefineryCore._script_scrape_deprotect(self, tag_path_handler,
                                              map_name, engine, **kw)

    def _heuristics_deprotect(self, tag_path_handler, map_name=ACTIVE_INDEX,
                              engine=ACTIVE_INDEX, **kw):
        print("Renaming tags using heuristics...")
        RefineryCore._heuristics_deprotect(self, tag_path_handler,
                                           map_name, engine, **kw)
    def save_map_as(self, e=None):
        # NOTE: This function now returns a Path instead of a string
        halo_map = self.active_map

        if self.running or halo_map is None:
            return Path("")
        elif halo_map.is_resource:
            print("Cannot save resource maps.")
            return Path("")
        elif halo_map.engine not in ("halo1ce", "halo1yelo",
                                     "halo1pc", "halo1vap"):
            print("Cannot save this kind of map.")
            return Path("")

        filetypes = [("All", "*")]
        if halo_map.engine == "halo1vap":
            filetypes.insert(0, ("Halo mapfile(chimerified)", "*.vap"))
        elif halo_map.engine == "halo1yelo":
            filetypes.insert(0, ("Halo mapfile(extra sauce)", "*.yelo"))
        else:
            filetypes.insert(0, ("Halo mapfile", "*.map"))

        save_path = asksaveasfilename(
            initialdir=self.active_map_path.parent, parent=self,
            title="Choose where to save the map",
            filetypes=tuple(filetypes))

        save_path = Path(save_path)
        if is_path_empty(save_path):
            return Path("")

        self._running = True
        try:
            save_path = self.save_map(
                save_path, prompt_strings_expand=True,
                prompt_internal_rename=True)
        except Exception:
            print(format_exc())
        self._running = False
        return save_path

    def save_map(self, save_path=None, map_name=ACTIVE_INDEX,
                 engine=ACTIVE_INDEX, **kw):
        # NOTE: This function now returns a Path instead of a string
        reload_window = kw.pop("reload_window", True)
        prompt_strings_expand = kw.pop("prompt_strings_expand", False)
        prompt_internal_rename = kw.pop("prompt_internal_rename", False)

        halo_map = self._maps_by_engine.get(engine, {}).get(map_name)
        if halo_map is None:
            return Path("")
        elif halo_map.is_resource:
            print("Cannot save resource maps.")
            return Path("")
        elif halo_map.engine not in ("halo1ce", "halo1yelo",
                                     "halo1pc", "halo1vap"):
            print("Cannot save this kind of map.")
            return Path("")
        elif save_path is None or is_path_empty(save_path):
            save_path = halo_map.filepath

        save_path = Path(save_path)

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
            return Path("")

        new_map_name = save_path.name
        if (prompt_internal_rename and len(new_map_name) < 32 and
            halo_map.map_name.lower() != new_map_name.lower()):
            if messagebox.askyesno(
                    "Internal name mismatch",
                    ("A maps internal and file names must match for Halo "
                     "to be able to properly load them. Do you want to "
                     "change the internal name to match its filename?"),
                    icon='question', parent=self):
                halo_map.map_header.map_name = new_map_name

        print('Saving "%s"' % save_path)
        try:
            save_path = RefineryCore.save_map(
                self, save_path, map_name, engine, **kw)
            print("    Finished")
        except Exception:
            print(format_exc())
            print("    Could not save map")

        if reload_window and not is_path_empty(save_path):
            print("Reloading map to apply changes...")
            self.load_map(save_path, make_active=True, autoload_resources=False)

        return save_path

    def start_extraction(self, e=None):
        if self.running:
            return

        if not self.map_loaded:
            return
        elif not self.queue_tree.queue_info:
            self.queue_add_all()
            if not self.queue_tree.queue_info:
                return

        self._running = True
        try:
            self.process_queue()
        except Exception:
            print(format_exc())
        self._running = False

    def process_queue(self, **kw):
        # lets be a lazy fuck and generate self._extract_queue
        # on the fly rather than reworking a lot of the widgets
        # module to work with RefineryQueueItem
        del self._extract_queue[:]
        cheapes = set()

        for queue_item_iid in self.queue_tree.get_item_names():
            settings = self.queue_tree.get_item(queue_item_iid)
            op_kw = {k: v.get() for k, v in
                     settings.items() if k in self.tk_vars}
            if "out_dir" in settings:
                op_kw["out_dir"] = settings["out_dir"].get()

            tag_ids = list(b.id & 0xFFff for b in settings["tag_index_refs"])

            engine = op_kw["engine"] = settings['halo_map'].engine
            map_name = op_kw["map_name"] = settings['halo_map'].map_name

            engine_map_key = (engine, map_name)
            if (op_kw.get("extract_yelo_cheape", self.extract_yelo_cheape)
                and engine_map_key not in cheapes and engine == "halo1yelo"):
                self.enqueue("extract_cheape", **op_kw)
                cheapes.add(engine_map_key)

            self.enqueue("extract_tags"
                         if op_kw["extract_mode"] == "tags" else
                         "extract_data",
                         queue_item_iid=queue_item_iid, tag_ids=tag_ids,
                         **op_kw)

        tags_by_map, data_by_map = RefineryCore.process_queue(self, **kw)
        items_extracted = sum(len(item) for item in tags_by_map.values()) +\
                          sum(len(item) for item in data_by_map.values())

        if not items_extracted:
            print("Nothing was extracted. This might be a permissions issue.\n"
                  "Close Refinery and run it as admin to potentially fix this.")

    def prompt_globals_overwrite(self, halo_map, tag_id):
        map_name = halo_map.map_name
        tag_name = halo_map.tag_index.tag_index[tag_id & 0xFFff].path
        ans = messagebox.askyesno(
            "Attempting to overwrite existing globals",
            ('The tag "%s.globals" already exists in the extraction directory. '
             'Do you want to overwrite it with the globals from the map "%s"?') %
            (tag_name, map_name), icon='warning', parent=self)
        return bool(ans)

    def process_queue_item(self, queue_item, **kw):
        self.update_idletasks()
        try:
            del self.queue_tree.queue_info[queue_item.queue_item_iid]
            self.queue_tree.tags_tree.delete(queue_item.queue_item_iid)
            self.update()
        except Exception:
            pass

        self.update_idletasks()
        RefineryCore.process_queue_item(self, queue_item, **kw)

    def reload_explorers(self):
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
            filetypes=(("Halo mapfile", "*.map *.yelo *.vap *.map.dtz"),
                       ("Halo mapfile(vanilla)", "*.map"),
                       ("Halo mapfile(extra sauce)", "*.yelo"),
                       ("Halo mapfile(chimerified)", "*.vap"),
                       ("Halo 2 Vista compressed mapfile", "*.map.dtz"),
                       ("All", "*")))

        if not fps:
            return

        fps = tuple(Path(fp) for fp in fps)
        self.last_dir = fps[0].parent

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
            iconbitmap=self.icon_filepath, appbitmap=self.app_bitmap_filepath,
            app_name=self.app_name, messages=self.about_messages)
        self.place_window_relative(self.about_window, 30, 50)

    def open_issue_tracker(self):
        webbrowser.open_new_tab(self.issue_tracker_url)

    def some_func(self):
        self.title(self.title().replace(self.app_name, "rotidE paM ehT"[::-1]))
        self.app_name = "rotidE paM ehT"[::-1]
        AboutWindow.orig_pressed(self.about_window)
