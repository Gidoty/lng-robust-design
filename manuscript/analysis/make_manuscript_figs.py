"""Figures 1, 2 and 4 for the manuscript (drawn from the repository data; no new results).
Figure 1: study workflow. Figure 2: process flow diagrams as modelled (lng_robust/cycles/*.py).
Figure 4: composition envelope from lng_robust/results/envelopes/{main,fieldD}/scenarios.csv."""
import sys, json, pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Circle, Rectangle, FancyArrowPatch
REPO = sys.argv[1]; OUT = sys.argv[2]
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7, 'pdf.fonttype': 42, 'svg.fonttype': 'none'})
MM = 1 / 25.4
INK = '#1f2a36'

def save(fig, name):
    fig.savefig(f'{OUT}/{name}.pdf')
    fig.savefig(f'{OUT}/{name}.png', dpi=1000)
    fig.savefig(f'{OUT}/{name}.tif', dpi=1000, pil_kwargs={'compression': 'tiff_lzw'})
    plt.close(fig)

# ------------------------------------------------------------------ Figure 1: workflow
def fig1():
    W, H = 190, 128
    fig = plt.figure(figsize=(W * MM, H * MM)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
    lanes = [('Data', '#5b6b7c', '#eef1f5'), ('Models', '#0b5c94', '#e3eff9'), ('Design', '#007a57', '#e1f4ec'), ('Evaluation and\nanalyses', '#b34a00', '#fdeee3')]
    ys = [104, 76, 48, 6]; hs = [22, 22, 22, 36]
    for (lab, ec, fc), y, h in zip(lanes, ys, hs):
        ax.add_patch(FancyBboxPatch((2, y), 186, h, boxstyle='round,pad=0,rounding_size=2.2', fc=fc, ec='none'))
        ax.add_patch(Rectangle((2, y), 3.2, h, fc=ec, ec='none'))
        ax.text(10.5, y + h / 2, lab, rotation=90, ha='center', va='center', fontsize=7.5, color=ec, weight='bold')
    def box(x, y, w, h, title, body, ec, bold_fc='white'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=1.6', fc=bold_fc, ec=ec, lw=1.0))
        ax.text(x + 2, y + h - 2.2, title, ha='left', va='top', fontsize=7.2, weight='bold', color=ec)
        ax.text(x + 2, y + h - 6.6, body, ha='left', va='top', fontsize=6.3, color=INK, linespacing=1.25)
    def arr(p, q, color=INK, cs='arc3,rad=0'):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=7, lw=0.9, color=color, connectionstyle=cs, shrinkA=0, shrinkB=0))
    g, b, gr, o = '#5b6b7c', '#0b5c94', '#007a57', '#b34a00'
    # data lane
    box(16, 106, 52, 18, 'Measured compositions (2.7.1)', 'Seven flow stations, OML 30 and 34\n(Ebrunu and Akpoturi, 2025)\nField D (42.7 mol% N$_2$) kept for sensitivity', g)
    box(74, 106, 50, 18, 'Treated-feed specification (2.1)', 'CO$_2$ ≤ 50 ppmv, water removed\nC$_{4+}$ ≤ 2 mol%, C$_{5+}$ ≤ 0.1 mol%\nNitrogen not removed', g)
    box(130, 106, 56, 18, 'Scenario envelope (2.7.2)', '6 anchors + 44 Dirichlet samples\n$\\kappa$ = 178.7, $S$ = 50 scenarios\nNominal feed $z_0$ = Field C', g)
    arr((68, 115), (74, 115), g); arr((124, 115), (130, 115), g)
    # model lane
    box(16, 78, 82, 18, 'Cycle models (2.2–2.5)', 'SMR, single N$_2$ expander, dual N$_2$ expander\nPeng–Robinson; discretised MSHE ($N$ = 100), MITA and UA\nFailure codes for every infeasible evaluation', b)
    box(104, 78, 64, 18, 'Validation (2.6, 3.1)', 'Published SMR, single and dual N$_2$ designs,\nno tuning, ±5 % acceptance\nGERG-2008 and NeqSim property checks', b)
    arr((98, 87), (104, 87), b)
    # design lane
    box(16, 50, 70, 18, 'Nominal design (2.9)', 'NSGA-II, population 60, 40 generations\nMinimise SEC and specific UA at $z_0$\nKnee of the front', gr)
    box(92, 50, 94, 18, 'Risk-averse design, two-stage (2.9)', 'First stage $x$ fixed: refrigerant, UA, rated flow\nSecond stage $y_s$ re-optimised for each scenario\nMinimise CVaR$_{0.9}$ of SEC; ≥ 95 % of scenarios feasible; iso-UA and UA × 1.25', gr)
    # evaluation lane
    box(16, 28, 170, 12, 'Evaluation of every design on all 50 scenarios (3.4, 3.5)', 'Feasible fraction with failure codes; SEC distribution; price of robustness, Eq. (8); bootstrap 95 % confidence intervals', o)
    xs = [16, 59.5, 103, 146.5]; ws = 39.5
    items = [('Ranking reversal (3.6)', '16 composition cells;\npreferred cycle per cell'),
             ('Surrogates (2.10, 3.7)', 'GP, gradient boosting, ridge;\nleave-one-anchor-out; FFR'),
             ('Sensitivity (2.11, 3.8)', 'Sobol and one-at-a-time;\n$\\kappa$, Fields D and E, basis'),
             ('Screening cost (2.12, 3.9)', 'Turton correlations;\n27 cost cases')]
    for x, (t, bdy) in zip(xs, items):
        box(x, 8, ws, 14.5, t, bdy, o)
        arr((x + ws / 2, 28), (x + ws / 2, 22.5), o)
    # vertical flow
    arr((177, 106), (177, 68), INK, 'arc3,rad=0')
    ax.text(178.5, 88, '50\nscenarios', fontsize=6, color=INK, va='center', style='italic')
    arr((45, 78), (45, 68), INK); arr((90, 78), (120, 68), INK)
    arr((86, 59), (92, 59), gr); ax.text(89, 61.2, 'seed', fontsize=6, ha='center', color=gr, style='italic')
    arr((51, 50), (51, 40), INK); arr((139, 50), (139, 40), INK)
    save(fig, 'Figure_1')

