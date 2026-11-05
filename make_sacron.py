"""Draws sacron-trace-{light,dark}.svg and sacron-scores-{light,dark}.svg.

The data is Sacron's demo scenario (synthetic): a lineage graph of tables,
features and models with weekly fairness scores (disparate impact ratio) and
one upstream change. The trace is computed here with the same root-cause rule
the product uses: walk the flagged model's ancestors, keep the ones whose
fairness dropped by at least 0.1, and blame the biggest drop that none of its
own parents explains. Both SVGs animate with CSS and show their final frame
when reduced motion is on.

    python3 make_sacron.py
"""
DATES = ["09-01", "09-08", "09-15", "09-22", "09-29", "10-06"]
WARN, FLAG, MIN_DROP = 0.80, 0.70, 0.10
NODES = {  # id: (kind, weekly fairness)
    "crm.customers_raw":         ("table",   [0.93, 0.93, 0.92, 0.92, 0.91, 0.91]),
    "loans.applications_raw":    ("table",   [0.89, 0.90, 0.89, 0.89, 0.88, 0.89]),
    "mkt.segment_definitions":   ("table",   [0.92, 0.91, 0.92, 0.63, 0.62, 0.62]),
    "feat.engagement_features":  ("table",   [0.90, 0.89, 0.90, 0.89, 0.86, 0.87]),
    "stg.customer_profile":      ("table",   [0.90, 0.90, 0.90, 0.68, 0.67, 0.66]),
    "feat.credit_features":      ("table",   [0.88, 0.88, 0.87, 0.66, 0.65, 0.64]),
    "feature.segment_score":     ("feature", [0.89, 0.89, 0.88, 0.64, 0.63, 0.63]),
    "feature.income_band":       ("feature", [0.90, 0.90, 0.90, 0.89, 0.89, 0.90]),
    "feature.sessions_30d":      ("feature", [0.90, 0.90, 0.90, 0.89, 0.87, 0.88]),
    "model.credit_approval_v3":  ("model",   [0.91, 0.90, 0.90, 0.72, 0.70, 0.69]),
    "model.limit_increase_v2":   ("model",   [0.90, 0.90, 0.89, 0.76, 0.75, 0.74]),
    "model.churn_risk_v1":       ("model",   [0.88, 0.88, 0.87, 0.87, 0.85, 0.86]),
}
EDGES = [
    ("mkt.segment_definitions", "stg.customer_profile"), ("crm.customers_raw", "stg.customer_profile"),
    ("crm.customers_raw", "mkt.segment_definitions"), ("stg.customer_profile", "feat.credit_features"),
    ("loans.applications_raw", "feat.credit_features"), ("crm.customers_raw", "feat.engagement_features"),
    ("feat.credit_features", "feature.segment_score"), ("feat.credit_features", "feature.income_band"),
    ("feat.engagement_features", "feature.sessions_30d"), ("feature.segment_score", "model.credit_approval_v3"),
    ("feature.income_band", "model.credit_approval_v3"), ("feature.segment_score", "model.limit_increase_v2"),
    ("feature.sessions_30d", "model.churn_risk_v1"),
]
CHANGE = dict(node="mkt.segment_definitions", date="09-19", file="segments/high_value.sql",
              message="Redefine high_value segment: require tenure of 3+ years",
              lines=[(10, " WHERE c.lifetime_value > 5000", " "), (11, "   AND c.tenure_years >= 3;", "+")])
MODEL = "model.credit_approval_v3"

parents = {n: [s for s, t in EDGES if t == n] for n in NODES}
children = {n: [t for s, t in EDGES if s == n] for n in NODES}


def biggest_drop(series):
    return min(((series[i] - series[i - 1], i) for i in range(1, len(series))), default=None)


