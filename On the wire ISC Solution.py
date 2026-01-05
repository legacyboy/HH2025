#!/usr/bin/env python3
"""
Decode I²C transactions from an annotated JSON stream (Holiday Hack format).

What this script does:
  1) Reads a text file containing lines like: [MSG] { ...JSON... }
  2) Filters the 'sda' line and segments transactions between 'start' and 'stop'.
  3) Reconstructs bytes from 'address-bit' / 'data-bit' markers (8 bits per byte).
     - Default bit order is MSB-first: bitIndex 0 is MSB, 7 is LSB.
     - You can flip to LSB-first via --bitorder lsb (diagnostic).
  4) Ignores ACK bits (they're sampled on SCL but not reconstructed into data here).
  5) From the first byte, extracts 7-bit address:  addr7 = (addr_rw >> 1) & 0x7F
     and R/W bit: rw = addr_rw & 1
  6) XOR-decodes the data bytes with the repeating key 'bananza' and prints ASCII if valid.
  7) Optional: filter by address, and/or export details to CSV.

Usage:
    python decode_i2c.py 3_wire.txt
    python decode_i2c.py 3_wire.txt --addr 0x3C
    python decode_i2c.py 3_wire.txt --bitorder lsb
    python decode_i2c.py 3_wire.txt --csv out.csv

Notes:
  - We reconstruct solely from SDA markers ('address-bit'/'data-bit'); ACKs are ignored by design.
  - If you need SCL-correlated sampling by timestamp, we can extend this, but it was not necessary here.
"""

import re
import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Iterable

# Repeating XOR key per the challenge
KEY = b"bananza"

def parse_msgs(text: str) -> List[Dict[str, Any]]:
    """Extract all JSON objects from '[MSG] { ... }' lines."""
    msgs = []
    for m in re.finditer(r"\[MSG\]\s*(\{.*?\})", text, re.S):
        try:
            msgs.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            # Skip malformed lines quietly
            continue
    return msgs

