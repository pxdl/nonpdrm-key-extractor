# coding=utf-8
import binascii

def main():
	textprint = ''
	titleid = ''
	JP = ['G','C']
	US = ['A', 'E']
	EU = ['F', 'B']
	KO = ['H']

	with open("work.bin", "rb") as f:
	    f.seek(16)

	    for i in range(0, 36):
	    	text = int.from_bytes(f.read(1), 'big')
	    	textprint = textprint + chr(text)
	    	if i in range(7,16):
	    		titleid = titleid + chr(text)
	    	i = i+1

	    if titleid[3] in JP:
	    	region = "JP"
	    elif titleid[3] in US:
	    	region = "US"
	    elif titleid[3] in EU:
	    	region = "EU"
	    elif titleid[3] in US:
	    	region = "EU"

	    print("Full Content ID: ", textprint)
	    print("Title ID: ", titleid)
	    print("Region: ", region)

	    f.seek(80)
	    key = int.from_bytes(f.read(16), 'big')
	    print("License key: ", hex(key))

	    #Save key.bin
	    with open("key.bin", "wb") as keybin:
	    	binstr = binascii.unhexlify((hex(key))[2:])
	    	keybin.write(binstr)

	    #Save [contentid].txt with key
	    with open("{}.txt".format(textprint), 'w') as keytext:
	    	print((hex(key))[2:].upper(), file=keytext)

if __name__ == '__main__':
    main()
