print_startup = True  # __name__ == "__main__"
if print_startup:
    print("Refinery is warming up...")

import tkinter as tk
import os
import zlib

from os.path import dirname, exists, join, isfile, splitext
from struct import unpack
from time import time
from tkinter.font import Font
from tkinter import messagebox
from tkinter.filedialog import askopenfilename, asksaveasfilename, askdirectory
from tkinter.font import Font
from traceback import format_exc
     

if print_startup:
    print("    Importing supyr_struct modules")

from supyr_struct.buffer import BytearrayBuffer, PeekableMmap
from supyr_struct.defs.constants import *
from supyr_struct.defs.util import *
from supyr_struct.field_types import FieldType


if print_startup:
    print("    Importing refinery modules")

from .class_repair import class_repair_functions, class_bytes_by_fcc
from .data_extraction import VALID_H1_DATA_TAGS, VALID_H2_DATA_TAGS
from .widgets import QueueTree, RefinerySettingsWindow,\
     RefineryRenameWindow, ExplorerHierarchyTree, ExplorerClassTree,\
     ExplorerHybridTree, is_protected
from .loaded_map import *
from .util import *
from . import halo1_methods, halo2_methods
from .defs.config_def import config_def


if print_startup:
    print("    Loading halo 1 map definitions")

from reclaimer.meta.halo_map import get_map_version, get_map_header,\
     get_tag_index, get_index_magic, get_map_magic,\
     decompress_map, get_is_compressed_map, tag_index_pc_def
from reclaimer.meta.resource import resource_def


if print_startup:
    print("    Loading halo 1 open sauce tag definitions")

from reclaimer.hek.defs.sbsp import sbsp_meta_header_def
from reclaimer.os_hek.defs.gelc import gelc_def
from reclaimer.os_hek.defs.gelo    import gelo_def as old_gelo_def
from reclaimer.os_v4_hek.defs.gelo import gelo_def as gelo_def
from reclaimer.os_v4_hek.defs.antr import antr_def
from reclaimer.os_v4_hek.defs.bipd import bipd_def
from reclaimer.os_v4_hek.defs.cdmg import cdmg_def
from reclaimer.os_v4_hek.defs.coll import coll_def
from reclaimer.os_v4_hek.defs.jpt_ import jpt__def
from reclaimer.os_v4_hek.defs.mode import mode_def
from reclaimer.os_v4_hek.defs.soso import soso_def
from reclaimer.os_v4_hek.defs.unit import unit_def
from reclaimer.os_v4_hek.defs.vehi import vehi_def
from reclaimer.os_v4_hek.defs.sbsp import fast_sbsp_def
from reclaimer.os_v4_hek.defs.coll import fast_coll_def
from reclaimer.os_v4_hek.handler import OsV4HaloHandler, NO_LOC_REFS


#if print_startup:
#    print("    Loading halo 2 tag definitions")
    
from reclaimer.h2.handler import Halo2Handler
from reclaimer.h2.defs.bitm import bitm_meta_def as h2_bitm_meta_def


if print_startup:
    print("    Loading stubbs tag definitions")

from reclaimer.stubbs.defs.antr import antr_def as stubbs_antr_def
from reclaimer.stubbs.defs.cdmg import cdmg_def as stubbs_cdmg_def
from reclaimer.stubbs.defs.coll import coll_def as stubbs_coll_def
from reclaimer.stubbs.defs.jpt_ import jpt__def as stubbs_jpt__def
from reclaimer.stubbs.defs.mode import mode_def as stubbs_mode_def,\
     pc_mode_def as stubbs_pc_mode_def
from reclaimer.stubbs.defs.soso import soso_def as stubbs_soso_def
from reclaimer.stubbs.defs.sbsp import fast_sbsp_def as stubbs_fast_sbsp_def
from reclaimer.stubbs.defs.coll import fast_coll_def as stubbs_fast_coll_def
#from reclaimer.stubbs.defs.imef import imef_def
#from reclaimer.stubbs.defs.terr import terr_def
#from reclaimer.stubbs.defs.vege import vege_def


if print_startup:
    print("    Initializing Refinery")


def run():
    return Refinery()

this_dir = dirname(__file__)
default_config_path = join(this_dir, 'refinery.cfg')

VALID_DISPLAY_MODES = frozenset(("hierarchy", "class", "hybrid"))
VALID_EXTRACT_MODES = frozenset(("tags", "data"))


def halo2_tag_index_to_halo1_tag_index(map_header, tag_index):
    new_index = tag_index_pc_def.build()
    old_index_array = tag_index.tag_index
    new_index_array = new_index.tag_index

    # copy information from the h2 index into the h1 index
    new_index.scenario_tag_id[:] = tag_index.scenario_tag_id[:]
    new_index.tag_index_offset = tag_index.tag_index_offset
    new_index.tag_count = tag_index.tag_count

    tag_types = {}
    for typ in tag_index.tag_types:
        tag_types[typ.class_1.data] = [typ.class_1, typ.class_2, typ.class_3]

    for i in range(len(old_index_array)):
        old_index_entry = old_index_array[i]
        new_index_array.append()
        new_index_entry = new_index_array[-1]
        if old_index_entry.tag_class.data not in tag_types:
            new_index_entry.tag.tag_path = "reserved for main map"
            new_index_entry.id.tag_table_index = i
            continue

        types = tag_types[old_index_entry.tag_class.data]
        new_index_entry.class_1 = types[0]
        new_index_entry.class_2 = types[1]
        new_index_entry.class_3 = types[2]

        new_index_entry.id = old_index_entry.id
        new_index_entry.meta_offset = old_index_entry.offset

        #new_index_entry.path_offset = ????
        new_index_entry.tag.tag_path = map_header.strings.\
                                       tag_name_table[i].tag_name

    return new_index


