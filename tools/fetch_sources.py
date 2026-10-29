"""Download each card's original issuer image (the `source` in cards.json) into a folder, for clean_art.py.

usage: py -3.12 -I tools/fetch_sources.py <raw dir>   (run from the repo root)
"""
import io, json, os, sys, urllib.request
from PIL import Image

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
for c in json.load(open('cards.json', encoding='utf-8'))['cards']:
    if not c['source'].startswith('https://'):
        continue   # drawn here, see make_bank_cards.py
    # `patch`: a smaller clean image of a card whose big image has a banner, used to fill the banner's place
    for url, name in ((c['source'], c['id']), (c.get('patch'), c['id'] + '.patch')):
        if not url:
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read())).convert('RGBA')
            im.save(f"{out}/{name}.png")
            print(name, im.size)
        except Exception as e:
            print('FAIL', name, e)
