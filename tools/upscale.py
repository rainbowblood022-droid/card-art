"""Enlarge each issuer image 4x with EDSR super-resolution (color) and Lanczos (transparency).

usage: py -3.12 -I upscale.py <raw dir> <out dir> <EDSR_x4.pb>
"""
import os, sys, time
import cv2
import numpy as np

src, out, model = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(model)
sr.setModel('edsr', 4)
for f in sorted(os.listdir(src)):
    if not f.endswith('.png') or f.startswith('_') or os.path.exists(os.path.join(out, f)):
        continue
    t = time.time()
    im = cv2.imread(os.path.join(src, f), cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    bgr, a = im[:, :, :3], im[:, :, 3]
    # see-through pixels carry junk color: give them the nearby card color so edges don't halo
    bgr = cv2.inpaint(bgr, (a < 128).astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA) if (a < 128).any() else bgr
    big = sr.upsample(bgr)
    alpha = cv2.resize(a, (big.shape[1], big.shape[0]), interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(os.path.join(out, f), np.dstack([big, alpha]))
    print(f, im.shape[1], '->', big.shape[1], f'{time.time() - t:.0f}s', flush=True)
