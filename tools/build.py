"""Build cards/<id>.webp from each issuer's own image, as faithful to it as possible.

Each image is cropped to exactly the card (its own rounded corners kept), enlarged 4x with EDSR super-resolution and
sized to 1012x638. Nothing on the card is changed, except a promo banner ("No annual fee", "New offer") on the few
cards the issuer publishes no clean image of.

usage: py -3.12 -I tools/build.py <raw dir> <EDSR_x4.pb> [id ...]   (run from the repo root; raw from fetch_sources.py)
"""
import json, os, sys
import cv2
import numpy as np
from PIL import Image

W, H = 1012, 638   # a real card (85.6 x 54 mm) at 300 dpi

# cards whose only published image has a promo banner: the corner it's in and its color (BGR)
BANNER = {
    'chase-freedom-unlimited': ('tr', (80, 220, 180)),
    'chase-freedom-rise': ('tr', (80, 220, 180)),
}
# parts of the card right next to a banner, kept out of its cleanup: (x0, y0, x1, y1) as fractions of the card
KEEP = {'chase-freedom-unlimited': [(0.82, 0.38, 0.93, 0.55)]}
# the banner's faint shadow and tip that its color doesn't catch
EXTRA = {'chase-freedom-unlimited': [(0.87, 0.24, 1.0, 0.42), (0.45, 0.0, 1.0, 0.025)]}


def banner_mask(bgr, corner, color, grow):
    """The banner: the largest patch of its color in its corner, filled in (its text too) and grown over its shadow."""
    h, w = bgr.shape[:2]
    region = np.zeros((h, w), np.uint8)
    if corner == 'tr':
        region[: int(h * 0.6), int(w * 0.45):] = 1
    else:
        region[: int(h * 0.4), : int(w * 0.4)] = 1
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.int32)
    ref = cv2.cvtColor(np.uint8([[color]]), cv2.COLOR_BGR2LAB)[0, 0].astype(np.int32)
    near = (np.sqrt(((lab - ref) ** 2).sum(axis=2)) < 48).astype(np.uint8) * region
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(near)
    m = np.zeros((h, w), np.uint8)
    if n > 1:
        big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        if corner == 'tl':
            # a flat tag: its whole box, so no edge of it is left behind
            x, y, bw, bh = stats[big, :4]
            m[y:y + bh, x:x + bw] = 255
        else:
            cv2.fillConvexPoly(m, cv2.convexHull(cv2.findNonZero((lbl == big).astype(np.uint8))), 255)
    return cv2.dilate(m, np.ones((grow, grow), np.uint8))


def card_box(rgba, cid):
    """Exactly the card's edges. A banner that sticks out past a corner is left out by measuring each edge on the
    side away from it."""
    a = rgba[:, :, 3] > 40
    h, w = a.shape
    if cid in BANNER and BANNER[cid][0] == 'tr':
        cols_l = a[:, : int(w * 0.4)]
        rows_b = a[int(h * 0.5):, :]
        top = np.where(cols_l.any(axis=1))[0][0]
        bottom = np.where(a.any(axis=1))[0][-1] + 1
        left = np.where(a.any(axis=0))[0][0]
        right = np.where(rows_b.any(axis=0))[0][-1] + 1
        return left, top, right, bottom
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def build(cid, path, sr):
    rgba = np.array(Image.open(path).convert('RGBA'))
    x0, y0, x1, y1 = card_box(rgba, cid)
    rgba = rgba[y0:y1, x0:x1]
    bgr = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)
    a = rgba[:, :, 3]
    # see-through pixels carry junk color: give them the nearby card color so edges don't halo when enlarged
    if (a < 128).any():
        bgr = cv2.inpaint(bgr, (a < 128).astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
    big = cv2.resize(sr.upsample(bgr), (W, H), interpolation=cv2.INTER_AREA)
    alpha = cv2.resize(a, (W, H), interpolation=cv2.INTER_LANCZOS4)
    if cid in BANNER:
        corner, color = BANNER[cid]
        m = banner_mask(big, corner, color, 61 if corner == 'tr' else 15)
        # a mark the banner touches (the contactless symbol): lifted out, the area filled, then put back exactly
        keep = np.zeros((H, W), np.float32)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        for x0, y0, x1, y1 in KEEP.get(cid, []):
            sl = (slice(int(y0 * H), int(y1 * H)), slice(int(x0 * W), int(x1 * W)))
            keep[sl] = (gray[sl] > 150).astype(np.float32)
        keep = cv2.GaussianBlur(cv2.dilate(keep, np.ones((3, 3), np.uint8)), (3, 3), 0)[..., None]
        for x0, y0, x1, y1 in EXTRA.get(cid, []):
            m[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = 255
        m |= (keep[..., 0] > 0).astype(np.uint8) * 255
        original = big.copy()
        patch = os.path.join(os.path.dirname(path), cid + '.patch.png')
        if os.path.exists(patch):
            # the issuer's own clean (smaller) image of this card fills the banner's place
            clean = build(cid + '.patch', patch, sr)
            soft = cv2.GaussianBlur(m.astype(np.float32) / 255, (31, 31), 0)[..., None]
            big = (big * (1 - soft) + cv2.cvtColor(clean[:, :, :3], cv2.COLOR_RGB2BGR) * soft).astype(np.uint8)
        else:
            big = cv2.inpaint(big, cv2.dilate(m, np.ones((5, 5), np.uint8)), 15, cv2.INPAINT_TELEA)
        big = (big * (1 - keep) + original * keep).astype(np.uint8)
        if corner == 'tr':
            # the banner covered this corner's rounding: use the card's own top-left corner, mirrored
            c = int(W * 0.08)
            alpha[:c, W - c:] = alpha[:c, :c][:, ::-1]
    return np.dstack([cv2.cvtColor(big, cv2.COLOR_BGR2RGB), alpha])


def main():
    raw, model, *only = sys.argv[1:]
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(model)
    sr.setModel('edsr', 4)
    for c in json.load(open('cards.json', encoding='utf-8'))['cards']:
        if c['source'] == 'original' or (only and c['id'] not in only):
            continue
        Image.fromarray(build(c['id'], os.path.join(raw, c['id'] + '.png'), sr)).save(f"cards/{c['id']}.webp", quality=94, method=6)
        print(c['id'], flush=True)


main()
