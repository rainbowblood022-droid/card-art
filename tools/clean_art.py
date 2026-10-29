"""Clean issuer card art: crop to the card, remove promo banners and sample cardholder names, same size and corners.

usage: py -3.12 -I clean_art.py <raw dir> <out dir>
"""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw

W, H = 1012, 638         # a real card (85.6 x 54 mm, 1.586) at 300 dpi: more than the app ever shows
K = W / 640              # the cleanup sizes below were tuned at 640 wide
RADIUS = round(26 * K)   # ~3.2 mm corner


def px(n):
    """A kernel size tuned at 640 wide, scaled and kept odd."""
    return int(n * K) // 2 * 2 + 1

# Sample cardholder names and numbers printed on the art: (x0, y0, x1, y1) as fractions of the card
TEXT = {
    'chase-freedom-unlimited': [(0.05, 0.76, 0.40, 0.92)],
    'chase-freedom-rise': [(0.05, 0.76, 0.40, 0.92)],
    'chase-slate-edge': [(0.03, 0.80, 0.40, 0.96)],
    'chase-hyatt': [(0.05, 0.78, 0.40, 0.92)],
    'chase-ink-cash': [(0.02, 0.75, 0.50, 0.95)],
    'chase-ink-unlimited': [(0.02, 0.75, 0.50, 0.95)],
    'chase-ink-preferred': [(0.02, 0.75, 0.50, 0.95)],
    'chase-prime-visa': [(0.08, 0.72, 0.58, 0.86)],
    'chase-amazon-visa': [(0.08, 0.72, 0.58, 0.86)],
    'chase-swa-priority': [(0.03, 0.78, 0.35, 0.89)],
    'chase-swa-premier': [(0.03, 0.78, 0.35, 0.89)],
    'chase-swa-plus': [(0.03, 0.78, 0.35, 0.89)],
    'amex-bce': [(0.07, 0.83, 0.35, 0.96), (0.84, 0.41, 0.97, 0.54)],
    'amex-bcp': [(0.07, 0.83, 0.35, 0.96), (0.84, 0.41, 0.97, 0.54)],
    'amex-delta-gold': [(0.04, 0.81, 0.29, 0.95), (0.86, 0.43, 0.98, 0.55), (0.81, 0.78, 0.97, 0.94)],
    'amex-hilton': [(0.07, 0.82, 0.34, 0.95), (0.85, 0.42, 0.97, 0.54), (0.56, 0.64, 0.71, 0.80)],
    'amex-gold': [(0.08, 0.83, 0.34, 0.96), (0.81, 0.50, 0.93, 0.62)],
    'amex-platinum': [(0.08, 0.83, 0.34, 0.96), (0.72, 0.50, 0.84, 0.62)],
    'amex-green': [(0.08, 0.82, 0.34, 0.96), (0.81, 0.46, 0.93, 0.58)],
    'citi-double-cash': [(0.03, 0.81, 0.40, 0.95)],
    'citi-custom-cash': [(0.03, 0.81, 0.40, 0.95)],
    'citi-strata-elite': [(0.02, 0.83, 0.40, 0.97, 60)],
    'citi-strata': [(0.02, 0.83, 0.40, 0.97, 60)],
    'citi-simplicity': [(0.03, 0.81, 0.40, 0.95)],
    'citi-diamond-preferred': [(0.03, 0.81, 0.40, 0.95)],
    'citi-aa-platinum': [(0.36, 0.48, 0.60, 0.69)],
    'wf-active-cash': [(0.04, 0.78, 0.40, 0.91)],
    'wf-autograph-journey': [(0.04, 0.78, 0.40, 0.91)],
    'wf-autograph': [(0.04, 0.78, 0.40, 0.91)],
    'wf-reflect': [(0.04, 0.78, 0.40, 0.91)],
}