def trace(model):
    """Port of the product's root-cause rule (one-window drops; this scenario has no sustained ones)."""
    seen, stack = set(), [model]
    while stack:
        for p in parents[stack.pop()]:
            if p not in seen:
                seen.add(p); stack.append(p)
    dropped = {}
    for n in [model, *seen]:
        d = biggest_drop(NODES[n][1])
        if d and -d[0] >= MIN_DROP:
            dropped[n] = d
    cands = sorted((dropped[n][0], n) for n in seen if n in dropped)
    root = next(n for _, n in cands if not any(p in dropped and dropped[p][1] == dropped[n][1] for p in parents[n]))
    prev, queue = {model: None}, [model]           # shortest path model -> root over parent links
    while queue:
        n = queue.pop(0)
        if n == root:
            break
        for p in parents[n]:
            if p not in prev:
                prev[p] = n; queue.append(p)
    path, n = [], root
    while n:
        path.append(n); n = prev[n]
    return root, path[::-1], dropped[root]


ROOT, PATH, (ROOT_DELTA, ROOT_WEEK) = trace(MODEL)
assert ROOT == CHANGE["node"]


def status(n):
    f = NODES[n][1][-1]
    return "flag" if f < FLAG else "warn" if f < WARN else "ok"


# --- layout: column = longest distance from a source; features and models pinned to the right
depth = {}


def col(n):
    if n not in depth:
        depth[n] = max((col(p) + 1 for p in parents[n]), default=0)
    return depth[n]


for n in NODES:
    col(n)
last = max(depth.values())
for n, (kind, _) in NODES.items():
    depth[n] = last if kind == "model" else last - 1 if kind == "feature" else depth[n]
columns = {}
for n in NODES:
    columns.setdefault(depth[n], []).append(n)

W, NW, NH, CX0, CSTEP, GY, RSTEP = 806, 122, 30, 8, 134, 92, 46
pos = {}
for c, ns in columns.items():
    for r, n in enumerate(ns):
        pos[n] = (CX0 + c * CSTEP, GY + (r - (len(ns) - 1) / 2) * RSTEP - NH / 2)

THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", sub="#59636e", line="#d0d7de", card="#f6f8fa", node="#ffffff",
                  ok="#1a7f37", warn="#9a6700", flag="#cf222e", blue="#3b6fe8", violet="#8b5cf6", pink="#c2389f",
                  add="#dafbe1", addfg="#116329"),
    "dark": dict(bg="#0d1117", fg="#e6edf3", sub="#9198a1", line="#30363d", card="#161b22", node="#0d1117",
                 ok="#3fb950", warn="#d29922", flag="#ff7b72", blue="#6e9bff", violet="#a78bfa", pink="#e46ad6",
                 add="#12261e", addfg="#7ee2a8"),
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
CYCLE = 12.0


def short(n):
    return n.split(".", 1)[1]


def edge_d(s, t):
    (x1, y1), (x2, y2) = pos[s], pos[t]
    x1, y1, x2, y2 = x1 + NW, y1 + NH / 2, x2, y2 + NH / 2
    m = (x1 + x2) / 2
    return f"M{x1:.1f},{y1:.1f} C{m:.1f},{y1:.1f} {m:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"


def kf(name, steps):
    return f"@keyframes {name}{{{''.join(f'{p}{{{v}}}' for p, v in steps)}}}"


def reduced(selectors):
    return f"@media (prefers-reduced-motion:reduce){{{selectors}{{animation:none}}}}"


# ---------------- trace graph ----------------
n_hops = len(PATH) - 1
HOP0, HOP = 12, 9                           # % of the cycle: first hop starts, each hop takes
hop_pct = [HOP0 + i * HOP for i in range(n_hops)]
ROOT_AT = HOP0 + n_hops * HOP               # root found
CARD_AT = ROOT_AT + 6


