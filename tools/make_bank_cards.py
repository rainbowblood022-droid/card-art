"""Original card art for cards issuers don't publish an image of (debit cards, credit unions): drawn from the bank's
colors, with a chip, contactless mark and network.

usage: py -3.12 -I tools/make_bank_cards.py   (run from the repo root; writes cards/<id>.webp)
"""
import json
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, S = 640, 404, 4          # layout units (drawn 4x larger, for smooth edges)
OUT = (1012, 638)              # final size: a real card at 300 dpi
RADIUS = 26
FONTS = 'C:/Windows/Fonts/'

# id, bank name on the card, product line, colors (top-left, bottom-right), accent, network
CARDS = [
    {'id': 'penfed-debit', 'name': 'PenFed Debit Card', 'issuer': 'PenFed Credit Union', 'bank': 'PenFed',
     'line': 'CREDIT UNION', 'colors': ('#0a6a86', '#022a3a'), 'accent': '#9fd3e0', 'network': 'visa'},
    {'id': 'pnc-debit', 'name': 'PNC Debit Card', 'issuer': 'PNC Bank', 'bank': 'PNC',
     'line': 'BANK', 'colors': ('#0b78c2', '#03345c'), 'accent': '#ef7622', 'network': 'visa'},
]


def font(name, size):
    return ImageFont.truetype(FONTS + name, size * S)


def gradient(c0, c1):
    """Diagonal from c0 (top left) to c1 (bottom right)."""
    import numpy as np
    y, x = np.mgrid[0:H * S, 0:W * S].astype(np.float32)
    t = np.clip((x / (W * S) * 0.65 + y / (H * S) * 0.35), 0, 1)[..., None]
    rgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    return Image.fromarray((rgb(c0) * (1 - t) + rgb(c1) * t).astype('uint8'), 'RGB')


def chip(d, x, y):
    w, h = 74 * S, 56 * S
    d.rounded_rectangle((x, y, x + w, y + h), 11 * S, fill='#d9d6cc', outline='#a9a59a', width=2 * S)
    for k in (0.36, 0.64):
        d.line((x, y + h * k, x + w * 0.34, y + h * k), fill='#9a958a', width=2 * S)
        d.line((x + w * 0.66, y + h * k, x + w, y + h * k), fill='#9a958a', width=2 * S)
    d.line((x + w * 0.34, y, x + w * 0.34, y + h), fill='#9a958a', width=2 * S)
    d.line((x + w * 0.66, y, x + w * 0.66, y + h), fill='#9a958a', width=2 * S)


def contactless(d, x, y, color):
    for i in range(4):
        r = (8 + i * 7) * S
        d.arc((x - r, y - r, x + r, y + r), -45, 45, fill=color, width=3 * S)


def draw(c):
    img = gradient(*c['colors']).convert('RGBA')
    # fine curved lines in the accent color, fanning across the lower right
    lines = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    for i in range(14):
        r = (380 + i * 16) * S
        cx, cy = 1.05 * W * S, 1.55 * H * S
        ld.arc((cx - r * 1.6, cy - r, cx + r * 1.6, cy + r), 180, 290, fill=c['accent'] + '55', width=max(S, 2))
    img.alpha_composite(lines)
    d = ImageDraw.Draw(img)
    d.text((40 * S, 34 * S), c['bank'], font=font('segoeuib.ttf', 46), fill='white')
    d.text((42 * S, 92 * S), c['line'], font=font('segoeui.ttf', 15), fill=c['accent'], spacing=4)
    d.text((W * S - 40 * S, 44 * S), 'DEBIT', font=font('segoeuib.ttf', 18), fill='#ffffffcc', anchor='ra')
    chip(d, 48 * S, 150 * S)
    contactless(d, 142 * S, 178 * S, '#ffffffcc')
    if c['network'] == 'visa':
        d.text((W * S - 40 * S, H * S - 34 * S), 'VISA', font=font('segoeuiz.ttf', 52), fill='white', anchor='rd')
    out = img.resize(OUT, Image.LANCZOS)
    mask = Image.new('L', (W * S, H * S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W * S - 1, H * S - 1), RADIUS * S, fill=255)
    out.putalpha(mask.resize(OUT, Image.LANCZOS))
    return out


def main():
    manifest = json.load(open('cards.json', encoding='utf-8'))
    known = {m['id']: m['source'] for m in manifest['cards']}
    for c in CARDS:
        if known.get(c['id'], 'original') != 'original':
            continue   # a real image of this card was supplied (from_image.py); the drawing is only a fallback
        draw(c).save(f"cards/{c['id']}.webp", quality=92, method=6)
        if c['id'] not in known:
            manifest['cards'].append({'id': c['id'], 'name': c['name'], 'issuer': c['issuer'], 'image': f"cards/{c['id']}.webp", 'source': 'original'})
    json.dump(manifest, open('cards.json', 'w', encoding='utf-8'), indent=2)
    print('done')


main()