# ------------------------------------------------------------------ Figure 2: PFDs
NG, HP, LP = '#1f2a36', '#c0392b', '#1f6fb2'
def pfd(ax, kind, title):
    ax.set_xlim(0, 62); ax.set_ylim(0, 100); ax.axis('off')
    ax.text(1, 100, title, fontsize=7.5, weight='bold', va='top', color=INK)
    def line(pts, col, lw=1.3, arrow=True):
        xs, ys = zip(*pts); ax.plot(xs, ys, color=col, lw=lw, solid_capstyle='round', solid_joinstyle='round', zorder=2)
        if arrow:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            ax.add_patch(FancyArrowPatch((x0 + (x1 - x0) * 0.4, y0 + (y1 - y0) * 0.4), (x0 + (x1 - x0) * 0.62, y0 + (y1 - y0) * 0.62),
                                         arrowstyle='-|>', mutation_scale=7, color=col, lw=0, zorder=3))
    def comp(x, y, w=7, h=6, flip=False, label=None, fc='#dfe6ee'):
        pts = [(x, y - h / 2), (x + w, y - h / 4), (x + w, y + h / 4), (x, y + h / 2)] if not flip else \
              [(x, y - h / 4), (x + w, y - h / 2), (x + w, y + h / 2), (x, y + h / 4)]
        ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=INK, lw=0.8, zorder=4))
        if label: ax.text(x + w / 2, y - h / 2 - 1.6, label, ha='center', va='top', fontsize=6, color=INK)
    def cooler(x, y, r=2.2, label=None):
        ax.add_patch(Circle((x, y), r, fc='white', ec=INK, lw=0.8, zorder=4))
        ax.plot([x - r * 0.7, x - r * 0.2, x + r * 0.2, x + r * 0.7], [y - r * 0.5, y + r * 0.5, y - r * 0.5, y + r * 0.5], color=INK, lw=0.6, zorder=5)
        if label: ax.text(x, y + r + 1, label, ha='center', va='bottom', fontsize=5.8, color=INK)
    def valve(x, y, s=2.0, vertical=True):
        p1 = [(x - s, y + s), (x + s, y + s), (x, y)] if vertical else [(x - s, y - s), (x - s, y + s), (x, y)]
        p2 = [(x - s, y - s), (x + s, y - s), (x, y)] if vertical else [(x + s, y - s), (x + s, y + s), (x, y)]
        for p in (p1, p2): ax.add_patch(Polygon(p, closed=True, fc='white', ec=INK, lw=0.8, zorder=4))
    # MSHE
    mx, mw, my0, my1 = 25, 9, 22, 80
    ax.add_patch(FancyBboxPatch((mx, my0), mw, my1 - my0, boxstyle='round,pad=0,rounding_size=1.2', fc='#eef3f8', ec=INK, lw=0.9, zorder=1))
    ax.text(mx + mw / 2, my0 + 30, 'MSHE', rotation=90, ha='center', va='center', fontsize=6.3, color='#3d4b59', zorder=6, weight='bold', bbox=dict(boxstyle='round,pad=0.25', fc='#eef3f8', ec='none'))
    # pretreatment + natural gas (hot, downwards)
    ax.add_patch(FancyBboxPatch((1, 82), 13, 7, boxstyle='round,pad=0,rounding_size=1', fc='#f4f4f4', ec='#8a96a3', lw=0.7, ls='--'))
    ax.text(7.5, 85.5, 'Pretreatment\n(specification)', ha='center', va='center', fontsize=5.4, color='#5b6b7c')
    line([(7.5, 89), (7.5, 92.5)], NG, arrow=False); ax.text(1, 94, 'Treated feed', fontsize=5.8, va='center', color=NG)
    line([(7.5, 82), (7.5, 78), (mx + 1.6, 78), (mx + 1.6, 24)], NG, arrow=True)
    line([(mx + 1.6, 24), (mx + 1.6, 16), (19, 16)], NG, arrow=False)
    valve(17, 16, 1.6, vertical=False)
    line([(15.4, 16), (9, 16)], NG, arrow=False)
    ax.add_patch(FancyBboxPatch((4, 8), 5, 13, boxstyle='round,pad=0,rounding_size=2', fc='white', ec=INK, lw=0.8, zorder=4))
    ax.text(10, 10, 'End\nflash', ha='left', va='center', fontsize=5.8)
    line([(6.5, 8), (6.5, 2)], NG); ax.text(8, 2.5, 'LNG', fontsize=6.5, weight='bold', va='center', color=NG)
    line([(6.5, 21), (6.5, 25.5)], '#7f8c8d', lw=0.9); ax.text(2, 27.5, 'flash gas', fontsize=5.6, color='#7f8c8d', va='center')
    # compression train (top right): LP in -> stage 1 -> intercooler -> stage n -> aftercooler -> HP
    cy = 90
    comp(37, cy, w=6, label='Stage 1'); cooler(46, cy, r=2.0, label='IC'); comp(50, cy, w=6, label='Stage n'); cooler(59.6, cy, r=1.9, label='AC')
    line([(43, cy), (44, cy)], LP, arrow=False); line([(48, cy), (50, cy)], LP, arrow=False); line([(56, cy), (57.7, cy)], HP, arrow=False)
    if kind == 'smr':
        # HP down through MSHE (hot), JT valve, LP up (cold) to compressor
        line([(59.6, cy - 1.9), (59.6, 74), (mx + 4.5, 74), (mx + 4.5, 24)], HP)
        line([(mx + 4.5, 24), (mx + 4.5, 14), (44, 14), (44, 18)], HP, arrow=False)
        valve(44, 20, 1.8)
        line([(44, 22), (44, 26), (mx + 7.4, 26), (mx + 7.4, 82)], LP)
        line([(mx + 7.4, 82), (mx + 7.4, cy), (37, cy)], LP)
        ax.text(46.5, 20, 'JT valve', fontsize=5.8, va='center')
        ax.text(57.5, 77.2, 'HP mixed refrigerant', fontsize=5.8, color=HP, va='bottom', ha='right')
        ax.text(37, 30, 'LP mixed refrigerant', fontsize=5.8, color=LP, va='center')
    elif kind == 'single':
        line([(59.6, cy - 1.9), (59.6, 74), (mx + 4.5, 74), (mx + 4.5, 40)], HP)
        line([(mx + 4.5, 40), (mx + 4.5, 36), (45, 36), (45, 31)], HP, arrow=False)
        comp(42, 27, w=6, h=5, flip=True, fc='#f6e1dc'); ax.text(49.5, 27, 'Expander', fontsize=5.8, va='center')
        line([(45, 24.5), (45, 20), (mx + 7.4, 20), (mx + 7.4, 82)], LP)
        line([(mx + 7.4, 82), (mx + 7.4, cy), (37, cy)], LP)
        ax.text(57.5, 75.2, 'HP nitrogen', fontsize=5.8, color=HP, va='bottom', ha='right')
        ax.text(37, 16, 'LP nitrogen', fontsize=5.8, color=LP, va='center')
    else:
        line([(59.6, cy - 1.9), (59.6, 74), (mx + 4.5, 74), (mx + 4.5, 60)], HP)
        line([(mx + 4.5, 60), (mx + 4.5, 57), (40, 57), (40, 54)], HP, arrow=False)          # split to warm expander
        comp(37, 51, w=6, h=5, flip=True, fc='#f6e1dc'); ax.text(43.8, 52, 'Warm\nexpander', fontsize=5.6, va='center')
        line([(40, 48.5), (40, 45), (mx + 7.4, 45)], LP, arrow=False)
        line([(mx + 4.5, 57), (mx + 4.5, 36)], HP)                                            # remainder continues
        line([(mx + 4.5, 36), (mx + 4.5, 33), (48, 33), (48, 30)], HP, arrow=False)
        comp(45, 27, w=6, h=5, flip=True, fc='#f6e1dc'); ax.text(51.8, 28, 'Cold\nexpander', fontsize=5.6, va='center')
        line([(48, 24.5), (48, 20), (mx + 7.4, 20), (mx + 7.4, 82)], LP)
        line([(mx + 7.4, 82), (mx + 7.4, cy), (37, cy)], LP)
        ax.plot([mx + 7.4], [45], 'o', ms=2.2, color=LP, zorder=6)
        ax.text(57.5, 75.2, 'HP nitrogen', fontsize=5.8, color=HP, va='bottom', ha='right')
        ax.text(41.5, 59, 'split', fontsize=5.6, color=HP, style='italic')
        ax.text(37, 16, 'LP nitrogen (merged)', fontsize=5.8, color=LP, va='center')

