# nonpdrm-key-extractor
A simple python program to extract the key from NoNPDRM license files.

![image](https://user-images.githubusercontent.com/17756301/30679170-ec33124c-9e6d-11e7-809d-bff9e9185aae.png)

## Introduction
This program is written in Python 3.6 and reads the Content ID and key from NoNPDRM fake licenses.

## Description
It reads the key located at offset `0x50` from the NoNPDRM generated license, shows the content ID and key as text, and offers options to extract it to a `[CONTENTID].bin` file and to recreate a NoNPDRM `6488b73b912a753a492e2714e9b38bc7.rif` license file from a `[CONTENTID].bin` file or from the user's text input.

You need both a Content ID and a Key to recreate a license.

The python script currently only works from its tkinter graphical user interface.

### Planned features
* Command line functionality
* Batch file extraction and license rebuild from a specified directory
* Key database
