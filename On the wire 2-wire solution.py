#!/usr/bin/env python3
"""
Decode interlaced wire log frames (e.g., Holiday Hack "On The Wire") into bytes
by sampling the data line on clock rising edges, then XOR-decrypting the
result with a repeating key. This script specifically reproduces the message
extracted from 2_wire.txt when using the key 'icy'.

Input format (one frame per line):
    [MSG] {"line":"<wire>", "t":<timestamp>, "v":<0|1>, ...}

Wires:
 - clock wire (e.g., 'sck') toggles regularly and provides sampling points
 - data wire (e.g., 'mosi') carries the bit value; sampled at each clock rising edge

Steps:
 1) Parse all JSON frames and group by wire name
 2) Sort each wire's events by timestamp
 3) Identify clock (prefer 'sck' by name) and data (prefer 'mosi' by name)
 4) For every clock rising edge, fetch the most recent data wire value at that time
 5) Pack bits into bytes (MSB-first)
 6) XOR with repeating key 'icy' and print plaintext

CLI:
    python decode_2wire_icy.py [--file 2_wire.txt] [--key icy]

Outputs:
 - Prints stats and the XOR-decoded ASCII text
 - Optionally writes decoded bytes and text to files (see flags)
"""

import argparse
import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple

# ----------------------------- utility helpers -----------------------------

def parse_frames(text: str) -> List[dict]:
    """Extract JSON objects from lines matching the wire frame format.
    Skips malformed JSON silently.
    """
    frames = []
    for line in text.splitlines():
        m = re.search(r"\[MSG\]\s*(\{.*\})", line)
        if not m:
            continue
        js = m.group(1)
        try:
            obj = json.loads(js)
        except json.JSONDecodeError:
            # Some lines may be truncated or contain escaped markers; ignore.
            continue
        # Require minimal fields
        if all(k in obj for k in ("line", "t", "v")):
            frames.append(obj)
    return frames


def group_by_wire(frames: List[dict]) -> Dict[str, List[Tuple[int, int]]]:
    """Return mapping: wire -> list of (timestamp, value) sorted by time."""
    wires = defaultdict(list)
    for f in frames:
        wires[f["line"]].append((int(f["t"]), int(f["v"])) )
    for w in wires:
        wires[w].sort(key=lambda tv: tv[0])
    return wires


def choose_clock_and_data(wires: Dict[str, List[Tuple[int, int]]]) -> Tuple[str, str]:
    """Pick clock and data wires, preferring names 'sck' and 'mosi'.
    If names not present, choose clock by highest transition count,
    and data as the other wire.
    """
    clock = None
    data = None
    # Name-based preference
    for w in wires:
        if w.lower() in ("sck", "clk", "clock"):
            clock = w
        if w.lower() in ("mosi", "sda", "data", "miso"):
            data = w
    if clock and data:
        return clock, data
    # Fallback: pick wire with highest transitions as clock
    def transitions(seq):
        return sum(1 for i in range(1, len(seq)) if seq[i][1] != seq[i-1][1])
    by_trans = sorted(((w, transitions(seq)) for w, seq in wires.items()),
                      key=lambda x: x[1], reverse=True)
    clock = by_trans[0][0]
    # Choose any other wire with events as data
    for w in wires:
        if w != clock:
            data = w
            break
    return clock, data


def sample_bits_on_rising_edges(clk_seq: List[Tuple[int, int]], data_seq: List[Tuple[int, int]]) -> List[int]:
    """Sample data wire at each rising edge of the clock (0 -> 1).
    Uses the last-known data value at the edge timestamp.
    """
    bits = []
    idx = 0
    last_val = data_seq[0][1]
    for i in range(1, len(clk_seq)):
        t_prev, v_prev = clk_seq[i-1]
        t_curr, v_curr = clk_seq[i]
        if v_prev == 0 and v_curr == 1:  # rising edge
            # Advance data pointer up to current time
            while idx < len(data_seq) and data_seq[idx][0] <= t_curr:
                last_val = data_seq[idx][1]
                idx += 1
            bits.append(last_val)
    return bits


def pack_bits_to_bytes(bits: List[int], msb_first: bool = True) -> bytes:
    """Pack a list of 0/1 bits into bytes.
    msb_first=True means bit[0] becomes the most significant bit of byte 0.
    """
    out = bytearray()
    for i in range(0, (len(bits) // 8) * 8, 8):
        b = 0
        for j in range(8):
            if msb_first:
                b = (b << 1) | bits[i + j]
            else:
                b |= (bits[i + j] << j)
        out.append(b)
    return bytes(out)


def xor_repeat(data: bytes, key: bytes) -> bytes:
    """XOR data with repeating key bytes."""
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

# ------------------------------- main routine ------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Decode wire log by sampling MOSI on SCK rising edges and XOR with key"
    )
    ap.add_argument("--file", default="2_wire.txt", help="Path to wire log file (default: 2_wire.txt)")
    ap.add_argument("--key", default="icy", help="XOR key (default: icy)")
    ap.add_argument("--msb-first", action="store_true", help="Pack bits MSB-first (default)")
    ap.add_argument("--lsb-first", action="store_true", help="Pack bits LSB-first")
    ap.add_argument("--write-bytes", default=None, help="Optional path to write raw decoded bytes")
    ap.add_argument("--write-text", default=None, help="Optional path to write decoded ASCII text")
    args = ap.parse_args()

    # Read input file
    with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # Parse frames and group by wire
    frames = parse_frames(text)
    wires = group_by_wire(frames)

    if not wires:
        raise SystemExit("No wire data found.")

    # Identify clock and data wires
    clock, data = choose_clock_and_data(wires)
    clk_seq = wires[clock]
    data_seq = wires[data]

    print(f"Clock wire: {clock}  events={len(clk_seq)}  time=[{clk_seq[0][0]}..{clk_seq[-1][0]}]")
    print(f"Data  wire: {data}   events={len(data_seq)}  time=[{data_seq[0][0]}..{data_seq[-1][0]}]")

    # Sample and pack bits
    bits = sample_bits_on_rising_edges(clk_seq, data_seq)
    print(f"Collected bits: {len(bits)}")

    msb_first = True
    if args.lsb_first:
        msb_first = False
    # If both flags are set, prefer LSB; otherwise default MSB
    elif args.msb_first:
        msb_first = True

    raw_bytes = pack_bits_to_bytes(bits, msb_first=msb_first)
    print(f"Packed bytes: {len(raw_bytes)} (msb_first={msb_first})")

    # XOR decrypt with provided key
    key_bytes = args.key.encode("ascii")
    decoded = xor_repeat(raw_bytes, key_bytes)

    # Print ASCII preview
    try:
        text_out = decoded.decode("ascii")
    except UnicodeDecodeError:
        # Fallback: replace non-ascii
        text_out = decoded.decode("ascii", errors="replace")
    print("\n=== XOR-decoded text ===")
    print(text_out)

    # Optional writes
    if args.write_bytes:
        with open(args.write_bytes, "wb") as fb:
            fb.write(decoded)
        print(f"Wrote decoded bytes -> {args.write_bytes}")
    if args.write_text:
        with open(args.write_text, "w", encoding="utf-8") as ft:
            ft.write(text_out)
        print(f"Wrote decoded text  -> {args.write_text}")


if __name__ == "__main__":
    main()
