import tkinter as tk
import binascii
from tkinter import filedialog, messagebox
from pathlib import Path


root = tk.Tk()
root.withdraw()
root.filename = filedialog.askopenfilename(initialdir = "/",title = "Select license file",filetypes = (("bin files","*.bin"),("rif files","*.rif"),("all files","*.*")))

def main():
	contentid = ''
	titleid = ''
	JP = ['G','C']
	US = ['A', 'E']
	EU = ['F', 'B']
	KO = ['H']

	#print (root.filename)

	abs_path = Path(root.filename)
	parent_dir = Path(abs_path).parent
	out_dir = parent_dir.joinpath('out')
	out_dir.mkdir(exist_ok = True, parents = True)

	with open(abs_path, "rb") as f:
	    f.seek(16)

	    # Get Content ID and Title ID
	    for i in range(0, 36):
	    	text = int.from_bytes(f.read(1), 'big')
	    	contentid = contentid + chr(text)
	    	if i in range(7,16):
	    		titleid = titleid + chr(text)
	    	i = i+1

	    # Get key
	    f.seek(80)
	    key = int.from_bytes(f.read(16), 'big')

	    # Determine region
	    if titleid[3] in JP:
	    	region = "JP"
	    elif titleid[3] in US:
	    	region = "US"
	    elif titleid[3] in EU:
	    	region = "EU"
	    elif titleid[3] in US:
	    	region = "EU"

	    pkg_info = ("Content ID: {}\nTitle ID: {}\nRegion: {}\nLicense Key: {}".format(contentid, titleid, region, hex(key)[2:].upper()))
	    messagebox.showinfo("Info", pkg_info)

	    # Save key.bin
	    with open(out_dir.joinpath('key.bin'), "wb") as keybin:
	    	binstr = binascii.unhexlify((hex(key))[2:])
	    	keybin.write(binstr)

	    # Save info.txt
	    out_dir.joinpath('info.txt').write_text(pkg_info)

	    # Save [contentid].txt with key
	    out_dir.joinpath("{}.txt".format(contentid)).write_text((hex(key))[2:].upper())

	    messagebox.showinfo("Info", "Exported files successfully!\n\nOutput folder: {}".format(out_dir))

if __name__ == '__main__':
    main()
