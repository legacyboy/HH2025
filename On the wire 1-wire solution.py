import json, re
from pathlib import Path

# Load and parse
txt = Path('1_wire.txt').read_text()
objs = []
for line in txt.splitlines():
    m = re.search(r'\{.*\}', line)
    if m:
        try:
            objs.append(json.loads(m.group(0)))
        except json.JSONDecodeError:
            pass

# Find presence -> stop window
start_idx = next(i for i,o in enumerate(objs) if o.get('marker') == 'presence')
stop_idx  = next(i for i,o in enumerate(objs) if o.get('marker') == 'stop')

# Recover bits by low-pulse width
bits = []
prev_v, low_start_t = None, None
for o in objs[start_idx+1:stop_idx]:
    v, t = o['v'], o['t']
    if prev_v is None:
        prev_v = v
        continue
    if prev_v == 1 and v == 0:
        low_start_t = t
    elif prev_v == 0 and v == 1 and low_start_t is not None:
        dt = t - low_start_t
        bits.append(0 if dt >= 30 else 1)
        low_start_t = None
    prev_v = v

# Group into bytes (LSB-first) and render hex/ASCII
bytes_list = []
for i in range(0, len(bits), 8):
    chunk = bits[i:i+8]
    if len(chunk) < 8: break
    val = sum((bit << j) for j, bit in enumerate(chunk))
    bytes_list.append(val)

hex_str   = ' '.join(f'{b:02x}' for b in bytes_list)
ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in bytes_list)

# Save a proof file with the outputs
content = (
    'Decoded 1-Wire bitstream from presence->stop\n'
    f'Bits: {len(bits)}\nBytes: {len(bytes_list)}\n\nHEX:\n{hex_str}\n\nASCII:\n'
    + ''.join(chr(b) if 32 <= b <= 126 else '\n' if b==10 else '' for b in bytes_list) + '\n'
)
Path('1_wire_decoded.txt').write_text(content)
print(ascii_str)
