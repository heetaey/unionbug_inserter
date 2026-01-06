import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
from pdf_handler import (
    load_pdf, get_page_image, get_bug_image, save_pdf_with_overlays,
    get_brightness_from_image
)
from assets import get_bug_paths, get_indicia_paths
import os

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class UnionBugInserter:
    def __init__(self, root):
        self.root = root
        self.root.title("Union Bug & Indicia Placer")
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_rowconfigure(0, weight=1)

        # Load Assets
        self.bug_black, self.bug_white = get_bug_paths()
        
        # Handle tuple vs string return from assets
        indicia_asset = get_indicia_paths()
        self.indicia_pdf = indicia_asset[0] if isinstance(indicia_asset, tuple) else indicia_asset

        # --- STATE MANAGEMENT ---
        self.overlays = {
            "bug": {
                "name": "Union Bug",
                "active": tk.BooleanVar(value=False),
                "coords": None,
                "size": tk.DoubleVar(value=0.3),
                "pdf_asset": self.bug_black, 
                "preview_id": None
            },
            "indicia": {
                "name": "Indicia",
                "active": tk.BooleanVar(value=False),
                "coords": None,
                "size": tk.DoubleVar(value=1.0),
                "pdf_asset": self.indicia_pdf,
                "preview_id": None
            }
        }
        
        self.current_target = tk.StringVar(value="bug") 

        # Global App State
        self.pdf_doc = None
        self.pdf_path = None
        self.page_image = None
        self.tk_img = None
        self.current_page_index = 0
        self.zoom_level = 1.0
        self.display_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Temporary vars for UI inputs
        self.ui_size_var = tk.DoubleVar(value=0.3)
        self.ui_x_var = tk.DoubleVar(value=0.0)
        self.ui_y_var = tk.DoubleVar(value=0.0)

        self.setup_ui()

    def setup_ui(self):
        # ================= MAIN CANVAS =================
        self.canvas_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scroll_y = ctk.CTkScrollbar(self.canvas_frame, orientation="vertical", command=self.canvas.yview)
        self.scroll_x = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)
        
        self.scroll_y.grid(row=0, column=1, sticky="ns")
        self.scroll_x.grid(row=1, column=0, sticky="ew")

        # Events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.root.bind("<Configure>", self.on_window_resize)

        # ================= SIDEBAR =================
        self.sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        
        # --- 1. Actions ---
        ctk.CTkLabel(self.sidebar, text="ACTIONS", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")
        ctk.CTkButton(self.sidebar, text="Open PDF", command=self.open_pdf).pack(padx=20, pady=5, fill="x")
        ctk.CTkButton(self.sidebar, text="Save PDF", command=self.save_pdf, fg_color="green").pack(padx=20, pady=5, fill="x")
        
        # --- 2. Toggles ---
        ctk.CTkLabel(self.sidebar, text="ENABLE ELEMENTS", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")
        
        self.chk_bug = ctk.CTkCheckBox(
            self.sidebar, text="Union Bug", variable=self.overlays["bug"]["active"], command=self.refresh_previews
        )
        self.chk_bug.pack(padx=20, pady=5, anchor="w")

        self.chk_indicia = ctk.CTkCheckBox(
            self.sidebar, text="Indicia / Postage", variable=self.overlays["indicia"]["active"], command=self.refresh_previews
        )
        self.chk_indicia.pack(padx=20, pady=5, anchor="w")

        # --- 3. Edit Controls ---
        ctk.CTkLabel(self.sidebar, text="EDIT CONTROLS", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")
        
        self.target_selector = ctk.CTkSegmentedButton(
            self.sidebar, values=["Union Bug", "Indicia"], variable=tk.StringVar(value="Union Bug"), command=self.on_target_switch
        )
        self.target_selector.pack(padx=20, pady=5, fill="x")
        
        # Size
        ctk.CTkLabel(self.sidebar, text="Size (inches):").pack(padx=20, pady=(5, 0), anchor="w")
        self.size_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.size_frame.pack(padx=20, pady=5, fill="x")

        self.slider_size = ctk.CTkSlider(
            self.size_frame, from_=0.1, to=2.0, number_of_steps=190,
            variable=self.ui_size_var, command=self.on_ui_size_change
        )
        self.slider_size.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.ent_size = ctk.CTkEntry(self.size_frame, textvariable=self.ui_size_var, width=60)
        self.ent_size.pack(side="right")
        self.ent_size.bind("<Return>", lambda e: self.on_ui_size_change(None))

        # Position
        ctk.CTkLabel(self.sidebar, text="Position (X / Y inches):").pack(padx=20, pady=(5, 0), anchor="w")
        self.pos_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.pos_frame.pack(padx=20, pady=5, fill="x")

        ctk.CTkLabel(self.pos_frame, text="X:").grid(row=0, column=0, padx=5)
        ctk.CTkEntry(self.pos_frame, textvariable=self.ui_x_var, width=60).grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(self.pos_frame, text="Y:").grid(row=0, column=2, padx=5)
        ctk.CTkEntry(self.pos_frame, textvariable=self.ui_y_var, width=60).grid(row=0, column=3, padx=5)

        ctk.CTkButton(self.sidebar, text="Apply Manual Pos", command=self.apply_manual_pos, height=25).pack(padx=20, pady=5, fill="x")

        # --- 4. View & Navigation (RESTORED) ---
        ctk.CTkLabel(self.sidebar, text="VIEW & NAV", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")
        
        # Zoom
        ctk.CTkLabel(self.sidebar, text="Zoom Level:").pack(padx=20, anchor="w")
        self.slider_zoom = ctk.CTkSlider(self.sidebar, from_=0.5, to=3.0, command=self.on_zoom)
        self.slider_zoom.set(1.0)
        self.slider_zoom.pack(padx=20, pady=5, fill="x")

        # Page Navigation
        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(padx=20, pady=10, fill="x")
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="◄", width=30, command=self.prev_page)
        self.btn_prev.pack(side="left", padx=2)
        
        self.page_label = ctk.CTkLabel(self.nav_frame, text="Page 1", width=80)
        self.page_label.pack(side="left", padx=5)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text="►", width=30, command=self.next_page)
        self.btn_next.pack(side="left", padx=2)

        # File Info
        self.file_info_label = ctk.CTkLabel(self.sidebar, text="No file loaded", font=("Arial", 10), text_color="gray")
        self.file_info_label.pack(side="bottom", pady=10)

    # --- LOGIC ---

    def get_target_key(self):
        return "bug" if "Bug" in self.target_selector.get() else "indicia"

    def on_target_switch(self, value):
        key = self.get_target_key()
        target_data = self.overlays[key]
        self.ui_size_var.set(target_data["size"].get())
        if target_data["coords"]:
            self.ui_x_var.set(round(target_data["coords"][0] / 72, 3))
            self.ui_y_var.set(round(target_data["coords"][1] / 72, 3))
        else:
            self.ui_x_var.set(0)
            self.ui_y_var.set(0)

    def on_canvas_click(self, event):
        if not self.tk_img: return 
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        if not (self.offset_x <= canvas_x <= self.offset_x + self.tk_img.width()) or \
           not (self.offset_y <= canvas_y <= self.offset_y + self.tk_img.height()):
            return

        img_x = canvas_x - self.offset_x
        img_y = canvas_y - self.offset_y
        
        x_pt = img_x / self.display_scale
        y_pt = img_y / self.display_scale
        
        target_key = self.get_target_key()
        
        if not self.overlays[target_key]["active"].get():
            self.overlays[target_key]["active"].set(True)
        
        self.overlays[target_key]["coords"] = (x_pt, y_pt)
        self.ui_x_var.set(round(x_pt / 72, 3))
        self.ui_y_var.set(round(y_pt / 72, 3))
        self.refresh_previews()

    def refresh_previews(self):
        if not self.page_image: return

        for key, data in self.overlays.items():
            if data["preview_id"]:
                self.canvas.delete(data["preview_id"])
                data["preview_id"] = None
            
            if data["active"].get() and data["coords"]:
                x_pt, y_pt = data["coords"]
                
                # Brightness check for Bug only
                if key == "bug":
                    check_x = int(x_pt * self.display_scale)
                    check_y = int(y_pt * self.display_scale)
                    try:
                        check_x = max(0, min(check_x, self.page_image.width - 1))
                        check_y = max(0, min(check_y, self.page_image.height - 1))
                        brightness = get_brightness_from_image(self.page_image, check_x, check_y)
                        data["pdf_asset"] = self.bug_white if brightness < 128 else self.bug_black
                    except:
                        pass

                try:
                    tk_img = get_bug_image(data["pdf_asset"], data["size"].get(), self.display_scale)
                    data["tk_ref"] = tk_img 
                    display_x = x_pt * self.display_scale + self.offset_x
                    display_y = y_pt * self.display_scale + self.offset_y
                    data["preview_id"] = self.canvas.create_image(
                        display_x, display_y, anchor="nw", image=tk_img
                    )
                except Exception as e:
                    print(f"Error drawing {key}: {e}")

    def on_ui_size_change(self, val):
        target_key = self.get_target_key()
        self.overlays[target_key]["size"].set(self.ui_size_var.get())
        self.refresh_previews()

    def apply_manual_pos(self):
        target_key = self.get_target_key()
        try:
            x_pt = self.ui_x_var.get() * 72
            y_pt = self.ui_y_var.get() * 72
            self.overlays[target_key]["coords"] = (x_pt, y_pt)
            self.overlays[target_key]["active"].set(True)
            self.refresh_previews()
        except:
            pass

    def open_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path: return
        self.pdf_path = file_path
        self.pdf_doc = load_pdf(file_path)
        self.current_page_index = 0
        
        # Display dimensions
        page = self.pdf_doc[0]
        w_in = page.rect.width / 72
        h_in = page.rect.height / 72
        self.file_info_label.configure(text=f"{os.path.basename(file_path)}\n{w_in:.2f} x {h_in:.2f} in")
        
        self.render_page()

    def render_page(self):
        self.canvas.delete("all")
        for d in self.overlays.values(): d["preview_id"] = None

        if not self.pdf_doc: return

        page = self.pdf_doc[self.current_page_index]
        base_pil, _, _, self.base_scale = get_page_image(page, self.canvas)
        
        w, h = base_pil.size
        new_w, new_h = int(w * self.zoom_level), int(h * self.zoom_level)
        self.page_image = base_pil.resize((new_w, new_h), Image.LANCZOS)
        
        self.tk_img = ImageTk.PhotoImage(self.page_image)
        self.display_scale = self.base_scale * self.zoom_level

        cx = float(self.canvas.winfo_width()) / 2
        cy = float(self.canvas.winfo_height()) / 2
        
        self.img_id = self.canvas.create_image(cx, cy, anchor="center", image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        bbox = self.canvas.bbox(self.img_id)
        if bbox: self.offset_x, self.offset_y = bbox[0], bbox[1]

        self.page_label.configure(text=f"Page {self.current_page_index+1} / {len(self.pdf_doc)}")
        self.refresh_previews()

    # --- RESTORED NAVIGATION METHODS ---
    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            # Reset Overlays on page change (Optional: Remove lines below to keep position)
            for d in self.overlays.values(): d["coords"] = None
            self.render_page()

    def next_page(self):
        if self.pdf_doc and self.current_page_index < len(self.pdf_doc) - 1:
            self.current_page_index += 1
            # Reset Overlays on page change
            for d in self.overlays.values(): d["coords"] = None
            self.render_page()

    def on_zoom(self, val):
        self.zoom_level = float(val)
        self.render_page()
        
    def save_pdf(self):
        save_pdf_with_overlays(self)

    def on_window_resize(self, event):
        if hasattr(self, "_resize_after_id"): self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(300, self.render_page)

    def on_mouse_wheel(self, event):
        direction = 1 if (hasattr(event, "delta") and event.delta > 0) or event.num == 4 else -1
        new_zoom = max(0.5, min(3.0, self.zoom_level * (1 + 0.1 * direction)))
        self.slider_zoom.set(new_zoom) # Sync slider
        self.zoom_level = new_zoom
        self.render_page()