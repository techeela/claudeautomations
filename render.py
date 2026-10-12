"""Render LinkedIn cards (1080x1350 PNG) from JSON specs.

Usage: python render.py specs/2026-10-12-india-ctv.json  -> cards/2026-10-12-india-ctv.png

Every spec has: "kicker", "headline" (1-2 lines, <= 28 chars each), "source".
Optional: "layout" (default "stats"), "theme" ("dark" default, "light", "ink").

layout "stats" (original):
  "heroes": [{"value": "664.9M", "label": "...", "bar": 0.26, "accent": true}]  (1-2)
  "tiles":  [{"big": "+60%", "line1": "...", "line2": "..."}]                     (0-3)

layout "timeline":  how a story unfolded
  "events": [{"when": "Nov 2025", "text": "<= 70 chars", "accent": false}]       (3-5)
  "note": "optional one-line status, <= 60 chars"

layout "quote":  one line someone said or a ruling/rule, verbatim from the source
  "quote": "<= 160 chars", "by": "Name, role", "stat": {"value": "...", "label": "..."} (optional)

layout "ranking":  a top-N list with proportional bars
  "rows": [{"label": "<= 30 chars", "value": "17.5M", "bar": 0.0-1.0, "accent": false}]  (3-6)
  "unit": "optional caption above the list"

layout "split":  then vs now, or A vs B
  "left":  {"tag": "2025", "value": "129.2M", "label": "..."}
  "right": {"tag": "2026", "value": "206.9M", "label": "...", "accent": true}
  "delta": "optional, e.g. +60%"
"""
import json, os, sys, glob, textwrap
from PIL import Image, ImageDraw, ImageFont

W, H, M = 1080, 1350, 80
THEMES = {
    "dark":  dict(BG="#0E1116", FG="#F4F1EA", MUTED="#8A919C", ACC="#FF6A3D", ACC2="#F7B32B", LINE="#232833", TILE="#171B22"),
    "light": dict(BG="#F6F3EC", FG="#14171C", MUTED="#5E6570", ACC="#E0451B", ACC2="#B7790B", LINE="#DDD7CB", TILE="#FFFFFF"),
    "ink":   dict(BG="#0B1F3A", FG="#F2F5FA", MUTED="#9FB0C8", ACC="#36C5A3", ACC2="#FFC857", LINE="#1C3457", TILE="#12294A"),
}
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


