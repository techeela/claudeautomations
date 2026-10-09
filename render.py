"""Render LinkedIn stat cards (1080x1350 PNG) from JSON specs.

Usage: python render.py specs/2026-10-09-india-ott.json  -> cards/2026-10-09-india-ott.png

Spec format:
{
  "kicker": "INDIA OTT · 2026",
  "headline": ["The audience is here.", "The paying habit isn't."],
  "heroes": [
    {"value": "664.9M", "label": "people watch OTT (≈45% of India)", "bar": 1.0, "accent": false},
    {"value": "172.6M", "label": "active paid subscriptions", "bar": 0.26, "accent": true}
  ],
  "tiles": [{"big": "+60%", "line1": "Connected TV users", "line2": "206.9M"}],
  "source": "Ormax OTT Audience Report 2026"
}
heroes: 1-2 items; "bar" (0-1) optional. tiles: 0-3 items.
"""
import json, os, sys, glob
from PIL import Image, ImageDraw, ImageFont

W, H, M = 1080, 1350, 80
BG, FG, MUTED, ACC, ACC2, LINE, TILE = "#0E1116", "#F4F1EA", "#8A919C", "#FF6A3D", "#F7B32B", "#232833", "#171B22"
BYLINE = "Deepak Joshi  ·  in/deepakjoshi-ai"

FONT_DIRS = ["/usr/share/fonts/opentype/inter/", "/usr/share/fonts/truetype/inter/"]
FALLBACK = {"Bold": "DejaVuSans-Bold.ttf", "SemiBold": "DejaVuSans-Bold.ttf", "Medium": "DejaVuSans.ttf", "Regular": "DejaVuSans.ttf"}


def font(weight, size):
    for d in FONT_DIRS:
        for ext in ("otf", "ttf"):
            p = os.path.join(d, f"Inter-{weight}.{ext}")
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/" + FALLBACK[weight], size)


def fit(d, text, weight, size, max_w, min_size=18):
    while size > min_size and d.textlength(text, font=font(weight, size)) > max_w:
        size -= 2
    return font(weight, size)


def render(spec, out):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    inner = W - 2 * M

    d.text((M, 84), spec["kicker"], font=fit(d, spec["kicker"], "SemiBold", 28, inner), fill=ACC)
    h1, h2 = (spec["headline"] + [""])[:2]
    d.text((M, 130), h1, font=fit(d, h1, "Bold", 64, inner), fill=FG)
    if h2:
        d.text((M, 206), h2, font=fit(d, h2, "Bold", 64, inner), fill=MUTED)

    y = 330
    for hero in spec.get("heroes", [])[:2]:
        color = ACC if hero.get("accent") else FG
        d.text((M, y), hero["value"], font=fit(d, hero["value"], "Bold", 120, inner), fill=color)
        d.text((M, y + 140), hero["label"], font=fit(d, hero["label"], "Regular", 30, inner), fill=MUTED)
        if "bar" in hero:
            frac = max(0.04, min(1.0, float(hero["bar"])))
            d.rounded_rectangle((M, y + 192, W - M, y + 222), 15, fill=LINE)
            d.rounded_rectangle((M, y + 192, M + int(inner * frac), y + 222), 15, fill=color)
            y += 270
        else:
            y += 220

    tiles = spec.get("tiles", [])[:3]
    if tiles:
        ty, gap = 1010, 24
        tw = (inner - (len(tiles) - 1) * gap) // len(tiles)
        for i, t in enumerate(tiles):
            x = M + i * (tw + gap)
            d.rounded_rectangle((x, ty, x + tw, ty + 200), 18, fill=TILE, outline=LINE, width=2)
            d.text((x + 26, ty + 26), t["big"], font=fit(d, t["big"], "Bold", 54, tw - 52), fill=ACC2)
            d.text((x + 26, ty + 104), t.get("line1", ""), font=fit(d, t.get("line1", ""), "Medium", 24, tw - 52), fill=FG)
            d.text((x + 26, ty + 140), t.get("line2", ""), font=fit(d, t.get("line2", ""), "Regular", 24, tw - 52), fill=MUTED)

    d.line((M, 1262, W - M, 1262), fill=LINE, width=2)
    byf = font("SemiBold", 22)
    bw = d.textlength(BYLINE, font=byf)
    src = "Source: " + spec.get("source", "")
    d.text((M, 1280), src, font=fit(d, src, "Regular", 22, inner - bw - 30, 14), fill=MUTED)
    d.text((W - M - bw, 1280), BYLINE, font=byf, fill=FG)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    img.save(out, optimize=True)


if __name__ == "__main__":
    paths = sys.argv[1:] or glob.glob("specs/*.json")
    for p in paths:
        out = os.path.join("cards", os.path.splitext(os.path.basename(p))[0] + ".png")
        with open(p, encoding="utf-8") as f:
            render(json.load(f), out)
        print("rendered", out)
