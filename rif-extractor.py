"""Vita RIF Tools - Extract, inspect, and rebuild NoNPDRM license files."""

import argparse
import base64
import struct
import sys
import zlib
from pathlib import Path

# --- Constants ---

REGION_MAP: dict[str, list[str]] = {
    "JP": ["G", "C"],
    "US": ["A", "E"],
    "EU": ["F", "B"],
    "KO": ["H"],
    "ASIA": ["D"],
}

TITLE_ID_REGIONS: dict[str, str] = {
    "PCSA": "US (1st party)",
    "PCSE": "US (3rd party)",
    "PCSF": "EU (1st party)",
    "PCSB": "EU (3rd party)",
    "PCSC": "JP (1st party)",
    "PCSG": "JP (3rd party)",
    "PCSD": "Asia (1st party)",
    "PCSH": "Asia (3rd party)",
    "NPXS": "System",
}

CONTENT_ID_REGIONS: dict[str, str] = {
    "IP": "JP",
    "JP": "JP",
    "UP": "US",
    "EP": "EU",
    "HP": "Asia",
    "KP": "KO",
    "AP": "CN",
}

SKU_FLAGS: dict[int, str] = {
    0: "Not bootable",
    1: "Trial",
    3: "Full game",
}

NONPDRM_HEADER = bytes.fromhex("0001000100010002efcdab8967452301")
FAKE_AID = 0x0123456789ABCDEF
RIF_SIZE = 512
RIF_FILENAME = "6488b73b912a753a492e2714e9b38bc7.rif"

# zRIF preset dictionary (common strings in .rif files for better compression)
_ZRIF_DICT_COMPRESSED = (
    b"eNpjYBgFo2AU0AsYAIElGt8MRJiDCAsw3xhEmIAIU4N4AwNdRxcXZ3+/EJCAkW6Ac7C7ARwY"
    b"gviuQAaIdoPSzlDaBUo7QmknIM3ACIZM78+u7kx3VWYEAGJ9HV0="
)
ZRIF_DICT = bytes(zlib.decompress(base64.b64decode(_ZRIF_DICT_COMPRESSED)))


# --- License data structure ---


def parse_license(data: bytes) -> dict:
    """Parse a full 512-byte NoNPDRM license into its fields."""
    if len(data) < RIF_SIZE:
        data = data.ljust(RIF_SIZE, b"\x00")

    version, version_flag, license_type, flags = struct.unpack_from(">HHHH", data, 0x00)
    aid = struct.unpack_from("<Q", data, 0x08)[0]
    content_id_raw = data[0x10:0x40]
    content_id = content_id_raw.rstrip(b"\x00").decode("ascii", errors="replace")
    key_table = data[0x40:0x50]
    key = data[0x50:0x60]
    start_time, expiration_time = struct.unpack_from("<QQ", data, 0x60)
    ecdsa_sig = data[0x70:0x98]
    flags2 = struct.unpack_from("<Q", data, 0x98)[0]
    key2 = data[0xA0:0xB0]
    openpsid = data[0xC0:0xD0]
    sku_flag = struct.unpack_from(">I", data, 0xFC)[0]

    return {
        "version": version,
        "version_flag": version_flag,
        "license_type": license_type,
        "flags": flags,
        "aid": aid,
        "content_id": content_id,
        "key_table": key_table,
        "key": key,
        "start_time": start_time,
        "expiration_time": expiration_time,
        "ecdsa_signature": ecdsa_sig,
        "flags2": flags2,
        "key2": key2,
        "openpsid": openpsid,
        "sku_flag": sku_flag,
        "is_fake": aid == FAKE_AID,
        "is_extracted_key": False,
        "raw": data,
    }