def halo3_tag_index_to_halo1_tag_index(map_header, tag_index):
    new_index = tag_index_pc_def.build()
    old_index_array = tag_index.tag_index
    new_index_array = new_index.tag_index

    # copy information from the h2 index into the h1 index
    new_index.tag_index_offset = tag_index.tag_index_offset
    new_index.tag_count = tag_index.tag_count

    tag_types = [(typ.class_1, typ.class_2, typ.class_3)
                 for typ in tag_index.tag_types]

    for i in range(len(old_index_array)):
        old_index_entry = old_index_array[i]
        new_index_array.append()
        new_index_entry = new_index_array[-1]
        if old_index_entry.tag_type_index >= len(tag_types):
            new_index_entry.tag.tag_path = "reserved for main map"
            new_index_entry.id.tag_table_index = i
            continue

        types = tag_types[old_index_entry.tag_type_index]
        new_index_entry.class_1 = types[0]
        new_index_entry.class_2 = types[1]
        new_index_entry.class_3 = types[2]

        new_index_entry.id[:] = (i, old_index_entry.table_index)
        new_index_entry.meta_offset = old_index_entry.offset

        #new_index_entry.path_offset = ????
        new_index_entry.tag.tag_path = map_header.strings.\
                                       tag_name_table[i].tag_name

    return new_index


