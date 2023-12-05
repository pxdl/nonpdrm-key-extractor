import tkinter as tk
from tkinter import filedialog, messagebox, Label, Button
from pathlib import Path



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
        parent_dir = Path(abs_path).parent
        out_dir = parent_dir.joinpath('out')
        out_dir.mkdir(exist_ok = True, parents = True)

        contentid = ''
        titleid = ''
        JP = ['G','C']
        US = ['A', 'E']
        EU = ['F', 'B']
        KO = ['H']


        with open(abs_path, "rb") as f:
            f.seek(16)

            # Get Content ID and Title ID
            for i in range(0,36):
                text = f.read(1).decode('ascii')
                contentid = contentid + text
                # Get Title ID
                if i in range(7,16):
                    titleid = titleid + text
                i = i+1

            # Get key
            f.seek(80)
            key = f.read(16)

        # Determine region
        if titleid[3] in JP:
            region = "JP"
        elif titleid[3] in US:
            region = "US"
        elif titleid[3] in EU:
            region = "EU"
        elif titleid[3] in US:
            region = "EU"
        
        pkg_info = ("Content ID: {}\nTitle ID: {}\nRegion: {}\nLicense Key: {}".format(contentid, titleid, region, key.hex().upper()))
        messagebox.showinfo("Info", pkg_info)

        # Save key.bin
        with open(out_dir.joinpath('key.bin'), "wb") as keybin:
            keybin.write(key)

        # Save info.txt
        out_dir.joinpath('info.txt').write_text(pkg_info)

        # Save [contentid].txt with key
        out_dir.joinpath("{}.txt".format(contentid)).write_text(key.hex().upper())

        messagebox.showinfo("Info", "Exported files successfully!\n\nOutput folder: {}".format(out_dir))

    def recreate(self):
        messagebox.showinfo("Info", "In development")


root = tk.Tk()
maingui = MainGUI(root)
root.mainloop()