def format_license_detail(lic: dict) -> str:
    """Format all parsed license fields for display."""
    content_id = lic["content_id"]
    title_id, region = get_title_and_region(content_id)
    title_region = TITLE_ID_REGIONS.get(title_id[:4], "") if title_id else ""

    lines = [
        f"Content ID:  {content_id}",
        f"Title ID:    {title_id or 'N/A'}",
        f"Region:      {region}" + (f" - {title_region}" if title_region else ""),
        f"Key:         {lic['key'].hex().upper()}",
        "",
        f"Version:     {lic['version']}",
        f"Type:        {lic['license_type']}",
        f"Flags:       0x{lic['flags']:04X}",
        f"Flags2:      0x{lic['flags2']:016X}",
        f"Account ID:  0x{lic['aid']:016X}" + (" (fake)" if lic["is_fake"] else ""),
        f"SKU:         {lic['sku_flag']} ({SKU_FLAGS.get(lic['sku_flag'], 'Unknown')})",
    ]

    if lic["start_time"]:
        lines.append(f"Start time:  {lic['start_time']}")
    if lic["expiration_time"]:
        lines.append(f"Expiration:  {lic['expiration_time']}")

    key_table = lic["key_table"]
    if key_table != b"\x00" * 16:
        lines.append(f"Key table:   {key_table.hex().upper()}")

    key2 = lic["key2"]
    if key2 != b"\x00" * 16:
        lines.append(f"Key2:        {key2.hex().upper()}")

    openpsid = lic["openpsid"]
    if openpsid != b"\x00" * 16:
        lines.append(f"OpenPSID:    {openpsid.hex().upper()}")

    return "\n".join(lines)


# --- Core functions ---


def is_extracted_key_file(filepath: Path) -> bool:
    """Check if a file is an extracted 16-byte key with Content ID as filename."""
    return len(filepath.stem) == 36 and filepath.stat().st_size == 16


def read_license_file(filepath: Path) -> dict:
    """Read and parse a license file (.rif, work.bin, or extracted key .bin)."""
    data = filepath.read_bytes()
    if len(data) == RIF_SIZE and data[:16] == NONPDRM_HEADER:
        return parse_license(data)
    if len(data) == 16 and len(filepath.stem) == 36:
        return {
            "content_id": filepath.stem,
            "key": data,
            "is_fake": False,
            "is_extracted_key": True,
            "raw": None,
        }
    raise ValueError("Not a valid NoNPDRM license or extracted key file.")


def title_id_from_content_id(content_id: str) -> str:
    """Extract the Title ID from a Content ID string."""
    return content_id[7:16]


def get_title_and_region(content_id: str) -> tuple[str, str]:
    """Derive Title ID and region from a Content ID. Returns ("", "Unknown") if invalid."""
    if len(content_id) != 36:
        return "", "Unknown"
    title_id = title_id_from_content_id(content_id)
    return title_id, get_region(title_id)


def get_region(identifier: str) -> str:
    """Determine the region from a Title ID (9 chars) or Content ID (36 chars)."""
    if len(identifier) == 9:
        char = identifier[3]
    elif len(identifier) == 36:
        char = identifier[10]
    else:
        return "Unknown"

    for region, codes in REGION_MAP.items():
        if char in codes:
            return region
    return "Unknown"


def save_key_binary(key: bytes, out_dir: Path, filename: str) -> Path:
    """Save a key as a .bin file."""
    out_path = out_dir / f"{filename}.bin"
    out_path.write_bytes(key)
    return out_path


def build_rif_bytes(content_id: str, key: bytes, *, sku_flag: int = 3) -> bytes:
    """Build a 512-byte NoNPDRM fake license in memory."""
    rif = bytearray(RIF_SIZE)
    rif[0x00:0x10] = NONPDRM_HEADER
    cid_bytes = content_id.encode("ascii")
    rif[0x10 : 0x10 + len(cid_bytes)] = cid_bytes
    rif[0x50:0x60] = key
    struct.pack_into(">I", rif, 0xFC, sku_flag)
    return bytes(rif)


def rebuild_license(
    key: bytes,
    out_dir: Path,
    content_id: str,
    *,
    sku_flag: int = 3,
    as_work_bin: bool = False,
) -> Path:
    """Rebuild a NoNPDRM .rif or work.bin license file."""
    filename = "work.bin" if as_work_bin else RIF_FILENAME
    out_path = out_dir / filename
    out_path.write_bytes(build_rif_bytes(content_id, key, sku_flag=sku_flag))
    return out_path


