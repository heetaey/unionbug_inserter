"""
User Interface module for the Union Bug Placement App.
Contains the UnionBugApp class which manages the GUI and user interactions.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import subprocess
import sys
import fitz  # PyMuPDF

from config import BUG_WIDTH_IN, SAFE_MARGIN_PT
import pdf_handler
import bug_placer

class UnionBugApp:
    """Main application GUI for placing a union bug on a PDF."""
    
    def __init__(self, root):
        """
        Initialize the main app window and set up UI components.
        
        Parameters:
            root (tk.Tk): The main Tkinter window.
        """
        self.root = root
        self.root.title("Union Bug Placer")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        
        # Determine the bundle directory and asset paths
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        self.black_bug = os.path.join(bundle_dir, "assets", "UnionBug - Small Black.pdf")
        self.white_bug = os.path.join(bundle_dir, "assets", "UnionBug - Small White.pdf")
        
        self.pdf_path = ""
        self.chosen_bug = self.black_bug
        
        self.selected_page = 0
        self.doc = None
        self.selected_pages = []
        self.trimbox = None
        self.click_coords = {}  # Maps page index to (x, y) coordinates in points
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.scale_x = 1
        self.scale_y = 1
        
        self.bug_width_in = BUG_WIDTH_IN
        
        self.canvas_width = 600
        self.canvas_height = 800
        
        self.manual_x_in = tk.StringVar()
        self.manual_y_in = tk.StringVar()
        
        self.no_placement = set()
        
        # Build the GUI layout
        self.build_ui()
    
    def build_ui(self):
        """Construct the layout and widgets for the GUI."""
        tk.Label(self.root, text="PDF File:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.pdf_entry = tk.Entry(self.root, width=60)
        self.pdf_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Browse", command=self.select_pdf).grid(row=0, column=2)
        
        tk.Label(self.root, text="Pages:").grid(row=1, column=0, padx=5, pady=5, sticky="ne")
        self.page_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE, height=5, exportselection=False)
        self.page_listbox.bind("<<ListboxSelect>>", self.on_checkbox_change)
        self.page_listbox.bind("<<ListboxSelect>>", self.on_page_listbox_change)
        self.page_listbox.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Single-page preview controls
        preview_frame = tk.Frame(self.root)
        preview_frame.grid(row=1, column=1, padx=5, pady=5, sticky="e")
        tk.Button(preview_frame, text="←", width=3, command=self.prev_page).pack(side="left")
        self.page_selector = ttk.Combobox(preview_frame, state="readonly", width=10)
        self.page_selector.pack(side="left", padx=5)
        tk.Button(preview_frame, text="→", width=3, command=self.next_page).pack(side="left")
        
        self.trim_label = tk.Label(self.root, text="")
        self.trim_label.grid(row=1, column=2, padx=5)
        
        tk.Button(self.root, text="Choose Save Location", command=self.choose_output_path).grid(row=2, column=0, sticky="e")
        self.filename_entry = tk.Entry(self.root, width=60)
        self.filename_entry.grid(row=2, column=1, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.root, width=self.canvas_width, height=self.canvas_height, bg="gray")
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.canvas.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        # Coordinates input frame
        coord_frame = tk.Frame(self.root)
        coord_frame.grid(row=7, column=0, columnspan=3, pady=5)
        tk.Label(coord_frame, text="X (in):").pack(side="left")
        tk.Entry(coord_frame, width=6, textvariable=self.manual_x_in).pack(side="left", padx=(0, 10))
        tk.Label(coord_frame, text="Y (in):").pack(side="left")
        tk.Entry(coord_frame, width=6, textvariable=self.manual_y_in).pack(side="left", padx=(0, 10))
        tk.Button(coord_frame, text="Apply Coordinates", command=self.apply_manual_coords).pack(side="left")
        tk.Button(coord_frame, text="Clear This Page", command=self.clear_current_page_placement).pack(side="left", padx=(10, 0))
        
        tk.Label(self.root, text="Bug Width (inches):").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        self.bug_width_entry = tk.Entry(self.root, width=10)
        self.bug_width_entry.insert(0, str(self.bug_width_in))
        self.bug_width_entry.grid(row=6, column=1, sticky="w")
        tk.Button(self.root, text="Update Size", command=self.update_bug_width).grid(row=6, column=2, padx=5, pady=5)
        
        self.status_label = tk.Label(self.root, text="Load a PDF to begin.", fg="gray")
        self.status_label.grid(row=4, column=0, columnspan=3)
        
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=5, column=0, columnspan=3)
        tk.Button(button_frame, text="Place Union Bug & Save PDF", command=self.place_and_save).pack(side="left", padx=10)
        tk.Button(button_frame, text="Clear Placement", command=self.clear_placement).pack(side="left")
    
    def on_checkbox_change(self, event=None):
        """
        Handle changes in the page selection listbox.
        
        Updates placement status and re-renders the preview.
        """
        self.no_placement.discard(self.selected_page)
        self.update_page_selection()
        self.render_preview()
    
    def update_bug_width(self):
        """Update the union bug width based on user input."""
        try:
            value = float(self.bug_width_entry.get())
            if value <= 0:
                raise ValueError
            self.bug_width_in = value
            self.render_preview()
        except ValueError:
            messagebox.showerror("Invalid Input", "Bug width must be a positive number.")
    
    def select_pdf(self):
        """Handle PDF file selection and load the PDF."""
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.load_pdf(file_path)
    
    def load_pdf(self, file_path):
        """
        Load the selected PDF and initialize related UI components.
        
        Parameters:
            file_path (str): Path to the PDF file.
        """
        self.pdf_path = file_path
        self.doc = pdf_handler.load_pdf(file_path)
        base = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(os.path.dirname(file_path), f"{base}_bug.pdf")
        self.filename_entry.delete(0, tk.END)
        self.filename_entry.insert(0, output_path)
        self.page_listbox.delete(0, tk.END)
        for i in range(len(self.doc)):
            self.page_listbox.insert(tk.END, f"Page {i + 1}")
        self.page_listbox.select_set(0)
        
        self.page_selector['values'] = [f"Page {i + 1}" for i in range(len(self.doc))]
        if not hasattr(self, "selected_page"):
            self.page_selector.current(0)
        self.page_selector.bind("<<ComboboxSelected>>", self.update_page_selection)
        
        self.update_page_selection()
    
    def update_page_selection(self, event=None):
        """
        Update the currently selected page and its preview details.
        
        Computes the trim box and re-renders the preview.
        """
        if self.selected_page in self.page_listbox.curselection():
            self.no_placement.discard(self.selected_page)
        
        page = self.doc[self.selected_page]
        self.trimbox = pdf_handler.get_trimbox(page)
        # Display trim box dimensions in inches
        tw = round(self.trimbox.width / 72, 2)
        th = round(self.trimbox.height / 72, 2)
        self.trim_label.config(text=f"Trim: {tw}\" x {th}\"")
        self.render_preview()
    
    def render_preview(self):
        """
        Render the PDF page preview along with trim, bleed, and safe zone outlines.
        
        Also triggers rendering of the union bug preview if applicable.
        """
        page = self.doc[self.selected_page]
        pix = page.get_pixmap(dpi=100)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        rect = page.rect
        is_landscape = rect.width > rect.height
        if is_landscape:
            img.thumbnail((self.canvas_width, self.canvas_height // 1.5), Image.Resampling.LANCZOS)
        else:
            img.thumbnail((self.canvas_width // 1.5, self.canvas_height), Image.Resampling.LANCZOS)
        
        img_w, img_h = img.size
        self.canvas_offset_x = (self.canvas_width - img_w) // 2
        self.canvas_offset_y = (self.canvas_height - img_h) // 2
        self.scale_x = page.rect.width / img_w
        self.scale_y = page.rect.height / img_h
        
        self.preview_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.canvas_width, self.canvas_height, fill="gray")
        
        # Draw trim area (RED)
        trim = self.trimbox
        trim_x1 = int(trim.x0 * self.scale_x + self.canvas_offset_x)
        trim_y1 = int(trim.y0 * self.scale_y + self.canvas_offset_y)
        trim_x2 = int(trim.x1 * self.scale_x + self.canvas_offset_x)
        trim_y2 = int(trim.y1 * self.scale_y + self.canvas_offset_y)
        self.canvas.create_rectangle(trim_x1, trim_y1, trim_x2, trim_y2, outline="red")
        
        # Draw bleed area (ORANGE) - full page rect
        bleed = page.rect
        bleed_x1 = int(bleed.x0 * self.scale_x + self.canvas_offset_x)
        bleed_y1 = int(bleed.y0 * self.scale_y + self.canvas_offset_y)
        bleed_x2 = int(bleed.x1 * self.scale_x + self.canvas_offset_x)
        bleed_y2 = int(bleed.y1 * self.scale_y + self.canvas_offset_y)
        self.canvas.create_rectangle(bleed_x1, bleed_y1, bleed_x2, bleed_y2, outline="orange", dash=(4, 4))
        
        # Draw safe zone (GREEN), inset from trim box using SAFE_MARGIN_PT
        safe_x1 = int((trim.x0 + SAFE_MARGIN_PT) * self.scale_x + self.canvas_offset_x)
        safe_y1 = int((trim.y0 + SAFE_MARGIN_PT) * self.scale_y + self.canvas_offset_y)
        safe_x2 = int((trim.x1 - SAFE_MARGIN_PT) * self.scale_x + self.canvas_offset_x)
        safe_y2 = int((trim.y1 - SAFE_MARGIN_PT) * self.scale_y + self.canvas_offset_y)
        self.canvas.create_rectangle(safe_x1, safe_y1, safe_x2, safe_y2, outline="green", dash=(2, 2))
        
        self.canvas.create_image(self.canvas_offset_x, self.canvas_offset_y, anchor="nw", image=self.preview_img)
        
        # Show bug preview if page is selected and placement is enabled
        selected_indices = self.page_listbox.curselection()
        if (self.selected_page in selected_indices and 
            self.selected_page not in self.no_placement and 
            (self.selected_page in self.click_coords or len(self.click_coords) > 0)):
            self.render_bug_preview()
        
        self.sync_page_selector_to_preview()
    
    def render_bug_preview(self):
        """
        Render a preview of the union bug on the canvas based on click coordinates.
        
        Uses bug placer to select the appropriate bug and renders it at the calculated position.
        """
        if self.selected_page in self.no_placement:
            return
        
        coords = self.click_coords.get(self.selected_page)
        if coords:
            x, y = coords
        elif self.click_coords:
            first_page = next(iter(self.click_coords))
            x, y = self.click_coords[first_page]
        else:
            return  # No placement coordinate available
        
        # Choose bug based on contrast using the bug placer module
        self.chosen_bug = bug_placer.choose_bug_by_contrast(self.doc[self.selected_page], x, y, self.white_bug, self.black_bug)
        
        bug_doc = fitz.open(self.chosen_bug)
        bug_page = bug_doc[0]
        bug_rect = bug_page.rect
        
        target_width_pt = self.bug_width_in * 72
        scale = target_width_pt / bug_rect.width
        
        matrix = fitz.Matrix(scale, scale)
        bug_pix = bug_page.get_pixmap(matrix=matrix, alpha=True)
        bug_img = Image.frombytes("RGBA", [bug_pix.width, bug_pix.height], bug_pix.samples)
        
        display_width = int(bug_pix.width / self.scale_x)
        display_height = int(bug_pix.height / self.scale_y)
        bug_img_resized = bug_img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        
        preview_img = ImageTk.PhotoImage(bug_img_resized)
        
        x_canvas = x / self.scale_x + self.canvas_offset_x - display_width // 2
        y_canvas = y / self.scale_y + self.canvas_offset_y - display_height // 2

        
        self.canvas.create_image(x_canvas, y_canvas, anchor="nw", image=preview_img)
        self.canvas.bug_preview = preview_img  # Prevent garbage collection
        
        self.status_label.config(text=f"Placement: {round(x / 72, 2)}\" x {round(y / 72, 2)}\"")
    
    def on_canvas_click(self, event):
        """
        Handle click events on the canvas to record placement coordinates.
        
        Converts canvas coordinates to PDF points and stores them for the selected page.
        """
        x_pdf = (event.x - self.canvas_offset_x) * self.scale_x
        y_pdf = (event.y - self.canvas_offset_y) * self.scale_y
        self.click_coords[self.selected_page] = (x_pdf, y_pdf)
        self.render_preview()
    
    def clear_placement(self):
        """
        Clear the current bug placement.
        
        Reloads the original PDF and clears any stored click coordinates.
        """
        try:
            self.doc.close()
            self.doc = pdf_handler.load_pdf(self.pdf_path)
            self.click_coords = {}
            self.status_label.config(text="Placement cleared. Source PDF reloaded.")
            self.update_page_selection()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset: {str(e)}")
    
    def choose_output_path(self):
        """Let the user choose the output PDF save location."""
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.filename_entry.delete(0, tk.END)
            self.filename_entry.insert(0, file_path)
    
    def place_and_save(self):
        """
        Place the union bug on selected pages and save the modified PDF.
        
        Iterates over selected pages, uses the bug placer for placement, and saves the final PDF.
        """
        try:
            selected_indices = self.page_listbox.curselection()
            if not selected_indices:
                messagebox.showerror("No Pages Selected", "Please select one or more pages.")
                return
            
            for idx in selected_indices:
                page_num = int(self.page_listbox.get(idx).split()[-1]) - 1
                page = self.doc[page_num]
                click_coord = self.click_coords.get(page_num, None)
                bug_placer.place_union_bug_on_page(page, click_coord, self.chosen_bug, self.bug_width_in, SAFE_MARGIN_PT)
            
            output_path = self.filename_entry.get().strip()
            if not output_path.lower().endswith(".pdf"):
                output_path += ".pdf"
            if os.path.abspath(output_path) == os.path.abspath(self.pdf_path):
                messagebox.showerror("Save Error", "Can't overwrite original file.")
                return
            
            pdf_handler.save_pdf(self.doc, output_path)
            self.status_label.config(text=f"Saved to {output_path}")
            messagebox.showinfo("Success", f"Saved to: {output_path}")
            subprocess.run(["open", os.path.dirname(output_path)])
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))
    
    def prev_page(self):
        """Navigate to the previous page in the PDF preview."""
        if self.selected_page > 0:
            self.selected_page -= 1
            self.page_selector.current(self.selected_page)
            self.update_page_selection()
    
    def next_page(self):
        """Navigate to the next page in the PDF preview."""
        if self.selected_page < len(self.doc) - 1:
            self.selected_page += 1
            self.page_selector.current(self.selected_page)
            self.update_page_selection()
    
    def on_page_listbox_change(self, event=None):
        """
        Handle changes in the page listbox selection.
        
        Updates the preview and active page based on user selection.
        """
        selected_indices = self.page_listbox.curselection()
        if self.selected_page not in selected_indices:
            self.render_preview()
            return
        
        if selected_indices:
            self.selected_page = selected_indices[0]
            self.no_placement.discard(self.selected_page)
            
            if self.page_selector.get() != f"Page {self.selected_page + 1}":
                self.page_selector.set(f"Page {self.selected_page + 1}")
            
            self.update_page_selection()
            self.render_preview()
    
    def apply_manual_coords(self):
        """Apply manual coordinate input for bug placement."""
        try:
            x_in = float(self.manual_x_in.get())
            y_in = float(self.manual_y_in.get())
            x_pt = x_in * 72
            y_pt = y_in * 72
            self.click_coords[self.selected_page] = (x_pt, y_pt)
            self.render_preview()
            self.status_label.config(text=f"Manual placement at {x_in}\" x {y_in}\"")
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid numbers for X and Y.")
    
    def clear_current_page_placement(self):
        """
        Clear the bug placement for the current page.
        
        Warns if the current page is the fallback for other pages.
        """
        page = self.selected_page
        if page in self.click_coords and len(self.click_coords) == 1:
            messagebox.showinfo(
                "Fallback Placement",
                f"Page {page + 1} is currently the fallback for other pages.\n"
                "You must place the bug somewhere else first before clearing this one."
            )
            return
        if page in self.click_coords:
            del self.click_coords[page]
            self.status_label.config(text=f"Placement cleared for Page {page + 1}")
        else:
            self.status_label.config(text=f"Fallback disabled for Page {page + 1}")
        self.no_placement.add(page)
        self.page_listbox.selection_clear(page)
        self.render_preview()
    
    def sync_page_selector_to_preview(self):
        """Ensure the page selector dropdown matches the current preview page."""
        current_dropdown_text = self.page_selector.get()
        correct_text = f"Page {self.selected_page + 1}"
        if current_dropdown_text != correct_text:
            self.page_selector.set(correct_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = UnionBugApp(root)
    root.mainloop()
