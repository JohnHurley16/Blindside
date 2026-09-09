"""Tile shots into one contact sheet so a round of variants can be judged at once."""
import sys, os
from PIL import Image
out = sys.argv[1]; files = sys.argv[2:]
ims = [Image.open(f).convert('RGB') for f in files]
cols = 2 if len(ims) <= 4 else 3
rows = (len(ims) + cols - 1) // cols
w = 1400 // cols
th = [im.resize((w, int(w * im.height / im.width))) for im in ims]
h = max(i.height for i in th)
sheet = Image.new('RGB', (w * cols, h * rows), (0, 0, 0))
for i, im in enumerate(th):
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
print(out, sheet.size, [os.path.basename(f) for f in files])