def format_info(content_id: str, title_id: str, region: str, key: bytes) -> str:
    """Format basic license info as a human-readable string."""
    return (
        f"Content ID: {content_id}\n"
        f"Title ID:   {title_id}\n"
        f"Region:     {region}\n"
        f"Key:        {key.hex().upper()}"
    )


def is_valid_hex_key(text: str) -> bool:
    """Check if a string is a valid 32-character hex key."""
    if len(text) != 32:
        return False
    try:
        bytes.fromhex(text)
        return True
    except ValueError:
        return False


# --- zRIF ---


def rif_to_zrif(rif_data: bytes) -> str:
    """Encode a .rif file's bytes into a zRIF string."""
    c = zlib.compressobj(level=9, wbits=10, memLevel=8, zdict=ZRIF_DICT)
    compressed = c.compress(rif_data) + c.flush()

    # Pad to multiple of 3 for clean base64
    remainder = len(compressed) % 3
    if remainder:
        compressed += b"\x00" * (3 - remainder)

    return base64.b64encode(compressed).decode("ascii")


def zrif_to_rif(zrif_string: str) -> bytes:
    """Decode a zRIF string back into .rif file bytes."""
    compressed = base64.b64decode(zrif_string.encode("ascii"))
    d = zlib.decompressobj(wbits=10, zdict=ZRIF_DICT)
    return d.decompress(compressed) + d.flush()


def zrif_to_license(zrif_string: str) -> dict:
    """Decode a zRIF string and parse it as a license."""
    return parse_license(zrif_to_rif(zrif_string))


# --- CLI ---


def _print_license_info(lic: dict) -> None:
    """Print basic Content ID / Title ID / Region / Key for a license dict."""
    content_id = lic["content_id"]
    title_id, region = get_title_and_region(content_id)
    print(format_info(content_id, title_id or "N/A", region, lic["key"]))


def cli_info(filepath: Path, *, detailed: bool = False) -> None:
    """Extract and display key info from a license file."""
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    try:
        lic = read_license_file(filepath)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if lic["is_extracted_key"]:
        _print_license_info(lic)
        print("\n(Extracted key file — no full license data available)")
    elif detailed:
        print(format_license_detail(lic))
        if lic["raw"]:
            print(f"\nzRIF:        {rif_to_zrif(lic['raw'])}")
    else:
        _print_license_info(lic)


def cli_export(filepath: Path, out_dir: Path | None) -> None:
    """Extract key from a license and save as .bin."""
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    try:
        lic = read_license_file(filepath)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    content_id = lic["content_id"]
    title_id, region = get_title_and_region(content_id)

    if out_dir is None:
        out_dir = filepath.parent / (title_id or "unknown")
    out_dir.mkdir(exist_ok=True, parents=True)

    out_path = save_key_binary(lic["key"], out_dir, content_id)
    print(format_info(content_id, title_id or "N/A", region, lic["key"]))
    print(f"\nExported to: {out_path}")


def cli_rebuild(
    content_id: str,
    key_hex: str,
    out_dir: Path | None,
    *,
    as_work_bin: bool = False,
) -> None:
    """Rebuild a .rif license from Content ID and key."""
    if len(content_id) != 36:
        print(f"Error: Content ID must be 36 characters (got {len(content_id)}).")
        sys.exit(1)

    if not is_valid_hex_key(key_hex):
        print("Error: Key must be 32 valid hex characters.")
        sys.exit(1)

    key = bytes.fromhex(key_hex)

    if out_dir is None:
        out_dir = Path.cwd() / "rifrebuilt" / content_id
    out_dir.mkdir(exist_ok=True, parents=True)

    out_path = rebuild_license(key, out_dir, content_id, as_work_bin=as_work_bin)
    print(f"License rebuilt: {out_path}")
    print(f"zRIF: {rif_to_zrif(out_path.read_bytes())}")


