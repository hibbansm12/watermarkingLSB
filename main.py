import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import numpy as np
import hashlib
import rsa
import ast
import Crypto
from math import log10, sqrt
import random
import sys
from bitstring import BitArray

# Program fragile watermarking====================================================
def XOR(bit1, bit2):
    if bit1 == bit2:
        return 0
    else:
        return 1

def insert_watermark(host_image, watermark_image, key_size=64):
    height, width = host_image.shape[:2]

    watermark_image = cv2.resize(watermark_image, (width, height))

    for i in range(watermark_image.shape[0]):
            for j in range(watermark_image.shape[1]):
                if watermark_image[i][j] > 127:
                    watermark_image[i][j] = 1
                else:
                    watermark_image[i][j] = 0

    block_size = 8

    sub_image_x = width // block_size
    sub_image_y = height // block_size

    host_blocks = []
    watermark_blocks = []
    host_blocks_lsb = []
    watermarked_blocks = []

    for i in range(sub_image_y):
        for j in range(sub_image_x):
            x0 = j * block_size
            y0 = i * block_size
            x1 = x0 + block_size
            y1 = y0 + block_size

            sub_image = host_image[y0:y1, x0:x1]
            host_blocks.append(sub_image)

            sub_image = watermark_image[y0:y1, x0:x1]
            watermark_blocks.append(sub_image)

    host_blocks_lsb = host_blocks

    for host_block_lsb, watermark_block in zip(host_blocks_lsb, watermark_blocks):
        for i in range(host_block_lsb.shape[0]):
            for j in range(host_block_lsb.shape[1]):
                if (host_block_lsb[i][j] % 2) != 0:
                    host_block_lsb[i][j] -= 1
        
        host_block_bytes = host_block_lsb.tobytes()
        m = hashlib.md5()
        m.update(host_block_bytes)
        hash = m.digest()
        host_block_hash_bits = ''.join(f'{b:08b}' for b in hash)
        
        first_64_bit_of_hash = host_block_hash_bits[:64]

        flattened_watermark_block = watermark_block.flatten()

        XOR_of_hash_and_watermark = []
        for i in range(64):
            XOR_of_hash_and_watermark.append(XOR(flattened_watermark_block[i], int(first_64_bit_of_hash[i])))
        
        XOR_of_hash_and_watermark_array = np.reshape(XOR_of_hash_and_watermark, (8, 8))

        for i in range(8):
            for j in range(8):
                if XOR_of_hash_and_watermark_array[i][j] == 1:
                    host_block_lsb[i][j] += 1

        watermarked_blocks.append(host_block_lsb)
    
    watermarked_image = np.zeros((host_image.shape[0], host_image.shape[1]), dtype=np.uint8)

    k = 0
    for i in range(sub_image_y):
        for j in range(sub_image_x):
            x0 = j * block_size
            y0 = i * block_size
            x1 = x0 + block_size
            y1 = y0 + block_size

            watermarked_image[y0:y1, x0:x1] = watermarked_blocks[k]
            k += 1

    return watermarked_image

def extract_watermark(watermarked_image):
    height, width = watermarked_image.shape[:2]

    block_size = 8

    sub_image_x = width // block_size
    sub_image_y = height // block_size


    watermarked_blocks = []
    extracted_watermark_blocks = []

    for i in range(sub_image_y):
        for j in range(sub_image_x):
            x0 = j * block_size
            y0 = i * block_size
            x1 = x0 + block_size
            y1 = y0 + block_size

            sub_image = watermarked_image[y0:y1, x0:x1]
            watermarked_blocks.append(sub_image)

    watermarked_blocks_lsb = watermarked_blocks
    watermark_blocks = []

    for  watermarked_block_lsb, watermarked_block in zip(watermarked_blocks_lsb, watermarked_blocks):
        lsbs_of_watermarked = []
        for i in range(watermarked_block_lsb.shape[0]):
            for j in range(watermarked_block_lsb.shape[1]):
                if (watermarked_block_lsb[i][j] % 2) != 0:
                    lsbs_of_watermarked.append(1)
                    watermarked_block_lsb[i][j] -= 1
                else:
                    lsbs_of_watermarked.append(0)

        watermarked_block_bytes = watermarked_block_lsb.tobytes()
        m = hashlib.md5()
        m.update(watermarked_block_bytes)
        hash = m.digest()
        watermarked_block_hash_bits = ''.join(f'{b:08b}' for b in hash)
        
        first_64_bit_of_hash = watermarked_block_hash_bits[:64]

        XOR_of_hash_and_watermark = []
        for i in range(64):
            XOR_of_hash_and_watermark.append(XOR(lsbs_of_watermarked[i], int(first_64_bit_of_hash[i])))
        
        watermark_block = XOR_of_hash_and_watermark

        watermark_block = np.reshape(watermark_block, (8, 8))

        for i in range(8):
            for j in range(8):
                if watermark_block[i][j] == 1:
                    watermark_block[i][j] = 255
        

        

        watermark_blocks.append(watermark_block)
    
    extracted_watermark_image = np.zeros((watermarked_image.shape[0], watermarked_image.shape[1]), dtype=np.uint8)

    k = 0
    for i in range(sub_image_y):
        for j in range(sub_image_x):
            x0 = j * block_size
            y0 = i * block_size
            x1 = x0 + block_size
            y1 = y0 + block_size

            extracted_watermark_image[y0:y1, x0:x1] = watermark_blocks[k]
            k += 1

    return extracted_watermark_image

