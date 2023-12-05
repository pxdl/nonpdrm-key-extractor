import tkinter as tk
from tkinter import filedialog, messagebox, Label, Button, Entry, LEFT, RIGHT, W, E, N, S, StringVar, END
from pathlib import Path
import argparse
import sys
import os

JP = ['G','C']
US = ['A', 'E']
EU = ['F', 'B']
KO = ['H']

nonpdrmheader = bytes.fromhex('0001000100010002efcdab8967452301')

parser = argparse.ArgumentParser(description='Extract key from NoNPDRM license.')
parser.add_argument('filepath', metavar='FILEPATH', type=Path, help='*.bin or .*rif license file.')

# If there are arguments, parse them. If not, run the GUI
if (len(sys.argv) > 1):
    print("command line functionality not yet implemented, please use the GUI in the meantime.")
    parser.parse_args()

def checkNoNPDRM(filepath):
    with open(filepath, "rb") as f:
            if f.read(16) != nonpdrmheader:
                if (len(sys.argv) < 2):
                    messagebox.showerror("Error", "Not a valid NoNPDRM license.")
                else:
                    print("Error: Not a valid NoNPDRM License.")
                return False
            else:
                return True

def getContentID(filepath):
    with open(filepath, "rb") as f:
        # Get Content ID
        f.seek(16)
        contentid = f.read(36).decode('ascii')
        return contentid

def getTitleID(filepath):
    with open(filepath, "rb") as f:
        # Get Title ID
        f.seek(23)
        titleid = f.read(9).decode('ascii')
        return titleid

def getKey(filepath):
    with open(filepath, "rb") as f:
        # Get key
        f.seek(80)
        key = f.read(16)
        return key

def getExtractedKey(filepath):
    with open(filepath, "rb") as f:
        # Get key
        key = f.read(16)
        return key

def getTitleIDFromContentID(contentid):
    return contentid[7:16]

def getRegion(id):
    if len(id) == 9:
        i = 3
    elif len(id) == 36:
        i = 10
    # Determine region
    if id[i] in JP:
        return "JP"
    elif id[i] in US:
        return "US"
    elif id[i] in EU:
        return "EU"
    elif id[i] in KO:
        return "KO"

def showPKGInfo(contentid, titleid, region, key):
    pkg_info = ("Content ID: {}\nTitle ID: {}\nRegion: {}\nLicense Key: {}".format(contentid, titleid, region, key.hex().upper()))
    if (len(sys.argv) < 2):
        messagebox.showinfo("Info", pkg_info)
    else:
        print(pkg_info)

def saveBinary(key, out_dir, filename):
    # Save filename.bin
    with open(out_dir.joinpath("{}.bin".format(filename)), "wb") as keybin:
        keybin.write(key)

def rebuildLicense(key, out_dir, contentid):
    with open(out_dir.joinpath("6488b73b912a753a492e2714e9b38bc7.rif"), 'wb') as rebuiltlicense:
        rebuiltlicense.write(nonpdrmheader)
        rebuiltlicense.write(contentid)
        rebuiltlicense.seek(80)
        rebuiltlicense.write(key)
        rebuiltlicense.seek(511)
        rebuiltlicense.write(b'\x00')

