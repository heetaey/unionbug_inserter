
import os

def get_bug_paths():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return (
        os.path.join(base_dir, "assets", "UnionBug - Small Black.pdf"),
        os.path.join(base_dir, "assets", "UnionBug - Small White.pdf")
    )