def cli_batch(directory: Path, out_dir: Path | None) -> None:
    """Batch extract keys from all license files in a directory."""
    if not directory.is_dir():
        print(f"Error: Not a directory: {directory}")
        sys.exit(1)

    files = sorted(directory.glob("*.rif")) + sorted(directory.glob("*.bin"))
    if not files:
        print("No .rif or .bin files found.")
        return

    count = 0
    for filepath in files:
        try:
            lic = read_license_file(filepath)
        except ValueError:
            print(f"Skipping (not a valid license): {filepath.name}")
            continue

        content_id = lic["content_id"]
        title_id, region = get_title_and_region(content_id)

        target_dir = (out_dir or filepath.parent) / (title_id or "unknown")
        target_dir.mkdir(exist_ok=True, parents=True)

        save_key_binary(lic["key"], target_dir, content_id)
        print(f"[{region}] {title_id or 'N/A'} - {content_id} -> {target_dir}")
        count += 1

    print(f"\nProcessed {count} file(s).")


def cli_zrif_decode(zrif_string: str, out_dir: Path | None, *, as_work_bin: bool = False) -> None:
    """Decode a zRIF string and save as .rif or work.bin."""
    try:
        rif_data = zrif_to_rif(zrif_string)
    except Exception as e:
        print(f"Error decoding zRIF: {e}")
        sys.exit(1)

    lic = parse_license(rif_data)
    print(format_license_detail(lic))

    if out_dir is None:
        out_dir = Path.cwd()
    out_dir.mkdir(exist_ok=True, parents=True)

    filename = "work.bin" if as_work_bin else RIF_FILENAME
    out_path = out_dir / filename
    out_path.write_bytes(rif_data[:RIF_SIZE])
    print(f"\nSaved to: {out_path}")


def cli_zrif_encode(filepath: Path) -> None:
    """Encode a .rif or work.bin file into a zRIF string."""
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    try:
        lic = read_license_file(filepath)
    except ValueError:
        print("Error: Not a valid NoNPDRM license file.")
        sys.exit(1)

    if lic["is_extracted_key"]:
        print("Error: Cannot encode an extracted key file to zRIF (need full license).")
        sys.exit(1)

    _print_license_info(lic)
    print(f"\nzRIF: {rif_to_zrif(lic['raw'])}")


# --- GUI ---


