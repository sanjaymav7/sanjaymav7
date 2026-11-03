"""Draws manifold-{light,dark}.svg, the profile banner. The surface is not a drawing.

An autoencoder (64 -> 64 -> 32 -> 2 -> 32 -> 64 -> 64, tanh) is trained to squeeze each of
scikit-learn's 8x8 handwritten digits through just two numbers and rebuild it.
Sweeping those two numbers over a grid and decoding every point traces out the
decoder's latent manifold: a curved 2D sheet inside 64-dimensional pixel space.
The sheet is placed in 3D by its first three principal components, shaded by
how it faces a light, and the real digits sit on it where the encoder put
them, coloured by which digit they are.

    python3 make_banner.py
"""
import numpy as np
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA
from sklearn.neural_network import MLPRegressor

X, y = load_digits(return_X_y=True)
X = X / 16.0
ae = MLPRegressor(hidden_layer_sizes=(64, 32, 2, 32, 64), activation="tanh", max_iter=4000,
                  random_state=0, learning_rate_init=0.002, tol=1e-6, n_iter_no_change=50).fit(X, X)
W, B = ae.coefs_, ae.intercepts_
MID = 3                                # layers up to and including the 2-unit bottleneck


def encode(x):
    for w, b in zip(W[:MID], B[:MID]):
        x = np.tanh(x @ w + b)
    return x


def decode(z):
    for w, b in zip(W[MID:-1], B[MID:-1]):
        z = np.tanh(z @ w + b)
    return z @ W[-1] + B[-1]


Z = encode(X)
lo, hi = np.percentile(Z, 0.5, axis=0), np.percentile(Z, 99.5, axis=0)
N = 46
g0, g1 = np.meshgrid(np.linspace(lo[0], hi[0], N), np.linspace(lo[1], hi[1], N), indexing="ij")
surf_hd = decode(np.column_stack([g0.ravel(), g1.ravel()]))
pca = PCA(3).fit(surf_hd)
S = pca.transform(surf_hd).reshape(N, N, 3)
D = pca.transform(decode(Z))          # every digit, sitting on the sheet
R2 = 1 - ((ae.predict(X) - X) ** 2).sum() / ((X - X.mean(0)) ** 2).sum()

# normalise to a unit box, then camera
c = S.reshape(-1, 3).mean(0); s = np.abs(S.reshape(-1, 3) - c).max()
S, D = (S - c) / s, (D - c) / s
YAW, PITCH, CAM = np.radians(38), np.radians(24), 4.0


def cam(p):
    x, y_, z = p[..., 0], p[..., 1], p[..., 2]
    x1 = x * np.cos(YAW) - z * np.sin(YAW)
    z1 = x * np.sin(YAW) + z * np.cos(YAW)
    y1 = y_ * np.cos(PITCH) - z1 * np.sin(PITCH)
    z2 = y_ * np.sin(PITCH) + z1 * np.cos(PITCH)
    return np.stack([x1, y1, z2], axis=-1)


CS, CD = cam(S), cam(D)


def proj(q):
    k = CAM / (CAM + q[..., 2])
    return np.stack([q[..., 0] * k, -q[..., 1] * k], axis=-1)


PS, PD = proj(CS), proj(CD)
allp = PS.reshape(-1, 2)
X0, X1, Y0, Y1 = 440, 792, 14, 206
span = np.ptp(allp, axis=0)
scale = min((X1 - X0) / span[0], (Y1 - Y0) / span[1])
off = np.array([X0 + ((X1 - X0) - span[0] * scale) / 2, Y0 + ((Y1 - Y0) - span[1] * scale) / 2]) - allp.min(0) * scale
PS, PD = PS * scale + off, PD * scale + off

LIGHT = np.array([-0.4, 0.7, -0.6]); LIGHT /= np.linalg.norm(LIGHT)


