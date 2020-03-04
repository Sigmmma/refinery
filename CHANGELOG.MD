# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.0]
### Added
 - Added \_\_main\_\_ so Refinery can be executed using `python -m refinery` or just `refinery` on some systems.

## [2.3.2]
### Changed
 - Fix readme potentially breaking setup.

## [2.3.1]
### Add
 - Project is now automatically built for pypi.

## [2.3.0] Into the GPLv3
Something that is very important to us is collaboration and the ability to share knowledge. Since this library is just to help mod some games, we've decided that switching to GPLv3 is the right thing to do for us to avoid any future loss of knowledge.

### Added
 - Add report bug button.
 - Michelle to the authors!
 - This changelog!

### Changed
 - All valid Halo 1 map types are now selected by default instead of having to click a few buttons to also see opensauce maps.
 - Config is now saved in current_working_directory/mek_config on Windows. And ~/.local/share/mek/ on Linux.
 - Data extraction mode can be entered without loading a map first now.
 - Fix a bunch of issues relating to different path separators between map files and the filesystem.
 - Fix sounds extracting incorrectly during data extraction.
 - Fix tag class deprotection failing on scenario tag.
 - Fix valid classes for explorers being set wrong if not in data extraction mode.
 - Make numerous path handling changes to support POSIX systems.
 - Refactor a bunch of the Refinery core.
 - Use kdialog whenever available instead of default tkinter filepicker.
 - Use pathlib Path objects where applicable to ease compatibility with multiple operating systems.
 - Various changes to work with new reclaimer codebase.
 - **THIS PROJECT IS NOW LICENSED UNDER THE GNU General Public License version 3**

### Removed
 - **REMOVED SUPPORT FOR VERSIONS OF PYTHON BELOW 3.5**