class MainGUI:
    def __init__(self, master):
        self.filename = None
        self.master = master
        master.title("Vita RIF Tools")

        self.open = Button(master, text="Open...", command=self.load)
        self.open.grid(row=0)

        self.contentid_text = StringVar()

        self.contentid_label = Label(master, text="Content ID: ", pady=5, padx=5)
        self.contentid_label.grid(row=1, sticky=W)

        self.contentid_entry = Entry(master, width=45, textvariable=self.contentid_text)
        self.contentid_entry.focus_set()
        self.contentid_entry.grid(row=1, columnspan=2, sticky=E)

        self.key_text = StringVar()

        self.key_label = Label(master, text="Key: ", pady=5, padx=5)
        self.key_label.grid(row=2, sticky=W)

        self.key_entry = Entry(master, width=45, textvariable=self.key_text)
        self.key_entry.focus_set()
        self.key_entry.grid(row=2, columnspan=2, sticky=E)

        self.label = Label(master, text="Choose an option:", padx=120, pady=5)
        self.label.grid(row= 3, columnspan=2, sticky=W)

        self.extract_button = Button(master, text="Extract", width=10, command=self.extract)
        self.extract_button.grid(row=4)

        self.recreate_button = Button(master, text="Recreate .rif file", width=15, command=self.recreate)
        self.recreate_button.grid(row=4, column=1)






    def extract(self):
        if len(self.contentid_text.get()) != 36:
            messagebox.showerror("Error", "Invalid content ID.")
            return
        elif len(self.key_text.get()) != 32:
            messagebox.showerror("Error", "Invalid key.")
            return

        contentid = self.contentid_entry.get()
        titleid = getTitleIDFromContentID(contentid)
        region = getRegion(titleid)
        key = bytes.fromhex(self.key_text.get())

        #showPKGInfo(contentid, titleid, region, key)
        
        out_dir = Path(__file__).parent.joinpath('rifout', '{}'.format(titleid))
        out_dir.mkdir(exist_ok = True, parents = True)

        # Save key as [contentid].bin
        saveBinary(key, out_dir, contentid)

        # Save info.txt
        #out_dir.joinpath('info.txt').write_text(pkg_info)

        # Save [contentid].txt with key
        #out_dir.joinpath("{}.txt".format(contentid)).write_text(key.hex().upper())

        pkg_info = ("Content ID: {}\nTitle ID: {}\nRegion: {}\nLicense Key: {}".format(contentid, titleid, region, key.hex().upper()))
        messagebox.showinfo("Info", "Exported key successfully!\n\n{}\n\nOutput folder: {}".format(pkg_info, out_dir))

    def recreate(self):        
        if len(self.contentid_text.get()) != 36:
            messagebox.showerror("Error", "Cannot recreate license file with specified content ID.")
            return
        elif len(self.key_text.get()) != 32:
            messagebox.showerror("Error", "Cannot recreate license file with specified key.")
            return

        contentid = bytes(self.contentid_text.get(), 'ascii')
        titleid = getTitleIDFromContentID(self.contentid_text.get())
        key = bytes.fromhex(self.key_text.get())

        rebuild_dir = Path(__file__).parent.joinpath('rifrebuilt', '{}'.format(self.contentid_text.get()))
        rebuild_dir.mkdir(exist_ok = True, parents = True)

        rebuildLicense(key, rebuild_dir, contentid)

        messagebox.showinfo("Info", "License recreated successfully!\n\nOutput folder: {}".format(rebuild_dir))



    def load(self):
        self.filename = filedialog.askopenfilename(initialdir = Path(__file__).parent, title = "Select license file",filetypes = (("bin files","*.bin"),("rif files","*.rif"),("all files","*.*")))
        if self.filename:
            abs_path = Path(self.filename)
        else:
            return

        if len(abs_path.stem) == 36 and abs_path.stat().st_size == 16:
            self.contentid_entry.delete(0, END) # Clear text entry
            self.contentid_entry.insert(0, abs_path.stem)
            self.key_entry.delete(0, END) # Clear text entry
            self.key_binary = getExtractedKey(abs_path)
            self.key_entry.insert(0, self.key_binary.hex().upper())
            return

        if checkNoNPDRM(abs_path) == False:
            return

        self.contentid_entry.delete(0, END) # Clear text entry
        self.contentid_entry.insert(0, getContentID(abs_path))

        self.key_entry.delete(0, END) # Clear text entry
        self.key_entry.insert(0, getKey(abs_path).hex().upper())

root = tk.Tk()
maingui = MainGUI(root)

# If no arguments are passed through command line, run the GUI
if len(sys.argv) < 2:
    print("Not enough arguments, running GUI...")
    root.mainloop()

