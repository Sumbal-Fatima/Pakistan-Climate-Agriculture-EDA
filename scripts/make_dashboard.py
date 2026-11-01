"""Build an interactive HTML dashboard (docs/index.html) from the project's CSV files.
Run from the project root:  python scripts/make_dashboard.py
Host it free with GitHub Pages (Settings > Pages > deploy from branch, /docs folder)."""
import numpy as np, pandas as pd, plotly.graph_objects as go, pymannkendall as mk
from plotly.subplots import make_subplots
from scipy.stats import theilslopes

INK, MUTED, SURF, GRID = '#0b0b0b', '#52514e', '#fcfcfb', '#e7e6e2'
BLUE, ORANGE, AQUA, GREY = '#2a78d6', '#eb6834', '#1baf7a', '#b9b8b3'
LAYOUT = dict(paper_bgcolor=SURF, plot_bgcolor=SURF, font=dict(color=INK, family='Inter, Arial, sans-serif', size=13),
              margin=dict(l=60, r=30, t=120, b=50), hoverlabel=dict(bgcolor='white'), legend=dict(orientation='h', y=-.2))
AX = dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)

def T(main, sub=''):
    return dict(text=main + (f'<br><sup>{sub}</sup>' if sub else ''), x=0, xanchor='left', y=.97, yanchor='top', yref='container', font=dict(size=16))
MENU = dict(x=0, xanchor='left', y=1.0, yanchor='bottom', pad=dict(t=0, b=6))

# ---------- data ----------
t = pd.read_csv('data/temp.csv'); pk = t[(t.country == 'Pakistan')].dropna(subset=['avg_temp']).drop_duplicates()  # exact repeated rows would double-count readings
d = pk.groupby('year').avg_temp.mean().reset_index(name='temp'); d = d[d.year >= 1870].reset_index(drop=True)
y = pd.read_csv('data/yield_df.csv', index_col=0).rename(columns={'hg/ha_yield': 'yld'})
yc = y.groupby(['Area', 'Item', 'Year'], as_index=False).agg(yld=('yld', 'first')); yc['t_ha'] = yc.yld / 10000

def load(path, city):
    c = pd.read_csv(path); c.columns = [x.strip() for x in c.columns]
    c = c.rename(columns={'Highest Maximum Temperature in Celsius': 'hi', 'Lowest Minimum Temperature in Celsius': 'lo', 'Monthly Heaviest Rainfall in mm': 'rain'})
    c = c[c.Month != 'Annual']; c['city'] = city; return c
cl = pd.concat([load('data/peshawar.csv', 'Peshawar'), load('data/gilgit.csv', 'Gilgit')])

# ---------- A. temperature explorer ----------
figA = go.Figure()
figA.add_scatter(x=d.year, y=d.temp, mode='markers', marker=dict(color=BLUE, size=6, opacity=.5), name='Annual mean', hovertemplate='%{x}: %{y:.2f} °C<extra></extra>')
figA.add_scatter(x=d.year, y=d.temp.rolling(10, center=True).mean(), mode='lines', line=dict(color=BLUE, width=3), name='10-year average', hovertemplate='%{x}: %{y:.2f} °C<extra>10-yr avg</extra>')
starts = [1870, 1900, 1950, 1980]; buttons = []
for k, a in enumerate(starts):
    s = d[d.year >= a]; sl, ic, lo, up = theilslopes(s.temp.values, s.year.values); hr = mk.hamed_rao_modification_test(s.temp.values)
    figA.add_scatter(x=s.year, y=ic + sl * s.year, mode='lines', line=dict(color=ORANGE, width=3, dash='dash'), visible=(k == 1), name=f'Trend since {a}',
                     hovertemplate=f'Trend since {a}: +{sl*10:.2f} °C/decade<extra></extra>')
    vis = [True, True] + [i == k for i in range(len(starts))]
    buttons.append(dict(label=f'Since {a}', method='update', args=[{'visible': vis}, {'title.text': f'Pakistan temperature: +{sl*10:.2f} °C per decade since {a}<br><sup>95% CI {lo*10:.2f} to {up*10:.2f} · autocorrelation-adjusted p = {hr.p:.1g}</sup>'}]))
