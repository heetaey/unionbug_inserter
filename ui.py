import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import fitz
import os
from tkinterdnd2 import DND_FILES  # Import DnD constants

# Import our optimized handler
from pdf_handler import (
    load_pdf, get_page_image, render_preview_image, 
    save_pdf_with_overlays, get_brightness_at_loc
)
from assets import get_bug_paths, get_indicia_paths

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class UnionBugInserter:
    def __init__(self, root):
        self.root = root
        self.root.title("Union Bug & Indicia Placer")
        self.root.geometry("1200x850")

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_rowconfigure(0, weight=1)

        # --- DRAG & DROP SETUP ---
        # Tell the window to accept file drops
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop_file)

        # --- ASSET LOADING ---
        bug_blk_path, bug_wht_path = get_bug_paths()
        indicia_path = get_indicia_paths()
        
        try:
            self.assets = {
                "bug_black": fitz.open(bug_blk_path),
                "bug_white": fitz.open(bug_wht_path),
                "indicia": fitz.open(indicia_path)
            }
        except Exception as e:
            print(f"Error loading assets: {e}")
            self.assets = {}

        # --- APP STATE ---
        self.overlays = {
            "bug": {
                "active": tk.BooleanVar(value=False),
                "coords": None,        
                "page_index": None,
                "size": tk.DoubleVar(value=0.3),
                "asset_key": "bug_black",
                "preview_id": None
            },
            "indicia": {
                "active": tk.BooleanVar(value=False),
                "coords": None,
                "page_index": None,
                "size": tk.DoubleVar(value=1.0),
                "asset_key": "indicia",
                "preview_id": None
            }
        }
        
        self.show_grid = tk.BooleanVar(value=False)
        self.current_target_key = "bug"
        self.pdf_doc = None
        self.pdf_path = None
        self.current_page_index = 0
        self.zoom_level = 1.0
        self.display_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.page_image = None
        self.page_width_px = 0
        self.page_height_px = 0
        
        self.current_pdf_page_width_pt = 0 
        self.current_pdf_page_height_pt = 0

        self.ui_size = tk.DoubleVar(value=0.3)
        self.ui_x = tk.DoubleVar(value=0.0)
        self.ui_y = tk.DoubleVar(value=0.0)

        self.setup_ui()

    def setup_ui(self):
        # 1. Canvas Area
        self.canvas_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        sb_y = ctk.CTkScrollbar(self.canvas_frame, command=self.canvas.yview)
        sb_x = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")

        # Events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel) 
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)   
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)   
        self.root.bind("<Configure>", self.on_window_resize)

        # 2. Sidebar
        self.sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        
        # Actions
        self._add_header("ACTIONS")
        ctk.CTkButton(self.sidebar, text="Open PDF", command=lambda: self.open_pdf(None)).pack(padx=20, pady=5, fill="x")
        ctk.CTkButton(self.sidebar, text="Save PDF", command=self.save_pdf, fg_color="green").pack(padx=20, pady=5, fill="x")
        ctk.CTkButton(self.sidebar, text="Clean / Reset", command=self.clear_all, fg_color="red").pack(padx=20, pady=5, fill="x")
        
        # Toggles
        self._add_header("ENABLE ELEMENTS")
        ctk.CTkCheckBox(self.sidebar, text="Union Bug", variable=self.overlays["bug"]["active"], 
                        command=self.refresh_previews).pack(padx=20, pady=5, anchor="w")
        ctk.CTkCheckBox(self.sidebar, text="Indicia / Postage", variable=self.overlays["indicia"]["active"], 
                        command=self.refresh_previews).pack(padx=20, pady=5, anchor="w")

        # Edit Controls
        self._add_header("EDIT CONTROLS")
        self.target_selector = ctk.CTkSegmentedButton(self.sidebar, values=["Union Bug", "Indicia"], 
                                                     command=self.on_target_switch)
        self.target_selector.set("Union Bug")
        self.target_selector.pack(padx=20, pady=5, fill="x")
        
        ctk.CTkLabel(self.sidebar, text="Size (inches):").pack(padx=20, pady=(5, 0), anchor="w")
        frame_size = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_size.pack(padx=20, pady=5, fill="x")
        
        ctk.CTkSlider(frame_size, from_=0.1, to=2.0, number_of_steps=190, variable=self.ui_size, 
                      command=self.on_ui_change).pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        entry_size = ctk.CTkEntry(frame_size, textvariable=self.ui_size, width=60)
        entry_size.pack(side="right")
        entry_size.bind("<Return>", lambda e: self.on_ui_change(None))

        ctk.CTkLabel(self.sidebar, text="Position (X / Y inches):").pack(padx=20, pady=(5, 0), anchor="w")
        frame_pos = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_pos.pack(padx=20, pady=5, fill="x")
        ctk.CTkLabel(frame_pos, text="X:").grid(row=0, column=0, padx=5)
        ctk.CTkEntry(frame_pos, textvariable=self.ui_x, width=60).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(frame_pos, text="Y:").grid(row=0, column=2, padx=5)
        ctk.CTkEntry(frame_pos, textvariable=self.ui_y, width=60).grid(row=0, column=3, padx=5)
        
        ctk.CTkButton(self.sidebar, text="Apply Position", command=self.apply_manual_pos, height=25).pack(padx=20, pady=5, fill="x")
        
        self._add_header("ALIGNMENT & GRID")
        ctk.CTkButton(self.sidebar, text="Center Bug Horizontally", command=self.center_bug_horizontally, 
                     fg_color="#444", hover_color="#555").pack(padx=20, pady=5, fill="x")
        ctk.CTkSwitch(self.sidebar, text="Show Grid (0.25\")", variable=self.show_grid, command=self.render_page).pack(padx=20, pady=10, anchor="w")

        self._add_header("VIEW & NAV")
        frame_nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_nav.pack(pady=10)

        ctk.CTkButton(frame_nav, text="◄", width=30, command=self.prev_page).pack(side="left", padx=5)
        self.lbl_page = ctk.CTkLabel(frame_nav, text="Page 1", width=70, anchor="center")
        self.lbl_page.pack(side="left", padx=5)
        ctk.CTkButton(frame_nav, text="►", width=30, command=self.next_page).pack(side="left", padx=5)

        self.lbl_info = ctk.CTkLabel(self.sidebar, text="", font=("Arial", 10), text_color="gray")
        self.lbl_info.pack(side="bottom", pady=10)

    def _add_header(self, text):
        ctk.CTkLabel(self.sidebar, text=text, font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")

    # --- DRAG & DROP LOGIC ---

    def on_drop_file(self, event):
        """Handles the file drop event."""
        file_path = event.data
        
        # Windows D&D paths are often wrapped in curly braces if they contain spaces
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
            
        # If multiple files are dropped, we only take the first one
        if " " in file_path and not os.path.exists(file_path):
             # Try splitting (simple logic for now)
             parts = self.root.tk.splitlist(event.data)
             if parts:
                 file_path = parts[0]

        if os.path.isfile(file_path):
            if file_path.lower().endswith('.pdf'):
                self.open_pdf(file_path)
            else:
                messagebox.showerror("Error", "Please drop a PDF file.")

    # --- MAIN LOGIC ---

    def open_pdf(self, path=None):
        """Modified to accept an optional path argument."""
        if path:
            f = path
        else:
            f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        
        if f:
            self.pdf_path = f
            try:
                self.pdf_doc = load_pdf(f)
                self.current_page_index = 0
                
                # Info Display
                page = self.pdf_doc[0]
                w_in = page.rect.width / 72
                h_in = page.rect.height / 72
                
                self.lbl_info.configure(text=f"{os.path.basename(f)}\n{w_in:.2f} x {h_in:.2f} in")
                self.render_page()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load PDF: {e}")

    def clear_all(self):
        for key, data in self.overlays.items():
            data["active"].set(False)
            data["coords"] = None
            data["page_index"] = None
            if data["preview_id"]:
                self.canvas.delete(data["preview_id"])
                data["preview_id"] = None
        
        self.ui_x.set(0.0)
        self.ui_y.set(0.0)
        self.refresh_previews()

    def center_bug_horizontally(self):
        if not self.pdf_doc: return

        self.target_selector.set("Union Bug")
        self.on_target_switch("Union Bug")

        data = self.overlays["bug"]
        asset_doc = self.assets[data["asset_key"]]
        if not asset_doc: return
        page = asset_doc[0]
        
        width_pt = data["size"].get() * 72
        page_width_pt = self.current_pdf_page_width_pt
        
        new_x = (page_width_pt - width_pt) / 2
        current_y = data["coords"][1] if data["coords"] else 0
        
        data["coords"] = (new_x, current_y)
        data["active"].set(True)
        data["page_index"] = self.current_page_index
        
        self.ui_x.set(round(new_x / 72, 3))
        self.ui_y.set(round(current_y / 72, 3))
        self.refresh_previews()

    def on_target_switch(self, value):
        self.current_target_key = "bug" if "Bug" in value else "indicia"
        data = self.overlays[self.current_target_key]
        
        self.ui_size.set(data["size"].get())
        if data["coords"]:
            self.ui_x.set(round(data["coords"][0] / 72, 3))
            self.ui_y.set(round(data["coords"][1] / 72, 3))
        else:
            self.ui_x.set(0); self.ui_y.set(0)

    def on_canvas_click(self, event):
        if not self.pdf_doc: return
        
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        if not (self.offset_x <= cx <= self.offset_x + self.page_width_px) or \
           not (self.offset_y <= cy <= self.offset_y + self.page_height_px):
            return

        click_x_pt = (cx - self.offset_x) / self.display_scale
        click_y_pt = (cy - self.offset_y) / self.display_scale
        
        target = self.overlays[self.current_target_key]
        
        asset_key = target["asset_key"]
        if self.current_target_key == "bug": asset_key = "bug_black"
        
        asset_doc = self.assets.get(asset_key)
        
        if asset_doc:
            page = asset_doc[0]
            width_pt = target["size"].get() * 72
            aspect_ratio = page.rect.height / page.rect.width
            height_pt = width_pt * aspect_ratio
            
            final_x = click_x_pt - (width_pt / 2)
            final_y = click_y_pt - (height_pt / 2)
        else:
            final_x = click_x_pt
            final_y = click_y_pt
        
        target["active"].set(True)
        target["coords"] = (final_x, final_y)
        target["page_index"] = self.current_page_index
        
        self.ui_x.set(round(final_x/72, 3))
        self.ui_y.set(round(final_y/72, 3))
        self.refresh_previews()

    def draw_grid(self):
        if not self.show_grid.get(): return
        step_pt = 18 # 0.25 inch
        step_px = step_pt * self.display_scale
        
        curr_x = self.offset_x
        while curr_x <= self.offset_x + self.page_width_px:
            self.canvas.create_line(curr_x, self.offset_y, curr_x, self.offset_y + self.page_height_px, 
                                    fill="#555555", width=1, dash=(2, 4), tags="grid_line")
            curr_x += step_px
            
        curr_y = self.offset_y
        while curr_y <= self.offset_y + self.page_height_px:
            self.canvas.create_line(self.offset_x, curr_y, self.offset_x + self.page_width_px, curr_y, 
                                    fill="#555555", width=1, dash=(2, 4), tags="grid_line")
            curr_y += step_px

    def refresh_previews(self):
        if not self.pdf_doc: return

        for key, data in self.overlays.items():
            if data["preview_id"]:
                self.canvas.delete(data["preview_id"])
                data["preview_id"] = None

            if data["active"].get() and data["coords"] and data["page_index"] == self.current_page_index:
                x_pt, y_pt = data["coords"]
                
                if key == "bug":
                    check_x = int(x_pt * self.display_scale)
                    check_y = int(y_pt * self.display_scale)
                    check_x = max(0, min(check_x, self.page_image.width - 1))
                    check_y = max(0, min(check_y, self.page_image.height - 1))
                    b = get_brightness_at_loc(self.page_image, check_x, check_y)
                    data["asset_key"] = "bug_white" if b < 128 else "bug_black"

                asset_doc = self.assets[data["asset_key"]]
                tk_img = render_preview_image(asset_doc[0], data["size"].get(), self.display_scale)
                data["tk_ref"] = tk_img 
                
                dx = x_pt * self.display_scale + self.offset_x
                dy = y_pt * self.display_scale + self.offset_y
                data["preview_id"] = self.canvas.create_image(dx, dy, anchor="nw", image=tk_img)

    def on_ui_change(self, value):
        raw_val = float(value) if value is not None else self.ui_size.get()
        rounded = round(raw_val, 2)
        self.ui_size.set(rounded)
        self.overlays[self.current_target_key]["size"].set(rounded)
        self.refresh_previews()

    def apply_manual_pos(self):
        try:
            x_pt = self.ui_x.get() * 72
            y_pt = self.ui_y.get() * 72
            target = self.overlays[self.current_target_key]
            target["coords"] = (x_pt, y_pt)
            target["page_index"] = self.current_page_index
            target["active"].set(True)
            self.refresh_previews()
        except ValueError:
            pass

    def render_page(self):
        self.canvas.delete("all")
        for d in self.overlays.values(): d["preview_id"] = None

        if not self.pdf_doc: return

        page = self.pdf_doc[self.current_page_index]
        self.current_pdf_page_width_pt = page.rect.width 
        self.current_pdf_page_height_pt = page.rect.height

        self.canvas.update_idletasks()
        
        pil_img, tk_img, scale = get_page_image(page, self.canvas.winfo_width(), self.canvas.winfo_height())
        
        w, h = pil_img.size
        new_w, new_h = int(w * self.zoom_level), int(h * self.zoom_level)
        self.page_image = pil_img.resize((new_w, new_h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(self.page_image)
        self.display_scale = scale * self.zoom_level
        self.page_width_px = new_w
        self.page_height_px = new_h

        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        img_id = self.canvas.create_image(cx, cy, anchor="center", image=self.tk_img)
        
        bbox = self.canvas.bbox(img_id)
        if bbox: self.offset_x, self.offset_y = bbox[0], bbox[1]

        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.lbl_page.configure(text=f"Page {self.current_page_index + 1} / {len(self.pdf_doc)}")
        
        self.draw_grid()
        self.refresh_previews()

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.render_page()

    def next_page(self):
        if self.pdf_doc and self.current_page_index < len(self.pdf_doc) - 1:
            self.current_page_index += 1
            self.render_page()

    def on_zoom(self, val):
        self.zoom_level = float(val)
        self.render_page()

    def save_pdf(self):
        save_pdf_with_overlays(self)
    
    def on_window_resize(self, event):
        if hasattr(self, "_resize_job"): self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(300, self.render_page)

    def on_mouse_wheel(self, event):
        if event.num == 5 or getattr(event, "delta", 0) < 0:
            direction = -1 
        else:
            direction = 1

        new_zoom = max(0.5, min(3.0, self.zoom_level + (0.1 * direction)))
        self.on_zoom(new_zoom)