def run_gui() -> None:
    """Launch the customtkinter GUI."""
    import customtkinter as ctk
    from tkinter import filedialog

    PAD = 14
    MUTED = ("gray50", "gray60")

    class App(ctk.CTk):
        def __init__(self) -> None:
            super().__init__()
            self.title("Vita RIF Tools")
            self.resizable(False, False)

            ctk.set_appearance_mode("system")
            ctk.set_default_color_theme("blue")

            self.content_id_var = ctk.StringVar()
            self.key_var = ctk.StringVar()
            self.zrif_var = ctk.StringVar()
            self._last_zrif_inputs: tuple[str, str] = ("", "")

            # Live-update info labels when fields change
            self.content_id_var.trace_add("write", self._on_fields_changed)
            self.key_var.trace_add("write", self._on_fields_changed)

            # =============================================
            # INPUT — how data gets in
            # =============================================
            input_frame = ctk.CTkFrame(self)
            input_frame.pack(fill="x", padx=PAD, pady=(PAD, 0))
            input_frame.columnconfigure(1, weight=1)

            ctk.CTkButton(
                input_frame, text="Open license file...", command=self.load
            ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=PAD, pady=(PAD, 8))

            ctk.CTkLabel(input_frame, text="or paste zRIF:").grid(
                row=1, column=0, sticky="w", padx=(PAD, 8), pady=(0, PAD)
            )
            zrif_input_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
            zrif_input_frame.grid(row=1, column=1, sticky="ew", padx=(0, PAD), pady=(0, PAD))
            zrif_input_frame.columnconfigure(0, weight=1)

            self.zrif_entry = ctk.CTkEntry(
                zrif_input_frame, textvariable=self.zrif_var,
                placeholder_text="Paste zRIF string here..."
            )
            self.zrif_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
            ctk.CTkButton(
                zrif_input_frame, text="Decode", width=70, command=self.decode_zrif
            ).grid(row=0, column=1)

            # =============================================
            # DATA — what we're working with
            # =============================================
            data_frame = ctk.CTkFrame(self)
            data_frame.pack(fill="x", padx=PAD, pady=PAD)
            data_frame.columnconfigure(1, weight=1)

            # Content ID
            ctk.CTkLabel(data_frame, text="Content ID:").grid(
                row=0, column=0, sticky="w", padx=(PAD, 8), pady=(PAD, 2)
            )
            self.content_id_entry = ctk.CTkEntry(
                data_frame, textvariable=self.content_id_var,
                placeholder_text="XX9999-XXXXXXXXX_99-XXXXXXXXXXXXXXXX"
            )
            self.content_id_entry.grid(
                row=0, column=1, sticky="ew", padx=(0, PAD), pady=(PAD, 2)
            )

            # Title ID + Region (auto-derived)
            self.info_label = ctk.CTkLabel(
                data_frame, text="", text_color=MUTED,
                font=ctk.CTkFont(size=12), anchor="w"
            )
            self.info_label.grid(
                row=1, column=1, sticky="w", padx=(4, PAD), pady=(0, 8)
            )

            # Key
            ctk.CTkLabel(data_frame, text="Key:").grid(
                row=2, column=0, sticky="w", padx=(PAD, 8), pady=(0, 2)
            )
            key_row = ctk.CTkFrame(data_frame, fg_color="transparent")
            key_row.grid(row=2, column=1, sticky="ew", padx=(0, PAD), pady=(0, 2))
            key_row.columnconfigure(0, weight=1)

            self.key_entry = ctk.CTkEntry(
                key_row, textvariable=self.key_var,
                placeholder_text="32 hex characters"
            )
            self.key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
            ctk.CTkButton(
                key_row, text="Copy", width=50, command=self.copy_key
            ).grid(row=0, column=1)

            # zRIF output (read-only display with copy)
            ctk.CTkLabel(data_frame, text="zRIF:").grid(
                row=3, column=0, sticky="w", padx=(PAD, 8), pady=(8, PAD)
            )
            zrif_out_row = ctk.CTkFrame(data_frame, fg_color="transparent")
            zrif_out_row.grid(row=3, column=1, sticky="ew", padx=(0, PAD), pady=(8, PAD))
            zrif_out_row.columnconfigure(0, weight=1)

            self.zrif_output = ctk.CTkEntry(
                zrif_out_row, state="disabled",
                placeholder_text="Auto-generated from Content ID + Key"
            )
            self.zrif_output.grid(row=0, column=0, sticky="ew", padx=(0, 8))
            ctk.CTkButton(
                zrif_out_row, text="Copy", width=50, command=self.copy_zrif
            ).grid(row=0, column=1)

            # =============================================
            # ACTIONS — what to do with the data
            # =============================================
            actions_frame = ctk.CTkFrame(self, fg_color="transparent")
            actions_frame.pack(fill="x", padx=PAD, pady=(0, 6))
            for i in range(3):
                actions_frame.columnconfigure(i, weight=1)

            ctk.CTkButton(
                actions_frame, text="Save key (.bin)", command=self.export_key
            ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
            ctk.CTkButton(
                actions_frame, text="Save license (.rif)", command=self.save_rif
            ).grid(row=0, column=1, sticky="ew", padx=4)
            ctk.CTkButton(
                actions_frame, text="Save work.bin", command=self.save_work_bin
            ).grid(row=0, column=2, sticky="ew", padx=(4, 0))

            # =============================================
            # STATUS BAR
            # =============================================
            self.status_var = ctk.StringVar(value="Ready")
            self.status_label = ctk.CTkLabel(
                self, textvariable=self.status_var,
                text_color=MUTED, font=ctk.CTkFont(size=12), anchor="w"
            )
            self.status_label.pack(fill="x", padx=PAD + 2, pady=(0, PAD))

        # --- Helpers ---

        def _set_field(self, entry: ctk.CTkEntry, value: str) -> None:
            was_disabled = entry.cget("state") == "disabled"
            if was_disabled:
                entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, value)
            if was_disabled:
                entry.configure(state="disabled")

        def _set_status(self, text: str) -> None:
            self.status_var.set(text)

        def _on_fields_changed(self, *_args: object) -> None:
            """Update derived info label and auto-generate zRIF."""
            content_id = self.content_id_var.get().strip()
            key_hex = self.key_var.get().strip()

            # Update info label
            if len(content_id) == 36:
                title_id, region = get_title_and_region(content_id)
                detail = TITLE_ID_REGIONS.get(title_id[:4], "")
                label = f"{title_id}  |  {region}"
                if detail:
                    label += f" ({detail})"
                cid_region = CONTENT_ID_REGIONS.get(content_id[:2], "")
                if cid_region:
                    label += f"  |  Publisher: {content_id[:2]}{content_id[2:6]}"
                self.info_label.configure(text=label)
            else:
                self.info_label.configure(text="")

            # Auto-generate zRIF only when inputs actually change
            inputs = (content_id, key_hex)
            if inputs == self._last_zrif_inputs:
                return
            self._last_zrif_inputs = inputs

            if len(content_id) == 36 and is_valid_hex_key(key_hex):
                rif_data = build_rif_bytes(content_id, bytes.fromhex(key_hex))
                self._set_field(self.zrif_output, rif_to_zrif(rif_data))
            else:
                self._set_field(self.zrif_output, "")

        def _validate_fields(self) -> tuple[str, bytes] | None:
            content_id = self.content_id_var.get().strip()
            key_hex = self.key_var.get().strip()

            if len(content_id) != 36:
                self._set_status("Error: Content ID must be 36 characters.")
                return None
            if not is_valid_hex_key(key_hex):
                self._set_status("Error: Key must be 32 valid hex characters.")
                return None

            return content_id, bytes.fromhex(key_hex)

        def _choose_output_dir(self) -> Path | None:
            out_dir = filedialog.askdirectory(
                initialdir=Path(__file__).parent,
                title="Select output directory",
            )
            return Path(out_dir) if out_dir else None

        # --- Clipboard ---

        def copy_key(self) -> None:
            key_hex = self.key_var.get().strip()
            if key_hex:
                self.clipboard_clear()
                self.clipboard_append(key_hex)
                self._set_status("Key copied to clipboard.")

        def copy_zrif(self) -> None:
            zrif = self.zrif_output.get().strip()
            if zrif:
                self.clipboard_clear()
                self.clipboard_append(zrif)
                self._set_status("zRIF copied to clipboard.")

        # --- Input actions ---

        def decode_zrif(self) -> None:
            zrif_string = self.zrif_var.get().strip()
            if not zrif_string:
                self._set_status("Error: Paste a zRIF string first.")
                return

            try:
                lic = zrif_to_license(zrif_string)
            except Exception as e:
                self._set_status(f"Error: Invalid zRIF string ({e})")
                return

            self._set_field(self.content_id_entry, lic["content_id"])
            self._set_field(self.key_entry, lic["key"].hex().upper())
            self._set_status("zRIF decoded — fields updated.")

        def load(self) -> None:
            filename = filedialog.askopenfilename(
                initialdir=Path(__file__).parent,
                title="Select license file",
                filetypes=[
                    ("License files", "*.rif *.bin"),
                    ("rif files", "*.rif"),
                    ("bin files", "*.bin"),
                    ("All files", "*.*"),
                ],
            )
            if not filename:
                return

            filepath = Path(filename)

            try:
                lic = read_license_file(filepath)
            except ValueError:
                self._set_status("Error: Not a valid NoNPDRM license.")
                return

            self._set_field(self.content_id_entry, lic["content_id"])
            self._set_field(self.key_entry, lic["key"].hex().upper())

            if lic["raw"]:
                self.zrif_var.set(rif_to_zrif(lic["raw"]))
            else:
                self.zrif_var.set("")

            self._set_status(f"Loaded: {filepath.name}")

        # --- Output actions ---

        def export_key(self) -> None:
            result = self._validate_fields()
            if result is None:
                return
            content_id, key = result

            out_dir = self._choose_output_dir()
            if out_dir is None:
                return

            title_id = title_id_from_content_id(content_id)
            target = out_dir / title_id
            target.mkdir(exist_ok=True, parents=True)

            out_path = save_key_binary(key, target, content_id)
            self._set_status(f"Key saved: {out_path}")

        def save_rif(self) -> None:
            result = self._validate_fields()
            if result is None:
                return
            content_id, key = result

            out_dir = self._choose_output_dir()
            if out_dir is None:
                return

            out_path = rebuild_license(key, out_dir, content_id)
            self._set_status(f"License saved: {out_path}")

        def save_work_bin(self) -> None:
            result = self._validate_fields()
            if result is None:
                return
            content_id, key = result

            out_dir = self._choose_output_dir()
            if out_dir is None:
                return

            out_path = rebuild_license(key, out_dir, content_id, as_work_bin=True)
            self._set_status(f"work.bin saved: {out_path}")

    app = App()
    app.mainloop()