# brushed-metal cards and a plain strip of each (x from, x to) to take the texture from
BRUSHED = {'chase-prime-visa': (0.30, 0.65), 'chase-amazon-visa': (0.30, 0.98)}
# parts of the design right next to a banner, kept out of the cleanup
KEEP = {'chase-amazon-visa': [(0.27, 0.33, 0.35, 0.50), (0.49, 0.05, 0.98, 0.25), (0.70, 0.66, 1.0, 0.92)],
        'chase-prime-visa': [(0.27, 0.33, 0.35, 0.50)]}

INSET = {'citi-strata': 0.025, 'citi-strata-elite': 0.02, 'chase-sapphire-preferred': 0.01, 'chase-sapphire-reserve': 0.01}

# Cards whose promo banner covers the chip: a clean chip from a sibling card, (donor, donor box, target box)
CHIP = {
    'chase-prime-visa': ('chase-swa-premier', (0.085, 0.325, 0.225, 0.505), (0.11, 0.30, 0.255, 0.53)),
    'chase-amazon-visa': ('chase-hyatt', (0.085, 0.315, 0.225, 0.485), (0.115, 0.325, 0.25, 0.49)),
}

# Promo banners ("No annual fee", "New offer"): the corner to search and the banner's color (BGR)
BANNER = {
    'chase-freedom-unlimited': ('tr', (80, 220, 180)),
    'chase-freedom-flex': ('tr', (80, 220, 180)),
    'chase-freedom-rise': ('tr', (80, 220, 180)),
    'chase-slate-edge': ('tr', (80, 220, 180)),
    'chase-prime-visa': ('tl', (40, 160, 245)),
    'chase-amazon-visa': ('tl', (140, 130, 20)),
    'bofa-customized-cash': ('tl', (90, 40, 10)),
    'bofa-unlimited-cash': ('tl', (90, 40, 10)),
}


def banner_mask(bgr, corner, color, grow=None):
    h, w = bgr.shape[:2]
    region = np.zeros((h, w), np.uint8)
    if corner == 'tr':
        region[: int(h * 0.6), int(w * 0.45):] = 1
    else:
        region[: int(h * 0.6), : int(w * 0.55)] = 1
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.int32)
    ref = cv2.cvtColor(np.uint8([[color]]), cv2.COLOR_BGR2LAB)[0, 0].astype(np.int32)
    near = (np.sqrt(((lab - ref) ** 2).sum(axis=2)) < 48).astype(np.uint8) * region
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(near)
    if n < 2:
        return np.zeros((h, w), np.uint8)
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    pts = cv2.findNonZero((lbl == big).astype(np.uint8))
    m = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(m, cv2.convexHull(pts), 255)
    # the banner's thin shadow and the "†" just outside it
    # the banner's drop shadow too: wider on the bigger Amazon banners
    g = grow or px(41 if corner == 'tl' and color[2] < 200 or color == (40, 160, 245) else 15)
    return cv2.dilate(m, np.ones((g, g), np.uint8))


def text_mask(bgr, boxes):
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    bg = cv2.medianBlur(gray, px(21))
    diff = cv2.absdiff(gray, bg)
    m = np.zeros((h, w), np.uint8)
    for x0, y0, x1, y1, *thr in boxes:
        sl = (slice(int(y0 * h), int(y1 * h)), slice(int(x0 * w), int(x1 * w)))
        m[sl] = (diff[sl] > (thr[0] if thr else 14)).astype(np.uint8) * 255
    return cv2.dilate(m, np.ones((px(7), px(7)), np.uint8))


def rounded(im: Image.Image) -> Image.Image:
    big = Image.new('L', (W * 4, H * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, W * 4 - 1, H * 4 - 1), RADIUS * 4, fill=255)
    out = im.convert('RGBA')
    out.putalpha(big.resize((W, H), Image.LANCZOS))
    return out


