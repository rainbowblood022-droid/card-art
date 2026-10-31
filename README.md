# card-art

Card images for [Finance Desk](https://github.com/rainbowblood022-droid), served raw from this repo:

```
https://raw.githubusercontent.com/rainbowblood022-droid/card-art/main/cards/<id>.webp
```

`cards.json` lists every card: `id`, `name`, `issuer`, `image` (path in this repo) and `source` (the issuer's original
image, `supplied` for an image the owner provided, kept in `supplied/`, or `original` for art drawn here).

Every image is the issuer's own published card image, as is: the full card with its own rounded corners, sample name
and numbers, sized to 1012×638 WebP (a real 85.6×54 mm card at 300 dpi). Issuers only publish small images (about
170–490 px wide), so each one is enlarged 4× with EDSR super-resolution, which keeps logos and edges sharp instead of
blurry.

Where an issuer publishes a version without a promo banner, that's the source. **Chase Freedom Rise** has none: it's
the larger image with the banner, with the banner's corner filled from Chase's smaller clean image of the same card
(`patch` in `cards.json`).

Supplied cards (`source: supplied`): high-resolution images the owner provided, for cards with no clean issuer image or
none at all: Chase Freedom Unlimited, and the Popular, PenFed and PNC Virtual Wallet debit cards. They're only cropped,
given see-through corners and sized to 1012×638.

Cards drawn here (`source: original`) are a fallback for debit cards with no image yet, made at full size.

## Rebuilding

```
py -3.12 -I tools/fetch_sources.py raw                 # issuer originals (and patches)
py -3.12 -I tools/build.py raw EDSR_x4.pb [id ...]     # crop, enlarge, size to 1012x638, write cards/<id>.webp
py -3.12 -I tools/from_image.py supplied/<id>.png <id> # a supplied image: crop, see-through corners, 1012x638
py -3.12 -I tools/align_mark.py <id> [<id> ...]       # then: its VISA/DEBIT mark at the standard place (60 px in, 22.5% wide)
py -3.12 -I tools/make_bank_cards.py                   # drawn art for debit cards with no image (skips supplied)
```

`build.py` needs `opencv-contrib-python-headless` and the EDSR x4 model (`EDSR_x4.pb` from Saafke/EDSR_Tensorflow).

## Adding a card

1. Add an entry to `cards.json` with the issuer's image URL as `source`, or put a full-card image (white background)
   in `supplied/<id>.png` with `source: supplied` and run `from_image.py`, or draw it in `make_bank_cards.py`.
2. Rebuild, check the review sheet, commit.
3. In Finance Desk, add a matching entry to `src/data/cardCatalog.ts`.

Card designs and logos are trademarks of their issuers. These images are here only to show each card in a personal
finance app.
