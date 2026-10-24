"""Render LinkedIn cards (1080x1350 PNG) from JSON specs.

Usage: python render.py specs/2026-10-12-india-ctv.json  -> cards/2026-10-12-india-ctv.png

Every spec has: "kicker", "headline" (1-2 lines, <= 28 chars each), "source".
Optional: "layout" (default "stats"), "theme".

Themes
  Classic (flat):  "dark" (default), "light", "ink"
  Bold news style (colourful gradient background, yellow top banner, highlighted headline,
  inspired by Instagram news cards):  "pop" (purple->pink), "ocean" (navy->teal),
  "sunset" (crimson->orange), "forest" (deep green->emerald).
  In the bold themes:
    - "kicker" becomes the yellow banner text, so keep it short and punchy (<= 22 chars),
      e.g. "OTT NUMBERS!", "LATEST NEWS!", "BOX OFFICE WEEK"
    - wrap words in *asterisks* in a headline line to highlight them in yellow,
      e.g. ["One ₹200 top-up", "now carries *22+ OTT apps*"]
    - optional "tag": short label chip above the headline (default "HEADLINE:")

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
import json, os, sys, glob, re
from PIL import Image, ImageDraw, ImageFont

W, H, M = 1080, 1350, 80
THEMES = {
    "dark":  dict(BG="#0E1116", FG="#F4F1EA", MUTED="#8A919C", ACC="#FF6A3D", ACC2="#F7B32B", LINE="#232833", TILE="#171B22"),
    "light": dict(BG="#F6F3EC", FG="#14171C", MUTED="#5E6570", ACC="#E0451B", ACC2="#B7790B", LINE="#DDD7CB", TILE="#FFFFFF"),
    "ink":   dict(BG="#0B1F3A", FG="#F2F5FA", MUTED="#9FB0C8", ACC="#36C5A3", ACC2="#FFC857", LINE="#1C3457", TILE="#12294A"),
    # bold news-style themes: gradient G1 (top-left) -> G2 (bottom-right)
    "pop":    dict(G1="#2B0A5E", G2="#C2185B", FG="#FFFFFF", MUTED="#F3D9F0", ACC="#FFE600", ACC2="#00E5FF", LINE="#5A2A7A", TILE="#1E0840", BOLD=True),
    "ocean":  dict(G1="#061A40", G2="#0E8C8C", FG="#FFFFFF", MUTED="#CDE9F2", ACC="#FFE600", ACC2="#FF7AB6", LINE="#1F4E6E", TILE="#04142F", BOLD=True),
    "sunset": dict(G1="#5C0A14", G2="#F26419", FG="#FFFFFF", MUTED="#FFE3CF", ACC="#FFE600", ACC2="#7CF5FF", LINE="#8A2A1E", TILE="#3A060C", BOLD=True),
    "forest": dict(G1="#03241A", G2="#14A06A", FG="#FFFFFF", MUTED="#D3F5E4", ACC="#FFE600", ACC2="#FF8A5B", LINE="#1D5A43", TILE="#021A12", BOLD=True),
}
BANNER = "#FFE600"
BYLINE = "Deepak Joshi  ·  in/deepakjoshi-ai"

FONT_DIRS = ["/usr/share/fonts/opentype/inter/", "/usr/share/fonts/truetype/inter/"]
FALLBACK = {"Black": "DejaVuSans-Bold.ttf", "ExtraBold": "DejaVuSans-Bold.ttf", "Bold": "DejaVuSans-Bold.ttf",
            "SemiBold": "DejaVuSans-Bold.ttf", "Medium": "DejaVuSans.ttf", "Regular": "DejaVuSans.ttf"}


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


def plain(text):
    return text.replace("*", "")


def rich(d, xy, text, f, base, hl):
    """Draw text where *segments* are highlighted."""
    x, y = xy
    for i, part in enumerate(re.split(r"\*", text)):
        if not part:
            continue
        d.text((x, y), part, font=f, fill=hl if i % 2 else base)
        x += d.textlength(part, font=f)


def header(d, spec, c, inner):
    d.text((M, 84), spec["kicker"], font=fit(d, spec["kicker"], "SemiBold", 28, inner), fill=c["ACC"])
    h1, h2 = ([plain(h) for h in spec["headline"]] + [""])[:2]
    d.text((M, 130), h1, font=fit(d, h1, "Bold", 64, inner), fill=c["FG"])
    if h2:
        d.text((M, 206), h2, font=fit(d, h2, "Bold", 64, inner), fill=c["MUTED"])


def gradient(c):
    a = tuple(int(c["G1"][i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c["G2"][i:i + 2], 16) for i in (1, 3, 5))
    small = Image.new("RGB", (64, 80))
    px = small.load()
    for yy in range(80):
        for xx in range(64):
            t = min(1.0, (xx / 63 * 0.45 + yy / 79 * 0.75) / 1.2)
            px[xx, yy] = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
    return small.resize((W, H), Image.BICUBIC)


def decorate(img, c):
    """Soft glow circles and a dotted grid for depth."""
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = ImageDraw.Draw(over)
    o.ellipse((W - 380, 140, W + 220, 740), fill=(255, 255, 255, 18))
    o.ellipse((-260, 900, 340, 1500), fill=(255, 230, 0, 16))
    for gx in range(W - 250, W - 60, 28):
        for gy in range(150, 300, 28):
            o.ellipse((gx, gy, gx + 5, gy + 5), fill=(255, 255, 255, 60))
    img.paste(Image.alpha_composite(img.convert("RGBA"), over).convert("RGB"))


def header_bold(d, spec, c, inner):
    # yellow banner
    d.rectangle((0, 0, W, 112), fill=BANNER)
    k = spec["kicker"].upper()
    kf = fit(d, k, "Black", 66, W - 2 * M)
    kw = d.textlength(k, font=kf)
    d.text(((W - kw) / 2, 56), k, font=kf, fill="#111111", anchor="lm")
    d.rectangle((0, 112, W, 120), fill="#111111")
    # tag chip
    tag = spec.get("tag", "HEADLINE:")
    tf = font("Black", 30)
    tw = d.textlength(tag, font=tf)
    d.rectangle((M, 138, M + tw + 32, 182), fill=BANNER)
    d.text((M + 16, 160), tag, font=tf, fill="#111111", anchor="lm")
    d.line((M + tw + 48, 160, W - M, 160), fill="#FFFFFF", width=4)
    # headline with highlights
    lines = spec["headline"][:2]
    size = 56
    while size > 36 and any(d.textlength(plain(l), font=font("ExtraBold", size)) > inner for l in lines):
        size -= 2
    hf = font("ExtraBold", size)
    for i, l in enumerate(lines):
        rich(d, (M, 192 + i * (size + 10)), l, hf, c["FG"], c["ACC"])


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
    bold = c.get("BOLD", False)
    if bold:
        img = gradient(c)
        decorate(img, c)
    else:
        img = Image.new("RGB", (W, H), c["BG"])
    d = ImageDraw.Draw(img)
    inner = W - 2 * M
    (header_bold if bold else header)(d, spec, c, inner)
    BODIES.get(spec.get("layout", "stats"), body_stats)(d, spec, c, inner)

    if bold:
        d.rectangle((0, 1250, W, H), fill="#111111")
        d.rectangle((0, 1250, W, 1256), fill=BANNER)
    else:
        d.line((M, 1262, W - M, 1262), fill=c["LINE"], width=2)
    byf = font("SemiBold", 22)
    bw = d.textlength(BYLINE, font=byf)
    src = "Source: " + spec.get("source", "")
    d.text((M, 1290 if bold else 1280), src, font=fit(d, src, "Regular", 22, inner - bw - 30, 14), fill="#D0D0D0" if bold else c["MUTED"])
    d.text((W - M - bw, 1290 if bold else 1280), BYLINE, font=byf, fill=BANNER if bold else c["FG"])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    img.save(out, optimize=True)


if __name__ == "__main__":
    paths = sys.argv[1:] or glob.glob("specs/*.json")
    for p in paths:
        out = os.path.join("cards", os.path.splitext(os.path.basename(p))[0] + ".png")
        with open(p, encoding="utf-8") as f:
            render(json.load(f), out)
        print("rendered", out)
