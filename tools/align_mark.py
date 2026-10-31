"""Put the network mark (VISA, with its DEBIT label when there is one) of a supplied card at the same place on
every card: lower right, MARGIN from the right and bottom edges, VISA_WIDTH of the card wide.

The mark is lifted from the card itself, so it keeps that card's own look (flat white, metallic...), the background
behind it is filled from its surroundings, and the mark is set back down at the standard place. Only the mark moves;
nothing else on the card changes.

usage: py -3.12 -I tools/align_mark.py <id> [<id>...]   (run from the repo root; edits cards/<id>.webp in place)
       add --preview <png> to also save a before/after sheet
"""
import sys
import cv2
import numpy as np
from PIL import Image

MARGIN = 60          # px of the 1012x638 card: about 6% of its width, equal from the right and the bottom
VISA_WIDTH = 0.225   # of the card's width, near what the supplied cards already use (22-23%)


def mark_mask(rgb: np.ndarray) -> np.ndarray:
    """The mark's pixels: brighter than the smooth background around them, in the card's lower right."""
    h, w = rgb.shape[:2]
    bg = cv2.medianBlur(rgb, 51).astype(np.int16)
    diff = np.abs(rgb.astype(np.int16) - bg).max(axis=2)
    fg = ((diff > 45) & (rgb.astype(np.int16).mean(axis=2) > bg.mean(axis=2))).astype(np.uint8)
    region = np.zeros_like(fg)
    region[int(.62 * h):h - 8, int(.55 * w):w - 6] = 1
    fg = cv2.morphologyEx(fg & region, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    parts = [i for i in range(1, n) if st[i][4] > 40]
    if not parts:
        raise SystemExit('no mark found in the lower right')
    right = max(st[i][0] + st[i][2] for i in parts)
    bottom = max(st[i][1] + st[i][3] for i in parts)
    # the mark is the group of shapes at the lower right corner; a light streak elsewhere isn't part of it
    keep = np.zeros_like(fg)
    for i in parts:
        x, y, ww, hh, _ = st[i]
        if x >= right - .30 * w and y >= bottom - .25 * h:
            keep[lab == i] = 1
    # thick letters: their centers match a blurred background made of them, so add every bright, colorless pixel
    # around the shapes found (white or silver ink; the card's colored glows and streaks are left out)
    ys, xs = np.where(keep)
    x0, y0, x1, y1 = xs.min() - 4, ys.min() - 4, xs.max() + 5, ys.max() + 5
    box = rgb[y0:y1, x0:x1].astype(np.int16)
    lum, sat = box.mean(axis=2), box.max(axis=2) - box.min(axis=2)
    far = cv2.medianBlur(rgb, 101)[y0:y1, x0:x1].astype(np.int16).mean(axis=2)
    keep[y0:y1, x0:x1] |= ((lum > far + 30) & (sat < 70) & (lum > 120)).astype(np.uint8)
    return cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))


def align(cid: str) -> tuple[np.ndarray, np.ndarray]:
    path = f'cards/{cid}.webp'
    im = np.array(Image.open(path).convert('RGBA'))
    rgb, alpha = im[..., :3].copy(), im[..., 3]
    h, w = rgb.shape[:2]
    keep = mark_mask(rgb)
    ys, xs = np.where(keep)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    # VISA is the widest line of the mark (DEBIT sits above it, shorter): its width sets the scale
    rows = np.where(keep[y0:y1].any(axis=1))[0] + y0
    gaps = np.where(np.diff(rows) > 4)[0]
    visa_top = rows[gaps[-1] + 1] if len(gaps) else y0
    vx = np.where(keep[visa_top:y1].any(axis=0))[0]
    scale = VISA_WIDTH * w / (vx.max() + 1 - vx.min())

    # the mark with its soft edge, cut from the original
    pad = 6
    bx0, by0, bx1, by1 = max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, w), min(y1 + pad, h)
    soft = cv2.GaussianBlur(cv2.dilate(keep, np.ones((3, 3), np.uint8)).astype(np.float32), (5, 5), 0)
    patch = rgb[by0:by1, bx0:bx1].astype(np.float32)
    pa = soft[by0:by1, bx0:bx1]
    size = (round((bx1 - bx0) * scale), round((by1 - by0) * scale))
    patch = cv2.resize(patch, size, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    pa = np.clip(cv2.resize(pa, size, interpolation=cv2.INTER_LINEAR), 0, 1)[..., None]

    # the background behind the old mark, filled in from around it
    hole = cv2.dilate(keep, np.ones((9, 9), np.uint8))
    out = cv2.inpaint(rgb, hole, 9, cv2.INPAINT_TELEA).astype(np.float32)

    # set down so the mark's own right and bottom edges sit MARGIN from the card's
    nx1 = w - MARGIN + round((bx1 - x1) * scale)
    ny1 = h - MARGIN + round((by1 - y1) * scale)
    nx0, ny0 = nx1 - size[0], ny1 - size[1]
    region = out[ny0:ny1, nx0:nx1]
    out[ny0:ny1, nx0:nx1] = region * (1 - pa) + patch * pa
    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(np.dstack([out, alpha])).save(path, quality=94, method=6)
    print(cid, f'mark {x1 - x0}x{y1 - y0} at right {w - x1}px, bottom {h - y1}px -> {MARGIN}px, {MARGIN}px, scale {scale:.3f}')
    return im[..., :3], out


def main():
    args = sys.argv[1:]
    preview = None
    if '--preview' in args:
        i = args.index('--preview')
        preview = args[i + 1]
        del args[i:i + 2]
    pairs = [align(cid) for cid in args]
    if preview:
        rows = [np.hstack([cv2.resize(a, (506, 319)), np.full((319, 10, 3), 128, np.uint8), cv2.resize(b, (506, 319))]) for a, b in pairs]
        Image.fromarray(np.vstack(rows)).save(preview)


main()