def PSNR(original, compressed):
    mse = np.mean((original - compressed) ** 2)
    if(mse == 0):
        return 100
    max_pixel = 255.0
    psnr = 20 * log10(max_pixel / sqrt(mse))
    return psnr

# GUI===============================================================================================
def load_image(path):
    return cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)

def save_image(path, image):
    cv2.imwrite(path, image)

def open_file_dialog(entry):
    file_path = filedialog.askopenfilename()
    entry.delete(0, tk.END)
    entry.insert(0, file_path)

def save_file_dialog(image):
    file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
    if file_path:
        save_image(file_path, image)
        messagebox.showinfo("Success", f"Image saved to {file_path}")

def display_image(image, label):
    im = Image.fromarray(image)
    basewidth = 300
    wpercent = (basewidth / float(im.size[0]))
    hsize = int((float(im.size[1]) * float(wpercent)))

    # Resize gambar dengan LANCZOS
    im = im.resize((basewidth, hsize), resample=Image.LANCZOS)
    imgtk = ImageTk.PhotoImage(image=im)
    label.config(image=imgtk)
    label.image = imgtk

def insert_watermark_action():
    global watermarked_image
    host_path = host_path_entry.get()
    watermark_path = watermark_path_entry.get()

    if not host_path or not watermark_path:
        messagebox.showerror("Error", "Please provide both host and watermark images.")
        return

    host_image = load_image(host_path)
    watermark_image = load_image(watermark_path)

    watermarked_image = insert_watermark(host_image, watermark_image)
    display_image(watermarked_image, watermarked_image_label)

    save_image("watermarked_image.png", watermarked_image)
    messagebox.showinfo("Success", "Watermark inserted and saved as watermarked_image.png")

def extract_watermark_action():
    watermarked_path = watermarked_path_entry.get()

    if not watermarked_path:
        messagebox.showerror("Error", "Please provide a watermarked image.")
        return

    watermarked_image = load_image(watermarked_path)

    extracted_watermark = extract_watermark(watermarked_image)
    display_image(extracted_watermark, extracted_watermark_label)

    save_image("extracted_watermark.png", extracted_watermark)
    messagebox.showinfo("Success", "Watermark extracted and saved as extracted_watermark.png")

def calculate_psnr_action():
    original_path = host_path_entry.get()
    watermarked_path = watermarked_path_entry.get()

    if not original_path or not watermarked_path:
        messagebox.showerror("Error", "Please provide both original and watermarked images.")
        return

    original_image = load_image(original_path)
    watermarked_image = load_image(watermarked_path)

    psnr_value = PSNR(original_image, watermarked_image)
    messagebox.showinfo("PSNR Value", f"PSNR value is {psnr_value:.2f} dB")

app = tk.Tk()
app.title("Watermarking GUI")

style = ttk.Style()
style.configure("TButton", padding=6, relief="flat", background="#ccc")
style.configure("TLabel", padding=6)

ttk.Label(app, text="Masukkan Gambar:").grid(row=0, column=0, padx=10, pady=5)
host_path_entry = ttk.Entry(app, width=50)
host_path_entry.grid(row=0, column=1, padx=10, pady=5)
ttk.Button(app, text="Pilih", command=lambda: open_file_dialog(host_path_entry)).grid(row=0, column=2, padx=10, pady=5)

ttk.Label(app, text="Masukkan Watermark:").grid(row=1, column=0, padx=10, pady=5)
watermark_path_entry = ttk.Entry(app, width=50)
watermark_path_entry.grid(row=1, column=1, padx=10, pady=5)
ttk.Button(app, text="Pilih", command=lambda: open_file_dialog(watermark_path_entry)).grid(row=1, column=2, padx=10, pady=5)

ttk.Button(app, text="Sisipkan Watermark", command=insert_watermark_action).grid(row=2, column=0, columnspan=3, padx=10, pady=10)

ttk.Label(app, text="Masukkan Gambar yang Sudah Diwatermark:").grid(row=3, column=0, padx=10, pady=5)
watermarked_path_entry = ttk.Entry(app, width=50)
watermarked_path_entry.grid(row=3, column=1, padx=10, pady=5)
ttk.Button(app, text="Pilih", command=lambda: open_file_dialog(watermarked_path_entry)).grid(row=3, column=2, padx=10, pady=5)

ttk.Button(app, text="Ekstrak Watermark", command=extract_watermark_action).grid(row=4, column=0, columnspan=3, padx=10, pady=10)
ttk.Button(app, text="Hitung PSNR", command=calculate_psnr_action).grid(row=5, column=0, columnspan=3, padx=10, pady=10)

ttk.Label(app, text="Gambar yang diwatermark:").grid(row=6, column=0, padx=10, pady=5)
watermarked_image_label = ttk.Label(app)
watermarked_image_label.grid(row=6, column=1, columnspan=2, padx=10, pady=5)

ttk.Label(app, text="Watermark yang Diekstrak:").grid(row=7, column=0, padx=10, pady=5)
extracted_watermark_label = ttk.Label(app)
extracted_watermark_label.grid(row=7, column=1, columnspan=2, padx=10, pady=5)

ttk.Button(app, text="Simpan Gambar", command=lambda: save_file_dialog(watermarked_image)).grid(row=8, column=0, columnspan=3, padx=10, pady=10)

app.mainloop()