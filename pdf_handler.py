import fitz
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
import os

def load_pdf(file_path):
    """Safely loads a PDF."""
    try:
        return fitz.open(file_path)
    except Exception as e:
        messagebox.showerror("Error", f"Could not load PDF: {e}")
        return None

def get_page_image(page, canvas_width, canvas_height):
    """Renders a PDF page to a PIL image that fits within the canvas dimensions."""
    margin = 50
    if page.rect.width == 0 or page.rect.height == 0:
        return None, None, 1.0

    scale = min((canvas_width - margin) / page.rect.width, (canvas_height - margin) / page.rect.height, 2.0)
    
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    return img, ImageTk.PhotoImage(img), scale

def render_preview_image(overlay_page, target_width_inch, display_scale):
    """Renders the overlay (Bug/Indicia) for the UI preview."""
    target_width_px = int(target_width_inch * 72 * display_scale)
    aspect = overlay_page.rect.height / overlay_page.rect.width
    target_height_px = int(target_width_px * aspect)
    
    mat = fitz.Matrix(target_width_px / overlay_page.rect.width, target_height_px / overlay_page.rect.height)
    pix = overlay_page.get_pixmap(matrix=mat, alpha=True)
    img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
    
    return ImageTk.PhotoImage(img)

def get_brightness_at_loc(pil_img, x, y):
    """Checks pixel brightness to decide black vs white bug."""
    try:
        r, g, b = pil_img.getpixel((x, y))
        return (0.299 * r + 0.587 * g + 0.114 * b)
    except Exception:
        return 255

def save_pdf_with_overlays(app):
    """
    Saves the PDF by copying pages to a NEW document structure.
    This fixes 'xref' and corruption errors by discarding the old container.
    """
    if not app.pdf_doc: return

    # 1. Collect Active Items
    active_items = []
    for key, data in app.overlays.items():
        if data["active"].get() and data["coords"] is not None:
            active_items.append({
                "page_index": data["page_index"],
                "coords": data["coords"],
                "size": data["size"],
                "asset_key": data["asset_key"]
            })

    if not active_items:
        messagebox.showinfo("Info", "No active overlays to save.")
        return

    # 2. Get Save Path
    original_name = os.path.splitext(os.path.basename(app.pdf_path))[0]
    save_path = filedialog.asksaveasfilename(
        title="Save PDF As",
        initialfile=f"{original_name}_processed.pdf",
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")]
    )
    if not save_path: return

    try:
        # 3. OPEN SOURCE & CREATE NEW DOC
        # We open a fresh handle to the source
        src_doc = fitz.open(app.pdf_path)
        
        # We create a brand new, empty PDF
        out_doc = fitz.open()
        
        # 4. COPY PAGES (Sanitizes the PDF structure)
        out_doc.insert_pdf(src_doc)
        
        # 5. APPLY OVERLAYS to the NEW document
        for item in active_items:
            try:
                # Target page in the NEW document
                page = out_doc[item["page_index"]]
            except IndexError:
                continue

            asset_doc = app.assets[item["asset_key"]] 
            overlay_page = asset_doc[0]

            x_pt, y_pt = item["coords"]
            width_pt = item["size"].get() * 72
            scale = width_pt / overlay_page.rect.width

            rect = fitz.Rect(
                x_pt, 
                y_pt, 
                x_pt + overlay_page.rect.width * scale, 
                y_pt + overlay_page.rect.height * scale
            )
            
            # Apply the overlay
            page.show_pdf_page(rect, asset_doc, 0)

        # 6. SAVE
        # garbage=4: removes unused objects
        # deflate=True: compresses streams to save space
        out_doc.save(save_path, garbage=4, deflate=True)
        
        # Cleanup
        out_doc.close()
        src_doc.close()
        
        messagebox.showinfo("Success", "PDF Saved Successfully.")
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save PDF: {e}")
        print(f"Detailed Error: {e}")