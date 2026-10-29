# card-art

Card images for [Finance Desk](https://github.com/rainbowblood022-droid), served raw from this repo:

```
https://raw.githubusercontent.com/rainbowblood022-droid/card-art/main/cards/<id>.webp
```

`cards.json` lists every card: `id`, `name`, `issuer`, `image` (path in this repo) and `source` (the issuer's original
image, or `original` for art drawn here).

Every image is the same: 1012×638 WebP (a real 85.6×54 mm card at 300 dpi), transparent rounded corners, and no promo
banners ("No annual fee", "New offer") or sample cardholder names and numbers.

Issuers only publish small images (about 250–480 px wide), so each one is enlarged 4× with EDSR super-resolution
before cleaning, which keeps logos and edges sharp instead of blurry. Cards drawn here (`source: original`) are made at
full size.

## Rebuilding

```
py -3.12 -I tools/fetch_sources.py raw          # issuer originals
py -3.12 -I tools/upscale.py raw raw4x EDSR_x4.pb   # 4x super-resolution (model: Saafke/EDSR_Tensorflow, EDSR_x4.pb)
py -3.12 -I tools/clean_art.py raw4x clean      # crop, remove banners and names, round corners (PNG + review sheet)
py -3.12 -I tools/make_bank_cards.py            # original art for debit and credit-union cards
```

`clean_art.py` writes PNGs; convert them to WebP into `cards/` (quality 92). Needs `opencv-contrib-python-headless`.

## Adding a card

1. Add an entry to `cards.json` with the issuer's image URL as `source` (or draw it in `make_bank_cards.py`).
2. Rebuild, check the review sheet, commit.
3. In Finance Desk, add a matching entry to `src/data/cardCatalog.ts`.

Card designs and logos are trademarks of their issuers. These images are here only to show each card in a personal
finance app.