class Refinery(tk.Tk):
    tk_map_path = None
    tk_tags_dir = None
    tk_data_dir = None
    last_dir = this_dir

    config_path = default_config_path
    config_file = None

    config_version = 1
    version = (1, 3, 3)

    data_extract_window = None
    settings_window     = None
    rename_window       = None

    tk_vars = None
    tree_frames = None
    hierarchy_tree = None
    hybrid_tree    = None
    class_tree     = None

    _map_loaded = False
    _running = False
    _initialized = False
    _display_mode = "hierarchy"
    stop_processing = False

    # dictionary of all loaded maps by their names
    maps = None

    ce_sound_offsets_by_path = None

    handler = None
    halo1_handler = None
    halo2_handler = None

    # a cache of all the different headers for
    # each type of tag to speed up writing tags
    tag_headers = None
    halo1_tag_headers = None
    halo2_tag_headers = None

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.title("Refinery v%s.%s.%s" % self.version)
        self.minsize(width=500, height=300)

        self.maps = {}

        # make the tkinter variables
        self.tk_map_path = tk.StringVar(self)
        self.tk_tags_dir = tk.StringVar(
            self, join(this_dir, "tags", ""))
        self.tk_data_dir = tk.StringVar(
            self, join(this_dir, "data", ""))
        self.tags_list_path = tk.StringVar(
            self, join(this_dir, "tags", "tagslist.txt"))
        self.extract_mode = tk.StringVar(self, "tags")
        self.fix_tag_classes = tk.IntVar(self, 1)
        self.fix_tag_index_offset = tk.IntVar(self)
        self.use_hashcaches = tk.IntVar(self)
        self.use_heuristics = tk.IntVar(self)
        self.use_old_gelo = tk.IntVar(self)
        self.extract_cheape = tk.IntVar(self)
        self.extract_from_ce_resources = tk.IntVar(self, 1)
        self.rename_duplicates_in_scnr = tk.IntVar(self)
        self.overwrite = tk.IntVar(self)
        self.recursive = tk.IntVar(self)
        self.show_output = tk.IntVar(self, 1)

        self.tk_vars = dict(
            fix_tag_classes=self.fix_tag_classes,
            fix_tag_index_offset=self.fix_tag_index_offset,
            use_hashcaches=self.use_hashcaches,
            use_heuristics=self.use_heuristics,
            rename_duplicates_in_scnr=self.rename_duplicates_in_scnr,
            extract_from_ce_resources=self.extract_from_ce_resources,
            overwrite=self.overwrite,
            use_old_gelo=self.use_old_gelo,
            extract_cheape=self.extract_cheape,
            recursive=self.recursive,
            show_output=self.show_output,
            tags_dir=self.tk_tags_dir,
            data_dir=self.tk_data_dir,
            tags_list_path=self.tags_list_path,
            extract_mode=self.extract_mode
            )

        if self.config_file is not None:
            pass
        elif exists(self.config_path):
            # load the config file
            try:
                self.load_config()
            except Exception:
                print(format_exc())
                self.make_config()
        else:
            # make a config file
            self.make_config()

        # menubar
        self.menubar = tk.Menu(self)
        self.file_menu = tk.Menu(self.menubar, tearoff=False)
        self.edit_menu = tk.Menu(self.menubar, tearoff=False)
        self.file_menu.add_command(
            label="Load map", command=self.map_path_browse)
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Unload Map", command=self.unload_maps)
        self.file_menu.add_command(
            label="Save map as", command=self.save_map_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.destroy)

        self.edit_menu.add_command(
            label="Rename map", command=self.show_rename)

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
            self.add_del_frame, text="Add\nAll", width=4,
            command=self.queue_add_all)
        self.del_all_button = tk.Button(
            self.add_del_frame, text="Del\nAll", width=4,
            command=self.queue_del_all)

        # pack everything
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

        # we wont need the ability to search for reflexives, rawdata refs,
        # or fps stuff, so set those to NO_LOC_REFS so they aren't generated.
        # This will speed up loading.
        OsV4HaloHandler.reflexive_cache = NO_LOC_REFS
        OsV4HaloHandler.raw_data_cache = NO_LOC_REFS
        OsV4HaloHandler.fps_dependent_cache = NO_LOC_REFS
        if print_startup:
            print("    Loading all tag definitions")

        self.halo1_handler = OsV4HaloHandler()
        self.halo2_handler = Halo2Handler()

        self.handler = self.halo1_handler

        self.halo1_handler.add_def(gelc_def)
        #self.halo1_handler.add_def(imef_def)
        #self.halo1_handler.add_def(terr_def)
        #self.halo1_handler.add_def(vege_def)

        self.halo1_tag_headers = h1_tag_headers = {}
        self.halo2_tag_headers = h2_tag_headers = {}

        # create a bunch of tag headers for each type of halo 1 tag
        defs = self.halo1_handler.defs
        for def_id in sorted(defs):
            if len(def_id) != 4:
                continue
            h_desc = defs[def_id].descriptor[0]
            
            h_block = [None]
            h_desc['TYPE'].parser(h_desc, parent=h_block, attr_index=0)
            h1_tag_headers[def_id] = bytes(
                h_block[0].serialize(buffer=BytearrayBuffer(),
                                     calc_pointers=False))

        for block_def in (stubbs_antr_def, stubbs_coll_def, stubbs_mode_def,
                          stubbs_soso_def):
            h_block = [None]
            def_id = block_def.def_id
            h_desc = block_def.descriptor[0]
            h_desc['TYPE'].parser(h_desc, parent=h_block, attr_index=0)
            h1_tag_headers[def_id + "_halo"]   = h1_tag_headers[def_id]
            h1_tag_headers[def_id + "_stubbs"] = bytes(
                h_block[0].serialize(buffer=BytearrayBuffer(), calc_pointers=0))

        self._initialized = True


    # These methods are kept in separate files for organizational purposes
    load_halo1_resource_map = halo1_methods.load_resource_map

    halo1_meta_to_tag_data = halo1_methods.meta_to_tag_data
    halo2_meta_to_tag_data = halo2_methods.meta_to_tag_data
    
    inject_halo1_rawdata = halo1_methods.inject_rawdata
    inject_halo2_rawdata = halo2_methods.inject_rawdata

    load_all_halo1_resource_maps = halo1_methods.load_all_resource_maps
    load_all_halo2_resource_maps = halo2_methods.load_all_resource_maps

    @property
    def running(self):
        return self._running

    @property
    def tags_dir(self):
        return self.tk_tags_dir.get()

    @property
    def active_map(self):
        return self.maps.get("active", NO_MAP)

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
        for attr_name in ("show_output", ):
            getattr(self, attr_name).set(bool(getattr(flags, attr_name)))

        flags = header.extraction_flags
        for attr_name in ("use_old_gelo", "extract_cheape", "overwrite",
                          "extract_from_ce_resources", "recursive",
                          "rename_duplicates_in_scnr", ):
            getattr(self, attr_name).set(bool(getattr(flags, attr_name)))

        flags = header.deprotection_flags
        for attr_name in ("fix_tag_classes", "fix_tag_index_offset",
                          "use_hashcaches", "use_heuristics", ):
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
        for attr_name in ("show_output", ):
            setattr(flags, attr_name, getattr(self, attr_name).get())

        flags = header.extraction_flags
        for attr_name in ("use_old_gelo", "extract_cheape", "overwrite",
                          "extract_from_ce_resources", "recursive",
                          "rename_duplicates_in_scnr", ):
            setattr(flags, attr_name, getattr(self, attr_name).get())

        flags = header.deprotection_flags
        for attr_name in ("fix_tag_classes", "fix_tag_index_offset",
                          "use_hashcaches", "use_heuristics", ):
            setattr(flags, attr_name, getattr(self, attr_name).get())

    def save_config(self, e=None):
        try:
            self.config_file.data.header.parse(attr_index="date_modified")
        except Exception:
            print(format_exc())
        self.config_file.serialize(temp=0, backup=0, calc_pointers=0)
        self.apply_config()

    def get_meta_descriptor(self, tag_cls):
        desc = None
        engine = self.active_map.engine
        if "halo_reach" in engine:
            pass
        elif "halo5" in engine:
            pass
        elif "halo4" in engine:
            pass
        elif "halo3" in engine:
            pass
        elif "halo2" in engine:
            if tag_cls == "bitm":
                desc = h2_bitm_meta_def.descriptor
        else:
            tagdef = self.halo1_handler.defs.get(tag_cls)
            if tag_cls == "gelo" and self.use_old_gelo.get():
                tagdef = old_gelo_def

            if tagdef is not None:
                desc = tagdef.descriptor[1]

        return desc

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
            if tree.tag_index is None:
                tree.reload(self.active_map.tag_index)
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
        elif new_mode == "tags":
            next_mode = "data"
        else:
            next_mode = "tags"

        engine = self.active_map.engine
        if new_mode == "tags":
            valid_classes = None
        elif "halo1" in engine or "stubbs" in engine:
            valid_classes = VALID_H1_DATA_TAGS
        elif "halo2" in engine:
            valid_classes = VALID_H2_DATA_TAGS
        else:
            return

        self.menubar.entryconfig(5, label="Switch to %s extraction" % next_mode)

        self.extract_mode.set(new_mode)

        for tree in self.tree_frames.values():
            tree.tag_index = None
            tree.valid_classes = valid_classes
            tree.reload()

        curr_tree = self.tree_frames.get(self._display_mode + "_tree")
        if curr_tree is not None:
            curr_tree.reload(self.active_map.tag_index)

    def show_settings(self, e=None):
        if self.settings_window is not None or self.running:
            return

        self.settings_window = RefinerySettingsWindow(
            self, tk_vars=self.tk_vars)
        # make sure the window gets a chance to set its size
        self.settings_window.update()
        self.place_window_relative(self.settings_window)

    def show_rename(self, e=None):
        if not(self.rename_window is None and
               self._map_loaded) or self.running:
            return
        elif self.active_map.is_resource:
            print("Cannot rename resource maps.")
            return

        self.rename_window = RefineryRenameWindow(self)
        # make sure the window gets a chance to set its size
        self.rename_window.update()
        self.place_window_relative(self.rename_window)

    def destroy(self, e=None):
        self.unload_maps()
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
        if not self._map_loaded:
            return

        if self._display_mode == "hierarchy":
            self.hierarchy_tree.activate_item()
        elif self._display_mode == "class":
            self.class_tree.activate_item()
        elif self._display_mode == "hybrid":
            self.hybrid_tree.activate_item()

    def queue_add_all(self, e=None):
        if not self._map_loaded:
            return

        if self._display_mode == "hierarchy":
            tree_frame = self.hierarchy_tree
        elif self._display_mode == "class":
            tree_frame = self.class_tree
        elif self._display_mode == "hybrid":
            tree_frame = self.hybrid_tree
        else:
            return

        tags_tree = tree_frame.tags_tree

        # get the current selection
        curr_sel = tags_tree.selection()
        # select all the tags
        tags_tree.selection_set(tags_tree.get_children())
        # tell the tree_frame to add the selection to the queue
        tree_frame.activate_item()
        # revert the selection to what it was
        tags_tree.selection_set(curr_sel)

    def queue_del_all(self, e=None):
        if not self._map_loaded:
            return

        ans = messagebox.askyesno(
            "Clearing queue", "Are you sure you want to clear\n" +
            "the entire extraction queue?", icon='warning', parent=self)

        if not ans:
            return True

        self.queue_tree.remove_items()

    def unload_maps(self):
        for loaded_map in self.maps.values():
            try: loaded_map.map_data.close()
            except Exception: pass

        self.maps = {}

        self.ce_sound_offsets_by_path = None
        self._map_loaded = self._running = False
        self.stop_processing = True

        self.display_map_info()
        self.hierarchy_tree.reload()
        self.class_tree.reload()
        self.hybrid_tree.reload()
        self.queue_tree.reload()
        self.set_extract_mode("tags")

    def set_defs(self):
        '''Switch definitions based on which game the map is for'''
        engine = self.active_map.engine
        if "halo3" in engine:
            pass
        elif "halo2" in engine:
            self.handler = self.halo2_handler
            self.tag_headers = self.halo2_tag_headers
        else:
            self.handler = self.halo1_handler
            self.tag_headers = self.halo1_tag_headers

            defs = self.handler.defs
            headers = self.tag_headers
            if "stubbs" in engine:
                headers["antr"] = headers["antr_stubbs"]
                headers["coll"] = headers["coll_stubbs"]
                headers["mode"] = headers["mode_stubbs"]
                headers["soso"] = headers["soso_stubbs"]
                if engine == "stubbspc":
                    defs["mode"] = stubbs_pc_mode_def
                else:
                    defs["mode"] = stubbs_mode_def
                defs["antr"] = stubbs_antr_def
                defs["bipd"] = None
                defs["cdmg"] = stubbs_cdmg_def
                defs["jpt!"] = stubbs_jpt__def
                defs["soso"] = stubbs_soso_def
                defs["unit"] = None
                defs["vehi"] = None
                defs["sbsp"] = stubbs_fast_sbsp_def
                defs["coll"] = stubbs_fast_coll_def
                #defs["imef"] = imef_def
                #defs["vege"] = vege_def
                #defs["terr"] = terr_def
            else:
                headers["antr"] = headers["antr_halo"]
                headers["coll"] = headers["coll_halo"]
                headers["mode"] = headers["mode_halo"]
                headers["soso"] = headers["soso_halo"]
                defs["mode"] = mode_def
                defs["antr"] = antr_def
                defs["bipd"] = bipd_def
                defs["cdmg"] = cdmg_def
                defs["jpt!"] = jpt__def
                defs["soso"] = soso_def
                defs["unit"] = unit_def
                defs["vehi"] = vehi_def
                defs["sbsp"] = fast_sbsp_def
                defs["coll"] = fast_coll_def
                defs.pop("imef", None)
                defs.pop("vege", None)
                defs.pop("terr", None)

        self.handler.reset_tags()

    def load_regular_map(self, map_path, will_be_active=True):
        with open(map_path, 'rb+') as f:
            comp_data = PeekableMmap(f.fileno(), 0)

        map_header = get_map_header(comp_data, True)
        if map_header is None:
            print("Could not read map header.")
            comp_data.close()
            return

        engine = get_map_version(map_header)
        if will_be_active:
            self.set_defs()

        decomp_path = None
        is_compressed = get_is_compressed_map(comp_data, map_header)
        if is_compressed:
            decomp_path = asksaveasfilename(
                initialdir=dirname(map_path), parent=self,
                title="Choose where to save the decompressed map",
                filetypes=(("mapfile", "*.map"),
                           ("All", "*")))
            decomp_path = splitext(decomp_path)[0] + ".map"

        map_data = decompress_map(comp_data, map_header, decomp_path)
        new_map = LoadedMap()
        new_map.map_data = map_data

        if comp_data is not map_data: comp_data.close()
        if will_be_active:
            self.maps["active"] = new_map

        map_header  = get_map_header(map_data)
        index_magic = get_index_magic(map_header)
        map_magic   = get_map_magic(map_header)
        tag_index   = get_tag_index(map_data, map_header)

        if tag_index is None:
            print("Could not read tag index.")
            return

        new_map.is_compressed = is_compressed
        new_map.engine      = engine
        new_map.map_header  = map_header
        new_map.index_magic = index_magic
        new_map.map_magic   = map_magic
        new_map.tag_index   = tag_index
        new_map.orig_tag_index = tag_index

        tag_index_array = tag_index.tag_index

        # build a fake tag_index_array so we dont have to rewrite
        # lots of other parts of refinery to read halo 2/3 tag indices
        if "halo3" in engine:
            print("Cant let you do that.")
            map_header.pprint(printout=True)
            if comp_data is not map_data: comp_data.close()
            self.unload_maps()
            return

            new_map.tag_index = halo3_tag_index_to_halo1_tag_index(map_header,
                                                                   tag_index)

        elif "halo2" in engine:
            new_map.tag_index = halo2_tag_index_to_halo1_tag_index(map_header,
                                                                   tag_index)
            new_map.index_magic = new_map.map_magic   = 0
            matg_id = new_map.orig_tag_index.globals_tag_id[0]

            map_type = map_header.map_type.enum_name
            if map_type == "shared":
                self.maps["shared"] = new_map
            elif map_type == "ui":
                self.maps["mainmenu"] = new_map
            elif map_type == "sharedsp":
                self.maps["single_player_shared"] = new_map

        else:
            # record the original halo 1 tag_paths so we know if they change
            new_map.orig_tag_paths = tuple(
                b.tag.tag_path for b in tag_index.tag_index)

            # make all contents of the map parasble
            self.basic_deprotection()

            # get the scenario meta
            try:
                new_map.scnr_meta = self.get_meta(tag_index.scenario_tag_id[0])

                bsp_sizes   = new_map.bsp_sizes
                bsp_magics  = new_map.bsp_magics
                bsp_offsets = new_map.bsp_header_offsets
                for b in new_map.scnr_meta.structure_bsps.STEPTREE:
                    bsp = b.structure_bsp
                    bsp_offsets[bsp.id.tag_table_index] = b.bsp_pointer
                    bsp_magics[bsp.id.tag_table_index]  = b.bsp_magic
                    bsp_sizes[bsp.id.tag_table_index]   = b.bsp_size

                # read the sbsp headers
                for tag_id, offset in bsp_offsets.items():
                    header = sbsp_meta_header_def.build(rawdata=map_data,
                                                        offset=offset)
                    new_map.bsp_headers[tag_id] = header
                    if header.sig != header.get_desc("DEFAULT", "sig"):
                        print("Sbsp header is invalid for '%s'" %
                              tag_index_array[tag_id].tag.tag_path)

                if new_map.scnr_meta is None:
                    print("Could not read scenario tag")
            except Exception:
                print(format_exc())
                print("Could not read scenario tag")

            # get the globals meta
            try:
                matg_id = None
                for b in tag_index_array:
                    if fourcc(b.class_1.data) == "matg":
                        matg_id = b.id.tag_table_index
                        break

                if matg_id is not None:
                    new_map.matg_meta = self.get_meta(matg_id)

                if new_map.matg_meta is None:
                    print("Could not read globals tag")
            except Exception:
                print(format_exc())
                print("Could not read globals tag")

        if will_be_active:
            self._load_all_resource_maps(dirname(map_path))

    def _load_all_resource_maps(self, maps_dir=""):
        if self.active_map.engine in ("halo1pc", "halo1pcdemo",
                                      "halo1ce", "halo1yelo"):
            self.load_all_halo1_resource_maps(maps_dir)
        elif "halo2" in self.active_map.engine:
            self.load_all_halo2_resource_maps(maps_dir)

    def load_map(self, map_path=None):
        try:
            if map_path is None:
                map_path = self.tk_map_path.get()
            if not exists(map_path):
                return
            elif self.running:
                return

            self.unload_maps()

            self._running = True
            self.tk_map_path.set(map_path)

            with open(map_path, 'rb+') as f:
                header_integ = unpack("<I", f.read(4))[0]

            if header_integ in (1, 2, 3):
                self.load_halo1_resource_map(map_path)
            else:
                self.load_regular_map(map_path)

            self._map_loaded = True

            self.display_map_info()
            self.hierarchy_tree.map_magic = self.active_map.map_magic
            self.class_tree.map_magic = self.active_map.map_magic
            self.hybrid_tree.map_magic = self.active_map.map_magic
            self.reload_explorers()
        except Exception:
            self.display_map_info(
                "Could not load map.\nCheck console window for error.")
            self.unload_maps()
            self.reload_explorers()
            raise

        self._running = False

    def display_map_info(self, string=None):
        try:
            self.map_info_text.config(state='normal')
            self.map_info_text.delete('1.0', 'end')
        finally:
            self.map_info_text.config(state='disabled')

        if string is None:
            if not self._map_loaded:
                return
            try:
                active_map = self.active_map
                string = "%s\n" % self.tk_map_path.get()

                header     = active_map.map_header
                index      = active_map.tag_index
                orig_index = active_map.orig_tag_index
                decomp_size = "uncompressed"
                if active_map.is_compressed:
                    decomp_size = len(active_map.map_data)

                map_type = header.map_type.enum_name
                if active_map.is_resource: map_type = "resource cache"
                elif map_type == "sp":     map_type = "singleplayer"
                elif map_type == "mp":     map_type = "multiplayer"
                elif map_type == "ui":     map_type = "user interface"
                elif map_type == "shared":   map_type = "shared"
                elif map_type == "sharedsp": map_type = "shared singleplayer"
                else: map_type = "unknown"
                string += ((
                    "Header:\n" +
                    "    engine version      == %s\n" +
                    "    map name            == '%s'\n" +
                    "    build date          == '%s'\n" +
                    "    map type            == %s\n" +
                    "    decompressed size   == %s\n" +
                    "    index header offset == %s\n") %
                (active_map.engine, header.map_name, header.build_date,
                 map_type, decomp_size, header.tag_index_header_offset))

                tag_index_offset = index.tag_index_offset
                if "halo2" in active_map.engine:
                    string += ((
                        "\nTag index:\n" +
                        "    tag count           == %s\n" +
                        "    tag types count     == %s\n" +
                        "    scenario tag id     == %s\n" +
                        "    globals  tag id     == %s\n" +
                        "    index array pointer == %s\n") %
                    (orig_index.tag_count, orig_index.tag_types_count,
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
                        "\nCalculated information:\n" +
                        "    index magic    == %s\n" +
                        "    map magic      == %s\n") %
                    (active_map.index_magic, active_map.map_magic))

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
                            "    index  data size    == %s\n") %
                        (index.vertex_data_size, index.index_data_size))

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
                        "    Mod name              == '%s'\n" +
                        "    Memory upgrade amount == %sx\n" +
                        "\n    Flags:\n" +
                        "        uses memory upgrades       == %s\n" +
                        "        uses mod data files        == %s\n" +
                        "        is protected               == %s\n" +
                        "        uses game state upgrades   == %s\n" +
                        "        has compression parameters == %s\n" +
                        "\n    Build info:\n" +
                        "        build string  == '%s'\n" +
                        "        timestamp     == %s\n" +
                        "        stage         == %s\n" +
                        "        revision      == %s\n" +
                        "\n    Cheape:\n" +
                        "        build string      == '%s'\n" +
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

    def is_indexed(self, tag_index_ref):
        if self.active_map.engine in ("halo1ce", "halo1yelo"):
            return bool(tag_index_ref.indexed)
        return False

    def basic_deprotection(self):
        if self.active_map.tag_index is None:
            return
        elif self.active_map.is_resource:
            return
        elif "halo1" not in self.active_map.engine:
            return
        print("Running basic deprotection...")
        # rename all invalid names to usable ones
        i = 0
        found_counts = {}
        for b in self.active_map.tag_index.tag_index:
            tag_path = b.tag.tag_path
            tag_cls  = b.class_1.data
            name_id  = (tag_path, tag_cls)
            if is_protected(tag_path):
                b.tag.tag_path = "protected_%s" % i
                i += 1
            elif name_id in found_counts:
                b.tag.tag_path = "%s_%s" % (tag_path, found_counts[name_id])
                found_counts[name_id] += 1
            else:
                found_counts[name_id] = 0
        print("    Finished")

    def deprotect(self, e=None):
        active_map = self.active_map
        if not self._map_loaded:
            return
        elif self.running or active_map.is_resource:
            return
        elif "halo1" not in active_map.engine:
            return

        save_path = asksaveasfilename(
            initialdir=dirname(self.tk_map_path.get()), parent=self,
            title="Choose where to save the deprotected map",
            filetypes=(("Halo mapfile", "*.map"),
                       ("Halo mapfile(extra sauce)", "*.yelo"),
                       ("All", "*")))

        if not save_path:
            print("Deprotection cancelled.")
            return

        if not self.save_map_as(save_path=save_path):
            return

        start = time()
        self.stop_processing = False
        self._running = True

        tag_index        = active_map.tag_index
        tag_index_array = tag_index.tag_index
        map_data = active_map.map_data
        engine   = active_map.engine
        map_magic          = active_map.map_magic
        bsp_magics         = active_map.bsp_magics
        bsp_headers        = active_map.bsp_headers
        bsp_header_offsets = active_map.bsp_header_offsets

        if self.fix_tag_classes.get() and "stubbs" not in active_map.engine:
            print("Repairing tag classes...")
            #print("STILL NEED TO IMPLEMENT RENAMING BITMAP, USTR, AND FONT "
            #      "TAGS IN THE RESOURCE MAPS USING CACHED NAMES.")

            # locate the tags to start deprotecting with
            repair = {}
            for b in tag_index_array:
                if self.stop_processing:
                    print("    Deprotection stopped by user.")
                    self._running = False
                    return

                tag_id = b.id.tag_table_index
                if tag_id == tag_index.scenario_tag_id.tag_table_index:
                    tag_cls = "scnr"
                elif b.class_1.enum_name not in ("<INVALID>", "NONE"):
                    tag_cls = fourcc(b.class_1.data)
                else:
                    continue

                if tag_cls == "scnr":
                    repair[tag_id] = tag_cls
                elif tag_cls == "matg" and b.tag.tag_path == "globals\\globals":
                    repair[tag_id] = tag_cls
                else:
                    continue

            # scan the tags that need repairing and repair them
            repaired = {}
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
                        self._running = False
                        return

                    # DEBUG
                    # print('    %s %s' % (tag_id, tag_cls))
                    if tag_cls not in class_repair_functions:
                        continue
                    elif tag_index_array[tag_id].indexed:
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
                        active_map.matg_meta = self.get_meta(tag_id)
                    elif tag_cls == "scnr":
                        active_map.scnr_meta = self.get_meta(tag_id)

                # start repairing the newly accumulated tags
                repair = next_repair

                # exhausted tags to repair. try to repair tag colletions now
                if not repair:
                    for b in tag_index_array:
                        if self.stop_processing:
                            print("    Deprotection stopped by user.")
                            self._running = False
                            return

                        tag_id = b.id.tag_table_index
                        if tag_id in repaired:
                            continue

                        if b.class_1.enum_name not in ("<INVALID>", "NONE"):
                            tag_cls = fourcc(b.class_1.data)
                        else:
                            continue

                        if tag_index_array[tag_id].indexed:
                            repaired[tag_id] = tag_cls
                            continue

                        if tag_cls in ("Soul", "tagc", "yelo", "gelo", "gelc"):
                            repair[tag_id] = tag_cls

            # make sure the changes are committed
            map_data.flush()
            print("    Finished")
            print("    Deprotected classes of %s of the %s total tags(%s%%)." %
                  (len(repaired), len(tag_index_array),
                   1000*len(repaired)//len(tag_index_array)/10))

            print()
            print("These tags could not be deprotected:\n"
                  "    [ id,  offset,  path ]\n")
            for i in range(len(tag_index_array)):
                if i not in repaired:
                    b = tag_index_array[i]
                    try:
                        print("    [ %s, %s, %s ]" % (
                            i, b.meta_offset - map_magic, b.tag.tag_path))
                    except Exception:
                        print("    [ %s, %s, %s ]" % (
                            i, b.meta_offset - map_magic, "<UNPRINTABLE>"))
            print()

        # write the deprotected tag classes fourcc's to each
        # tag's header in the tag index in the map buffer
        index_array_offset = tag_index.tag_index_offset - map_magic
        for tag_id, tag_cls in repaired.items():
            map_data.seek(index_array_offset + 32*tag_id)
            map_data.write(class_bytes_by_fcc[tag_cls])

        if self.use_hashcaches.get():
            print("Hashcaches are not implemented.")
            # print("Renaming tags using hashcaches...")
            # print("    Finished")

        if self.use_heuristics.get():
            print("Heuristics are not implemented.")
            # print("Renaming tags using heuristics...")
            # print("    Finished")

        active_map.tag_index = get_tag_index(map_data, active_map.map_header)
        self.display_map_info()
        self.reload_explorers()

        # record the original tag_paths so we know if any were changed
        active_map.orig_tag_paths = tuple(
            b.tag.tag_path for b in active_map.tag_index.tag_index)

        self._running = False
        print("Completed. Took %s seconds." % round(time()-start, 1))

    def save_map_as(self, e=None, save_path=None, reload_after_saving=True):
        active_map = self.active_map
        if self.running:
            return
        elif active_map.is_resource:
            print("Cannot save resource maps.")
            return
        elif "halo1" not in active_map.engine:
            print("Cannot save this kind of map.")
            return

        if not save_path:
            save_path = asksaveasfilename(
                initialdir=dirname(self.tk_map_path.get()), parent=self,
                title="Choose where to save the map",
                filetypes=(("mapfile", "*.map"), ("All", "*")))

        if not save_path:
            return

        save_dir  = dirname(save_path)
        save_path = sanitize_path(splitext(save_path)[0] + ".map")
        if not exists(save_dir):
            os.makedirs(save_dir)

        self._running = True
        print("Saving map...")
        try:
            out_file = open(save_path, 'wb')
            map_file = active_map.map_data
            map_file.seek(0)
            chunk = True
            map_size = 0

            orig_tag_paths = active_map.orig_tag_paths
            map_magic   = active_map.map_magic
            index_magic = active_map.index_magic
            map_header   = active_map.map_header
            tag_index    = active_map.tag_index
            index_array  = tag_index.tag_index
            index_offset = tag_index.tag_index_offset

            # copy the map to the new save location
            while chunk:
                chunk = map_file.read(1024*1024*32)  # copy in 32Mb chunks
                map_size += len(chunk)
                out_file.write(chunk)

            # move the tag_index array back to where it SHOULD be
            index_header_size = tag_index.get_size()
            if self.fix_tag_index_offset.get():
                tag_index.tag_index_offset = index_magic + index_header_size

            # recalculate pointers for the strings if they were changed
            for i in range(len(index_array)):
                tag_path = index_array[i].tag.tag_path
                if orig_tag_paths[i].lower() == tag_path.lower():
                    # path wasnt changed
                    continue
                # change the pointer to the end of the map
                index_array[i].path_offset = map_size + map_magic
                # increment map size by the size of the string
                map_size += len(tag_path) + 1

            # write the tag_index_header, tag_index and
            # all the tag_paths to their locations
            tag_index.serialize(
                buffer=out_file, calc_pointers=False, magic=map_magic,
                offset=map_header.tag_index_header_offset)

            # change the decompressed size
            map_header.decomp_len = map_size

            # write the header to the beginning of the map
            out_file.seek(0)
            out_file.write(map_header.serialize(calc_pointers=False))
            print("    Finished")
        except Exception:
            print(format_exc())
            print("Could not save map")
            save_path = None

        try:
            out_file.close()
        except Exception:
            pass
        self._running = False

        if reload_after_saving:
            print("Reloading map to apply changes...")
            if save_path:
                self.load_map(save_path)
            else:
                self.unload_maps()

        return save_path

    def start_extraction(self, e=None):
        if not self._map_loaded:
            return
        elif self.running:
            return

        active_map = self.active_map
        if active_map.is_resource and active_map.engine in ("halo1pc",
                                                            "halo1pcdemo"):
            print("\nCannot extract HaloPC resource caches, as they contain\n"
                  "only rawdata(pixels/sound samples) and no meta data.\n")
            return

        self._running = True
        tag_index = active_map.tag_index
        tag_index_array = tag_index.tag_index
        start = time()
        self.stop_processing = False

        print("Starting extraction...")

        if self.extract_cheape and active_map.engine == "halo1yelo":
            abs_tag_path = sanitize_path(
                join(self.tk_tags_dir.get(), "cheape.map"))

            print(abs_tag_path)

            try:
                if not exists(dirname(abs_tag_path)):
                    os.makedirs(dirname(abs_tag_path))

                cheape = active_map.map_header.yelo_header.cheape_definitions
                size        = cheape.size
                decomp_size = cheape.decompressed_size

                active_map.map_data.seek(cheape.offset)
                cheape_data = active_map.map_data.read(size)
                with open(abs_tag_path, "wb") as f:
                    if decomp_size and decomp_size != size:
                        cheape_data = zlib.decompress(cheape_data)
                    f.write(cheape_data)

            except Exception:
                print(format_exc())
                print("Error ocurred while extracting cheape.map")

        extract_resources = active_map.engine in ("halo1ce", "halo1yelo") and \
                            self.extract_from_ce_resources.get()

        extracted = set()
        map_magic = active_map.map_magic
        queue_tree = self.queue_tree.tags_tree
        queue_info = self.queue_tree.queue_info
        queue_items = queue_tree.get_children()
        total = 0

        if not queue_items:
            print("Queue is empty. Extracting entire map "
                  "to default extraction folder.")
            out_dir = self.tk_tags_dir
            if self.extract_mode.get() == "data":
                out_dir = self.tk_data_dir

            queue_info = dict(
                all_tags=dict(
                    tag_index_refs=tag_index_array, recursive=self.recursive,
                    overwrite=self.overwrite, show_output=self.show_output,
                    extract_mode=self.extract_mode,
                    out_dir=out_dir, tags_list_path=self.tags_list_path)
                )
            queue_items = ['all_tags']

        for iid in queue_items:
            if self.stop_processing:
                print("Extraction stopped by user\n")
                break
            try:
                info = queue_info[iid]
                out_dir        = info['out_dir'].get()
                recursive      = info['recursive'].get()
                overwrite      = info['overwrite'].get()
                show_output    = info['show_output'].get()
                extract_mode   = info['extract_mode'].get()
                tags_list_path = info['tags_list_path'].get()
                tag_index_refs = info['tag_index_refs']
            except Exception:
                print(format_exc())
                continue

            tagslist = ""
            local_total = 0

            for tag_index_ref in tag_index_refs:
                try:
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
                    elif (self.is_indexed(tag_index_ref) and
                          not extract_resources):
                        continue
                    extracted.add((tag_id, extract_mode))

                    file_path = sanitize_path("%s.%s" %
                        (tag_index_ref.tag.tag_path,
                         tag_index_ref.class_1.enum_name))
                    abs_file_path = join(out_dir, file_path)

                    meta = self.get_meta(tag_id, True)
                    self.update()
                    if not meta:
                        print("    Could not get: %s" % file_path)
                        continue

                    if tag_index_ref.class_1.enum_name in ("<INVALID>", "NONE"):
                        print(("Unknown tag class for '%s'\n" +
                               "    Run deprotection to fix this.") %
                              file_path)
                        continue

                    if not overwrite and (extract_mode == "tags" and
                                          isfile(abs_file_path)):
                        # not overwriting, and we are about to
                        continue

                    tag_cls = fourcc(tag_index_ref.class_1.data)

                    # these might have been edited since they
                    # were first extracted, so re-extract them
                    if tag_cls == "scnr":
                        active_map.scnr_meta = meta
                    elif tag_cls == "matg":
                        active_map.matg_meta = meta

                    if show_output:
                        print("%s: %s" % (extract_mode, file_path))
                    self.update()

                    if tags_list_path:
                        tagslist += "%s: %s\n" % (extract_mode, file_path)

                    if extract_mode == "tags":
                        meta = self.meta_to_tag_data(
                            meta, tag_cls, tag_index_ref)
                        if not meta:
                            print("    Failed to process: %s" % file_path)
                            continue

                        if not exists(dirname(abs_file_path)):
                            os.makedirs(dirname(abs_file_path))

                        FieldType.force_big()
                        with open(abs_file_path, "wb") as f:
                            f.write(self.tag_headers[tag_cls])
                            try:
                                f.write(meta.serialize(calc_pointers=False))
                            except Exception:
                                print(format_exc())
                                continue
                    elif extract_mode == "data":
                        extract_tag_data(self, info, meta, tag_index_ref)
                    else:
                        continue

                    local_total += 1
                except Exception:
                    print(format_exc())
                    print("Error ocurred while extracting '%s'" % file_path)

            FieldType.force_normal()
            try: queue_tree.delete(iid)
            except Exception: pass

            if tagslist:
                try:
                    try:
                        f = open(tags_list_path, 'a')
                    except Exception:
                        f = open(tags_list_path, 'w')

                    f.write("%s tags in: %s\n" % (local_total, out_dir))
                    f.write(tagslist)
                    f.write('\n\n')

                    f.close()
                except Exception:
                    print(format_exc())
                    print("Could not save tagslist.")

            total += local_total
            local_total = 0

        self._running = False
        print("Extracted %s tags. Took %s seconds\n" %
              (total, round(time()-start, 1)))

    def get_ce_resource_meta(self, tag_cls, tag_index_ref):
        '''Returns just the meta of the tag without any raw data.'''
        # read the meta data from the map
        if self.get_meta_descriptor(tag_cls) is None:
            return
        elif self.active_map.engine not in ("halo1ce", "halo1yelo"):
            return

        kwargs = dict(parsing_resource=True)
        rsrc_map = self.active_map
        if rsrc_map.is_resource:
            # we have JUST a resource map loaded. not a real map
            rsrc_head   = rsrc_map.rsrc_header
            meta_offset = tag_index_ref.meta_offset
        else:
            if   tag_cls == "snd!": rsrc_map = self.maps.get("sounds")
            elif tag_cls == "bitm": rsrc_map = self.maps.get("bitmaps")
            else:                   rsrc_map = self.maps.get("loc")

            rsrc_head = rsrc_map.rsrc_header

            # resource map not loaded
            if rsrc_head is None:
                return
            elif tag_cls == "snd!":
                sound_mapping = self.ce_sound_offsets_by_path
                tag_path  = tag_index_ref.tag.tag_path
                if sound_mapping is None or tag_path not in sound_mapping:
                    return

                meta_offset = sound_mapping[tag_path]
            else:
                meta_offset = rsrc_head.tag_headers[
                    tag_index_ref.meta_offset].offset

        map_data = rsrc_map.map_data
        if map_data is None:
            # resource map not loaded
            return

        if tag_cls != 'snd!':
            kwargs['magic'] = 0

        h_desc  = self.get_meta_descriptor(tag_cls)
        h_block = [None]

        try:
            FieldType.force_little()
            h_desc['TYPE'].parser(
                h_desc, parent=h_block, attr_index=0, rawdata=map_data,
                tag_index=rsrc_head.tag_paths, root_offset=meta_offset,
                tag_cls=tag_cls, **kwargs)
            FieldType.force_normal()
        except Exception:
            print(format_exc())
            return
        self.inject_rawdata(h_block[0], tag_cls, tag_index_ref)

        return h_block[0]

    def get_meta(self, tag_id, reextract=False):
        '''
        Takes a tag reference id as the sole argument.
        Returns that tags meta data as a parsed block.
        '''
        active_map = self.active_map
        tag_index  = active_map.tag_index
        tag_index_array = tag_index.tag_index
        magic    = active_map.map_magic
        engine   = active_map.engine
        map_data = active_map.map_data

        # if we are given a 32bit tag id, mask it off
        tag_id &= 0xFFFF

        tag_index_ref = tag_index_array[tag_id]

        if tag_id != tag_index.scenario_tag_id[0] or active_map.is_resource:
            tag_cls = None
            if tag_index_ref.class_1.enum_name not in ("<INVALID>", "NONE"):
                tag_cls = fourcc(tag_index_ref.class_1.data)
        else:
            tag_cls = "scnr"

        # if we dont have a defintion for this tag_cls, then return nothing
        if self.get_meta_descriptor(tag_cls) is None:
            return

        if tag_cls is None:
            # couldn't determine the tag class
            return
        elif self.is_indexed(tag_index_ref) and engine in ("halo1ce",
                                                           "halo1yelo"):
            # tag exists in a resource cache
            return self.get_ce_resource_meta(tag_cls, tag_index_ref)
        elif not reextract:
            if tag_id == tag_index.scenario_tag_id[0] and active_map.scnr_meta:
                return active_map.scnr_meta
            elif tag_cls == "matg" and active_map.matg_meta:
                return active_map.matg_meta

        h_desc = self.get_meta_descriptor(tag_cls)
        h_block = [None]
        offset = tag_index_ref.meta_offset - magic
        if tag_cls == "sbsp":
            # bsps use their own magic because they are stored in
            # their own section of the map, directly after the header
            magic  = (active_map.bsp_magics[tag_id] -
                      active_map.bsp_header_offsets[tag_id])
            offset = active_map.bsp_headers[tag_id].meta_pointer - magic

        try:
            # read the meta data from the map
            FieldType.force_little()
            print(tag_index_ref)
            print(map_data)
            map_data.seek(0, 2)
            print(map_data.tell())
            map_data.seek(0)
            h_desc['TYPE'].parser(
                h_desc, parent=h_block, attr_index=0, magic=magic,
                tag_index=tag_index_array, rawdata=map_data, offset=offset)
            FieldType.force_normal()
        except Exception:
            print(format_exc())
            FieldType.force_normal()
            return

        self.inject_rawdata(h_block[0], tag_cls, tag_index_ref)

        return h_block[0]

    def inject_rawdata(self, meta, tag_cls, tag_index_ref):
        if "halo2" in self.active_map.engine:
            return self.inject_halo2_rawdata(meta, tag_cls, tag_index_ref)

        return self.inject_halo1_rawdata(meta, tag_cls, tag_index_ref)

    def meta_to_tag_data(self, meta, tag_cls, tag_index_ref):
        '''
        Changes anything in a meta data block that needs to be changed for
        it to be a working tag. This includes removing predicted_resource
        references, fetching rawdata for the bitmaps, sounds, and models,
        and byteswapping any rawdata that needs it(animations, bsp, etc).
        '''
        if "halo2" in self.active_map.engine:
            return self.halo2_meta_to_tag_data(meta, tag_cls, tag_index_ref)

        return self.halo1_meta_to_tag_data(meta, tag_cls, tag_index_ref)

    def cancel_action(self, e=None):
        if not self._map_loaded:
            return
        self.stop_processing = True

    def reload_explorers(self):
        if not self._map_loaded:
            return
        print("Reloading map explorer...")
        if self._display_mode == "hierarchy":
            self.hierarchy_tree.reload(self.active_map.tag_index)
        elif self._display_mode == "class":
            self.class_tree.reload(self.active_map.tag_index)
        elif self._display_mode == "hybrid":
            self.hybrid_tree.reload(self.active_map.tag_index)

        self.queue_tree.reload()
        self.update()
        print("    Finished\n")

    def map_path_browse(self):
        if self.running:
            return
        fp = askopenfilename(
            initialdir=self.last_dir,
            title="Select map to load", parent=self,
            filetypes=(("Halo mapfile", "*.map"),
                       ("Halo mapfile(extra sauce)", "*.yelo"),
                       ("Halo 2 Vista compressed mapfile", "*.map.dtz"),
                       ("All", "*")))

        if not fp:
            return

        fp = sanitize_path(fp)
        self.last_dir = dirname(fp)
        self.tk_map_path.set(fp)
        self.unload_maps()
        self.load_map()


if __name__ == "__main__":
    try:
        extractor = run()
        extractor.mainloop()
    except Exception:
        print(format_exc())
        input()