s = d[d.year >= 1900]; sl, ic, lo, up = theilslopes(s.temp.values, s.year.values); hr = mk.hamed_rao_modification_test(s.temp.values)
figA.update_layout(**LAYOUT, title=T(f'Pakistan temperature: +{sl*10:.2f} °C per decade since 1900', f'95% CI {lo*10:.2f} to {up*10:.2f} · autocorrelation-adjusted p = {hr.p:.1g}'),
                   yaxis_title='Annual mean temperature (°C)', updatemenus=[dict(buttons=buttons, active=1, **MENU)], xaxis=AX, yaxis=AX)

# ---------- B. crop explorer ----------
crops = ['Wheat', 'Rice, paddy', 'Maize', 'Potatoes', 'Sorghum', 'Sweet potatoes', 'Soybeans']; figB = go.Figure(); buttons = []
for k, c in enumerate(crops):
    g = yc[(yc.Area == 'Pakistan') & (yc.Item == c)].sort_values('Year'); sl, ic, lo, up = theilslopes(g.t_ha.values, g.Year.values); hr = mk.hamed_rao_modification_test(g.t_ha.values)
    gi = yc[(yc.Area == 'India') & (yc.Item == c)].sort_values('Year')
    figB.add_scatter(x=g.Year, y=g.t_ha, mode='lines+markers', line=dict(color=ORANGE, width=3), name='Pakistan', visible=(k == 0), hovertemplate='%{x}: %{y:.2f} t/ha<extra>Pakistan</extra>')
    figB.add_scatter(x=gi.Year, y=gi.t_ha, mode='lines', line=dict(color=BLUE, width=2.4), name='India (comparison)', visible=(k == 0), hovertemplate='%{x}: %{y:.2f} t/ha<extra>India</extra>')
    figB.add_scatter(x=g.Year, y=ic + sl * g.Year, mode='lines', line=dict(color=INK, width=1.6, dash='dash'), name='Pakistan trend', visible=(k == 0), hoverinfo='skip')
    vis = [False] * (3 * len(crops)); vis[3 * k:3 * k + 3] = [True] * 3
    verdict = f'+{sl:.3f} t/ha per year (95% CI {lo:.3f} to {up:.3f}; autocorrelation-adjusted p = {hr.p:.2g})' if hr.p < .05 else f'no significant trend (autocorrelation-adjusted p = {hr.p:.2g})'
    buttons.append(dict(label=c.replace(', paddy', ''), method='update', args=[{'visible': vis}, {'title.text': f'{c}, Pakistan<br><sup>{verdict}</sup>'}]))
g0 = yc[(yc.Area == 'Pakistan') & (yc.Item == 'Wheat')]; sl, ic, lo, up = theilslopes(g0.sort_values('Year').t_ha.values, g0.sort_values('Year').Year.values); hr = mk.hamed_rao_modification_test(g0.sort_values('Year').t_ha.values)
figB.update_layout(**LAYOUT, title=T('Wheat, Pakistan', f'+{sl:.3f} t/ha per year (95% CI {lo:.3f} to {up:.3f}; autocorrelation-adjusted p = {hr.p:.2g})'), yaxis_title='Yield (t/ha)',
                   updatemenus=[dict(buttons=buttons, **MENU)], xaxis=AX, yaxis=AX)

