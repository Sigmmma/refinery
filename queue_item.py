
from refinery.tag_index_crawler import TagIndexCrawler


class RefineryQueueItem:
    # TODO: consider moving these into optional kwargs in op_args
    recursive = False
    overwrite = False
    tagslist_path = ""
    out_dir = ""

    engine_name = ""
    map_name = ""

    _op = "extract_tags"
    _op_args = ()
    _op_kwargs = ()

    _valid_ops = frozenset((
        # each of these operation types requires specific numbers
        # and types of arguments(op_args) to be provided to work.
        
        "extract_tags", # first arg is an iterable of any mix of tag ids,
        #                 paths, or file extensions. if extensions, ensure
        #                 everything before the period(.) is an asterisk(*).
        "extract_data", # same as extract_tags.
        "extract_cheape", # first arg is the filepath to save cheape to. if not
        #                   provided, defaults to out_dir + halo_map.map_name
        "deprotect", # first arg is the filepath to save the deprotected map to.
        "load_map", # first arg is the filepath to the map to load.
        "save_map", # first arg is the filepath to save the map to.
        #             optional second arg is a 2-tuple specifying which map
        #             to save as (engine_name, map_name).

        # NOTE: These operations require a separate save_map operation
        #       to be done before their changes will be saved anywhere.
        "crc_spoof",  # first arg is the crc to spoof the map with. can be
        #               provided as either an int, or a length 4 byte string.
        #               optional second arg is a 2-tuple specifying which map
        #               to spoof (engine_name, map_name).
        "rename_map", # first arg is the new name of the map. must be a valid
        #               filename, and must be less than 32 characters.
        #               optional second arg is a 2-tuple specifying which map
        #               to rename as (engine_name, map_name).
        "rename_tag", # first arg is an iterable of 2-tuples specifying the
        #               source and destination for each rename as (src, dst)
        #               optional second arg is a 2-tuple specifying which map
        #               to rename as (engine_name, map_name).
        "rename_dir", # same as rename_tag.
        ))
    def __init__(self, operation, operation_args, **kwargs):
        self.recursive = kwargs.pop("recursive", self.recursive)
        self.overwrite = kwargs.pop("overwrite", self.overwrite)
        self.tagslist_path = kwargs.pop("tagslist_path", self.tagslist_path)
        self.out_dir = kwargs.pop("out_dir", self.out_dir)

        self.engine_name = kwargs.pop("engine_name", self.engine_name)
        self.map_name = kwargs.pop("map_name", self.map_name)

        self._op = str(operation)
        if isinstance(operation_args, str):
            self._op_args = (operation_args, )
        else:
            self._op_args = tuple(operation_args)
            
        self._op_kwargs = tuple(kwargs)

        # fill these out for determining vailidity of operation_args
        # also ensure all unprovided args are set to blank defaults
        if operation in ("extract_tags", "extract_data"):
            pass
        elif operation == "extract_cheape":
            pass
        elif operation == ("deprotect", "load_map"):
            pass
        elif operation == "save_map":
            pass
        elif operation == "crc_spoof":
            pass
        elif operation == "rename_map":
            pass
        elif operation in ("rename_tag", "rename_dir"):
            pass

    def __setattr__(self, attr_name, new_val):
        if attr_name == "_op":
            assert new_val in self._valid_ops
        object.__setattr__(self, attr_name, new_val)

    @property
    def operation(self): return self._op
    @property
    def operation_args(self): return self._op_args
    @property
    def operation_kwargs(self): return self._op_kwargs

    def get_filtered_tag_ids(self, halo_map):
        if self.operation in ("extract_tags", "extract_data"):
            return TagIndexCrawler(self.operation_args).get_filtered_tag_ids(halo_map)
        return ()