def segment_sda_transactions(msgs: Iterable[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Segment transactions on SDA:
      - Start when marker == 'start'
      - Stop when marker == 'stop'
      - Collect everything between (including bits and ack markers—ACKs are later ignored)
    """
    sda = [j for j in msgs if j.get("line") == "sda"]
    txs, cur, started = [], [], False
    for j in sda:
        marker = j.get("marker", "")
        if marker == "start":
            started, cur = True, [j]
        elif marker == "stop":
            if started:
                cur.append(j)
                txs.append(cur)
            started, cur = False, []
        else:
            if started:
                cur.append(j)
    return txs

def reconstruct_bytes(tx: List[Dict[str, Any]], bitorder: str = "msb") -> List[int]:
    """
    Reconstruct a byte sequence from one SDA transaction.
    We consume only 'address-bit' and 'data-bit' markers.

    bitorder:
      - 'msb': bitIndex 0 is MSB -> shift by (7 - i)
      - 'lsb': bitIndex 0 is LSB -> shift by i          (diagnostic toggle)
    """
    # Collect bits per byteIndex
    bits_by_byte: Dict[int, Dict[int, int]] = {}
    for j in tx:
        if j.get("marker") in ("address-bit", "data-bit"):
            bidx = int(j["byteIndex"])
            bits_by_byte.setdefault(bidx, {})[int(j["bitIndex"])] = int(j["v"])

    # Assemble bytes in ascending byteIndex order
    seq: List[int] = []
    for bidx in sorted(bits_by_byte):
        bits = bits_by_byte[bidx]
        if len(bits) != 8:
            # If a byte has fewer/more than 8 bits, skip it (incomplete sample)
            continue
        val = 0
        if bitorder == "msb":
            for i in range(8):
                val |= (bits[i] & 1) << (7 - i)
        else:  # 'lsb'
            for i in range(8):
                val |= (bits[i] & 1) << i
        seq.append(val)
    return seq

def repeat_xor(data: bytes, key: bytes) -> bytes:
    """Apply repeating XOR: data[i] ^ key[i % len(key)]"""
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

def decode_file(
    infile: Path,
    addr_filter: int = None,
    bitorder: str = "msb",
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Parse, segment, reconstruct, and decode all transactions in 'infile'.
    Returns a dict keyed by 7-bit address -> list of dicts:
        { 'rw': 0/1, 'raw': bytes, 'xor': bytes, 'ascii': str or None }
    """
    text = infile.read_text()
    msgs = parse_msgs(text)
    txs = segment_sda_transactions(msgs)

    by_addr: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

    for tx in txs:
        seq = reconstruct_bytes(tx, bitorder=bitorder)
        if not seq:
            continue
        addr_rw = seq[0]
        addr7 = (addr_rw >> 1) & 0x7F
        rw = addr_rw & 1
        if addr_filter is not None and addr7 != addr_filter:
            continue
        raw = bytes(seq[1:])
        x = repeat_xor(raw, KEY)
        # Try ASCII decode (not all payloads will be printable)
        try:
            s = x.decode("ascii")
        except UnicodeDecodeError:
            s = None
        by_addr[addr7].append({"rw": rw, "raw": raw, "xor": x, "ascii": s})
    return by_addr

def write_csv(outfile: Path, decoded: Dict[int, List[Dict[str, Any]]]) -> None:
    """Write a simple CSV with address, index, rw, raw_hex, xor_hex, ascii."""
    with outfile.open("w", encoding="utf-8") as f:
        f.write("address,index,rw,raw_hex,xor_hex,ascii\n")
        for addr in sorted(decoded):
            entries = decoded[addr]
            for i, e in enumerate(entries):
                raw_hex = e["raw"].hex(" ")
                xor_hex = e["xor"].hex(" ")
                ascii_txt = e["ascii"] if e["ascii"] is not None else ""
                f.write(f"0x{addr:02X},{i},{e['rw']},{raw_hex},{xor_hex},{ascii_txt}\n")

def main():
    ap = argparse.ArgumentParser(description="Decode I²C JSON stream and XOR with 'bananza'.")
    ap.add_argument("infile", help="Input text file (e.g., 3_wire.txt)")
    ap.add_argument("--addr", help="Filter to a single 7-bit address (e.g., 0x3C)", default=None)
    ap.add_argument("--bitorder", choices=["msb", "lsb"], default="msb",
                    help="Bit order when reconstructing bytes (default: msb)")
    ap.add_argument("--csv", help="Optional CSV output path", default=None)
    args = ap.parse_args()

    infile = Path(args.infile)
    addr_filter = None
    if args.addr:
        # Accept inputs like '0x3C' or '3C'
        s = args.addr.lower().strip()
        if s.startswith("0x"):
            s = s[2:]
        addr_filter = int(s, 16)

    decoded = decode_file(infile, addr_filter=addr_filter, bitorder=args.bitorder)

    # Print summary to stdout
    if not decoded:
        print("No transactions decoded (check file path, address filter, or bit order).")
        return

    print("Addresses found:", ", ".join(f"0x{a:02X}" for a in sorted(decoded)))
    for addr in sorted(decoded):
        entries = decoded[addr]
        print(f"\nAddress 0x{addr:02X} — {len(entries)} transaction(s)")
        for i, e in enumerate(entries[:10]):  # show first 10 examples
            raw_hex = e["raw"].hex(" ")
            xor_hex = e["xor"].hex(" ")
            ascii_txt = e["ascii"] if e["ascii"] is not None else "<non-ASCII>"
            print(f"  #{i:02d} rw={e['rw']}  raw={raw_hex}  xor={xor_hex}  ascii={ascii_txt}")

    if args.csv:
        out = Path(args.csv)
        write_csv(out, decoded)
        print(f"\nCSV written to: {out.resolve()}")

if __name__ == "__main__":
    main()
