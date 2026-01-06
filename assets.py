import os
import sys

def get_asset_path(filename):
    """Returns the absolute path to an asset, handling Dev vs PyInstaller modes."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, 'assets', filename)

def get_bug_paths():
    """Returns paths for Black and White versions of the Union Bug."""
    return get_asset_path("UnionBug - Small Black.pdf"), get_asset_path("UnionBug - Small White.pdf")

def get_indicia_paths():
    """Returns path for Indicia. Always returns a string for consistency."""
    return get_asset_path("indicia.pdf")