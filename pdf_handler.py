import fitz
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
import os
import sys
import subprocess

def load_pdf(file_path):
    """Safely loads a PDF."""
    try:
        return fitz.open(file_path)
    except Exception as e:
        messagebox.showerror("Error", f"Could not load PDF: {e}")
        return None

def get_page_image(page, canvas_width, canvas_height):
    """Renders a PDF page to a PIL image that fits within the canvas dimensions."""
    # Logic to calculate scale to fit window
    margin = 50
    scale = min((canvas_width - margin) / page.rect.width, (canvas_height - margin) / page.rect.height, 2.0)
    
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    return img, ImageTk.PhotoImage(img), scale

def render_preview_image(overlay_page, target_width_inch, display_scale):
    """
    Renders the overlay (Bug/Indicia) for the UI preview.
    Uses the in-memory 'overlay_page' object, not a file path.
    """
    # Calculate how many pixels wide the overlay should be on screen
    target_width_px = int(target_width_inch * 72 * display_scale)
    
    scale_factor = target_width_px / overlay_page.rect.width
    mat = fitz.Matrix(scale_factor, scale_factor)
    
    pix = overlay_page.get_pixmap(matrix=mat, alpha=True)
    img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
    return ImageTk.PhotoImage(img)

def get_brightness_at_loc(image, x, y):
    """Checks pixel brightness to decide if we need a white or black bug."""
    try:
        r, g, b = image.getpixel((x, y))
        return int(0.299 * r + 0.587 * g + 0.114 * b)
    except Exception:
        return 128 # Default to mid-grey if out of bounds

def save_pdf_with_overlays(app):
    """Saves the final PDF with overlays applied to specific pages."""
    
    # Filter for valid items
    active_items = [v for v in app.overlays.values() if v["active"].get() and v["coords"] and v["page_index"] is not None]

    if not active_items:
        messagebox.showwarning("No Overlays", "No elements are active and placed.")
        return

    original_name = os.path.splitext(os.path.basename(app.pdf_path))[0]
    save_path = filedialog.asksaveasfilename(
        initialfile=f"{original_name} - Proof.pdf",
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")]
    )
    if not save_path: return

    try:
        doc = fitz.open(app.pdf_path)

        for item in active_items:
            # 1. Get the correct page
            try:
                page = doc[item["page_index"]]
            except IndexError:
                continue

            # 2. Get the asset page (from app memory)
            # app.assets stores the fitz.Document, we need the first page
            asset_doc = app.assets[item["asset_key"]] 
            overlay_page = asset_doc[0]

            # 3. Calculate Scale
            x_pt, y_pt = item["coords"]
            width_pt = item["size"].get() * 72
            scale = width_pt / overlay_page.rect.width

            # 4. Place it
            rect = fitz.Rect(
                x_pt, 
                y_pt, 
                x_pt + overlay_page.rect.width * scale, 
                y_pt + overlay_page.rect.height * scale
            )
            page.show_pdf_page(rect, asset_doc, 0)

        doc.save(save_path)
        messagebox.showinfo("Success", "PDF Saved Successfully.")
        
        # Open File
        if sys.platform == "darwin": subprocess.call(["open", "-R", save_path])
        elif sys.platform == "win32": os.startfile(os.path.normpath(save_path))

    except Exception as e:
        messagebox.showerror("Error", f"Failed to save PDF: {e}")