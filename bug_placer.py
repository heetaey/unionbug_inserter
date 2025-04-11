"""
Bug placer module for Union Bug App.

Provides functions for selecting the appropriate union bug based on contrast,
and placing the bug onto a PDF page.
"""

import fitz
from pdf_handler import get_trimbox
from PIL import Image

def choose_bug_by_contrast(page, x, y, white_bug, black_bug):
    """
    Determine which union bug to use (white or black) based on the image contrast at the given coordinates.
    
    Parameters:
        page (fitz.Page): The PDF page where the union bug will be placed.
        x (float): The x-coordinate (in points) where the bug is to be placed.
        y (float): The y-coordinate (in points) where the bug is to be placed.
        white_bug (str): File path for the white union bug.
        black_bug (str): File path for the black union bug.
        
    Returns:
        str: The selected bug file path.
    """
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    scale_x = page.rect.width / img.width
    scale_y = page.rect.height / img.height
    ix = int(x / scale_x)
    iy = int(y / scale_y)
    # Crop a small box (10 x 10 pixels) around the point
    box = img.crop((ix - 5, iy - 5, ix + 5, iy + 5))
    brightness = sum(box.convert("L").getdata()) / (box.size[0] * box.size[1])
    return white_bug if brightness < 128 else black_bug

def place_union_bug_on_page(page, click_coord, bug_pdf_path, bug_width_in, safe_margin):
    """
    Place the union bug on a specific PDF page.
    
    This function calculates the appropriate placement rectangle on the page
    based on the provided click coordinates (in PDF points) or uses fallback placement if not available.
    
    Parameters:
        page (fitz.Page): The PDF page to place the bug on.
        click_coord (tuple or None): A tuple (x, y) in points specifying the placement,
            or None to use fallback positioning.
        bug_pdf_path (str): File path to the union bug PDF.
        bug_width_in (float): Desired union bug width in inches.
        safe_margin (float): Safe margin in points.
    """
    bug_doc = fitz.open(bug_pdf_path)
    bug_page = bug_doc[0]
    bug_rect = bug_page.rect

    target_width = bug_width_in * 72  # Convert inches to points
    scale = target_width / bug_rect.width
    target_height = bug_rect.height * scale

    trimbox = get_trimbox(page)

    if click_coord is not None:
        x, y = click_coord
        # Clamp the coordinates within the trimbox dimensions
        x = max(trimbox.x0, min(x, trimbox.x1 - target_width))
        y = max(trimbox.y0 + target_height, min(y, trimbox.y1))
        rect = fitz.Rect(x, y - target_height, x + target_width, y)
    else:
        # Fallback positioning if no click coordinate was provided
        bleed_x = max(0, (page.rect.width - trimbox.width) / 2)
        bleed_y = max(0, (page.rect.height - trimbox.height) / 2)
        x = bleed_x + trimbox.width - target_width - safe_margin
        y = bleed_y + trimbox.height - target_height - safe_margin
        rect = fitz.Rect(x, y, x + target_width, y + target_height)
    
    page.show_pdf_page(rect, bug_doc, 0)
    bug_doc.close()
