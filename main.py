from tkinter import Tk
from ui import UnionBugInserter

if __name__ == "__main__":
    root = Tk()
    app = UnionBugInserter(root)
    root.geometry("1200x750")
    root.mainloop()
