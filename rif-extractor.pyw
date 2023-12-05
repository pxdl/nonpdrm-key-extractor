import tkinter as tk
from tkinter import filedialog, messagebox, Label, Button
from pathlib import Path
import argparse
import sys

JP = ['G','C']
US = ['A', 'E']
EU = ['F', 'B']
KO = ['H']

parser = argparse.ArgumentParser(description='Extract key from NoNPDRM license.')
parser.add_argument('filepath', metavar='FILEPATH', type=Path, help='*.bin or .*rif license file.')

# If there are arguments, parse them. If not, run the GUI
if (len(sys.argv) > 1):
    print("command line functionality not yet implemented, please use the GUI in the meantime.")
    parser.parse_args()

def checkNoNPDRM(filepath):
    with open(filepath, "rb") as f:
            if (f.read(16)).hex() != '0001000100010002efcdab8967452301':
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
        text = f.read(9).decode('ascii')
        titleid = titleid + text
        return titleid

def getKey(filepath):
    # Get key
    with open(filepath, "rb") as f:
        f.seek(80)
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


class MainGUI:
    def __init__(self, master):
        self.master = master
        master.title("Vita RIF Tools")

        self.label = Label(master, text="Choose an option")
        self.label.pack()

        self.extract_button = Button(master, text="Extract", command=self.extract)
        self.extract_button.pack()

        self.recreate_button = Button(master, text="Recreate", command=self.recreate)
        self.recreate_button.pack()



    def extract(self):
        self.filename = filedialog.askopenfilename(initialdir = "/",title = "Select license file",filetypes = (("bin files","*.bin"),("rif files","*.rif"),("all files","*.*")))
        abs_path = Path(self.filename)

        if checkNoNPDRM(abs_path) == False:
            messagebox.showerror("Error", "Not a valid NoNPDRM license.")
            return

        contentid = getContentID(abs_path)
        titleid = getTitleIDFromContentID(contentid)
        region = getRegion(titleid)
        key = getKey(abs_path)

        #showPKGInfo(contentid, titleid, region, key)
        
        out_dir = Path(abs_path).parent.joinpath('out')
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
        messagebox.showinfo("Info", "In development")


root = tk.Tk()
maingui = MainGUI(root)

# If no arguments are passed through command line, run the GUI
if len(sys.argv) < 2:
    print("Not enough arguments, running GUI...")
    root.mainloop()

