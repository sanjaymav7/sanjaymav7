"""Draws skills-{light,dark}.svg (coloured skill chips) and divider-{light,dark}.svg (section divider).

    python3 make_chips.py
"""
GROUPS = [
    ("languages", "blue", ["Python", "C++", "Java"]),
    ("ML & data", "purple", ["Machine Learning", "NumPy", "SciPy", "scikit-learn", "pandas"]),
    ("web", "green", ["Node", "Django", "React", "Vite"]),
    ("tools", "orange", ["Git", "GitHub"]),
]
THEMES = {
    "light": dict(label="#59636e", blue="#0969da", purple="#8250df", green="#1a7f37", orange="#bc4c00",
                  red="#cf222e", text_op=1.0, fill_op=0.10, rule_edge="#0b1020", rule_mid="#1e3a8a"),
    "dark": dict(label="#9198a1", blue="#58a6ff", purple="#d2a8ff", green="#3fb950", orange="#ffa657",
                 red="#ff7b72", text_op=1.0, fill_op=0.14, rule_edge="#0e1d45", rule_mid="#3b6fe8"),
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
W, CHIP_H, GAP, ROW_H = 806, 24, 7, 34


def text_w(s, size=12.5):
    # rough advance widths for the system UI font, good enough to size a pill
    narrow, wide = set("iljtfr.,'I1 "), set("mwMW")
    return sum(size * (0.32 if c in narrow else 0.86 if c in wide else 0.58) for c in s)


for name, t in THEMES.items():
    parts, x, y = [], 0.0, 4.0
    for label, colour, items in GROUPS:
        lw = text_w(label.upper(), 10.5) + 0.8 * len(label) + 12   # caps plus letter-spacing
        need = lw + sum(text_w(i) + 22 + GAP for i in items)
        if x > 0 and x + need > W:
            x, y = 0.0, y + ROW_H
        c = t[colour]
        parts.append(f'<text x="{x:.1f}" y="{y + 16:.1f}" font-size="10" font-weight="600" letter-spacing="0.8" '
                     f'fill="{t["label"]}">{label.upper().replace("&", "&amp;")}</text>')
        x += lw
        for item in items:
            w = text_w(item) + 22
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{CHIP_H}" rx="12" fill="{c}" '
                         f'fill-opacity="{t["fill_op"]}" stroke="{c}" stroke-opacity="0.55"/>'
                         f'<text x="{x + w / 2:.1f}" y="{y + 16.2:.1f}" font-size="12.5" font-weight="600" '
                         f'text-anchor="middle" fill="{c}">{item.replace("&", "&amp;")}</text>')
            x += w + GAP
        x += 14
    h = y + CHIP_H + 4
    open(f"skills-{name}.svg", "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h:.0f}" viewBox="0 0 {W} {h:.0f}">'
        f'<g font-family="{FONT}">{"".join(parts)}</g></svg>\n')

    open(f"divider-{name}.svg", "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="14" viewBox="0 0 {W} 14">'
        f'<defs><linearGradient id="g" x1="0" x2="1">'
        f'<stop offset="0" stop-color="{t["rule_edge"]}" stop-opacity="0"/>'
        f'<stop offset="0.25" stop-color="{t["rule_edge"]}"/><stop offset="0.5" stop-color="{t["rule_mid"]}"/>'
        f'<stop offset="0.75" stop-color="{t["rule_edge"]}"/>'
        f'<stop offset="1" stop-color="{t["rule_edge"]}" stop-opacity="0"/></linearGradient></defs>'
        f'<rect x="0" y="6" width="{W}" height="2" rx="1" fill="url(#g)"/>'
        f'<circle cx="{W / 2}" cy="7" r="3.5" fill="{t["rule_mid"]}"/></svg>\n')
