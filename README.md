# Vita RIF Tools

A Python tool to extract, inspect, and rebuild NoNPDRM license files for the PS Vita. Supports zRIF encoding/decoding for compatibility with NPS Browser, PKGj, and NoPayStation databases.

![image](https://user-images.githubusercontent.com/17756301/30679170-ec33124c-9e6d-11e7-809d-bff9e9185aae.png)

## Requirements

- Python 3.10+
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) (GUI only)

```
pip install customtkinter
```

## Usage

Running without arguments launches the GUI:

```
python rif-extractor.py
```

### GUI

The GUI is organized into three sections:

- **Input** — Open a `.rif`, `work.bin`, or extracted `.bin` key file, or paste a zRIF string and decode it
- **Data** — View and edit Content ID and Key, with live-updating Title ID, region, and publisher info. The zRIF string auto-generates as you type. Copy buttons for Key and zRIF.
- **Actions** — Save as key (`.bin`), license (`.rif`), or `work.bin`

A status bar at the bottom shows feedback inline without popups.

### CLI Commands

**Show license info:**
```
python rif-extractor.py info license.rif
python rif-extractor.py info work.bin
python rif-extractor.py info -d license.rif   # detailed view (all fields + zRIF)
```

**Export key to `.bin` file:**
```
python rif-extractor.py export license.rif
python rif-extractor.py export license.rif -o ./output
```

**Rebuild a `.rif` license from Content ID and key:**
```
python rif-extractor.py rebuild <CONTENT_ID> <HEX_KEY>
python rif-extractor.py rebuild <CONTENT_ID> <HEX_KEY> --work-bin    # output as work.bin
python rif-extractor.py rebuild <CONTENT_ID> <HEX_KEY> -o ./output
```

**Batch extract keys from a directory:**
```
python rif-extractor.py batch ./licenses
python rif-extractor.py batch ./licenses -o ./output
```

**Decode a zRIF string to `.rif` file:**
```
python rif-extractor.py zrif-decode <ZRIF_STRING>
python rif-extractor.py zrif-decode <ZRIF_STRING> --work-bin   # output as work.bin
python rif-extractor.py zrif-decode <ZRIF_STRING> -o ./output
```

**Encode a `.rif` file to zRIF string:**
```
python rif-extractor.py zrif-encode license.rif
python rif-extractor.py zrif-encode work.bin
```

## Features

- **Extract** keys from NoNPDRM fake license files (`.rif`, `work.bin`)
- **Rebuild** NoNPDRM licenses from Content ID and key (as `.rif` or `work.bin`)
- **zRIF encode/decode** for compatibility with NPS Browser, PKGj, and NoPayStation
- **Live info** — Title ID, region, and publisher auto-update as you type the Content ID
- **Auto zRIF** — zRIF string generates automatically from valid Content ID + Key
- **Detailed inspector** (CLI) showing all license fields (version, flags, account ID, SKU, timestamps, signatures)
- **Batch processing** of entire directories
- **Region detection** for JP, US, EU, KO, Asia, and CN title IDs
- **Copy to clipboard** for Key and zRIF fields
- Modern GUI ([customtkinter](https://github.com/TomSchimansky/CustomTkinter)) and full CLI interface

## License Format

The tool works with the `SceNpDrmLicense` structure (512 bytes):

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 2 | Version |
| 0x02 | 2 | Version flag |
| 0x04 | 2 | License type |
| 0x06 | 2 | Flags |
| 0x08 | 8 | Account ID (fake = `0x0123456789ABCDEF`) |
| 0x10 | 48 | Content ID (36 ASCII chars + padding) |
| 0x40 | 16 | Key table |
| 0x50 | 16 | **Klicensee (decryption key)** |
| 0x60 | 8 | Start time |
| 0x68 | 8 | Expiration time |
| 0x70 | 40 | ECDSA signature |
| 0x98 | 8 | Flags2 |
| 0xA0 | 16 | Secondary key |
| 0xC0 | 16 | OpenPSID |
| 0xFC | 4 | SKU flag (0=not bootable, 1=trial, 3=full) |
| 0x100 | 256 | RSA signature |

The fake license header is always `0001000100010002EFCDAB8967452301` (version 1, type 1, flags 2, fake account ID).

The `.rif` filename for NoNPDRM fakes is always `6488b73b912a753a492e2714e9b38bc7.rif`.

### zRIF Format

zRIF is a zlib-compressed, base64-encoded representation of the full 512-byte `.rif` file, using a preset dictionary of common PS Vita strings (title ID prefixes like `PCSG`, `PCSE`, etc.) for better compression. Used by NPS Browser, PKGj, and NoPayStation databases.

### Content ID Format

`XX9999-XXXXXXXXX_99-XXXXXXXXXXXXXXXX` (36 characters)

| Position | Field | Example |
|----------|-------|---------|
| 0-1 | Region prefix | `UP` (US), `EP` (EU), `JP` (JP), `HP` (Asia) |
| 2-5 | Publisher ID | `9000` (Sony 1st party) |
| 7-15 | Title ID | `PCSE00000` |
| 17-18 | Sub-version | `00` |
| 20-35 | Content descriptor | `TESTCONTENT00000` |
