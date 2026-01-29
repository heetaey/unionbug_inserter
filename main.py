import customtkinter as ctk
from tkinterdnd2 import TkinterDnD
from ui import UnionBugInserter

# Create a class that combines CustomTkinter + Drag & Drop
class Tk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # Use our special DnD-enabled window
    root = Tk()  
    root.geometry("1200x850")
    
    app = UnionBugInserter(root)
    root.mainloop()