def wrap(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def header(d, spec, c, inner):
    d.text((M, 84), spec["kicker"], font=fit(d, spec["kicker"], "SemiBold", 28, inner), fill=c["ACC"])
    h1, h2 = (spec["headline"] + [""])[:2]
    d.text((M, 130), h1, font=fit(d, h1, "Bold", 64, inner), fill=c["FG"])
    if h2:
        d.text((M, 206), h2, font=fit(d, h2, "Bold", 64, inner), fill=c["MUTED"])


def body_stats(d, spec, c, inner):
    y = 330
    for hero in spec.get("heroes", [])[:2]:
        color = c["ACC"] if hero.get("accent") else c["FG"]
        d.text((M, y), hero["value"], font=fit(d, hero["value"], "Bold", 120, inner), fill=color)
        d.text((M, y + 140), hero["label"], font=fit(d, hero["label"], "Regular", 30, inner), fill=c["MUTED"])
        if "bar" in hero:
            frac = max(0.04, min(1.0, float(hero["bar"])))
            d.rounded_rectangle((M, y + 192, W - M, y + 222), 15, fill=c["LINE"])
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
            d.rounded_rectangle((x, ty, x + tw, ty + 200), 18, fill=c["TILE"], outline=c["LINE"], width=2)
            d.text((x + 26, ty + 26), t["big"], font=fit(d, t["big"], "Bold", 54, tw - 52), fill=c["ACC2"])
            d.text((x + 26, ty + 104), t.get("line1", ""), font=fit(d, t.get("line1", ""), "Medium", 24, tw - 52), fill=c["FG"])
            d.text((x + 26, ty + 140), t.get("line2", ""), font=fit(d, t.get("line2", ""), "Regular", 24, tw - 52), fill=c["MUTED"])


def body_timeline(d, spec, c, inner):
    events = spec.get("events", [])[:5]
    top, bottom = 340, 1100 if spec.get("note") else 1220
    step = (bottom - top) // max(1, len(events))
    x_dot, x_txt = M + 14, M + 70
    d.line((x_dot, top + 20, x_dot, top + step * (len(events) - 1) + 20), fill=c["LINE"], width=4)
    tf = font("Medium", 32)
    for i, e in enumerate(events):
        y = top + i * step
        col = c["ACC"] if e.get("accent") else c["FG"]
        r = 14 if e.get("accent") else 11
        d.ellipse((x_dot - r, y + 20 - r, x_dot + r, y + 20 + r), fill=col)
        d.text((x_txt, y), e["when"].upper(), font=font("SemiBold", 26), fill=c["ACC2"] if not e.get("accent") else c["ACC"])
        for j, line in enumerate(wrap(d, e["text"], tf, W - M - x_txt)[:2]):
            d.text((x_txt, y + 42 + j * 42), line, font=tf, fill=col if e.get("accent") else c["FG"])
    if spec.get("note"):
        d.rounded_rectangle((M, 1130, W - M, 1220), 18, fill=c["TILE"], outline=c["LINE"], width=2)
        n = spec["note"]
        d.text((M + 30, 1158), n, font=fit(d, n, "Medium", 30, inner - 60), fill=c["FG"])


def body_quote(d, spec, c, inner):
    q = spec["quote"]
    size = 60
    while size > 36:
        f = font("Bold", size)
        lines = wrap(d, q, f, inner)
        if len(lines) * size * 1.25 <= 560:
            break
        size -= 4
    d.text((M - 6, 300), "“", font=font("Bold", 160), fill=c["ACC"])
    y = 440
    for line in lines:
        d.text((M, y), line, font=f, fill=c["FG"])
        y += int(size * 1.25)
    d.text((M, y + 24), "— " + spec.get("by", ""), font=fit(d, "— " + spec.get("by", ""), "Medium", 30, inner), fill=c["MUTED"])
    st = spec.get("stat")
    if st:
        d.rounded_rectangle((M, 1060, W - M, 1220), 18, fill=c["TILE"], outline=c["LINE"], width=2)
        vf = fit(d, st["value"], "Bold", 72, 360)
        d.text((M + 30, 1090), st["value"], font=vf, fill=c["ACC2"])
        vw = d.textlength(st["value"], font=vf)
        lab = wrap(d, st["label"], font("Regular", 28), inner - vw - 100)[:2]
        for j, line in enumerate(lab):
            d.text((M + 70 + vw, 1100 + j * 38), line, font=font("Regular", 28), fill=c["MUTED"])


def body_ranking(d, spec, c, inner):
    rows = spec.get("rows", [])[:6]
    y = 330
    if spec.get("unit"):
        d.text((M, y), spec["unit"], font=fit(d, spec["unit"], "Medium", 28, inner), fill=c["MUTED"])
        y += 60
    step = (1220 - y) // max(1, len(rows))
    step = min(step, 150)
    for i, r in enumerate(rows):
        col = c["ACC"] if r.get("accent") else c["FG"]
        d.text((M, y), f"{i + 1:>2}", font=font("Bold", 30), fill=c["MUTED"])
        lf = fit(d, r["label"], "Medium", 32, inner - 300)
        d.text((M + 60, y), r["label"], font=lf, fill=col)
        vf = font("Bold", 36)
        d.text((W - M - d.textlength(r["value"], font=vf), y - 4), r["value"], font=vf, fill=col)
        frac = max(0.03, min(1.0, float(r.get("bar", 0))))
        d.rounded_rectangle((M + 60, y + 54, W - M, y + 72), 9, fill=c["LINE"])
        d.rounded_rectangle((M + 60, y + 54, M + 60 + int((inner - 60) * frac), y + 72), 9, fill=c["ACC"] if r.get("accent") else c["ACC2"])
        y += step


def body_split(d, spec, c, inner):
    gap = 40
    cw = (inner - gap) // 2
    for i, side in enumerate([spec["left"], spec["right"]]):
        x = M + i * (cw + gap)
        col = c["ACC"] if side.get("accent") else c["FG"]
        d.rounded_rectangle((x, 340, x + cw, 960), 24, fill=c["TILE"], outline=c["ACC"] if side.get("accent") else c["LINE"], width=3)
        d.text((x + 36, 380), side.get("tag", "").upper(), font=font("SemiBold", 30), fill=c["MUTED"])
        vf = fit(d, side["value"], "Bold", 110, cw - 72)
        d.text((x + 36, 520), side["value"], font=vf, fill=col)
        for j, line in enumerate(wrap(d, side.get("label", ""), font("Regular", 30), cw - 72)[:4]):
            d.text((x + 36, 700 + j * 42), line, font=font("Regular", 30), fill=c["MUTED"])
    if spec.get("delta"):
        dt = spec["delta"]
        df = font("Bold", 96)
        tw = d.textlength(dt, font=df)
        d.text(((W - tw) / 2, 1030), dt, font=df, fill=c["ACC2"])


BODIES = {"stats": body_stats, "timeline": body_timeline, "quote": body_quote, "ranking": body_ranking, "split": body_split}


def render(spec, out):
    c = THEMES.get(spec.get("theme", "dark"), THEMES["dark"])
    img = Image.new("RGB", (W, H), c["BG"])
    d = ImageDraw.Draw(img)
    inner = W - 2 * M
    header(d, spec, c, inner)
    BODIES.get(spec.get("layout", "stats"), body_stats)(d, spec, c, inner)

    d.line((M, 1262, W - M, 1262), fill=c["LINE"], width=2)
    byf = font("SemiBold", 22)
    bw = d.textlength(BYLINE, font=byf)
    src = "Source: " + spec.get("source", "")
    d.text((M, 1280), src, font=fit(d, src, "Regular", 22, inner - bw - 30, 14), fill=c["MUTED"])
    d.text((W - M - bw, 1280), BYLINE, font=byf, fill=c["FG"])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    img.save(out, optimize=True)


if __name__ == "__main__":
    paths = sys.argv[1:] or glob.glob("specs/*.json")
    for p in paths:
        out = os.path.join("cards", os.path.splitext(os.path.basename(p))[0] + ".png")
        with open(p, encoding="utf-8") as f:
            render(json.load(f), out)
        print("rendered", out)
