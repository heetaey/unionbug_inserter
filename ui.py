
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from pdf_handler import (
    load_pdf, get_page_image, get_bug_image, save_pdf_with_bug,
    get_brightness_from_image
)
from assets import get_bug_paths
import os

class UnionBugInserter:
    def __init__(self, root):
        self.root = root
        self.root.title("Union Bug Placer")

        self.black_bug_path, self.white_bug_path = get_bug_paths()

        self.file_type = None
        self.original_width_in = None
        self.original_height_in = None
        self.zoom_level = 1.0
        self.bug_size_inch = 0.3
        self.bug_coords = None
        self.bug_pdf = None
        self.current_page_index = 0
        self.pdf_doc = None
        self.page_image = None
        self.tk_img = None
        self.pdf_pix = None
        self.offset_x = 0
        self.offset_y = 0
        self.pdf_path = None
        self.setup_ui()

    def setup_ui(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill=tk.X)
        
        # Info label for file dimensions
        self.file_info_label = tk.Label(self.root, text="", anchor="w", fg="black")
        self.file_info_label.pack(fill=tk.X, padx=10, pady=(0, 5))

        tk.Button(toolbar, text="Open PDF", command=self.open_pdf).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Clear Bug", command=self.clear_bug).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Save PDF", command=self.save_pdf).pack(side=tk.LEFT)

        # tk.Label(toolbar, text="Bug Width (in):").pack(side=tk.LEFT)
        # self.bug_size_var = tk.DoubleVar(value=self.bug_size_inch)
        # tk.Entry(toolbar, textvariable=self.bug_size_var, width=5).pack(side=tk.LEFT)
        tk.Label(toolbar, text="Bug Width (in):").pack(side=tk.LEFT)
        self.bug_size_var = tk.DoubleVar(value=self.bug_size_inch)
        
        self.bug_slider = tk.Scale(toolbar, variable=self.bug_size_var, from_=0.1, to=2.0, resolution=0.05,
                           orient=tk.HORIZONTAL, length=150, command=self.update_bug_size)
        self.bug_slider.pack(side=tk.LEFT)
        
        # tk.Label(toolbar, text="Zoom:").pack(side=tk.LEFT)
        # self.zoom_var = tk.DoubleVar(value=1.0)
        # tk.Scale(
            # toolbar, variable=self.zoom_var,
            # from_=0.5, to=3.0, resolution=0.1,
            # orient=tk.HORIZONTAL, length=150,
            # command=self.on_zoom
        # ).pack(side=tk.LEFT)

        tk.Label(toolbar, text="X (in):").pack(side=tk.LEFT)
        self.x_var = tk.DoubleVar()
        tk.Entry(toolbar, textvariable=self.x_var, width=6).pack(side=tk.LEFT)

        tk.Label(toolbar, text="Y (in):").pack(side=tk.LEFT)
        self.y_var = tk.DoubleVar()
        tk.Entry(toolbar, textvariable=self.y_var, width=6).pack(side=tk.LEFT)
        
        # center‐X button
        tk.Button(toolbar, text="Center X", command=self.center_x).pack(side=tk.LEFT)
        # manual set
        tk.Button(toolbar, text="Set Bug Position", command=self.update_bug_from_inputs).pack(side=tk.LEFT)

        tk.Button(toolbar, text="◀", command=self.prev_page).pack(side=tk.LEFT)
        self.page_label = tk.Label(toolbar, text="Page 1")
        self.page_label.pack(side=tk.LEFT)
        tk.Button(toolbar, text="▶", command=self.next_page).pack(side=tk.LEFT)

        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="gray")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scroll_y = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_x = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)

        self.scroll_y.grid(row=0, column=1, sticky="ns")
        self.scroll_x.grid(row=1, column=0, sticky="ew")

        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        
        self.root.bind("<Configure>", self.on_window_resize)

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

        self.file_info_label.config(
            text=f"{os.path.basename(self.pdf_path)} — {width_in:.2f} × {height_in:.2f} in")

    def render_page(self):
        # Clear existing canvas
        self.canvas.delete("all")

        # Load base image and its natural scale
        page = self.pdf_doc[self.current_page_index]
        pil_img, _, self.pdf_pix, base_scale = get_page_image(page, self.canvas)

        # Resize according to zoom level
        w, h = pil_img.size
        zoomed = pil_img.resize(
            (int(w * self.zoom_level), int(h * self.zoom_level)),
            Image.LANCZOS
        )
        self.tk_img = ImageTk.PhotoImage(zoomed)

        # Combined scale for coordinate conversions
        self.display_scale = base_scale * self.zoom_level

        # Draw centered
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        self.img_id = self.canvas.create_image(cx, cy, anchor="center", image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        # Recompute offsets
        bbox = self.canvas.bbox(self.img_id)
        self.offset_x, self.offset_y = bbox[0], bbox[1]

        # Update toolbar labels
        self.page_label.config(text=f"Page {self.current_page_index + 1} of {len(self.pdf_doc)}")
        width_in = page.rect.width  / 72
        height_in = page.rect.height / 72
        self.file_info_label.config(
            text=f"{os.path.basename(self.pdf_path)} — {width_in:.2f} × {height_in:.2f} in"
        )

        # If there’s already a bug placed, re‐draw it at the same coords
        if self.bug_coords:
            self.place_bug_preview(*self.bug_coords)

    def on_canvas_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        bbox = self.canvas.bbox(self.img_id)
        if not bbox:
            return
        img_left, img_top = bbox[0], bbox[1]
        img_x = canvas_x - img_left
        img_y = canvas_y - img_top
        if not (0 <= img_x < self.tk_img.width() and 0 <= img_y < self.tk_img.height()):
            return
        self.bug_coords = (img_x, img_y)
        self.update_toolbar_coords(img_x, img_y)
        self.place_bug_preview(img_x, img_y)
        
    def on_zoom(self, val):
        # when the user moves the slider
        self.zoom_level = float(val)
        self.render_page()

    def place_bug_preview(self, img_x, img_y):
        brightness = get_brightness_from_image(self.page_image, int(img_x), int(img_y))
        self.bug_pdf = self.white_bug_path if brightness < 128 else self.black_bug_path

        try:
            self.bug_imgtk = get_bug_image(self.bug_pdf, self.bug_size_var.get(), self.display_scale)
        except Exception as e:
            messagebox.showerror("Bug Image Error", f"Could not load bug image: {e}")
            return  # ✅ Exit early if the bug image fails to load

        # Delete previous bug if exists
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)

        # ✅ Always create a new preview image
        self.preview_bug_id = self.canvas.create_image(
            img_x + self.offset_x,
            img_y + self.offset_y,
            anchor="nw",
            image=self.bug_imgtk
        )

    def update_bug_from_inputs(self):
        if not self.page_image or not self.original_width_in or not self.original_height_in:
            return

        try:
            x_in = float(self.x_var.get())
            y_in = float(self.y_var.get())
        except Exception as e:
            messagebox.showerror("Invalid Input", f"Error parsing X/Y inches: {e}")
            return

        # Bounds check
        if not (0 <= x_in < self.original_width_in) or not (0 <= y_in < self.original_height_in):
            messagebox.showerror(
                "Out of Bounds",
                f"Coordinates are outside the page bounds.\n"
                f"Size: {self.original_width_in:.2f} × {self.original_height_in:.2f} in"
            )
            return

        # Convert to points or pixels
        if self.file_type == "pdf":
            x_orig = x_in * 72
            y_orig = y_in * 72
        else:
            dpi = self.pdf_pix.xres
            x_orig = x_in * dpi
            y_orig = y_in * dpi

        # Scale to preview
        x_scaled = x_orig * self.display_scale
        y_scaled = y_orig * self.display_scale

        # ✅ Store scaled coords for preview placement
        self.bug_coords = (x_scaled, y_scaled)
        self.update_toolbar_coords(x_scaled, y_scaled)

        # Clear and re-place
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)
            del self.preview_bug_id

        self.place_bug_preview(x_scaled, y_scaled)

    def save_pdf(self):
        save_pdf_with_bug(self)

    def clear_bug(self):
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)
            self.bug_coords = None

    def update_bug_size(self, value=None):
        if self.bug_coords is None:
            return

        # Fully remove and replace the bug
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)
            del self.preview_bug_id

        # Re-render bug at last coordinates with new size
        img_x, img_y = self.bug_coords
        self.place_bug_preview(img_x, img_y)
        
    def center_x(self):
         if not self.original_width_in or not self.page_image:
             return
         # compute center in inches
         center_x_in = self.original_width_in / 2
         # populate the entry (so the user sees it)
         self.x_var.set(round(center_x_in, 3))
         # now place the bug just like update_bug_from_inputs would
         self.update_bug_from_inputs()

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.bug_coords = None
            self.render_page()

    def next_page(self):
        if self.pdf_doc and self.current_page_index < len(self.pdf_doc) - 1:
            self.current_page_index += 1
            self.bug_coords = None
            self.render_page()
            
    def update_toolbar_coords(self, img_x, img_y):
        # img_x/img_y are in scaled‐pixels; undo scale then convert to inches
        if self.file_type == "pdf":
            pts_x = img_x / self.display_scale
            pts_y = img_y / self.display_scale
            x_in = pts_x / 72
            y_in = pts_y / 72
        else:
            dpi = self.pdf_pix.xres
            px_x = img_x / self.display_scale
            px_y = img_y / self.display_scale
            x_in = px_x / dpi
            y_in = px_y / dpi

        # round and push into the entries
        self.x_var.set(round(x_in, 3))
        self.y_var.set(round(y_in, 3))

    def on_window_resize(self, event):
        if hasattr(self, "_resize_after_id"):
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(300, self.render_page)

    def on_mouse_wheel(self, event):
        # Determine scroll direction
        if hasattr(event, "delta"):
            direction = 1 if event.delta > 0 else -1
        else:
            direction = 1 if event.num == 4 else -1

        # Adjust zoom by 10% per tick (tweak as desired)
        new_zoom = self.zoom_level * (1 + 0.1 * direction)
        # clamp between your min/max
        new_zoom = max(0.5, min(3.0, new_zoom))

        # update state & slider (optional)
        self.zoom_level = new_zoom
        self.zoom_var.set(new_zoom)

        # re-render at new zoom
        self.render_page()
