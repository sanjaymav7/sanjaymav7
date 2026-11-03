"""Draws network-{light,dark}.svg, the profile banner. The network is not a drawing.

A 64-16-16-10 multilayer perceptron is trained on scikit-learn's handwritten
digits, then shown reading one held-out digit. The first layer is that
digit's 8x8 pixels, every node's brightness is its real activation, and the
edges are the connections carrying the most signal (|activation x weight|),
blue when they push a neuron up and red when they push it down. The layers
are placed in 3D and projected with perspective, nearest drawn last.

    python3 make_banner.py
"""
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

X, y = load_digits(return_X_y=True)
X = X / 16.0
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
net = MLPClassifier(hidden_layer_sizes=(16, 16), max_iter=2000, random_state=0).fit(Xtr, ytr)
ACC = net.score(Xte, yte)

# one held-out 3 the network gets right
i = next(k for k in range(len(yte)) if yte[k] == 3 and net.predict(Xte[k:k + 1])[0] == 3)
acts = [Xte[i]]
for W, b in zip(net.coefs_[:-1], net.intercepts_[:-1]):
    acts.append(np.maximum(0, acts[-1] @ W + b))
acts.append(net.predict_proba(Xte[i:i + 1])[0])
acts = [a / (a.max() + 1e-12) for a in acts]

# layer geometry in world coordinates: u runs across, (gy, gz) is each layer's own grid
SHAPES = [(8, 8, 0.17), (4, 4, 0.34), (4, 4, 0.34), (10, 1, 0.155)]
U = [-1.7, -0.45, 0.65, 1.65]
nodes = []   # per layer: array of (u, gy, gz)
for (rows, cols, sp), u in zip(SHAPES, U):
    r, c = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    gy = -(r - (rows - 1) / 2) * sp
    gz = -(c - (cols - 1) / 2) * sp    # columns run left to right as seen by the camera
    nodes.append(np.column_stack([np.full(r.size, u), gy.ravel(), gz.ravel()]))

YAW, PITCH, CAM = np.radians(55), np.radians(16), 4.6


def project(p):
    u, gy, gz = p[..., 0], p[..., 1], p[..., 2]
    x1 = u * np.cos(YAW) - gz * np.sin(YAW)
    z1 = u * np.sin(YAW) + gz * np.cos(YAW)
    y1 = gy * np.cos(PITCH) - z1 * np.sin(PITCH)
    z2 = gy * np.sin(PITCH) + z1 * np.cos(PITCH)
    s = CAM / (CAM + z2)
    return np.stack([x1 * s, -y1 * s, s, z2], axis=-1)


P = [project(n) for n in nodes]
allp = np.vstack(P)
X0, X1, Y0, Y1 = 452, 790, 18, 204
scale = min((X1 - X0) / np.ptp(allp[:, 0]), (Y1 - Y0) / np.ptp(allp[:, 1]))
ox = X0 + ((X1 - X0) - np.ptp(allp[:, 0]) * scale) / 2 - allp[:, 0].min() * scale
oy = Y0 + ((Y1 - Y0) - np.ptp(allp[:, 1]) * scale) / 2 - allp[:, 1].min() * scale


def screen(q):
    return q[..., 0] * scale + ox, q[..., 1] * scale + oy


# strongest connections between consecutive layers
KEEP = [70, 45, 24]
edges = []   # (layer, i, j, signed strength 0..1)
for L, W in enumerate(net.coefs_):
    contrib = acts[L][:, None] * W
    flat = np.argsort(-np.abs(contrib).ravel())[:KEEP[L]]
    top = np.abs(contrib).ravel()[flat[0]]
    for f in flat:
        a, b = np.unravel_index(f, W.shape)
        edges.append((L, a, b, contrib[a, b] / top))

pred = int(np.argmax(acts[-1]))

THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", sub="#59636e", rule="#d1d9e0",
                  on="#0969da", hi="#ffffff", off="#d8dee4", offhi="#ffffff", neg="#cf222e",
                  plate="#0969da", plate_op=0.05),
    "dark": dict(bg="#0d1117", fg="#f0f6fc", sub="#9198a1", rule="#3d444d",
                 on="#58a6ff", hi="#e6f1ff", off="#262c36", offhi="#484f58", neg="#ff7b72",
                 plate="#58a6ff", plate_op=0.06),
}