def fig2():
    fig, axes = plt.subplots(1, 3, figsize=(190 * MM, 92 * MM))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.07, wspace=0.05)
    for ax, k, t in zip(axes, ['smr', 'single', 'dual'], ['(a) SMR', '(b) Single N$_2$ expander', '(c) Dual N$_2$ expander']):
        pfd(ax, k, t)
    # legend
    lax = fig.add_axes([0, 0, 1, 0.06]); lax.axis('off'); lax.set_xlim(0, 1); lax.set_ylim(0, 1)
    for x, c, t in [(0.04, NG, 'Natural gas / LNG'), (0.24, HP, 'High-pressure refrigerant'), (0.47, LP, 'Low-pressure refrigerant')]:
        lax.plot([x, x + 0.04], [0.5, 0.5], color=c, lw=1.6); lax.text(x + 0.05, 0.5, t, va='center', fontsize=6.3)
    lax.text(0.70, 0.5, 'IC, intercooler; AC, aftercooler; JT, Joule–Thomson', va='center', fontsize=6.3)
    save(fig, 'Figure_2')

# ------------------------------------------------------------------ Figure 4: envelope
FIELD_COL = {'A2': '#0072B2', 'A3': '#56B4E9', 'A4': '#009E73', 'A6': '#CC79A7', 'A7': '#E69F00', 'A8': '#7f3c8d'}
LET = {'A2': 'A', 'A3': 'B', 'A4': 'C', 'A5': 'D', 'A6': 'E', 'A7': 'F', 'A8': 'G'}
def env(path):
    d = pd.read_csv(path)
    c2 = [c for c in d.columns if c.startswith('treated_') and c not in ('treated_C1', 'treated_CO2', 'treated_N2')]
    d['N2'] = d.treated_N2 * 100; d['C2p'] = d[c2].sum(axis=1) * 100
    return d
