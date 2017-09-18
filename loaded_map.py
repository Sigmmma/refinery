
__all__ = ("LoadedMap", "NO_MAP")

class LoadedMap:
    map_data = b''

    # these are the different pieces of the map as parsed blocks
    map_header  = None
    rsrc_header = None
    tag_index   = None
    orig_tag_index = None  # the tag index specific to the
    #                        halo version that this map is from

    # the original tag_path of each tag in the map before any deprotection
    orig_tag_paths = None

    # the parsed meta of the root tags in the map
    scnr_meta = None
    matg_meta = None

    # determines how to work with this map
    engine        = ""
    is_resource   = False
    is_compressed = False

    index_magic = 0
    map_magic   = 0

    bsp_magics  = ()
    bsp_sizes   = ()
    bsp_headers = ()
    bsp_header_offsets = ()

    _empty_map = None

    def __init__(self):
        self.bsp_magics = {}
        self.bsp_sizes  = {}
        self.bsp_header_offsets = {}
        self.bsp_headers = {}
        self.orig_tag_paths = ()

    def __setattr__(self, attr_name, new_val):
        if self is type(self)._empty_map:
            raise AttributeError("Cannot modify the empty map.")
        object.__setattr__(self, attr_name, new_val)

    def set_is_empty_map(self):
        if type(self)._empty_map is not None:
            raise TypeError("Empty map already set.")
        type(self)._empty_map = self


NO_MAP = LoadedMap()
del NO_MAP.bsp_magics
del NO_MAP.bsp_sizes
del NO_MAP.bsp_headers
del NO_MAP.bsp_header_offsets
NO_MAP.set_is_empty_map()
