# card-art

Card images for [Finance Desk](https://github.com/rainbowblood022-droid), served raw from this repo:

```
https://raw.githubusercontent.com/rainbowblood022-droid/card-art/main/cards/<id>.webp
```

`cards.json` lists every card: `id`, `name`, `issuer`, `image` (path in this repo) and `source` (the issuer's original
image, or `original` for art drawn here).

Every image is the same: 640×404 WebP (the 1.586 shape of a real card), transparent rounded corners, and no promo
banners ("No annual fee", "New offer") or sample cardholder names and numbers.

## Rebuilding

```
py -3.12 -I tools/fetch_sources.py raw          # issuer originals
py -3.12 -I tools/clean_art.py raw clean        # crop, remove banners and names, round corners (PNG + review sheet)
py -3.12 -I tools/make_bank_cards.py            # original art for debit and credit-union cards
```

`clean_art.py` writes PNGs; convert them to WebP into `cards/` (quality 90).

## Adding a card

1. Add an entry to `cards.json` with the issuer's image URL as `source` (or draw it in `make_bank_cards.py`).
2. Rebuild, check the review sheet, commit.
3. In Finance Desk, add a matching entry to `src/data/cardCatalog.ts`.

Card designs and logos are trademarks of their issuers. These images are here only to show each card in a personal
finance app.