def fig4():
    m = env(f'{REPO}/lng_robust/results/envelopes/main/scenarios.csv')
    D = env(f'{REPO}/lng_robust/results/envelopes/fieldD/scenarios.csv'); D = D[D.id == 'A5'].iloc[0]
    fig = plt.figure(figsize=(140 * MM, 86 * MM))
    ax = fig.add_axes([0.085, 0.13, 0.5, 0.82]); ax2 = fig.add_axes([0.66, 0.13, 0.32, 0.82])
    for a, xlim in ((ax, (-1.5, 50)), (ax2, (-0.03, 0.9))):
        for pid, g in m[m.synthetic].groupby('parent_anchor'):
            a.scatter(g.N2, g.C2p, s=12, color=FIELD_COL[pid], alpha=0.45, lw=0, zorder=2)
        an = m[~m.synthetic]
        for _, r in an.iterrows():
            if xlim[0] <= r.N2 <= xlim[1]:
                a.scatter(r.N2, r.C2p, s=46, marker='D', color=FIELD_COL[r.id], ec=INK, lw=0.6, zorder=4)
                dx = 0.02 * (xlim[1] - xlim[0])
                a.text(r.N2 + dx, r.C2p + 0.6, LET[r.id], fontsize=7, weight='bold', color=INK, zorder=5)
        a.set_xlim(*xlim); a.set_ylim(0, 28)
        a.spines[['top', 'right']].set_visible(False)
        a.grid(alpha=0.25, lw=0.4)
    ax.scatter(D.N2, D.C2p, s=60, marker='X', color='#D55E00', ec=INK, lw=0.5, zorder=4)
    ax.text(D.N2 - 1, D.C2p + 1.2, 'D (excluded)', fontsize=6.5, ha='right', color='#D55E00', weight='bold')
    ax.add_patch(Rectangle((-0.5, 0.3), 1.5, 27.2, fc='none', ec='#8a96a3', lw=0.7, ls='--'))
    ax.text(1.6, 26.6, 'enlarged at right', fontsize=6, color='#5b6b7c', va='top')
    ax.set_xlabel('Nitrogen in treated feed (mol%)'); ax.set_ylabel('Ethane and heavier in treated feed (mol%)')
    ax2.set_xlabel('Nitrogen in treated feed (mol%)'); ax2.set_title('(b) Low-nitrogen fields, enlarged', fontsize=7, loc='left', color=INK)
    ax.set_title('(a) All fields', fontsize=7, loc='left', color=INK)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker='D', ls='', color='#9aa5b1', mec=INK, ms=5, label='Measured anchor (field letter)'),
         Line2D([], [], marker='o', ls='', color='#9aa5b1', alpha=0.6, ms=4, label='Synthetic scenario, coloured by parent field'),
         Line2D([], [], marker='X', ls='', color='#D55E00', mec=INK, ms=6, label='Field D (sensitivity case only)')]
    ax.legend(handles=h, frameon=False, fontsize=6.2, loc='upper right', bbox_to_anchor=(1.02, 0.86))
    save(fig, 'Figure_4')

fig1(); fig2(); fig4()
print('ok')
