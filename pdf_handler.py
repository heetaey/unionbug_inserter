import fitz
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
import os
import sys
import subprocess

def load_pdf(file_path): 
    return fitz.open(file_path)

def get_page_image(page, canvas):
    canvas.update_idletasks()
    max_w = canvas.winfo_width()
    max_h = canvas.winfo_height()
    margin_x = max(max_w * 0.05, 50)
    margin_y = max(max_h * 0.05, 50)
    scale = min((max_w - 2 * margin_x) / page.rect.width, (max_h - 2 * margin_y) / page.rect.height, 2.0)
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img, ImageTk.PhotoImage(img), pix, scale

def get_bug_image(bug_pdf_path, width_inch, scale):
    bug_doc = fitz.open(bug_pdf_path)
    bug_page = bug_doc[0]
    bug_width_px = int(width_inch * 72 * scale)
    scale_factor = bug_width_px / bug_page.rect.width
    mat = fitz.Matrix(scale_factor, scale_factor)
    bug_pix = bug_page.get_pixmap(matrix=mat, alpha=True)
    bug_img = Image.frombytes("RGBA", [bug_pix.width, bug_pix.height], bug_pix.samples)
    return ImageTk.PhotoImage(bug_img)

def get_brightness_from_image(image, x, y):
    r, g, b = image.getpixel((x, y))
    return int(0.299 * r + 0.587 * g + 0.114 * b)

# === NEW SAVE FUNCTION ===
def save_pdf_with_overlays(app):
    # Check if ANY overlay is active
    active_items = [k for k, v in app.overlays.items() if v["active"].get() and v["coords"]]
    
    if not active_items:
        messagebox.showwarning("No Overlays", "No elements (Bug or Indicia) are active and placed.")
        return

    original_basename = os.path.splitext(os.path.basename(app.pdf_path))[0]
    save_path = filedialog.asksaveasfilename(
        initialfile=f"{original_basename}_processed.pdf",
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")]
    )
    if not save_path: return

    doc = fitz.open(app.pdf_path)
    page = doc[app.current_page_index]

    # Iterate through all overlays in the dictionary
    for key, item in app.overlays.items():
        # Only process if Checkbox is Checked AND Coords exist
        if item["active"].get() and item["coords"]:
            x_pt, y_pt = item["coords"]
            
            # Load the specific PDF asset for this item
            overlay_doc = fitz.open(item["pdf_asset"])
            overlay_page = overlay_doc[0]
            
            # Calculate Scale
            target_width_pt = item["size"].get() * 72
            scale_factor = target_width_pt / overlay_page.rect.width
            
            # Create Rect
            rect = fitz.Rect(
                x_pt,
                y_pt,
                x_pt + overlay_page.rect.width * scale_factor,
                y_pt + overlay_page.rect.height * scale_factor
            )
            
            # Insert
            page.show_pdf_page(rect, overlay_doc, 0)

    doc.save(save_path)
    messagebox.showinfo("Saved", f"PDF saved successfully.")
    
    # Open file (Platform specific)
    if sys.platform == "darwin": subprocess.call(["open", "-R", save_path])
    elif sys.platform == "win32": os.startfile(os.path.normpath(save_path))