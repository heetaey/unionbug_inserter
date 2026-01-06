import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk  # NEW: Modern UI library
from PIL import Image, ImageTk
from pdf_handler import (
    load_pdf, get_page_image, get_bug_image, save_pdf_with_bug,
    get_brightness_from_image
)
# Assuming assets.py exists as per your original code
from assets import get_bug_paths
import os

# Set default theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

class UnionBugInserter:
    def __init__(self, root):
        self.root = root
        self.root.title("Union Bug Placer")
        
        # Configure grid layout for the main window
        # Column 0: Canvas (expandable), Column 1: Sidebar (fixed)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_rowconfigure(0, weight=1)

        # Import BOTH functions
        from assets import get_bug_paths, get_indicia_paths
        self.bug_black, self.bug_white = get_bug_paths()
        self.indicia = get_indicia_paths()        

        # Application State
        self.overlay_mode = "Union Bug"
        self.file_type = None
        self.zoom_level = 1.0
        self.bug_size_inch = 0.3
        self.file_type = None
        self.original_width_in = None
        self.original_height_in = None
        self.zoom_level = 1.0
        self.bug_size_inch = 0.3
        self.bug_coords_pt = None
        self.bug_pdf = None
        self.current_page_index = 0
        self.pdf_doc = None
        self.page_image = None
        self.tk_img = None
        self.pdf_pix = None
        self.offset_x = 0
        self.offset_y = 0
        self.pdf_path = None
        self.display_scale = 1.0
        self.base_scale = 1.0
        self.bug_size_var = tk.DoubleVar(value=self.bug_size_inch)
        self.bug_coords_pt = None       

        self.setup_ui()

    def setup_ui(self):
        # ================= MAIN CANVAS AREA =================
        self.canvas_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # We stick to standard tk.Canvas for image manipulation performance
        self.canvas = tk.Canvas(self.canvas_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        self.scroll_y = ctk.CTkScrollbar(self.canvas_frame, orientation="vertical", command=self.canvas.yview)
        self.scroll_x = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)
        
        self.scroll_y.grid(row=0, column=1, sticky="ns")
        self.scroll_x.grid(row=1, column=0, sticky="ew")

        # Events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)    # Linux scroll down
        self.root.bind("<Configure>", self.on_window_resize)

        # ================= SIDEBAR CONTROLS =================
        self.sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        
        # --- 1. File Operations ---
        self.lbl_title = ctk.CTkLabel(self.sidebar, text="ACTIONS", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_title.pack(padx=20, pady=(20, 10), anchor="w")

        self.btn_open = ctk.CTkButton(self.sidebar, text="Open PDF", command=self.open_pdf)
        self.btn_open.pack(padx=20, pady=5, fill="x")

        self.btn_save = ctk.CTkButton(self.sidebar, text="Save PDF", command=self.save_pdf, fg_color="green")
        self.btn_save.pack(padx=20, pady=5, fill="x")
        
        # --- 2. Overlay Settings (Toggle & Size) ---
        ctk.CTkLabel(self.sidebar, text="OVERLAY SETTINGS", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")
        
        # === THIS IS THE MISSING TOGGLE BUTTON ===
        self.overlay_type_var = ctk.StringVar(value="Union Bug")
        self.overlay_switch = ctk.CTkSegmentedButton(
            self.sidebar, 
            values=["Union Bug", "Indicia"],
            variable=self.overlay_type_var,
            command=self.on_overlay_switch
        )
        self.overlay_switch.pack(padx=20, pady=5, fill="x")
        # =========================================

        ctk.CTkLabel(self.sidebar, text="Size (inches):").pack(padx=20, pady=(5, 0), anchor="w")
        
        # Frame for Slider + Input Box
        self.size_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.size_frame.pack(padx=20, pady=5, fill="x")

        # Slider
        self.slider_bug = ctk.CTkSlider(
            self.size_frame, 
            from_=0.1, 
            to=2.0, 
            number_of_steps=190,
            variable=self.bug_size_var, 
            command=self.update_bug_size
        )
        self.slider_bug.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Input Box
        self.ent_bug_size = ctk.CTkEntry(
            self.size_frame, 
            textvariable=self.bug_size_var, 
            width=60
        )
        self.ent_bug_size.pack(side="right")
        self.ent_bug_size.bind("<Return>", lambda e: self.update_bug_size())
        self.ent_bug_size.bind("<FocusOut>", lambda e: self.update_bug_size())

        self.btn_clear = ctk.CTkButton(self.sidebar, text="Clear Overlay", command=self.clear_bug, fg_color="transparent", border_width=1)
        self.btn_clear.pack(padx=20, pady=5, fill="x")
        
        # Slider (Expanded to fill left side)
        self.slider_bug = ctk.CTkSlider(
            self.size_frame, 
            from_=0.1, 
            to=2.0, 
            number_of_steps = 190,
            variable=self.bug_size_var, 
            command=self.update_bug_size
        )
        self.slider_bug.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Entry (Fixed width on right side)
        self.ent_bug_size = ctk.CTkEntry(
            self.size_frame, 
            textvariable=self.bug_size_var, 
            width=60
        )
        self.ent_bug_size.pack(side="right")
        
        # Bind keys to update immediately when user types specific size
        self.ent_bug_size.bind("<Return>", lambda e: self.update_bug_size())
        self.ent_bug_size.bind("<FocusOut>", lambda e: self.update_bug_size())

        self.btn_clear = ctk.CTkButton(self.sidebar, text="Clear Bug", command=self.clear_bug, fg_color="transparent", border_width=1)
        self.btn_clear.pack(padx=20, pady=5, fill="x")

        # --- Position Controls ---
        ctk.CTkLabel(self.sidebar, text="POSITION (in)", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")

        self.pos_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.pos_frame.pack(padx=20, pady=0, fill="x")
        
        self.x_var = tk.DoubleVar()
        self.y_var = tk.DoubleVar()

        # Grid for X/Y inputs
        ctk.CTkLabel(self.pos_frame, text="X:").grid(row=0, column=0, padx=5)
        self.ent_x = ctk.CTkEntry(self.pos_frame, textvariable=self.x_var, width=60)
        self.ent_x.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(self.pos_frame, text="Y:").grid(row=0, column=2, padx=5)
        self.ent_y = ctk.CTkEntry(self.pos_frame, textvariable=self.y_var, width=60)
        self.ent_y.grid(row=0, column=3, padx=5)

        self.btn_set_pos = ctk.CTkButton(self.sidebar, text="Set Manual Pos", command=self.update_bug_from_inputs, height=25)
        self.btn_set_pos.pack(padx=20, pady=(10, 5), fill="x")
        
        self.btn_center = ctk.CTkButton(self.sidebar, text="Center Horizontally", command=self.center_x, height=25)
        self.btn_center.pack(padx=20, pady=5, fill="x")

        # --- View / Navigation ---
        ctk.CTkLabel(self.sidebar, text="VIEW & NAV", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")

        # Zoom
        ctk.CTkLabel(self.sidebar, text="Zoom Level:").pack(padx=20, anchor="w")
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.slider_zoom = ctk.CTkSlider(self.sidebar, from_=0.5, to=3.0, variable=self.zoom_var, command=self.on_zoom)
        self.slider_zoom.pack(padx=20, pady=5, fill="x")

        # Pages
        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(padx=20, pady=10, fill="x")
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="◄", width=30, command=self.prev_page)
        self.btn_prev.pack(side="left", padx=2)
        
        self.page_label = ctk.CTkLabel(self.nav_frame, text="Page 1", width=80)
        self.page_label.pack(side="left", padx=5)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text="►", width=30, command=self.next_page)
        self.btn_next.pack(side="left", padx=2)

        # Info at bottom
        self.file_info_label = ctk.CTkLabel(self.sidebar, text="No file loaded", font=("Arial", 10), text_color="gray")
        self.file_info_label.pack(side="bottom", pady=10)

    # ... [Keep all logic methods below unchanged: open_pdf, render_page, etc.] ...
    # ... [Just ensure they reference self.canvas or self.x_var correctly] ...

    def open_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path:
            return
        self.pdf_path = file_path
        self.pdf_doc = load_pdf(file_path)
        self.file_type = "pdf"
        self.current_page_index = 0
        
        self.render_page()
        
        page = self.pdf_doc[self.current_page_index]
        width_in = page.rect.width / 72
        height_in = page.rect.height / 72
        self.original_width_in = width_in
        self.original_height_in = height_in

        self.file_info_label.configure(
            text=f"{os.path.basename(self.pdf_path)}\n{width_in:.2f} × {height_in:.2f} in")

    def render_page(self):
        # Logic remains identical, but ensure we delete only if items exist
        self.canvas.delete("all")

        if not self.pdf_doc: return

        page = self.pdf_doc[self.current_page_index]
        base_pil, _, self.pdf_pix, self.base_scale = get_page_image(page, self.canvas)

        w, h = base_pil.size
        zoomed = base_pil.resize(
            (int(w * self.zoom_level), int(h * self.zoom_level)),
            Image.LANCZOS
        )

        self.page_image = zoomed
        self.tk_img = ImageTk.PhotoImage(zoomed)
        self.display_scale = self.base_scale * self.zoom_level

        cx = float(self.canvas.winfo_width()) / 2
        cy = float(self.canvas.winfo_height()) / 2
        
        self.img_id = self.canvas.create_image(cx, cy, anchor="center", image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        bbox = self.canvas.bbox(self.img_id)
        if bbox:
            self.offset_x, self.offset_y = bbox[0], bbox[1]

        self.page_label.configure(text=f"Page {self.current_page_index+1} / {len(self.pdf_doc)}")
        
        # Redraw bug if exists
        if self.bug_coords_pt:
            x_display = self.bug_coords_pt[0] * self.display_scale
            y_display = self.bug_coords_pt[1] * self.display_scale
            self.place_bug_preview(x_display, y_display)

    def on_canvas_click(self, event):
        if not self.tk_img: return 
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Check if we are clicking inside the image
        if not (self.offset_x <= canvas_x <= self.offset_x + self.tk_img.width()) or \
           not (self.offset_y <= canvas_y <= self.offset_y + self.tk_img.height()):
            return

        img_x = canvas_x - self.offset_x
        img_y = canvas_y - self.offset_y
        
        # Convert to PDF points
        x_pt = img_x / self.display_scale
        y_pt = img_y / self.display_scale
        
        self.bug_coords_pt = (x_pt, y_pt)
        self.update_toolbar_coords(x_pt, y_pt)
        self.place_bug_preview(img_x, img_y)
        
    def on_zoom(self, val):
        self.zoom_level = float(val)
        self.render_page()
        
    def on_overlay_switch(self, value):
        self.overlay_mode = value
        # If an overlay is already placed, refresh it to show the new type immediately
        if self.bug_coords_pt:
            self.update_bug_size()

    def place_bug_preview(self, img_x, img_y):
        # Clamp coordinates to prevent errors if user clicks edge
        clamped_x = max(0, min(int(img_x), self.page_image.width - 1))
        clamped_y = max(0, min(int(img_y), self.page_image.height - 1))
        
        # LOGIC: Choose Asset based on Mode
        if self.overlay_mode == "Union Bug":
            # Smart Contrast for Union Bug
            try:
                brightness = get_brightness_from_image(self.page_image, clamped_x, clamped_y)
                is_dark_bg = brightness < 128
            except Exception:
                is_dark_bg = False # Default to black bug if check fails
            
            self.bug_pdf = self.bug_white if is_dark_bg else self.bug_black
            
        else:
            self.bug_pdf = self.indicia

        # Generate the preview image
        try:
            self.bug_imgtk = get_bug_image(self.bug_pdf, self.bug_size_var.get(), self.display_scale)
        except Exception as e:
            print(f"Error loading asset: {e}")
            return

        # Clear old preview
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)

        # Place new preview
        self.preview_bug_id = self.canvas.create_image(
            img_x + self.offset_x,
            img_y + self.offset_y,
            anchor="nw",
            image=self.bug_imgtk
        )

    def update_bug_from_inputs(self):
        if not self.page_image: return
        try:
            x_in = float(self.x_var.get())
            y_in = float(self.y_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid coordinates")
            return
            
        x_pt = x_in * 72
        y_pt = y_in * 72
        self.bug_coords_pt = (x_pt, y_pt)
        
        x_display = x_pt * self.display_scale
        y_display = y_pt * self.display_scale
        
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)
        self.place_bug_preview(x_display, y_display)

    def save_pdf(self):
        save_pdf_with_bug(self)

    def clear_bug(self):
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)
            del self.preview_bug_id
        self.bug_coords_pt = None
        self.x_var.set(0.0)
        self.y_var.set(0.0)

    def update_bug_size(self, value=None):
        # Validate input (in case user typed garbage in the text box)
        try:
            # If the update comes from the slider (value is passed), round it and update the Var.
            # This fixes the text box display immediately.
            if value is not None:
                rounded_value = round(float(value), 2)
                self.bug_size_var.set(rounded_value)
            
            # Retrieve the clean value (whether from slider or manual entry)
            current_size = self.bug_size_var.get()
            
        except tk.TclError:
            return

        if self.bug_coords_pt is None:
            return

        # Force redraw at current position with new size
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)
            del self.preview_bug_id

        # Calculate display position
        x_display = self.bug_coords_pt[0] * self.display_scale
        y_display = self.bug_coords_pt[1] * self.display_scale
        
        self.place_bug_preview(x_display, y_display)
        
    def center_x(self):
        if not self.original_width_in: return
        self.x_var.set(round(self.original_width_in / 2, 3))
        self.update_bug_from_inputs()

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.bug_coords_pt = None
            self.render_page()

    def next_page(self):
        if self.pdf_doc and self.current_page_index < len(self.pdf_doc) - 1:
            self.current_page_index += 1
            self.bug_coords_pt = None
            self.render_page()
            
    def update_toolbar_coords(self, x_pt, y_pt):
        self.x_var.set(round(x_pt / 72, 3))
        self.y_var.set(round(y_pt / 72, 3))

    def on_window_resize(self, event):
        if hasattr(self, "_resize_after_id"):
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(300, self.render_page)

    def on_mouse_wheel(self, event):
        if hasattr(event, "delta"):
            direction = 1 if event.delta > 0 else -1
        else:
            direction = 1 if event.num == 4 else -1
        
        new_zoom = self.zoom_level * (1 + 0.1 * direction)
        new_zoom = max(0.5, min(3.0, new_zoom))
        self.zoom_level = new_zoom
        self.zoom_var.set(new_zoom)
        self.render_page()