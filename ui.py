
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

        tk.Button(toolbar, text="Open PDF", command=self.open_pdf).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Clear Bug", command=self.clear_bug).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Save PDF", command=self.save_pdf).pack(side=tk.LEFT)

        tk.Label(toolbar, text="Bug Width (in):").pack(side=tk.LEFT)
        self.bug_size_var = tk.DoubleVar(value=self.bug_size_inch)
        tk.Entry(toolbar, textvariable=self.bug_size_var, width=5).pack(side=tk.LEFT)

        tk.Label(toolbar, text="X (in):").pack(side=tk.LEFT)
        self.x_var = tk.DoubleVar()
        tk.Entry(toolbar, textvariable=self.x_var, width=6).pack(side=tk.LEFT)

        tk.Label(toolbar, text="Y (in):").pack(side=tk.LEFT)
        self.y_var = tk.DoubleVar()
        tk.Entry(toolbar, textvariable=self.y_var, width=6).pack(side=tk.LEFT)

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
        self.root.bind("<Configure>", self.on_window_resize)

    def open_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path:
            return
        self.pdf_path = file_path
        self.pdf_doc = load_pdf(file_path)
        self.current_page_index = 0
        self.render_page()

    def render_page(self):
        self.canvas.delete("all")
        self.page_image, self.tk_img, self.pdf_pix, self.scale = get_page_image(
            self.pdf_doc[self.current_page_index], self.canvas
        )
        canvas_center_x = self.canvas.winfo_width() / 2
        canvas_center_y = self.canvas.winfo_height() / 2
        self.img_id = self.canvas.create_image(canvas_center_x, canvas_center_y, anchor="center", image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        bbox = self.canvas.bbox(self.img_id)
        self.offset_x = bbox[0]
        self.offset_y = bbox[1]

        self.page_label.config(text=f"Page {self.current_page_index + 1} of {len(self.pdf_doc)}")
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
        self.place_bug_preview(img_x, img_y)

    def place_bug_preview(self, img_x, img_y):
        brightness = get_brightness_from_image(self.page_image, int(img_x), int(img_y))
        self.bug_pdf = self.white_bug_path if brightness < 128 else self.black_bug_path
        try:
            self.bug_imgtk = get_bug_image(self.bug_pdf, self.bug_size_var.get(), self.scale)
            self.preview_bug_id = self.canvas.create_image(
                img_x + self.offset_x, img_y + self.offset_y, anchor="nw", image=self.bug_imgtk
            )
        except Exception as e:
            print(f"Error rendering bug preview: {e}")

    def save_pdf(self):
        save_pdf_with_bug(self)

    def clear_bug(self):
        if hasattr(self, 'preview_bug_id'):
            self.canvas.delete(self.preview_bug_id)
            self.bug_coords = None

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

    def on_window_resize(self, event):
        if hasattr(self, "_resize_after_id"):
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(300, self.render_page)