# --- Entry point ---


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rif-tools",
        description="Extract, inspect, and rebuild NoNPDRM (PS Vita) license files.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("gui", help="Launch the graphical interface (default)")

    info_parser = subparsers.add_parser("info", help="Show license info")
    info_parser.add_argument("file", type=Path, help="License file (.rif, .bin, or work.bin)")
    info_parser.add_argument("-d", "--detailed", action="store_true", help="Show all license fields")

    export_parser = subparsers.add_parser("export", help="Extract key to .bin file")
    export_parser.add_argument("file", type=Path, help="License file (.rif, .bin, or work.bin)")
    export_parser.add_argument("-o", "--output", type=Path, default=None, help="Output directory")

    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild .rif from Content ID and key")
    rebuild_parser.add_argument("content_id", help="36-character Content ID")
    rebuild_parser.add_argument("key", help="32-character hex key")
    rebuild_parser.add_argument("-o", "--output", type=Path, default=None, help="Output directory")
    rebuild_parser.add_argument("--work-bin", action="store_true", help="Output as work.bin instead of .rif")

    batch_parser = subparsers.add_parser("batch", help="Batch extract keys from a directory")
    batch_parser.add_argument("directory", type=Path, help="Directory with license files")
    batch_parser.add_argument("-o", "--output", type=Path, default=None, help="Output directory")

    zrif_decode_parser = subparsers.add_parser("zrif-decode", help="Decode a zRIF string to .rif")
    zrif_decode_parser.add_argument("zrif", help="zRIF string")
    zrif_decode_parser.add_argument("-o", "--output", type=Path, default=None, help="Output directory")
    zrif_decode_parser.add_argument("--work-bin", action="store_true", help="Output as work.bin")

    zrif_encode_parser = subparsers.add_parser("zrif-encode", help="Encode a .rif file to zRIF")
    zrif_encode_parser.add_argument("file", type=Path, help="License file (.rif or work.bin)")

    args = parser.parse_args()

    match args.command:
        case None | "gui":
            run_gui()
        case "info":
            cli_info(args.file, detailed=args.detailed)
        case "export":
            cli_export(args.file, args.output)
        case "rebuild":
            cli_rebuild(args.content_id, args.key, args.output, as_work_bin=args.work_bin)
        case "batch":
            cli_batch(args.directory, args.output)
        case "zrif-decode":
            cli_zrif_decode(args.zrif, args.output, as_work_bin=args.work_bin)
        case "zrif-encode":
            cli_zrif_encode(args.file)


if __name__ == "__main__":
    main()
