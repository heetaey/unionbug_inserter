"""
PDF handling module for Union Bug App.

Provides functions to load, save PDF files and compute the trim box of a page.
"""

import fitz  # PyMuPDF

def load_pdf(path):
    """
    Load a PDF file from the given path.
    
    Parameters:
        path (str): Path to the PDF file.
    
    Returns:
        fitz.Document: The loaded PDF document.
    """
    return fitz.open(path)

def save_pdf(doc, output_path):
    """
    Save the PDF document to the specified output path.
    
    Parameters:
        doc (fitz.Document): The PDF document to save.
        output_path (str): Path where the PDF is to be saved.
    """
    doc.save(output_path, incremental=False)

def get_trimbox(page):
    """
    Compute and return the trim box for a PDF page.
    
    The trim box is determined based on the page's trimbox, cropbox, or rect.
    
    Parameters:
        page (fitz.Page): The PDF page.
        
    Returns:
        fitz.Rect: The computed trim box.
    """
    if page.trimbox and page.trimbox != fitz.Rect(0, 0, 0, 0):
        return page.trimbox
    elif page.cropbox and page.cropbox != fitz.Rect(0, 0, 0, 0):
        return page.cropbox
    else:
        return page.rect