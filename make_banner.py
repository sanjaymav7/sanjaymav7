"""Draws montecarlo-{light,dark}.svg, the profile banner. The paths are not a drawing.

20,000 stock-price paths are simulated under geometric Brownian motion
(S0 = 100, r = 5%, sigma = 30%, one year of daily steps). 48 of them, sampled
from the paths that stay inside the plotted price range, are drawn in 3D, fanned out in depth by where they finish and coloured
the same way. At the end of the time axis sits the histogram of where all
20,000 finished, with the exact lognormal density drawn over it, and the
caption prices an at-the-money call from the simulation next to
Black-Scholes.

    python3 make_banner.py
"""
import numpy as np
from scipy.stats import norm

S0, R, SIG, T, STEPS, PATHS, K = 100.0, 0.05, 0.30, 1.0, 252, 20_000, 100.0
rng = np.random.default_rng(7)
dt = T / STEPS
Z = rng.standard_normal((PATHS, STEPS))
logS = np.log(S0) + np.cumsum((R - 0.5 * SIG**2) * dt + SIG * np.sqrt(dt) * Z, axis=1)
logS = np.hstack([np.full((PATHS, 1), np.log(S0)), logS])
ST = np.exp(logS[:, -1])

pay = np.exp(-R * T) * np.maximum(ST - K, 0)
mc, se = pay.mean(), pay.std(ddof=1) / np.sqrt(PATHS)
d1 = (np.log(S0 / K) + (R + 0.5 * SIG**2) * T) / (SIG * np.sqrt(T))
bs = S0 * norm.cdf(d1) - K * np.exp(-R * T) * norm.cdf(d1 - SIG * np.sqrt(T))

# --- world coordinates: x = time, y = log price, z = depth (paths ordered by where they end)
SHOW = 48
ylo, yhi = np.percentile(logS[:, -1], [0.7, 99.3])
# the drawn sample comes from paths that stay inside the histogram's price range
inside = np.flatnonzero((logS.min(1) >= ylo) & (logS.max(1) <= yhi))
pick = rng.choice(inside, SHOW, replace=False)
pick = pick[np.argsort(ST[pick])]
ymid, yspan = (ylo + yhi) / 2, (yhi - ylo) / 2
tt = np.linspace(-1.0, 1.0, STEPS + 1)
sub = np.r_[0:STEPS + 1:3, STEPS]
zs = np.linspace(0.75, -0.75, SHOW)          # low finishers at the back
paths3 = [np.column_stack([tt[sub], (logS[k, sub] - ymid) / yspan * 0.85, np.full(len(sub), z)])
          for k, z in zip(pick, zs)]
rank = (np.argsort(np.argsort(ST[pick])) / (SHOW - 1))

# terminal histogram of all paths, standing at the end of the time axis in the z = 0 plane
edges = np.linspace(ylo, yhi, 40)
hist, _ = np.histogram(logS[:, -1], bins=edges, density=True)
yc = (edges[:-1] + edges[1:]) / 2
m, s = np.log(S0) + (R - 0.5 * SIG**2) * T, SIG * np.sqrt(T)
dens = norm.pdf(yc, m, s)                      # density of log S_T, exact
w = 0.55 / max(hist.max(), dens.max())
yb = lambda v: (v - ymid) / yspan * 0.85

YAW, PITCH, CAM = np.radians(-34), np.radians(27), 4.2


def cam(p):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    x1 = x * np.cos(YAW) - z * np.sin(YAW)
    z1 = x * np.sin(YAW) + z * np.cos(YAW)
    y1 = y * np.cos(PITCH) - z1 * np.sin(PITCH)
    z2 = y * np.sin(PITCH) + z1 * np.cos(PITCH)
    return np.stack([x1, y1, z2], axis=-1)


def proj(q):
    k = CAM / (CAM + q[..., 2])
    return np.stack([q[..., 0] * k, -q[..., 1] * k], axis=-1)


FLOOR = min(p[:, 1].min() for p in paths3) - 0.08   # just under the lowest path drawn
floor = np.array([[-1, FLOOR, -0.85], [1.62, FLOOR, -0.85], [1.62, FLOOR, 0.85], [-1, FLOOR, 0.85]])
hist_poly = [np.array([[1.04, yb(edges[i]), 0], [1.04 + hist[i] * w, yb(edges[i]), 0],
                       [1.04 + hist[i] * w, yb(edges[i + 1]), 0], [1.04, yb(edges[i + 1]), 0]])
             for i in range(len(hist))]
curve = np.column_stack([1.04 + dens * w, yb(yc), np.zeros_like(yc)])

everything = np.vstack(paths3 + hist_poly + [curve, floor])
P = proj(cam(everything))
X0, X1, Y0, Y1 = 436, 794, 16, 206
span = np.ptp(P, axis=0)
scale = min((X1 - X0) / span[0], (Y1 - Y0) / span[1])
off = np.array([X0 + ((X1 - X0) - span[0] * scale) / 2, Y0 + ((Y1 - Y0) - span[1] * scale) / 2]) - P.min(0) * scale