def frame(cid, path):
    """The card itself, 640x404, flattened: without the transparent margin or a banner sticking out past its edge."""
    im = Image.open(path).convert('RGBA')
    alpha = np.array(im)[:, :, 3] > 40
    if cid in BANNER:
        bgr = cv2.cvtColor(np.array(im.convert('RGB')), cv2.COLOR_RGB2BGR)
        alpha &= banner_mask(bgr, *BANNER[cid], grow=px(9)) == 0
    # rows and columns that are mostly card: a banner's tip past the edge is too thin to count
    rows = np.where(alpha.mean(axis=1) > 0.35)[0]
    cols = np.where(alpha.mean(axis=0) > 0.35)[0]
    x0, y0, x1, y1 = cols[0], rows[0], cols[-1] + 1, rows[-1] + 1
    # some issuer images have a light photo edge around the card
    k = INSET.get(cid, 0)
    dx, dy = int((x1 - x0) * k), int((y1 - y0) * k)
    im = im.crop((x0 + dx, y0 + dy, x1 - dx, y1 - dy))
    # flatten the transparent rounded corners on the card's own average color before resizing
    flat = Image.new('RGBA', im.size)
    flat.paste(im.resize((1, 1), Image.LANCZOS).resize(im.size), (0, 0))
    flat.alpha_composite(im)
    return cv2.cvtColor(np.array(flat.convert('RGB').resize((W, H), Image.LANCZOS)), cv2.COLOR_RGB2BGR)


def box(b):
    x0, y0, x1, y1 = b
    return int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)


def clean(cid, path):
    bgr = frame(cid, path)
    mask = np.zeros(bgr.shape[:2], np.uint8)
    bm = np.zeros(bgr.shape[:2], np.uint8)
    if cid in BANNER:
        bm |= banner_mask(bgr, *BANNER[cid])
        for b in KEEP.get(cid, []):
            x0, y0, x1, y1 = box(b)
            bm[y0:y1, x0:x1] = 0
    if cid in TEXT:
        if cid in BRUSHED:   # the texture fill hides a whole box cleanly, edges and all
            for b in TEXT[cid]:
                x0, y0, x1, y1 = box(b[:4])
                bm[y0:y1, x0:x1] = 255
        else:
            bm |= text_mask(bgr, TEXT[cid])
    if cid in BRUSHED:
        bgr = row_fill(bgr, bm, BRUSHED[cid], [*KEEP.get(cid, ()), *([CHIP[cid][2]] if cid in CHIP else [])])
    else:
        mask |= bm
    if cid in CHIP:
        donor, db, tb = CHIP[cid]
        d = frame(donor, os.path.join(os.path.dirname(path), donor + '.png'))
        x0, y0, x1, y1 = box(db)
        X0, Y0, X1, Y1 = box(tb)
        chip = cv2.resize(d[y0:y1, x0:x1], (X1 - X0, Y1 - Y0), interpolation=cv2.INTER_LANCZOS4)
        # only the chip's own rounded shape, so the donor card's background doesn't come along
        shape = np.zeros(chip.shape[:2], np.uint8)
        iw, ih = chip.shape[1], chip.shape[0]
        cv2.rectangle(shape, (int(iw * .1), int(ih * .1)), (int(iw * .9), int(ih * .9)), 255, -1)
        shape = cv2.dilate(shape, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(iw * .12), int(iw * .12))))
        region = bgr[Y0:Y1, X0:X1]
        region[shape > 0] = chip[shape > 0]
        mask[Y0:Y1, X0:X1][shape > 0] = 0
    if mask.any():
        bgr = cv2.inpaint(bgr, mask, px(9), cv2.INPAINT_TELEA)
    if cid == 'citi-strata':
        bgr = borrow_inverted(bgr, clean('citi-strata-elite', os.path.join(os.path.dirname(path), 'citi-strata-elite.png'))[2])
    return rounded(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))), mask, bgr


