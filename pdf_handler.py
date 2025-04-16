
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

def save_pdf_with_bug(app):
    if not app.bug_coords or not app.bug_pdf:
        messagebox.showwarning("No Bug", "No bug has been placed.")
        return

    original_basename = os.path.splitext(os.path.basename(app.pdf_path))[0]
    suggested_name = f"{original_basename}_bug.pdf"
    initial_dir = os.path.dirname(app.pdf_path)

    save_path = filedialog.asksaveasfilename(
        initialdir=initial_dir,
        initialfile=suggested_name,
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")]
    )
    if not save_path:
        return

    doc = fitz.open(app.pdf_path)
    page = doc[app.current_page_index]
    true_w, true_h = page.rect.width, page.rect.height
    render_w, render_h = app.pdf_pix.width, app.pdf_pix.height

    bbox = app.canvas.bbox(app.img_id)
    img_left, img_top = bbox[0], bbox[1]
    img_x = app.bug_coords[0]
    img_y = app.bug_coords[1]

    canvas_bug_x = img_x + app.offset_x - img_left
    canvas_bug_y = img_y + app.offset_y - img_top

    x_pt = canvas_bug_x * (page.rect.width / render_w)
    y_pt = canvas_bug_y * (page.rect.height / render_h)

    bug_doc = fitz.open(app.bug_pdf)
    bug_page = bug_doc[0]
    bug_width_pt = app.bug_size_var.get() * 72
    scale_factor = bug_width_pt / bug_page.rect.width

    bug_rect = fitz.Rect(
        x_pt,
        y_pt,
        x_pt + bug_page.rect.width * scale_factor,
        y_pt + bug_page.rect.height * scale_factor
    )

    page.show_pdf_page(bug_rect, bug_doc, 0)
    doc.save(save_path)
    messagebox.showinfo("Saved", f"PDF saved: {save_path}")

    if sys.platform == "darwin":
        subprocess.call(["open", "-R", save_path])
    elif sys.platform == "win32":
        os.startfile(os.path.normpath(save_path))
    elif sys.platform.startswith("linux"):
        subprocess.call(["xdg-open", os.path.dirname(save_path)])