def screen(p):
    return proj(cam(p)) * scale + off


def pts(a):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in screen(a))


def mix(a, b, t):
    a = np.array([int(a[i:i + 2], 16) for i in (1, 3, 5)]); b = np.array([int(b[i:i + 2], 16) for i in (1, 3, 5)])
    return "#%02x%02x%02x" % tuple(np.clip(np.round(a + (b - a) * t), 0, 255).astype(int))


THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", sub="#59636e", rule="#d1d9e0", grid="#8c959f",
                  low="#cf222e", mid="#8250df", high="#0969da", bar="#0969da", curve="#1f2328"),
    "dark": dict(bg="#0d1117", fg="#f0f6fc", sub="#9198a1", rule="#3d444d", grid="#6e7681",
                 low="#ff7b72", mid="#d2a8ff", high="#58a6ff", bar="#58a6ff", curve="#f0f6fc"),
}

for name, t in THEMES.items():
    out = [f'<polygon points="{pts(floor)}" fill="{t["grid"]}" fill-opacity="0.05"/>']
    for gx in np.linspace(-1, 1, 5):              # floor grid: quarters of the year
        out.append(f'<polyline points="{pts(np.array([[gx, FLOOR, -0.85], [gx, FLOOR, 0.85]]))}" '
                   f'stroke="{t["grid"]}" stroke-opacity="0.25" stroke-width="0.6" fill="none"/>')
    for gz in np.linspace(-0.85, 0.85, 5):
        out.append(f'<polyline points="{pts(np.array([[-1, FLOOR, gz], [1.62, FLOOR, gz]]))}" '
                   f'stroke="{t["grid"]}" stroke-opacity="0.18" stroke-width="0.6" fill="none"/>')
    # paths back to front; nearer ones are brighter and thicker
    for p3, r_, z in zip(paths3, rank, zs):
        col = mix(t["low"], t["mid"], r_ * 2) if r_ < 0.5 else mix(t["mid"], t["high"], r_ * 2 - 1)
        near = (0.75 - z) / 1.5
        if z > 0:
            continue
        out.append(f'<polyline points="{pts(p3)}" fill="none" stroke="{col}" stroke-width="{0.7 + 0.8 * near:.2f}" '
                   f'stroke-opacity="{0.35 + 0.5 * near:.2f}" stroke-linejoin="round"/>')
    for poly in hist_poly:
        out.append(f'<polygon points="{pts(poly)}" fill="{t["bar"]}" fill-opacity="0.28" '
                   f'stroke="{t["bar"]}" stroke-opacity="0.5" stroke-width="0.5"/>')
    out.append(f'<polyline points="{pts(curve)}" fill="none" stroke="{t["curve"]}" stroke-width="1.3" stroke-opacity="0.85"/>')
    for p3, r_, z in zip(paths3, rank, zs):     # front half of the fan, drawn over the histogram
        if z <= 0:
            continue
        col = mix(t["low"], t["mid"], r_ * 2) if r_ < 0.5 else mix(t["mid"], t["high"], r_ * 2 - 1)
        near = (0.75 - z) / 1.5
        out.append(f'<polyline points="{pts(p3)}" fill="none" stroke="{col}" stroke-width="{0.7 + 0.8 * near:.2f}" '
                   f'stroke-opacity="{0.35 + 0.5 * near:.2f}" stroke-linejoin="round"/>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="806" height="220" viewBox="0 0 806 220">
  <rect width="806" height="220" rx="10" fill="{t["bg"]}"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="28" y="72" font-size="34" font-weight="700" fill="{t["fg"]}">Sanjay Mavalli</text>
    <text x="28" y="104" font-size="15" fill="{t["fg"]}">Co-founder &amp; CEO, SAAChronicle (Sacron)</text>
    <text x="28" y="128" font-size="15" fill="{t["sub"]}">Math &amp; Computing @ Georgia Tech</text>
    <text x="28" y="152" font-size="15" fill="{t["sub"]}">quant models · ML · number theory</text>
    <text x="28" y="196" font-size="11" fill="{t["sub"]}">right: {PATHS:,} Monte Carlo paths · call {mc:.2f} ± {se:.2f} vs Black-Scholes {bs:.2f}</text>
  </g>
  <line x1="410" y1="30" x2="410" y2="196" stroke="{t["rule"]}"/>
  {"".join(out)}
</svg>
'''
    open(f"montecarlo-{name}.svg", "w").write(svg)

print(f"MC call {mc:.3f} ± {se:.3f}, Black-Scholes {bs:.3f}, |diff| = {abs(mc - bs) / se:.2f} standard errors")