def mix(a, b, t):
    a = np.array([int(a[i:i + 2], 16) for i in (1, 3, 5)]); b = np.array([int(b[i:i + 2], 16) for i in (1, 3, 5)])
    return "#%02x%02x%02x" % tuple(np.clip(np.round(a + (b - a) * t), 0, 255).astype(int))


THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", sub="#59636e", rule="#d1d9e0",
                  lo="#c6dcf7", hi="#0550ae", wire="#0550ae", wire_op=0.10,
                  digits=["#0969da", "#cf222e", "#1a7f37", "#8250df", "#bf8700",
                          "#e16f24", "#1b7c83", "#bf3989", "#57606a", "#4d2d00"]),
    "dark": dict(bg="#0d1117", fg="#f0f6fc", sub="#9198a1", rule="#3d444d",
                 lo="#0b1f38", hi="#9ecbff", wire="#a5d6ff", wire_op=0.08,
                 digits=["#58a6ff", "#ff7b72", "#3fb950", "#d2a8ff", "#e3b341",
                         "#ffa657", "#39c5cf", "#f778ba", "#b1bac4", "#ffdfb6"]),
}

rng = np.random.default_rng(0)
show = rng.choice(len(D), 420, replace=False)

for name, t in THEMES.items():
    items = []   # (depth, svg)
    for i in range(N - 1):
        for j in range(N - 1):
            quad3 = CS[[i, i + 1, i + 1, i], [j, j, j + 1, j + 1]]
            n = np.cross(quad3[1] - quad3[0], quad3[3] - quad3[0])
            n /= np.linalg.norm(n) + 1e-12
            lam = abs(n @ LIGHT)                      # two-sided surface
            near = np.clip((1.2 - quad3[:, 2].mean()) / 2.4, 0, 1)   # nearer faces a touch brighter
            col = mix(t["lo"], t["hi"], 0.05 + 0.95 * lam ** 1.8 * (0.55 + 0.45 * near))
            q2 = PS[[i, i + 1, i + 1, i], [j, j, j + 1, j + 1]]
            pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in q2)
            items.append((quad3[:, 2].mean(),
                          f'<polygon points="{pts}" fill="{col}" fill-opacity="0.9" stroke="{t["wire"]}" '
                          f'stroke-opacity="{t["wire_op"]}" stroke-width="0.5"/>'))
    for k in show:
        x, y_ = PD[k]
        r = 2.1 * CAM / (CAM + CD[k, 2])
        items.append((CD[k, 2] - 0.02,
                      f'<circle cx="{x:.1f}" cy="{y_:.1f}" r="{r:.2f}" fill="{t["digits"][y[k]]}" '
                      f'stroke="{t["bg"]}" stroke-width="0.6"/>'))
    body = "".join(svg for _, svg in sorted(items, key=lambda it: -it[0]))

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="806" height="220" viewBox="0 0 806 220">
  <rect width="806" height="220" rx="10" fill="{t["bg"]}"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="28" y="72" font-size="34" font-weight="700" fill="{t["fg"]}">Sanjay Mavalli</text>
    <text x="28" y="104" font-size="15" fill="{t["fg"]}">Co-founder &amp; CEO, SAAChronicle (Sacron)</text>
    <text x="28" y="128" font-size="15" fill="{t["sub"]}">Math &amp; Computing @ Georgia Tech</text>
    <text x="28" y="152" font-size="15" fill="{t["sub"]}">quant models · ML · number theory</text>
    <text x="28" y="196" font-size="11" fill="{t["sub"]}">right: the 2D latent manifold an autoencoder learned for handwritten digits</text>
  </g>
  <line x1="410" y1="30" x2="410" y2="196" stroke="{t["rule"]}"/>
  {body}
</svg>
'''
    open(f"manifold-{name}.svg", "w").write(svg)

print(f"reconstruction R^2 {R2:.3f}, latent range {lo.round(2)} to {hi.round(2)}, "
      f"3D view keeps {pca.explained_variance_ratio_.sum():.1%} of the sheet's variance")
