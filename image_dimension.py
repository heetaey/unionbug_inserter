import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

class ImageDimensionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Dimension Viewer")
        self.root.geometry("400x250")

        self.label = tk.Label(root, text="Select an image file to view its dimensions", wraplength=300)
        self.label.pack(pady=20)

        self.select_button = tk.Button(root, text="Choose Image", command=self.open_file)
        self.select_button.pack(pady=10)

        self.result_text = tk.Text(root, height=6, width=40)
        self.result_text.pack(pady=10)
        self.result_text.config(state=tk.DISABLED)

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp")]
        )
        if file_path:
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    dpi = img.info.get("dpi", (72, 72))
                    width_in = round(width / dpi[0], 2)
                    height_in = round(height / dpi[1], 2)

                    self.result_text.config(state=tk.NORMAL)
                    self.result_text.delete(1.0, tk.END)
                    self.result_text.insert(tk.END, f"Dimensions: {width} x {height} pixels\n")
                    self.result_text.insert(tk.END, f"Dimensions: {width_in} x {height_in} inches (approx)\n")
                    self.result_text.insert(tk.END, f"DPI: {dpi[0]} x {dpi[1]}")
                    self.result_text.config(state=tk.DISABLED)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageDimensionApp(root)
    root.mainloop()