# ---------- C. wheat ranking ----------
w = yc[yc.Item == 'Wheat'].groupby('Area').t_ha.mean().sort_values(ascending=False); rank = list(w.index).index('Pakistan') + 1
show = pd.concat([w.head(15), w[['India', 'Egypt', 'Pakistan']]]); show = show[~show.index.duplicated()].sort_values()
cols = [ORANGE if a == 'Pakistan' else BLUE if a in ('India', 'Egypt') else GREY for a in show.index]
figC = go.Figure(go.Bar(x=show.values, y=show.index, orientation='h', marker_color=cols, hovertemplate='%{y}: %{x:.2f} t/ha<extra></extra>', text=[f'{v:.1f}' for v in show.values], textposition='outside'))
figC.update_layout(**{**LAYOUT, 'margin': dict(l=110, r=40, t=70, b=50)}, title=T(f'Wheat yield 1990-2013: Pakistan ranks {rank} of {len(w)} countries'), xaxis_title='Mean yield (t/ha)', height=520, xaxis=AX, yaxis=dict(gridcolor=SURF))

# ---------- D. climate extremes ----------
figD = make_subplots(rows=1, cols=2, subplot_titles=('Peshawar', 'Gilgit'), shared_yaxes=True)
for j, (city, col) in enumerate([('Peshawar', BLUE), ('Gilgit', ORANGE)], 1):
    c = cl[cl.city == city]; m = [x[:3] for x in c.Month]
    figD.add_scatter(x=m, y=c.hi, mode='lines+markers', line=dict(color=col, width=3), name=f'{city} record high', row=1, col=j, customdata=c.rain, hovertemplate='%{x}: %{y} °C<extra>record high</extra>')
    figD.add_scatter(x=m, y=c.lo, mode='lines+markers', line=dict(color=col, width=3, dash='dash'), fill='tonexty', fillcolor='rgba(120,120,120,.10)', name=f'{city} record low', row=1, col=j, hovertemplate='%{x}: %{y} °C<extra>record low</extra>')
figD.update_layout(**{**LAYOUT, 'margin': dict(l=60, r=30, t=100, b=50)}, title=T('Record temperature range by month', 'Solid lines are record highs, dashed lines are record lows. Hover for values.'), yaxis_title='Temperature (°C)')
figD.update_xaxes(**AX); figD.update_yaxes(**AX)

# ---------- page ----------
parts = [f.to_html(full_html=False, include_plotlyjs=(True if i == 0 else False), config=dict(displaylogo=False)) for i, f in enumerate([figA, figB, figC, figD])]
head = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Climate and Agriculture in Pakistan</title><style>body{margin:0;background:#fcfcfb;color:#0b0b0b;font-family:Inter,Arial,sans-serif;line-height:1.55}
main{max-width:980px;margin:0 auto;padding:24px 16px 60px}h1{font-size:1.7rem;margin:.2em 0}h2{font-size:1.15rem;margin:2em 0 .2em}p{color:#52514e;margin:.2em 0 .8em}
.note{border-left:4px solid #eb6834;padding:.2em 1em;background:#f5f4f0}</style></head><body><main>
<h1>Climate and Agriculture in Pakistan</h1><p>Interactive companion to the EDA notebook. By Sumbal Fatima, BSc Agricultural Engineering, University of Agriculture, Faisalabad.</p>
<p class="note">Exploratory analysis of public Kaggle data. Trend tests show whether a series changes, not why. Hover over charts for values and use the menus to switch views.</p>"""
secs = [('1. Temperature trend', 'Pick a start year. Orange dashes are the Sen slope. p-values are autocorrelation-adjusted (Hamed-Rao). Early years before 1870 are excluded as unreliable.'),
        ('2. Crop yields, Pakistan vs India', 'Choose a crop. Maize jumped after about 2002, so a straight line fits it poorly.'),
        ('3. Wheat yield ranking', 'Pakistan in orange, India and Egypt in blue.'),
        ('4. Record climate extremes', 'Record highs (solid) and lows (dashed) for each month.')]
html = head + ''.join(f'<h2>{h}</h2><p>{p}</p>{part}' for (h, p), part in zip(secs, parts)) + '<p style="margin-top:2em">Data: Kaggle (Tayyar Hussain; patelris Crop Yield Prediction Dataset, from FAO and World Bank data).</p></main></body></html>'
open('docs/index.html', 'w', encoding='utf-8').write(html); print('wrote docs/index.html', len(html) // 1024, 'KB')