for name, t in THEMES.items():
    out = []
    # translucent plate behind each layer, so the grids read as planes in space
    for (rows, cols, sp), u in zip(SHAPES, U):
        hy, hz = (rows - 1) / 2 * sp + sp * 0.6, (cols - 1) / 2 * sp + sp * 0.6
        corners = np.array([[u, hy, -hz], [u, hy, hz], [u, -hy, hz], [u, -hy, -hz]])
        sx, sy = screen(project(corners))
        pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(sx, sy))
        out.append(f'<polygon points="{pts}" fill="{t["plate"]}" fill-opacity="{t["plate_op"]}" '
                   f'stroke="{t["plate"]}" stroke-opacity="0.18" stroke-width="0.8"/>')
    for L, a, b, s in sorted(edges, key=lambda e: abs(e[3])):
        x1, y1 = screen(P[L][a]); x2, y2 = screen(P[L + 1][b])
        depth = (P[L][a][2] + P[L + 1][b][2]) / 2
        col = t["on"] if s > 0 else t["neg"]
        op = 0.06 + 0.5 * abs(s) ** 1.2
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" '
                   f'stroke-opacity="{op:.2f}" stroke-width="{0.5 + 1.1 * abs(s) * depth:.2f}"/>')
    order = sorted(((L, k) for L in range(4) for k in range(len(P[L]))), key=lambda lk: -P[lk[0]][lk[1]][3])
    for L, k in order:
        cx, cy = screen(P[L][k])
        r = (3.0 if L == 0 else 3.8 if L < 3 else 2.9) * P[L][k][2]
        a = float(acts[L][k])
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="url(#off-{name})"/>')
        if a > 0.02:
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="url(#on-{name})" '
                       f'fill-opacity="{min(1, 0.15 + a):.2f}"/>')
        if L == 3 and k == pred:
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r + 2.4:.2f}" fill="none" '
                       f'stroke="{t["neg"]}" stroke-width="1.3"/>')
            out.append(f'<text x="{cx + r + 6:.1f}" y="{cy + 3.5:.1f}" font-size="10" fill="{t["sub"]}" '
                       f'font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif">'
                       f'"{pred}"</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="806" height="220" viewBox="0 0 806 220">
  <defs>
    <radialGradient id="on-{name}" cx="35%" cy="32%" r="70%">
      <stop offset="0%" stop-color="{t["hi"]}"/><stop offset="45%" stop-color="{t["on"]}"/>
      <stop offset="100%" stop-color="{t["on"]}" stop-opacity="0.75"/>
    </radialGradient>
    <radialGradient id="off-{name}" cx="35%" cy="32%" r="70%">
      <stop offset="0%" stop-color="{t["offhi"]}"/><stop offset="100%" stop-color="{t["off"]}"/>
    </radialGradient>
  </defs>
  <rect width="806" height="220" rx="10" fill="{t["bg"]}"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="28" y="72" font-size="34" font-weight="700" fill="{t["fg"]}">Sanjay Mavalli</text>
    <text x="28" y="104" font-size="15" fill="{t["fg"]}">Co-founder &amp; CEO, SAAChronicle (Sacron)</text>
    <text x="28" y="128" font-size="15" fill="{t["sub"]}">Math &amp; Computing @ Georgia Tech</text>
    <text x="28" y="152" font-size="15" fill="{t["sub"]}">quant models · ML · number theory</text>
    <text x="28" y="196" font-size="11" fill="{t["sub"]}">right: a trained network reading a handwritten 3, real activations</text>
  </g>
  <line x1="410" y1="30" x2="410" y2="196" stroke="{t["rule"]}"/>
  {"".join(out)}
</svg>
'''
    open(f"network-{name}.svg", "w").write(svg)

print(f"test accuracy {ACC:.3f}, digit index {i}, predicted {pred}")
