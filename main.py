import customtkinter as ctk
from ui import UnionBugInserter

if __name__ == "__main__":
   ctk.set_appearance_mode("System")
   ctk.set_default_color_theme("blue")

   root = ctk.CTk()  # Uses the 'ctk' alias we defined above
   root.geometry("1200x800")
    
   app = UnionBugInserter(root)
   root.mainloop()