def trace_svg(t):
    H = 268
    css = [
        kf("alert", [("0%", "r:9;opacity:.9"), ("10%", "r:22;opacity:0"), ("100%", "r:22;opacity:0")]),
        f".alert{{animation:alert 2.4s ease-out infinite}}",
        kf("fadein", [("0%", "opacity:0"), (f"{CARD_AT}%", "opacity:0"), (f"{CARD_AT + 4}%", "opacity:1"),
                      ("93%", "opacity:1"), ("100%", "opacity:0")]),
        f".card{{animation:fadein {CYCLE:g}s linear infinite both}}",
        kf("rootring", [("0%", "opacity:0"), (f"{ROOT_AT}%", "opacity:0"), (f"{ROOT_AT + 2}%", "opacity:1"),
                        ("93%", "opacity:1"), ("100%", "opacity:0")]),
        f".rootring{{animation:rootring {CYCLE:g}s linear infinite both}}",
        ".card,.rootring{opacity:1}",
    ]
    out = []
    for s, tgt in EDGES:
        out.append(f'<path d="{edge_d(s, tgt)}" fill="none" stroke="{t["line"]}" stroke-width="1.4"/>')
    # the traced path, drawn hop by hop from the model back to the root
    for i in range(n_hops):
        child, parent = PATH[i], PATH[i + 1]
        a, b = hop_pct[i], hop_pct[i] + HOP
        css.append(kf(f"hop{i}", [("0%", "stroke-dashoffset:-1;opacity:1"), (f"{a}%", "stroke-dashoffset:-1;opacity:1"),
                                  (f"{b}%", "stroke-dashoffset:0;opacity:1"), ("93%", "stroke-dashoffset:0;opacity:1"),
                                  ("100%", "stroke-dashoffset:0;opacity:0")]))
        css.append(f".hop{i}{{stroke-dasharray:1;animation:hop{i} {CYCLE:g}s linear infinite both}}")
        out.append(f'<path class="hop{i}" pathLength="1" d="{edge_d(parent, child)}" fill="none" '
                   f'stroke="{t["violet"]}" stroke-width="3" stroke-linecap="round"/>')
    for n, (kind, series) in NODES.items():
        x, y = pos[n]
        st = status(n)
        on_path = n in PATH
        stroke = t["flag"] if n == MODEL else t["line"]
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{NW}" height="{NH}" rx="7" fill="{t["node"]}" '
                   f'stroke="{stroke}" stroke-width="{1.6 if n == MODEL else 1}"/>')
        if on_path and n not in (MODEL, ROOT):
            i = PATH.index(n) - 1
            at = hop_pct[i] + HOP
            css.append(kf(f"lit{i}", [("0%", "opacity:0"), (f"{at}%", "opacity:0"), (f"{at + 1}%", "opacity:1"),
                                      ("93%", "opacity:1"), ("100%", "opacity:0")]))
            css.append(f".lit{i}{{animation:lit{i} {CYCLE:g}s linear infinite both}}.lit{i}{{opacity:1}}")
            out.append(f'<rect class="lit{i}" x="{x:.1f}" y="{y:.1f}" width="{NW}" height="{NH}" rx="7" '
                       f'fill="{t["violet"]}" fill-opacity="0.12" stroke="{t["violet"]}" stroke-width="1.6"/>')
        if n == ROOT:
            out.append(f'<rect class="rootring" x="{x - 3:.1f}" y="{y - 3:.1f}" width="{NW + 6}" height="{NH + 6}" rx="9" '
                       f'fill="{t["pink"]}" fill-opacity="0.14" stroke="{t["pink"]}" stroke-width="2"/>')
        out.append(f'<circle cx="{x + 11:.1f}" cy="{y + NH / 2:.1f}" r="3.6" fill="{t[st]}"/>')
        if n == MODEL:
            out.append(f'<circle class="alert" cx="{x + 11:.1f}" cy="{y + NH / 2:.1f}" r="9" fill="none" '
                       f'stroke="{t["flag"]}" stroke-width="1.5"/>')
        out.append(f'<text x="{x + 20:.1f}" y="{y + 13:.1f}" font-size="10" font-weight="600" fill="{t["fg"]}">{short(n)}</text>'
                   f'<text x="{x + 20:.1f}" y="{y + 24:.1f}" font-size="8.5" fill="{t["sub"]}">{kind} · '
                   f'<tspan fill="{t[st]}" font-weight="600">{series[-1]:.2f}</tspan></text>')
    # callout over the flagged model
    mx, my = pos[MODEL]
    out.append(f'<text x="{mx + NW:.1f}" y="{my - 7:.1f}" text-anchor="end" font-size="9.5" font-weight="600" '
               f'fill="{t["flag"]}">fairness {NODES[MODEL][1][-1]:.2f} &lt; {FLAG:.2f} flag</text>')
    # the change card, under the root
    rx, ry = pos[ROOT]
    cx, cy, cw = rx - 2, 176, 404
    card = [f'<g class="card"><path d="M{rx + NW / 2:.1f},{ry + NH + 4:.1f} L{rx + NW / 2:.1f},{cy:.1f}" '
            f'stroke="{t["pink"]}" stroke-width="1.4" stroke-dasharray="3 3"/>',
            f'<rect x="{cx}" y="{cy}" width="{cw}" height="82" rx="8" fill="{t["card"]}" stroke="{t["pink"]}" stroke-opacity="0.6"/>',
            f'<text x="{cx + 12}" y="{cy + 18}" font-size="10" font-weight="700" fill="{t["pink"]}">ROOT CAUSE</text>',
            f'<text x="{cx + 82}" y="{cy + 18}" font-size="10" fill="{t["sub"]}">{CHANGE["file"]} · {CHANGE["date"]} · '
            f'fairness {ROOT_DELTA:+.2f} in one week</text>',
            f'<text x="{cx + 12}" y="{cy + 34}" font-size="10.5" font-weight="600" fill="{t["fg"]}">{CHANGE["message"]}</text>']
    for k, (ln, code, mark) in enumerate(CHANGE["lines"]):
        yy = cy + 44 + k * 16
        if mark == "+":
            card.append(f'<rect x="{cx + 8}" y="{yy}" width="{cw - 16}" height="15" rx="3" fill="{t["add"]}"/>')
        col_ = t["addfg"] if mark == "+" else t["sub"]
        card.append(f'<text x="{cx + 14}" y="{yy + 11}" font-family="{MONO}" font-size="10" fill="{t["sub"]}">{ln}</text>'
                    f'<text x="{cx + 36}" y="{yy + 11}" font-family="{MONO}" font-size="10" fill="{col_}" '
                    f'xml:space="preserve">{mark}{code}</text>')
    card.append("</g>")
    out += card
    # legend
    lx, ly = 610, 190
    out.append(f'<path d="M{lx - 4},{ly} h18" stroke="{t["violet"]}" stroke-width="3" stroke-linecap="round"/>'
               f'<text x="{lx + 22}" y="{ly + 3.5}" font-size="9.5" fill="{t["sub"]}">traced from the flagged model</text>')
    for i, (k, label) in enumerate([("ok", "fairness within threshold"), ("warn", "below 0.80 (warn)"), ("flag", "below 0.70 (flag)")]):
        yy = ly + 17 * (i + 1)
        out.append(f'<circle cx="{lx + 5}" cy="{yy}" r="3.6" fill="{t[k]}"/>'
                   f'<text x="{lx + 22}" y="{yy + 3.5}" font-size="9.5" fill="{t["sub"]}">{label}</text>')
    css.append(reduced(".alert,.card,.rootring," + ",".join(f".hop{i},.lit{i}" for i in range(n_hops))))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<style>{"".join(css)}</style><rect width="{W}" height="{H}" rx="10" fill="{t["bg"]}"/>'
            f'<g font-family="{FONT}">{"".join(out)}</g></svg>\n')


