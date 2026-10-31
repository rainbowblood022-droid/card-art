"""Build cards/<id>.webp from a card image supplied by the owner (a full card on a white background).

The card is cropped out, the white around its rounded corners made see-through, and it is sized to 1012x638 like
every other card. Nothing on the card itself is changed.

usage: py -3.12 -I tools/from_image.py <image> <id>   (run from the repo root)
"""
import sys
import cv2
import numpy as np
from PIL import Image

W, H = 1012, 638


def main():
    path, cid = sys.argv[1:]
    rgb = np.array(Image.open(path).convert('RGB'))
    white = (rgb.min(axis=2) > 235).astype(np.uint8)
    # the card's edges: the rows and columns that aren't all background
    rows = np.where(~white.all(axis=1))[0]
    cols = np.where(~white.all(axis=0))[0]
    rgb = rgb[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    white = white[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    h, w = white.shape
    # background = the white reachable from the four corners (white text and logos on the card stay)
    bg = np.zeros((h + 2, w + 2), np.uint8)
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if white[y, x] and not bg[y + 1, x + 1]:
            cv2.floodFill(white.copy(), bg, (x, y), 1, flags=4 | (1 << 8))
    bg = bg[1:-1, 1:-1]
    # grown 2 px so the light edge the corners fade into doesn't show as a halo, then softened
    bg = cv2.dilate(bg, np.ones((5, 5), np.uint8))
    alpha = cv2.GaussianBlur((1 - bg).astype(np.float32) * 255, (3, 3), 0).astype(np.uint8)
    rgb = cv2.resize(rgb, (W, H), interpolation=cv2.INTER_AREA)
    alpha = cv2.resize(alpha, (W, H), interpolation=cv2.INTER_AREA)
    Image.fromarray(np.dstack([rgb, alpha])).save(f'cards/{cid}.webp', quality=94, method=6)
    print(cid, f'{w}x{h} ->', f'{W}x{H}')


main()
