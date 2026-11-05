"""Draws fedavg.svg and mcmc.svg: two small statistical simulations, computed here and animated with CSS.

fedavg.svg   Federated averaging on a 2-parameter problem. Five clients hold non-IID
             data, so each one's loss is a different quadratic with its own optimum and
             curvature. Every round each client starts from the global model, takes E
             gradient steps on its own loss, and the server averages the results. The
             contours are the true global loss. With E > 1 and clients that disagree,
             FedAvg settles away from the global optimum (client drift); the card
             measures how far.
mcmc.svg     Random-walk Metropolis-Hastings on a banana-shaped density. The chain's
             path draws out, its samples fill in, and the card compares the chain's
             estimate of E[y] with the exact value from numerical integration.

Both are dark cards meant to sit side by side; reduced motion shows the final frame.

    python3 make_sims.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W, H = 480, 300
C = dict(bg0="#070b16", bg1="#0c1630", border="#1e2a4a", grid="#16203a", text="#d6def5", muted="#7f8bb0",
         blue="#6e9bff", violet="#a78bfa", pink="#e46ad6", green="#3fb950", amber="#e3b341")
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
PLOT = (18, 46, 462, 262)          # x0, y0, x1, y1 of the plot area


def card(title, sub, body, css):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<style>{css}</style><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{C["bg1"]}"/><stop offset="1" stop-color="{C["bg0"]}"/></linearGradient></defs>'
            f'<rect width="{W}" height="{H}" rx="14" fill="url(#bg)"/>'
            f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="13.5" fill="none" stroke="{C["border"]}" stroke-width="1.5"/>'
            f'<g font-family="{FONT}"><text x="18" y="28" font-size="14" font-weight="700" fill="{C["text"]}">{title}</text>'
            f'<text x="{W - 18}" y="28" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{C["muted"]}">{sub}</text>'
            f'{body}</g></svg>\n')


def kf(name, steps):
    return f"@keyframes {name}{{{''.join(f'{p:.2f}%{{{v}}}' for p, v in steps)}}}"


def fmt(p):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in p)


# ======================= federated averaging =======================
rng = np.random.default_rng(4)
K, E, LR, ROUNDS = 5, 6, 0.11, 8
centres = np.array([[-2.2, 1.6], [1.9, 2.1], [2.4, -1.2], [-0.6, -2.3], [-2.6, -0.6]])
hess = []
for k in range(K):
    th = rng.uniform(0, np.pi)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    hess.append(R @ np.diag([rng.uniform(1.6, 3.6), rng.uniform(0.25, 0.7)]) @ R.T)
Hs = sum(hess) / K
w_star = np.linalg.solve(sum(hess), sum(h @ c for h, c in zip(hess, centres)))


def local(w):
    path = [w.copy()]
    for _ in range(E):
        w = w - LR * (hess_k @ (w - c_k))
        path.append(w.copy())
    return np.array(path)


w = np.array([3.4, -3.2])
glob, rounds = [w.copy()], []
for r in range(ROUNDS):
    paths = []
    for hess_k, c_k in zip(hess, centres):
        paths.append(local(w))
    w = np.mean([p[-1] for p in paths], axis=0)
    glob.append(w.copy()); rounds.append(paths)
glob = np.array(glob)
w_fix = w.copy()                                   # run on to FedAvg's fixed point
for _ in range(400):
    ps = []
    for hess_k, c_k in zip(hess, centres):
        ps.append(local(w_fix)[-1])
    w_fix = np.mean(ps, axis=0)
f = lambda v: 0.5 * np.mean([(v - c) @ h @ (v - c) for h, c in zip(hess, centres)])
drift = np.linalg.norm(w_fix - w_star)
excess = f(w_fix) - f(w_star)

lo, hi = np.array([-3.6, -3.6]), np.array([3.9, 3.6])
sx = (PLOT[2] - PLOT[0]) / (hi[0] - lo[0]); sy = (PLOT[3] - PLOT[1]) / (hi[1] - lo[1]); s_ = min(sx, sy)
ox = (PLOT[0] + PLOT[2]) / 2 - s_ * (lo[0] + hi[0]) / 2
oy = (PLOT[1] + PLOT[3]) / 2 + s_ * (lo[1] + hi[1]) / 2
P = lambda v: np.column_stack([ox + s_ * np.atleast_2d(v)[:, 0], oy - s_ * np.atleast_2d(v)[:, 1]])

CLIENT_COL = [C["blue"], C["violet"], C["pink"], C["green"], C["amber"]]
CYCLE = 14.0
START, SPAN = 4.0, 10.5                            # % of the cycle where round 1 starts, % per round


def fedavg_svg():
    body, css = [], []
    # global-loss contours: ellipses of the quadratic around w*
    vals, vecs = np.linalg.eigh(Hs)
    t = np.linspace(0, 2 * np.pi, 90)
    for lev in (0.15, 0.6, 1.4, 2.6, 4.2, 6.4):
        r_ = np.sqrt(2 * lev / vals)
        pts = w_star + (vecs @ np.vstack([r_[0] * np.cos(t), r_[1] * np.sin(t)])).T
        body.append(f'<polygon points="{fmt(P(pts))}" fill="none" stroke="{C["blue"]}" stroke-opacity="0.16" stroke-width="1"/>')
    for k, c in enumerate(centres):                # each client's own optimum
        x, y = P(c)[0]
        body.append(f'<path d="M{x - 4:.1f},{y - 4:.1f}l8,8m0,-8l-8,8" stroke="{CLIENT_COL[k]}" stroke-width="1.6"/>'
                    f'<text x="{x + 7:.1f}" y="{y + 3.5:.1f}" font-size="9" fill="{CLIENT_COL[k]}">client {k + 1}</text>')
    xs, ys = P(w_star)[0]
    body.append(f'<path d="M{xs:.1f},{ys - 6:.1f}l1.8,4 4.4,.4-3.3,3 1,4.3-3.9-2.3-3.9,2.3 1-4.3-3.3-3 4.4-.4z" fill="{C["text"]}"/>'
                f'<text x="{xs + 8:.1f}" y="{ys - 4:.1f}" font-size="9" fill="{C["text"]}">global optimum</text>')
    # each round: client paths draw out, then the server average moves
    for r, paths in enumerate(rounds):
        a = START + r * SPAN
        b, c_, d = a + 0.55 * SPAN, a + 0.85 * SPAN, a + SPAN
        last = r == ROUNDS - 1
        hold = "opacity:1" if last else "opacity:0"
        css.append(kf(f"cp{r}", [(0, "opacity:0;stroke-dashoffset:1"), (a, "opacity:1;stroke-dashoffset:1"),
                                 (b, "opacity:1;stroke-dashoffset:0"), (d, f"opacity:{1 if last else 0};stroke-dashoffset:0"),
                                 (92, f"{hold};stroke-dashoffset:0"), (100, "opacity:0;stroke-dashoffset:0")]))
        css.append(f".cp{r}{{stroke-dasharray:1;animation:cp{r} {CYCLE:g}s linear infinite both;opacity:{1 if last else 0}}}")
        for k, p in enumerate(paths):
            body.append(f'<polyline class="cp{r}" pathLength="1" points="{fmt(P(p))}" fill="none" stroke="{CLIENT_COL[k]}" '
                        f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
    # trail of global iterates, revealed segment by segment
    G = P(glob)
    seg = np.linalg.norm(np.diff(G, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()
    steps = [(0, "stroke-dashoffset:1;opacity:1")]
    for r in range(ROUNDS):
        a = START + r * SPAN
        steps += [(a + 0.55 * SPAN, f"stroke-dashoffset:{1 - cum[r]:.4f};opacity:1"),
                  (a + 0.85 * SPAN, f"stroke-dashoffset:{1 - cum[r + 1]:.4f};opacity:1")]
    steps += [(92, "stroke-dashoffset:0;opacity:1"), (100, "stroke-dashoffset:0;opacity:0")]
    css.append(kf("trail", steps) + f".trail{{stroke-dasharray:1;animation:trail {CYCLE:g}s linear infinite both}}")
    body.append(f'<polyline class="trail" pathLength="1" points="{fmt(G)}" fill="none" stroke="{C["text"]}" '
                f'stroke-width="1.4" stroke-dasharray="1" stroke-opacity="0.9"/>')
    # the server's model: a dot that jumps to each new average
    steps = [(0, f"transform:translate({G[0, 0]:.1f}px,{G[0, 1]:.1f}px)")]
    for r in range(ROUNDS):
        a = START + r * SPAN
        steps += [(a + 0.6 * SPAN, f"transform:translate({G[r, 0]:.1f}px,{G[r, 1]:.1f}px)"),
                  (a + 0.85 * SPAN, f"transform:translate({G[r + 1, 0]:.1f}px,{G[r + 1, 1]:.1f}px)")]
    steps.append((100, f"transform:translate({G[-1, 0]:.1f}px,{G[-1, 1]:.1f}px)"))
    css.append(kf("srv", steps) + f".srv{{animation:srv {CYCLE:g}s ease-in-out infinite both;"
               f"transform:translate({G[-1, 0]:.1f}px,{G[-1, 1]:.1f}px)}}")
    body.append(f'<g class="srv"><circle r="9" fill="{C["text"]}" fill-opacity="0.12"/><circle r="4.5" fill="{C["text"]}"/></g>')
    # round counter
    for r in range(ROUNDS):
        a, d = START + r * SPAN, START + (r + 1) * SPAN
        last = r == ROUNDS - 1
        css.append(kf(f"rc{r}", [(0, "opacity:0"), (max(a - 0.01, 0), "opacity:0"), (a, "opacity:1"), (d - 0.01, "opacity:1"),
                                 (d, f"opacity:{1 if last else 0}"), (100, f"opacity:{1 if last else 0}")]))
        css.append(f".rc{r}{{animation:rc{r} {CYCLE:g}s linear infinite both;opacity:{1 if last else 0}}}")
        body.append(f'<text class="rc{r}" x="{W - 18}" y="{H - 16}" text-anchor="end" font-family="{MONO}" '
                    f'font-size="10.5" fill="{C["text"]}">round {r + 1}/{ROUNDS}</text>')
    body.append(f'<text x="18" y="{H - 16}" font-size="10" fill="{C["muted"]}">settles <tspan fill="{C["pink"]}" '
                f'font-weight="700">{drift:.2f}</tspan> from the optimum: client drift with {E} local steps</text>')
    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    return card("federated averaging", f"{K} clients · non-IID", "".join(body), "".join(css))


# ======================= Metropolis-Hastings =======================
def logp(x, y):
    return -x**2 / (2 * 1.6**2) - (y - 0.45 * x**2 + 1.0) ** 2 / (2 * 0.45**2)


N, STEP = 1500, 0.75
rng = np.random.default_rng(11)
cur = np.array([2.6, 3.2]); lp = logp(*cur); chain = [cur.copy()]; acc = 0
for _ in range(N - 1):
    prop = cur + STEP * rng.standard_normal(2)
    lq = logp(*prop)
    if np.log(rng.random()) < lq - lp:
        cur, lp = prop, lq; acc += 1
    chain.append(cur.copy())
chain = np.array(chain)
gx, gy = np.meshgrid(np.linspace(-6, 6, 601), np.linspace(-4, 12, 801))
dens = np.exp(logp(gx, gy)); Ey_true = (dens * gy).sum() / dens.sum()
BURN = 100
Ey_chain = chain[BURN:, 1].mean()

lo2, hi2 = np.array([-4.6, -2.6]), np.array([4.6, 5.4])
s2 = min((PLOT[2] - PLOT[0]) / (hi2[0] - lo2[0]), (PLOT[3] - PLOT[1]) / (hi2[1] - lo2[1]))
ox2 = (PLOT[0] + PLOT[2]) / 2 - s2 * (lo2[0] + hi2[0]) / 2
oy2 = (PLOT[1] + PLOT[3]) / 2 + s2 * (lo2[1] + hi2[1]) / 2
P2 = lambda v: np.column_stack([ox2 + s2 * v[:, 0], oy2 - s2 * v[:, 1]])


def mcmc_svg():
    body, css = [], []
    fig = plt.figure(); cs = plt.contour(gx, gy, dens / dens.max(), levels=[0.03, 0.12, 0.3, 0.55, 0.8]); plt.close(fig)
    for li, segs in enumerate(cs.allsegs):
        for sgm in segs:
            if len(sgm) > 3:
                body.append(f'<polyline points="{fmt(P2(sgm[::2]))}" fill="none" stroke="{C["violet"]}" '
                            f'stroke-opacity="{0.14 + 0.08 * li:.2f}" stroke-width="1"/>')
    STAGES = [150, 500, N]
    T0, T1 = 4.0, 70.0                            # the chain's path draws out over this part of the cycle
    pts = P2(chain)
    for i, n in enumerate(STAGES):
        a = T0 + (T1 - T0) * (STAGES[i - 1] if i else 0) / N
        last = i == len(STAGES) - 1
        css.append(kf(f"sm{i}", [(0, "opacity:0"), (a, "opacity:0"), (a + 3, "opacity:0.75"), (92, "opacity:0.75"), (100, "opacity:0")]))
        css.append(f".sm{i}{{animation:sm{i} {CYCLE:g}s linear infinite both;opacity:.75}}")
        lo_i = STAGES[i - 1] if i else BURN
        dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.25"/>' for x, y in pts[lo_i:n])
        body.append(f'<g class="sm{i}" fill="{C["pink"]}">{dots}</g>')
    walk = pts[:400]
    css.append(kf("walk", [(0, "stroke-dashoffset:1;opacity:.85"), (T0, "stroke-dashoffset:1;opacity:.85"),
                           (T0 + (T1 - T0) * 400 / N, "stroke-dashoffset:0;opacity:.85"), (T1, "stroke-dashoffset:0;opacity:.25"),
                           (92, "stroke-dashoffset:0;opacity:.25"), (100, "stroke-dashoffset:0;opacity:0")]))
    css.append(f".walk{{stroke-dasharray:1;animation:walk {CYCLE:g}s linear infinite both;opacity:.25}}")
    body.append(f'<polyline class="walk" pathLength="1" points="{fmt(walk)}" fill="none" stroke="{C["text"]}" '
                f'stroke-width="0.9" stroke-linejoin="round"/>')
    x0, y0 = pts[0]
    body.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="3.5" fill="none" stroke="{C["text"]}" stroke-width="1.2"/>'
                f'<text x="{x0 + 7:.1f}" y="{y0 + 3:.1f}" font-size="9" fill="{C["muted"]}">start</text>')
    for i, n in enumerate(STAGES):
        a = T0 + (T1 - T0) * (STAGES[i - 1] if i else 0) / N
        d = T0 + (T1 - T0) * n / N if i < len(STAGES) - 1 else 100
        last = i == len(STAGES) - 1
        est = chain[BURN:max(n, BURN + 1), 1].mean()
        css.append(kf(f"ct{i}", [(0, "opacity:0"), (max(a - 0.01, 0), "opacity:0"), (a, "opacity:1"), (max(a, d - 0.01), "opacity:1"),
                                 (d, f"opacity:{1 if last else 0}"), (100, f"opacity:{1 if last else 0}")]))
        css.append(f".ct{i}{{animation:ct{i} {CYCLE:g}s linear infinite both;opacity:{1 if last else 0}}}")
        body.append(f'<text class="ct{i}" x="18" y="{H - 16}" font-size="10" fill="{C["muted"]}">n = {n:,} · '
                    f'E[y] ≈ <tspan fill="{C["pink"]}" font-weight="700">{est:.2f}</tspan> (exact {Ey_true:.2f})</text>')
    body.append(f'<text x="{W - 18}" y="{H - 16}" text-anchor="end" font-family="{MONO}" font-size="10.5" '
                f'fill="{C["text"]}">accept {acc / (N - 1):.0%}</text>')
    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    return card("Metropolis-Hastings", "random-walk MCMC", "".join(body), "".join(css))


open("fedavg.svg", "w").write(fedavg_svg())
open("mcmc.svg", "w").write(mcmc_svg())
print(f"FedAvg: global iterate after {ROUNDS} rounds {glob[-1].round(3)}, fixed point {w_fix.round(3)}, "
      f"optimum {w_star.round(3)}, drift {drift:.3f}, excess loss {excess:.4f}")
print(f"MH: accept {acc / (N - 1):.1%}, E[y] chain {Ey_chain:.3f} vs exact {Ey_true:.3f}")
