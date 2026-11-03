"""Draws banner-{light,dark}.svg. The curves are not a drawing.

Each one is the probability density of a USD/INR deviation, pushed forward by
the Fokker-Planck solver from github.com/sanjaymav7/probability-wave: it
starts as a spike, spreads, drifts back toward trend, and grows fat tails
because volatility rises the further the rate strays.

    python3 make_banner.py   (needs ../probability-wave next to this repo)
"""
import sys
import numpy as np
sys.path.insert(0, "../probability-wave")
from pwave import Grid, evolve

g = Grid(-0.12, 0.12, 480)
kappa, s0, gamma, sref = 0.03, 0.0022, 0.6, 0.009
sig = lambda d: s0 * (1 + gamma * np.abs(d) / sref)
p = np.exp(-(g.x - 0.045) ** 2 / (2 * (2 * g.dx) ** 2)); p /= p.sum() * g.dx
snaps, t_prev = [], 0
for t in (1, 3, 6, 10, 16, 25, 38, 55, 80):
    p = evolve(p, g, kappa, sig, t - t_prev, 40); t_prev = t
    snaps.append((t, p.copy()))

W, H = 806, 220
X0, X1, BASE = 470, 770, 196


def path(p, i):
    lift = i * 9.5
    xs = X0 + (g.x - g.x[0]) / (g.x[-1] - g.x[0]) * (X1 - X0) - i * 4
    ys = BASE - lift - np.sqrt(p / p.max()) * (150 - lift * 0.9)
    keep = slice(None, None, 3)
    return "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in zip(xs[keep], ys[keep]))


THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", sub="#59636e", line="#0969da", hot="#cf222e", rule="#d1d9e0"),
    "dark": dict(bg="#0d1117", fg="#f0f6fc", sub="#9198a1", line="#58a6ff", hot="#ff7b72", rule="#3d444d"),
}
for name, t in THEMES.items():
    curves = []
    n = len(snaps)
    for i, (tt, pp) in reversed(list(enumerate(snaps))):
        op = 0.35 + 0.65 * (1 - i / (n - 1))
        col = t["hot"] if i == 0 else t["line"]
        curves.append(f'<path d="{path(pp, i)}" fill="none" stroke="{col}" stroke-width="1.6" '
                      f'stroke-opacity="{op:.2f}" stroke-linejoin="round"/>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" rx="10" fill="{t["bg"]}"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="28" y="72" font-size="34" font-weight="700" fill="{t["fg"]}">Sanjay Mavalli</text>
    <text x="28" y="104" font-size="15" fill="{t["fg"]}">Co-founder &amp; CEO, SAAChronicle (Sacron)</text>
    <text x="28" y="128" font-size="15" fill="{t["sub"]}">Math &amp; Computing @ Georgia Tech</text>
    <text x="28" y="152" font-size="15" fill="{t["sub"]}">quant models · ML · number theory</text>
    <text x="28" y="196" font-size="11" fill="{t["sub"]}">right: a price density spreading over 80 days, solved, not drawn</text>
  </g>
  <line x1="410" y1="30" x2="410" y2="196" stroke="{t["rule"]}"/>
  {"".join(curves)}
</svg>
'''
    open(f"banner-{name}.svg", "w").write(svg)