# ---------------- scores over time ----------------
def scores_svg(t):
    H, L, R, T, B = 230, 52, 590, 26, 196
    ylo, yhi = 0.55, 0.96
    X = lambda i: L + (R - L) * i / (len(DATES) - 1)
    Y = lambda v: B - (B - T) * (v - ylo) / (yhi - ylo)
    css = [kf("draw", [("0%", "stroke-dashoffset:1"), ("45%", "stroke-dashoffset:0"), ("92%", "stroke-dashoffset:0;opacity:1"),
                       ("100%", "stroke-dashoffset:0;opacity:0")]),
           f".ln{{stroke-dasharray:1;animation:draw {CYCLE:g}s ease-out infinite both}}",
           kf("show", [("0%", "opacity:0"), ("40%", "opacity:0"), ("47%", "opacity:1"), ("92%", "opacity:1"), ("100%", "opacity:0")]),
           f".lab{{animation:show {CYCLE:g}s linear infinite both}}.lab{{opacity:1}}",
           reduced(".ln,.lab")]
    out = [f'<rect x="{L}" y="{Y(WARN):.1f}" width="{R - L}" height="{Y(FLAG) - Y(WARN):.1f}" fill="{t["warn"]}" fill-opacity="0.08"/>',
           f'<rect x="{L}" y="{Y(FLAG):.1f}" width="{R - L}" height="{B - Y(FLAG):.1f}" fill="{t["flag"]}" fill-opacity="0.08"/>']
    for v in (0.6, 0.7, 0.8, 0.9):
        out.append(f'<line x1="{L}" x2="{R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{t["line"]}" stroke-width="0.8"/>'
                   f'<text x="{L - 8}" y="{Y(v) + 3.5:.1f}" text-anchor="end" font-size="9.5" fill="{t["sub"]}">{v:.1f}</text>')
    out.append(f'<text x="{L + 6}" y="{Y(WARN) + 12:.1f}" font-size="9" fill="{t["warn"]}">warn</text>'
               f'<text x="{L + 6}" y="{Y(FLAG) + 12:.1f}" font-size="9" fill="{t["flag"]}">flag</text>')
    for i, d in enumerate(DATES):
        out.append(f'<text x="{X(i):.1f}" y="{B + 16}" text-anchor="middle" font-size="9.5" fill="{t["sub"]}">{d}</text>')
    # change marker between 09-15 and 09-22, at 09-19
    cxm = X(2) + (X(3) - X(2)) * 4 / 7
    out.append(f'<line x1="{cxm:.1f}" x2="{cxm:.1f}" y1="{T - 6}" y2="{B}" stroke="{t["pink"]}" stroke-width="1.2" stroke-dasharray="3 3"/>'
               f'<text x="{cxm + 6:.1f}" y="{T + 2}" font-size="9.5" font-weight="600" fill="{t["pink"]}">09-19 · high_value now requires 3+ years tenure</text>')
    series = [(n, NODES[n][1]) for n in reversed(PATH)] + [("model.churn_risk_v1", NODES["model.churn_risk_v1"][1])]
    colours = {ROOT: t["pink"], MODEL: t["flag"], "model.churn_risk_v1": t["sub"]}
    label_y = []
    for n, s in series:
        c = colours.get(n, t["violet"])
        w = 2.6 if n in (ROOT, MODEL) else 1.4
        op = 1 if n in (ROOT, MODEL) else 0.55 if n != "model.churn_risk_v1" else 0.7
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s))
        out.append(f'<polyline class="ln" pathLength="1" points="{pts}" fill="none" stroke="{c}" stroke-width="{w}" '
                   f'stroke-opacity="{op}" stroke-linejoin="round" stroke-linecap="round"/>')
        if n in (ROOT, MODEL, "model.churn_risk_v1"):
            label_y.append((Y(s[-1]), n, c, s[-1]))
    label_y.sort()
    last_y = -99
    for y, n, c, v in label_y:
        y = max(y, last_y + 13); last_y = y
        tag = {"model.churn_risk_v1": "churn_risk_v1 · unaffected", ROOT: "segment_definitions · the cause",
               MODEL: "credit_approval_v3 · flagged"}[n]
        out.append(f'<text class="lab" x="{R + 8}" y="{y + 3.5:.1f}" font-size="10" font-weight="600" fill="{c}">{tag} {v:.2f}</text>')
    out.append(f'<text class="lab" x="{R + 8}" y="{Y(0.655) + 3.5:.1f}" font-size="9" fill="{t["violet"]}">the path in between</text>')
    out.append(f'<text x="{L - 34}" y="{(T + B) / 2:.1f}" font-size="9.5" fill="{t["sub"]}" '
               f'transform="rotate(-90 {L - 34} {(T + B) / 2:.1f})" text-anchor="middle">disparate impact ratio</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<style>{"".join(css)}</style><rect width="{W}" height="{H}" rx="10" fill="{t["bg"]}"/>'
            f'<g font-family="{FONT}">{"".join(out)}</g></svg>\n')


for name, t in THEMES.items():
    open(f"sacron-trace-{name}.svg", "w").write(trace_svg(t))
    open(f"sacron-scores-{name}.svg", "w").write(scores_svg(t))
print("root", ROOT, "path", " <- ".join(short(p) for p in PATH), f"drop {ROOT_DELTA:+.2f} in week {DATES[ROOT_WEEK]}")