def borrow_inverted(bgr, elite):
    """Strata's name corner from Strata Elite: aligned on the waves above it, inverted and toned to Strata's colors."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    e = 255 - cv2.cvtColor(elite, cv2.COLOR_BGR2GRAY).astype(np.float32)
    band = (slice(int(H * .55), int(H * .80)), slice(0, int(W * .5)))
    (dx, dy), _ = cv2.phaseCorrelate(e[band], g[band])
    e = cv2.warpAffine(e, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    # match Strata's paper and ink tones
    lo, hi = np.percentile(g[band], 3), np.percentile(g[band], 97)
    elo, ehi = np.percentile(e[band], 3), np.percentile(e[band], 97)
    e = (e - elo) / max(ehi - elo, 1) * (hi - lo) + lo
    tone = bgr[band].reshape(-1, 3).mean(axis=0) / max(g[band].mean(), 1)
    patch = np.clip(e[..., None] * tone, 0, 255).astype(np.uint8)
    m = np.zeros((H, W), np.float32)
    cv2.rectangle(m, (0, int(H * .81)), (int(W * .43), H), 1, -1)
    m = cv2.GaussianBlur(m, (px(21), px(21)), 0)[..., None]
    return (bgr * (1 - m) + patch * m).astype(np.uint8)


def row_fill(bgr, mask, strip, keep=()):
    """Brushed-metal cards: fill each row's hidden pixels with that same row's visible pixels from a plain strip of the
    card, mirrored back and forth, so the horizontal streaks carry on. A row with nothing visible in the strip borrows
    the nearest row that has."""
    x0, x1 = int(strip[0] * W), int(strip[1] * W)
    usable = mask == 0
    for b in keep:
        bx0, by0, bx1, by1 = box(b)
        usable[by0:by1, bx0:bx1] = False
    tex = np.zeros_like(bgr)
    have = np.zeros(H, bool)
    for y in range(H):
        row = bgr[y, x0:x1][usable[y, x0:x1]]
        if len(row) < 12:
            continue
        n = len(row)
        idx = np.arange(W) % (2 * n)
        tex[y] = row[np.where(idx < n, idx, 2 * n - 1 - idx)]
        have[y] = True
    ok = np.where(have)[0]
    for y in np.where(~have)[0]:
        tex[y] = tex[ok[np.argmin(abs(ok - y))]]
    # keep the streaks from the texture but the light and shade of the surrounding card
    f = bgr.astype(np.float32)
    t = tex.astype(np.float32)
    w = usable.astype(np.float32)[..., None]
    low = lambda x, sd: cv2.GaussianBlur(x, (0, 0), sd)
    # deep inside a wide hidden area there's little nearby to go on: blend toward a wider look
    shade, cover = None, None
    for sd in (60 * K, 30 * K, 15 * K):
        sw = low(w[..., 0], sd)[..., None]
        sh = low(f * w, sd) / np.maximum(sw, 1e-4)
        shade = sh if shade is None else shade * (1 - np.clip(sw * 3, 0, 1)) + sh * np.clip(sw * 3, 0, 1)
    t = t - low(t, 18 * K) + shade
    soft = cv2.GaussianBlur((mask > 0).astype(np.float32), (px(7), px(7)), 0)[..., None]
    return np.clip(f * (1 - soft) + t * soft, 0, 255).astype(np.uint8)


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    done = []
    for f in sorted(os.listdir(src)):
        if not f.endswith('.png') or f.startswith('_'):
            continue
        cid = f[:-4]
        img, *_ = clean(cid, os.path.join(src, f))
        img.save(os.path.join(out, f), optimize=True)
        done.append((cid, img))
    cols, tw, th = 6, 320, 230
    sheet = Image.new('RGB', (cols * tw, ((len(done) + cols - 1) // cols) * th), '#2a2a2e')
    d = ImageDraw.Draw(sheet)
    for i, (cid, img) in enumerate(done):
        t = img.resize((310, 196), Image.LANCZOS)
        x, y = (i % cols) * tw + 5, (i // cols) * th + 5
        sheet.paste(t, (x, y), t)
        d.text((x, y + 200), cid, fill='white')
    sheet.save(os.path.join(out, '..', '_clean_sheet.png'))
    print(len(done), 'cards')


main()
