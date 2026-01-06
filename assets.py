import os
import sys

def get_asset_path(filename):
    # Handles looking for files whether running as script or .exe (PyInstaller)
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    return os.path.join(os.path.dirname(__file__), 'assets', filename)

def get_bug_paths():
    # Returns EXACTLY 2 values
    return get_asset_path("UnionBug - Small Black.pdf"), get_asset_path("UnionBug - Small White.pdf")

def get_indicia_paths():
    # Returns EXACTLY 2 values
    return get_asset_path("indicia.pdf")