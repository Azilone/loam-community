"""Draws assets/themes.svg (and themes-dark.svg) from themes.json: one card per theme, built from its own colours."""
import json, os, sys
root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..")
idx = json.load(open(os.path.join(root, "themes.json")))["themes"]
MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"

def card(theme, dark, x, y, w=268, h=176):
    c = dict(theme.get("colors", {}))
    if dark and theme.get("appearance") == "auto":
        c.update(theme.get("dark", {}).get("colors", {}))
    bg, side, text = c["background"], c.get("sidebar", c["background"]), c["text"]
    sec, acc = c.get("secondaryText", text), c["accent"]
    sep = c.get("separator", sec)
    head, tagt, tagb = c.get("heading", text), c.get("tagText", acc), c.get("tagBackground", sep)
    hl = c.get("highlight", sep)
    r = 2 if theme.get("shape", {}).get("corners") == "square" else 12
    sq = theme.get("tasks", {}).get("checkbox") == "square"
    box = lambda bx, by, done: (f'<rect x="{bx}" y="{by}" width="10" height="10" rx="{2.5 if sq else 5}" '
        + (f'fill="{acc}"/>' if done else f'fill="none" stroke="{c.get("checkboxBorder", sec)}" stroke-width="1.4"/>'))
    s = [f'<g transform="translate({x},{y})">',
         f'<rect width="{w}" height="{h}" rx="{r}" fill="{bg}" stroke="{sep}"/>',
         f'<path d="M{r} 0 H64 V{h} H{r} Q0 {h} 0 {h-r} V{r} Q0 0 {r} 0Z" fill="{side}"/>',
         f'<line x1="64" y1="0" x2="64" y2="{h}" stroke="{sep}"/>']
    for i, wd in enumerate((34, 26, 30, 22)):
        fill = acc if i == 0 else sec
        s.append(f'<rect x="12" y="{18 + i*16}" width="{wd}" height="5" rx="2.5" fill="{fill}" opacity="{1 if i == 0 else .45}"/>')
    s += [f'<rect x="84" y="20" width="110" height="10" rx="3" fill="{head}"/>',
          f'<line x1="84" y1="40" x2="{w-18}" y2="40" stroke="{sep}"/>',
          f'<rect x="84" y="52" width="150" height="5" rx="2.5" fill="{text}" opacity=".75"/>',
          f'<rect x="84" y="64" width="60" height="5" rx="2.5" fill="{text}" opacity=".75"/>',
          f'<rect x="148" y="62" width="56" height="9" rx="2" fill="{hl}"/>',
          f'<rect x="150" y="64" width="52" height="5" rx="2.5" fill="{c.get("highlightText", text)}" opacity=".75"/>',
          box(84, 84, True), f'<rect x="102" y="86.5" width="90" height="5" rx="2.5" fill="{sec}" opacity=".7"/>',
          box(84, 102, False), f'<rect x="102" y="104.5" width="110" height="5" rx="2.5" fill="{text}" opacity=".75"/>',
          f'<rect x="84" y="126" width="46" height="16" rx="{8 if theme.get("tags", {}).get("shape") == "capsule" else 4}" fill="{tagb}"/>',
          f'<rect x="92" y="131.5" width="30" height="5" rx="2.5" fill="{tagt}"/>',
          f'<circle cx="{w-24}" cy="{h-22}" r="8" fill="{acc}"/>',
          '</g>']
    return "\n".join(s)

def sheet(dark):
    ink, paper = ("#F5F4EF", "#0E0E10") if dark else ("#0E0E10", "#F5F4EF")
    cols, w, h, gap = 2, 268, 176, 24
    rows = (len(idx) + cols - 1) // cols
    W, H = cols * w + (cols - 1) * gap, rows * (h + 40) - 8
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 {W+2} {H+2}" width="{W+2}" height="{H+2}">']
    for i, e in enumerate(idx):
        t = json.load(open(os.path.join(root, "themes", e["id"] + ".json")))
        x, y = (i % cols) * (w + gap), (i // cols) * (h + 40)
        out.append(card(t, dark or t.get("appearance") == "dark", x, y))
        out.append(f'<text x="{x+2}" y="{y+h+22}" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{ink}">'
                   f'{e["name"].upper()}</text>')
        out.append(f'<text x="{x+w-2}" y="{y+h+22}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{ink}" '
                   f'opacity=".55">{e["id"]}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"

open(os.path.join(root, "assets/themes.svg"), "w").write(sheet(False))
open(os.path.join(root, "assets/themes-dark.svg"), "w").write(sheet(True))
