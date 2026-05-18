"""
AZ Dashboard v2 – Full Inventory Intelligence System
Single-file Dash application with all 6 pages.
Run: python app.py  →  open http://localhost:8050
"""

import base64, io, json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dash import (Dash, html, dcc, dash_table, ALL,
                  Input, Output, State, no_update, callback_context)
import dash_bootstrap_components as dbc

from modules.processor import process, STRATEGY

# ══════════════════════════════════════════════════════
# APP INIT
# ══════════════════════════════════════════════════════

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="AZ Inventory Dashboard",
    meta_tags=[{"name": "viewport",
                "content": "width=device-width, initial-scale=1"}],
)
server = app.server   # for deployment

# ══════════════════════════════════════════════════════
# THEME
# ══════════════════════════════════════════════════════

DARK = {
    "bg0":"#0D1117","bg1":"#161B22","bg2":"#1C2128","bg3":"#21262D",
    "border":"#30363D","t0":"#E6EDF3","t1":"#8B949E","t2":"#656D76",
    "blue":"#58A6FF","green":"#3FB950","amber":"#F0B429","red":"#F85149",
    "purple":"#BC8CFF","gold":"#C9A84C","gold2":"#F0CB6E",
    "tmpl":"plotly_dark",
}
LIGHT = {
    "bg0":"#FFFFFF","bg1":"#F6F8FA","bg2":"#FFFFFF","bg3":"#F6F8FA",
    "border":"#D0D7DE","t0":"#1F2328","t1":"#656D76","t2":"#8B949E",
    "blue":"#0969DA","green":"#1A7F37","amber":"#9A6700","red":"#CF222E",
    "purple":"#8250DF","gold":"#B8860B","gold2":"#DAA520",
    "tmpl":"plotly_white",
}

BC = {
    "A":"#3FB950","B":"#58A6FF","C":"#BC8CFF",
    "X":"#3FB950","Y":"#F0B429","Z":"#F85149",
    "F":"#3FB950","S":"#F0B429","N":"#F85149",
    "V":"#F85149","E":"#F0B429","D":"#8B949E",
    "H":"#F85149","M":"#F0B429","L":"#3FB950",
    "S_sde":"#F85149","D_sde":"#F0B429","E_sde":"#3FB950",
    "G":"#BC8CFF","O":"#8B949E","L_golf":"#58A6FF","F_golf":"#F0B429",
    "Stable":"#3FB950","Unstable":"#F0B429",
    "Intermittent":"#58A6FF","Lumpy":"#F85149","Non-moving":"#8B949E",
}
AC = {
    "Order":"#3FB950","Urgent Order":"#F85149","Urgent Review":"#F85149",
    "Monitor – Declining A":"#F0B429","Review":"#F0B429",
    "Do Not Order":"#F85149","Clear Stock":"#BC8CFF","Manual":"#8B949E",
}

def T(dark): return DARK if dark else LIGHT

def css(dark):
    t = T(dark)
    return f"""
* {{box-sizing:border-box;margin:0;padding:0;}}
body {{background:{t['bg0']};color:{t['t0']};
  font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;}}
::-webkit-scrollbar{{width:5px;height:5px;}}
::-webkit-scrollbar-track{{background:{t['bg1']};}}
::-webkit-scrollbar-thumb{{background:{t['border']};border-radius:3px;}}
.sidebar {{position:fixed;top:0;left:0;bottom:0;width:210px;
  background:{t['bg1']};border-right:1px solid {t['border']};
  display:flex;flex-direction:column;z-index:200;overflow-y:auto;}}
.main-content {{margin-left:210px;min-height:100vh;
  background:{t['bg0']};padding:24px;}}
.nav-item {{display:flex;align-items:center;gap:10px;padding:10px 16px;
  cursor:pointer;border-radius:6px;margin:2px 6px;
  color:{t['t1']};font-size:13px;transition:all 0.15s;
  border-left:3px solid transparent;text-decoration:none;}}
.nav-item:hover {{background:{t['bg3']};color:{t['t0']};}}
.nav-item.active {{background:{t['bg3']};color:{t['gold']};
  border-left:3px solid {t['gold']};font-weight:600;}}
.card {{background:{t['bg2']};border:1px solid {t['border']};
  border-radius:10px;padding:16px;margin-bottom:16px;}}
.kpi {{background:{t['bg1']};border-radius:8px;padding:16px;
  text-align:center;flex:1;min-width:120px;}}
.kpi-val {{font-size:28px;font-weight:700;
  font-family:'Consolas',monospace;line-height:1.2;}}
.kpi-lbl {{font-size:11px;color:{t['t1']};margin-top:4px;}}
.sec-title {{font-size:11px;font-weight:700;color:{t['t1']};
  text-transform:uppercase;letter-spacing:.07em;
  margin-bottom:12px;padding-bottom:6px;
  border-bottom:1px solid {t['border']};}}
.badge-cls {{display:inline-block;padding:2px 8px;border-radius:4px;
  font-size:11px;font-weight:700;font-family:'Consolas',monospace;
  text-align:center;min-width:24px;}}
.alert-red {{background:rgba(248,81,73,.12);border:1px solid rgba(248,81,73,.35);
  border-radius:8px;padding:12px 16px;margin-bottom:10px;
  color:#F85149;font-size:13px;}}
.alert-amber {{background:rgba(240,180,41,.12);border:1px solid rgba(240,180,41,.35);
  border-radius:8px;padding:12px 16px;margin-bottom:10px;
  color:{t['amber']};font-size:13px;}}
.upload-zone {{border:2px dashed {t['border']};border-radius:14px;
  padding:56px 40px;text-align:center;cursor:pointer;
  transition:border-color .2s;background:{t['bg1']};}}
.upload-zone:hover {{border-color:{t['gold']};}}
.row-flex {{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;}}
.row-flex > * {{flex:1;min-width:240px;}}
.theme-btn {{background:{t['bg3']};border:1px solid {t['border']};
  border-radius:20px;padding:5px 14px;cursor:pointer;
  font-size:12px;color:{t['t1']};display:inline-flex;
  align-items:center;gap:6px;transition:all .15s;}}
.theme-btn:hover {{border-color:{t['gold']};color:{t['gold']};}}
"""

def az_logo_svg(size=42):
    gold = "#C9A84C"
    return html.Div(
        "A.Z",
        style={
            "width": str(size)+"px",
            "height": str(size)+"px",
            "borderRadius": "50%",
            "border": f"2px solid {gold}",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "color": gold,
            "fontSize": str(size//3)+"px",
            "fontWeight": "700",
            "fontFamily": "Consolas,monospace",
            "letterSpacing": "1px",
            "flexShrink": "0",
        }
    )

PAGES = [
    ("overview",       "◈", "Overview"),
    ("classification", "⊞", "Classification"),
    ("ml",             "⟁", "ML & Demand"),
    ("inventory",      "◫", "Inventory"),
    ("anylogic",       "⟳", "AnyLogic Export"),
    ("help",           "?", "Help"),
]

def sidebar(dark, active):
    t = T(dark)
    items = []
    for pid, icon, label in PAGES:
        cls = "nav-item active" if pid == active else "nav-item"
        items.append(html.Div(
            [html.Span(icon, style={"fontSize":"15px","minWidth":"18px"}),
             html.Span(label)],
            id={"type":"nav","index":pid},
            n_clicks=0, className=cls,
        ))
    return html.Div([
        html.Div([az_logo_svg(38),
                  html.Div([
                      html.Div("AZ Dashboard",
                               style={"fontSize":"14px","fontWeight":"700","color":t["t0"]}),
                      html.Div("Inventory Intelligence",
                               style={"fontSize":"10px","color":t["t2"]}),
                  ])],
                 style={"display":"flex","alignItems":"center","gap":"10px",
                        "padding":"18px 16px 14px","borderBottom":f"1px solid {t['border']}",
                        "marginBottom":"6px"}),
        html.Div(items, style={"flex":"1"}),
        html.Div([
            html.Hr(style={"border":f"1px solid {t['border']}","margin":"8px 0"}),
            html.Div(
                [html.Span("☀" if dark else "☾"),
                 html.Span("Light Mode" if dark else "Dark Mode",
                           style={"marginLeft":"6px"})],
                id="theme-btn", n_clicks=0, className="theme-btn",
                style={"margin":"4px 10px 8px"}
            ),
            html.Div("v2.0 · 5 research papers",
                     style={"fontSize":"10px","color":t["t2"],
                            "textAlign":"center","paddingBottom":"12px"}),
        ])
    ], className="sidebar")

# ══════════════════════════════════════════════════════
# UPLOAD SCREEN
# ══════════════════════════════════════════════════════

def upload_screen(dark):
    t = T(dark)
    return html.Div([
        html.Div([
            az_logo_svg(64),
            html.H1("AZ Inventory Dashboard",
                    style={"color":t["gold"],"marginTop":"14px","fontSize":"28px",
                           "fontFamily":"Consolas,monospace","fontWeight":"700"}),
            html.P("Multi-criteria inventory classification & analytics",
                   style={"color":t["t1"],"marginBottom":"28px"}),
            dcc.Upload(
                id="upload",
                children=html.Div([
                    html.Div("📦", style={"fontSize":"52px","marginBottom":"14px"}),
                    html.Div("Drag & Drop your CSV file here",
                             style={"fontSize":"18px","fontWeight":"600",
                                    "color":t["t0"],"marginBottom":"6px"}),
                    html.Div("or click to browse",
                             style={"color":t["t1"],"fontSize":"13px","marginBottom":"18px"}),
                    html.Div([
                        *[html.Span(c, style={
                            "background":"rgba(201,168,76,.1)","color":t["gold"],
                            "border":"1px solid rgba(201,168,76,.3)",
                            "borderRadius":"4px","padding":"2px 8px",
                            "margin":"2px","display":"inline-block","fontSize":"11px"
                        }) for c in ["שם פריט","2021-2025","מחיר קניה",
                                      "תנועות","מטבע","חוסר","יתרה במלאי"]],
                    ]),
                ], className="upload-zone"),
            ),
            html.Div(id="upload-msg",
                     style={"marginTop":"14px","fontSize":"13px","color":t["t1"]}),
        ], style={"display":"flex","flexDirection":"column","alignItems":"center",
                  "justifyContent":"center","minHeight":"100vh","padding":"32px"}),
    ], style={"background":t["bg0"]})

# ══════════════════════════════════════════════════════
# HELPER WIDGETS
# ══════════════════════════════════════════════════════

def kpi(label, value, color, suffix=""):
    return html.Div([
        html.Div(f"{value:,}{suffix}" if isinstance(value,int) else f"{value}{suffix}",
                 className="kpi-val", style={"color":color}),
        html.Div(label, className="kpi-lbl"),
    ], className="kpi")

def badge(val, color):
    return html.Span(val, className="badge-cls", style={
        "background":f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},.15)",
        "color":color,
    })

def section(title, children, dark, extra_style=None):
    t = T(dark)
    s = {"background":t["bg2"],"border":f"1px solid {t['border']}",
         "borderRadius":"10px","padding":"16px","marginBottom":"16px"}
    if extra_style: s.update(extra_style)
    return html.Div([html.Div(title, className="sec-title"), *children], style=s)

def fig_layout(dark, height=240):
    t = T(dark)
    return dict(
        template=t["tmpl"], height=height,
        margin=dict(t=16,b=16,l=40,r=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["t1"], size=11),
        xaxis=dict(gridcolor=t["border"],linecolor=t["border"]),
        yaxis=dict(gridcolor=t["border"],linecolor=t["border"]),
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color=t["t1"])),
    )

# ══════════════════════════════════════════════════════
# PAGE 1 – OVERVIEW
# ══════════════════════════════════════════════════════

def page_overview(df, dark):
    t = T(dark)

    total      = len(df)
    avg_health = int(df["health"].mean())
    dead       = int((df["stock_status"]=="Dead Stock").sum())
    stockout   = int((df["stock_status"]=="Stockout").sum())
    critical   = int(df["is_critical"].sum())
    trending_up= int((df["trend"]=="up").sum())
    anomalies  = int(df["has_anomaly"].sum())
    overstock  = int((df["stock_status"]=="Overstock").sum())
    hc = t["green"] if avg_health>=70 else t["amber"] if avg_health>=40 else t["red"]

    # Alerts
    alerts = []
    if critical:
        alerts.append(html.Div([
            html.Strong(f"⚠ {critical} critical items: "),
            "Vital (VED=V) + Non-moving (FSN=N) – immediate action required"
        ], className="alert-red"))
    if stockout:
        alerts.append(html.Div([
            html.Strong(f"⚠ {stockout} stockouts "),
            "– items with zero inventory, service risk"
        ], className="alert-red"))
    if anomalies:
        alerts.append(html.Div([
            html.Strong(f"⚡ {anomalies} anomalous demand records "),
            "(negative values per Hong et al. 2024 detection method)"
        ], className="alert-amber"))
    if dead:
        alerts.append(html.Div([
            html.Strong(f"📦 {dead} dead stock items "),
            "– FSN=N with inventory on hand, recommend clearing"
        ], className="alert-amber"))

    # KPI row
    kpis = html.Div([
        kpi("Total Items",   total,      t["t0"]),
        kpi("Avg Health",    avg_health, hc, "/100"),
        kpi("Dead Stock",    dead,       t["red"]),
        kpi("Stockouts",     stockout,   t["red"]),
        kpi("Critical",      critical,   t["amber"]),
        kpi("Overstock",     overstock,  t["purple"]),
        kpi("Trending Up",   trending_up,t["green"]),
        kpi("Anomalies",     anomalies,  t["amber"]),
    ], style={"display":"flex","gap":"10px","flexWrap":"wrap","marginBottom":"16px"})

    # ABC bar
    abc_c = df["ABC"].value_counts().reindex(["A","B","C"], fill_value=0)
    fig_abc = go.Figure(go.Bar(
        x=["A","B","C"], y=abc_c.values,
        marker_color=[BC["A"],BC["B"],BC["C"]],
        text=abc_c.values, textposition="outside",
        textfont=dict(color=t["t0"]),
    ))
    fig_abc.update_layout(**fig_layout(dark,220))

    # XYZ bar
    xyz_c = df["XYZ"].value_counts().reindex(["X","Y","Z"], fill_value=0)
    fig_xyz = go.Figure(go.Bar(
        x=["X","Y","Z"], y=xyz_c.values,
        marker_color=[BC["X"],BC["Y"],BC["Z"]],
        text=xyz_c.values, textposition="outside",
        textfont=dict(color=t["t0"]),
    ))
    fig_xyz.update_layout(**fig_layout(dark,220))

    # Demand pattern bar
    pats = ["Stable","Unstable","Intermittent","Lumpy","Non-moving"]
    dp_c = df["demand_pattern"].value_counts().reindex(pats, fill_value=0)
    fig_dp = go.Figure(go.Bar(
        x=pats, y=dp_c.values,
        marker_color=[BC.get(p,"#8B949E") for p in pats],
        text=dp_c.values, textposition="outside",
        textfont=dict(color=t["t0"]),
    ))
    fig_dp.update_layout(**fig_layout(dark,220))

    # ABC×XYZ heatmap
    mat = [[int(((df.ABC==a)&(df.XYZ==x)).sum()) for x in ["X","Y","Z"]]
           for a in ["A","B","C"]]
    strat_labels = {k:v["label"] for k,v in STRATEGY.items()}
    anns = [dict(x=j,y=i,
                 text=f"<b>{mat[i][j]}</b><br><span style='font-size:9px'>"
                      f"{strat_labels.get('ABC'[i]+'XYZ'[j],'')}</span>",
                 showarrow=False, font=dict(color="white",size=11))
            for i in range(3) for j in range(3)]
    fig_mat = go.Figure(go.Heatmap(
        z=mat, x=["X","Y","Z"], y=["A","B","C"],
        colorscale="Blues", showscale=False,
        hoverongaps=False,
    ))
    fig_mat.update_layout(**fig_layout(dark,240), annotations=anns)
    fig_mat.update_yaxes(autorange="reversed")

    # Stock status donut
    st_labs = ["OK","Overstock","Dead Stock","Stockout","Low Stock"]
    st_cols = {"OK":t["green"],"Overstock":t["purple"],
               "Dead Stock":t["red"],"Stockout":t["red"],"Low Stock":t["amber"]}
    st_c = df["stock_status"].value_counts().reindex(st_labs, fill_value=0)
    fig_st = go.Figure(go.Pie(
        labels=st_labs, values=st_c.values, hole=0.58,
        marker_colors=[st_cols[s] for s in st_labs],
        textinfo="label+percent",
        textfont=dict(size=11, color=t["t0"]),
        insidetextorientation="radial",
    ))
    fig_st.update_layout(**fig_layout(dark,240), showlegend=False)

    # Yearly sales trend
    yr_cols = [c for c in ["2021","2022","2023","2024","2025"] if c in df.columns]
    yr_tot  = [df[c].clip(lower=0).sum() for c in yr_cols]
    fig_yr  = go.Figure(go.Scatter(
        x=yr_cols, y=yr_tot, mode="lines+markers",
        line=dict(color=t["gold"],width=2.5),
        marker=dict(size=7,color=t["gold"]),
        fill="tozeroy", fillcolor=f"rgba(201,168,76,.10)",
    ))
    fig_yr.update_layout(**fig_layout(dark,220))

    # Health distribution
    bins   = [0,20,40,60,80,100]
    labels = ["0-20","21-40","41-60","61-80","81-100"]
    h_col  = [t["red"],t["red"],t["amber"],t["green"],t["green"]]
    counts = pd.cut(df["health"], bins=bins).value_counts().sort_index()
    fig_h  = go.Figure(go.Bar(
        x=labels, y=counts.values,
        marker_color=h_col,
        text=counts.values, textposition="outside",
        textfont=dict(color=t["t0"]),
    ))
    fig_h.update_layout(**fig_layout(dark,220))

    # Top critical items table
    crit_df = df[df["is_critical"]].head(8)
    if len(crit_df)==0:
        crit_df = df[(df["VED"]=="V")&(df["stock_status"].isin(["Stockout","Low Stock"]))].head(8)
    crit_rows = []
    for _, r in crit_df.iterrows():
        name = str(r.get("שם פריט", r.get("מפתח","")))[:32]
        act  = r.get("action","Review")
        ac   = AC.get(act,t["t1"])
        crit_rows.append(html.Tr([
            html.Td(name,  style={"padding":"7px 12px","fontSize":"12px","color":t["t0"]}),
            html.Td(badge(r.get("ABC","?"),BC.get(r.get("ABC","?"),t["t1"])),
                    style={"padding":"7px 8px"}),
            html.Td(badge(r.get("VED","?"),BC.get(r.get("VED","?"),t["t1"])),
                    style={"padding":"7px 8px"}),
            html.Td(badge(r.get("FSN","?"),BC.get(r.get("FSN","?"),t["t1"])),
                    style={"padding":"7px 8px"}),
            html.Td(html.Span(act,style={
                        "background":f"rgba({int(ac[1:3],16)},{int(ac[3:5],16)},{int(ac[5:7],16)},.15)",
                        "color":ac,"padding":"2px 8px","borderRadius":"4px",
                        "fontSize":"11px","fontWeight":"600"}),
                    style={"padding":"7px 8px"}),
        ], style={"borderBottom":f"1px solid {t['border']}22"}))

    return html.Div([
        html.Div([
            html.H2("Overview", style={"fontSize":"20px","fontWeight":"600",
                                        "color":t["t0"],"margin":"0"}),
            html.Span(f"{total:,} items loaded",
                      style={"fontSize":"13px","color":t["t1"],"marginLeft":"12px"}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"18px",
                  "paddingBottom":"12px","borderBottom":f"1px solid {t['border']}"}),

        html.Div(alerts) if alerts else None,
        kpis,

        # Row 1: ABC / XYZ / Demand
        html.Div([
            section("ABC – Annual Demand Value",
                    [dcc.Graph(figure=fig_abc,config={"displayModeBar":False})],dark),
            section("XYZ – Demand Variability",
                    [dcc.Graph(figure=fig_xyz,config={"displayModeBar":False})],dark),
            section("Demand Pattern (ADI + CV²) [Hong et al. 2024]",
                    [dcc.Graph(figure=fig_dp, config={"displayModeBar":False})],dark,
                    {"flex":"2"}),
        ], className="row-flex"),

        # Row 2: Matrix / Stock / Trend / Health
        html.Div([
            section("ABC × XYZ Strategy Matrix",
                    [dcc.Graph(figure=fig_mat,config={"displayModeBar":False})],dark),
            section("Stock Status Distribution",
                    [dcc.Graph(figure=fig_st, config={"displayModeBar":False})],dark),
            section("Total Sales Trend 2021–2025",
                    [dcc.Graph(figure=fig_yr, config={"displayModeBar":False})],dark),
            section("Health Score Distribution",
                    [dcc.Graph(figure=fig_h,  config={"displayModeBar":False})],dark),
        ], className="row-flex"),

        # Critical items
        section("Critical Items Requiring Immediate Attention",
                [html.Table([
                    html.Thead(html.Tr([
                        html.Th(h, style={"padding":"7px 12px","color":t["t1"],"fontSize":"11px",
                                          "fontWeight":"600","textTransform":"uppercase",
                                          "borderBottom":f"1px solid {t['border']}"})
                        for h in ["Item Name","ABC","VED","FSN","Recommended Action"]
                    ])),
                    html.Tbody(crit_rows if crit_rows else [
                        html.Tr(html.Td("✓ No critical items found",
                                        colSpan=5,
                                        style={"padding":"20px","textAlign":"center",
                                               "color":t["green"],"fontSize":"13px"}))
                    ])
                ], style={"width":"100%","borderCollapse":"collapse"})],
                dark),
    ])

# ══════════════════════════════════════════════════════
# PAGE 2 – CLASSIFICATION
# ══════════════════════════════════════════════════════

def page_classification(df, dark):
    t = T(dark)

    disp_cols = [
        "idx","שם פריט","ABC","HML","XYZ","FSN","VED","SDE","GOLF",
        "demand_pattern","class_code","health","action","strat_label",
    ]
    avail = [c for c in disp_cols if c in df.columns]
    tbl   = df[avail].copy()
    rename = {"idx":"#","שם פריט":"Item","demand_pattern":"Demand Type",
               "class_code":"Code","health":"Health","action":"Action",
               "strat_label":"Strategy"}
    tbl.rename(columns=rename, inplace=True)

    cond = [
        {"if":{"row_index":"odd"},"backgroundColor":t["bg1"]},
        # ABC colors
        *[{"if":{"filter_query":f"{{ABC}} = '{v}'","column_id":"ABC"},
           "color":BC[v],"fontWeight":"700"} for v in ["A","B","C"]],
        # XYZ colors
        *[{"if":{"filter_query":f"{{XYZ}} = '{v}'","column_id":"XYZ"},
           "color":BC[v],"fontWeight":"700"} for v in ["X","Y","Z"]],
        # FSN colors
        *[{"if":{"filter_query":f"{{FSN}} = '{v}'","column_id":"FSN"},
           "color":BC[v],"fontWeight":"700"} for v in ["F","S","N"]],
        # VED
        *[{"if":{"filter_query":f"{{VED}} = '{v}'","column_id":"VED"},
           "color":BC[v],"fontWeight":"700"} for v in ["V","E","D"]],
        # Action colors
        *[{"if":{"filter_query":f"{{Action}} = '{v}'","column_id":"Action"},
           "color":AC.get(v,t["t1"]),"fontWeight":"700"}
          for v in AC],
        # Health coloring
        {"if":{"filter_query":"{Health} < 40","column_id":"Health"},
         "color":t["red"],"fontWeight":"700"},
        {"if":{"filter_query":"{Health} >= 70","column_id":"Health"},
         "color":t["green"],"fontWeight":"700"},
        {"if":{"filter_query":"{Health} >= 40 && {Health} < 70","column_id":"Health"},
         "color":t["amber"],"fontWeight":"700"},
    ]

    return html.Div([
        html.Div([
            html.H2("Classification", style={"fontSize":"20px","fontWeight":"600",
                                              "color":t["t0"],"margin":"0"}),
            html.Span(f"{len(df):,} items · 9 methods · AHP-K-VETO logic",
                      style={"fontSize":"13px","color":t["t1"],"marginLeft":"12px"}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"18px",
                  "paddingBottom":"12px","borderBottom":f"1px solid {t['border']}"}),

        # Legend
        html.Div([
            html.Span("Classification colors: ", style={"color":t["t1"],"fontSize":"12px","marginRight":"8px"}),
            *[badge(k,v) for k,v in list(BC.items())[:12] if len(k)==1],
        ], style={"marginBottom":"12px","display":"flex","alignItems":"center",
                  "flexWrap":"wrap","gap":"4px"}),

        # Search + filters
        html.Div([
            dcc.Input(id="cls-search", type="text",
                      placeholder="🔍  Search item name or code...",
                      debounce=True,
                      style={"background":t["bg3"],"border":f"1px solid {t['border']}",
                             "borderRadius":"6px","color":t["t0"],"padding":"6px 12px",
                             "fontSize":"13px","flex":"2","outline":"none",
                             "minWidth":"200px"}),
            *[dcc.Dropdown(id=f"cls-{fid}", options=[{"label":o,"value":o} for o in opts],
                           placeholder=ph, multi=True, clearable=True,
                           style={"minWidth":"90px","fontSize":"12px"})
              for fid, opts, ph in [
                  ("abc",["A","B","C"],"ABC"),
                  ("xyz",["X","Y","Z"],"XYZ"),
                  ("fsn",["F","S","N"],"FSN"),
                  ("ved",["V","E","D"],"VED"),
                  ("hml",["H","M","L"],"HML"),
                  ("pat",["Stable","Unstable","Intermittent","Lumpy","Non-moving"],"Pattern"),
                  ("act",list(AC.keys()),"Action"),
              ]],
        ], style={"display":"flex","gap":"8px","flexWrap":"wrap","marginBottom":"14px",
                  "alignItems":"center"}),

        html.Div(id="cls-count",
                 style={"fontSize":"12px","color":t["t1"],"marginBottom":"8px"}),

        html.Div([
            dash_table.DataTable(
                id="cls-table",
                columns=[{"name":c,"id":c,"deletable":False} for c in tbl.columns],
                data=tbl.to_dict("records"),
                page_size=50, page_action="native",
                sort_action="native", filter_action="native",
                style_table={"overflowX":"auto","borderRadius":"8px","border":f"1px solid {t['border']}"},
                style_cell={"backgroundColor":t["bg2"],"color":t["t0"],
                             "border":f"1px solid {t['border']}22",
                             "padding":"7px 12px","fontSize":"12px",
                             "fontFamily":"Segoe UI,sans-serif",
                             "textAlign":"left","maxWidth":"180px",
                             "overflow":"hidden","textOverflow":"ellipsis"},
                style_header={"backgroundColor":t["bg3"],"color":t["t1"],
                               "fontWeight":"700","fontSize":"11px",
                               "textTransform":"uppercase","letterSpacing":".05em",
                               "border":f"1px solid {t['border']}"},
                style_data_conditional=cond,
                style_filter={"backgroundColor":t["bg3"],"color":t["t0"],
                              "border":f"1px solid {t['border']}"},
                export_format="csv", export_headers="display",
                tooltip_data=[{c:{"value":str(r[c]),"type":"markdown"}
                                for c in tbl.columns} for r in tbl.to_dict("records")],
                tooltip_duration=None,
            )
        ]),
    ])

# ══════════════════════════════════════════════════════
# PAGE 3 – ML & DEMAND
# ══════════════════════════════════════════════════════

def page_ml(df, dark):
    t = T(dark)

    ml = df[df["MAPE"].notna()].copy()
    avg_mape = round(ml["MAPE"].mean(),1) if len(ml) else 0
    good     = int((ml["MAPE"]<20).sum())
    pct      = round(good/len(ml)*100) if len(ml) else 0

    # MAPE histogram
    bins_mape  = [0,10,20,35,50,101]
    labs_mape  = ["0-10%","10-20%","20-35%","35-50%",">50%"]
    cols_mape  = [t["green"],t["green"],t["amber"],t["red"],t["red"]]
    cnt_mape   = pd.cut(ml["MAPE"],bins=bins_mape).value_counts().sort_index()
    fig_mape   = go.Figure(go.Bar(
        x=labs_mape, y=cnt_mape.values,
        marker_color=cols_mape,
        text=cnt_mape.values, textposition="outside",
        textfont=dict(color=t["t0"]),
    ))
    fig_mape.update_layout(**fig_layout(dark,220))

    # Trend bar
    tr_c = df["trend"].value_counts()
    tr_col = {"up":t["green"],"stable":t["blue"],"down":t["red"]}
    fig_tr = go.Figure(go.Bar(
        x=tr_c.index.tolist(), y=tr_c.values,
        marker_color=[tr_col.get(x,t["t1"]) for x in tr_c.index],
        text=tr_c.values, textposition="outside",
        textfont=dict(color=t["t0"]),
    ))
    fig_tr.update_layout(**fig_layout(dark,220))

    # Demand pattern donut
    pat_c = df["demand_pattern"].value_counts()
    fig_dp = go.Figure(go.Pie(
        labels=pat_c.index.tolist(), values=pat_c.values, hole=0.56,
        marker_colors=[BC.get(p,"#8B949E") for p in pat_c.index],
        textinfo="label+percent",
        textfont=dict(size=11, color=t["t0"]),
    ))
    fig_dp.update_layout(**fig_layout(dark,240), showlegend=False)

    # Scatter: actual 2025 vs predicted 2025
    sc = df[(df["MAPE"].notna())&(df["pred_2025"]>0)].head(500)
    fig_sc = go.Figure()
    fig_sc.add_trace(go.Scatter(
        x=sc["pred_2025"], y=sc["2025"] if "2025" in sc.columns else sc["total_sales"]/5,
        mode="markers",
        marker=dict(color=t["gold"],size=4,opacity=0.6),
        name="Items",
    ))
    mx = sc["pred_2025"].max() if len(sc) else 1
    fig_sc.add_trace(go.Scatter(
        x=[0,mx], y=[0,mx],
        mode="lines", line=dict(color=t["red"],dash="dash",width=1.5),
        name="Perfect fit",
    ))
    fig_sc.update_layout(**fig_layout(dark,280),
        xaxis_title="Predicted 2025",
        yaxis_title="Actual 2025",
    )

    # Note on quantile forecasting (Lokad 2024)
    intermit_count = int((df["demand_pattern"].isin(["Lumpy","Intermittent"])).sum())

    # Top 10 forecast table
    top10 = df[df["pred_2026"].notna()].nlargest(10,"pred_2026")[
        ["שם פריט","pred_2025","pred_2026","trend","MAPE","demand_pattern","ABC"]
    ]
    rows = []
    for _, r in top10.iterrows():
        name = str(r.get("שם פריט",""))[:32]
        tr   = r.get("trend","stable")
        tc   = tr_col.get(tr,t["t1"])
        m    = r.get("MAPE",None)
        mc   = t["green"] if m and m<20 else t["amber"] if m and m<35 else t["red"]
        rows.append(html.Tr([
            html.Td(name, style={"padding":"7px 12px","color":t["t0"],"fontSize":"12px"}),
            html.Td(f"{int(r.get('pred_2025',0)):,}",
                    style={"padding":"7px 8px","color":t["blue"],
                           "fontFamily":"Consolas,monospace","fontSize":"12px"}),
            html.Td(f"{int(r.get('pred_2026',0)):,}",
                    style={"padding":"7px 8px","color":t["gold"],
                           "fontFamily":"Consolas,monospace","fontSize":"12px","fontWeight":"700"}),
            html.Td(html.Span(f"{'↗' if tr=='up' else '↘' if tr=='down' else '→'} {tr}",
                              style={"color":tc,"fontSize":"12px"}),
                    style={"padding":"7px 8px"}),
            html.Td(f"{m}%" if m else "—",
                    style={"padding":"7px 8px","color":mc,
                           "fontFamily":"Consolas,monospace","fontSize":"12px"}),
            html.Td(badge(r.get("ABC","?"),BC.get(r.get("ABC","?"),t["t1"])),
                    style={"padding":"7px 8px"}),
        ], style={"borderBottom":f"1px solid {t['border']}22"}))

    return html.Div([
        html.Div([
            html.H2("ML & Demand Analysis", style={"fontSize":"20px","fontWeight":"600",
                                                     "color":t["t0"],"margin":"0"}),
            html.Span("Linear regression 2021–2024 · validated on 2025 · 2026 forecast",
                      style={"fontSize":"13px","color":t["t1"],"marginLeft":"12px"}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"18px",
                  "paddingBottom":"12px","borderBottom":f"1px solid {t['border']}"}),

        html.Div([
            kpi("Items with ML",    len(ml),   t["blue"]),
            kpi("Avg MAPE",         f"{avg_mape}%", t["amber"] if avg_mape>20 else t["green"]),
            kpi("High Accuracy",    good,      t["green"]),
            kpi("% High Accuracy",  f"{pct}%", t["green"]),
        ], style={"display":"flex","gap":"10px","flexWrap":"wrap","marginBottom":"16px"}),

        # Quantile warning for intermittent items
        html.Div([
            html.Strong(f"ℹ {intermit_count:,} intermittent/lumpy items detected. "),
            "Linear regression is suboptimal for these — ",
            html.Strong("Quantile Forecasting (Lokad 2024) / Prophet"),
            " recommended for improved accuracy."
        ], className="alert-amber") if intermit_count > 0 else None,

        html.Div([
            section("MAPE Distribution",
                    [dcc.Graph(figure=fig_mape,config={"displayModeBar":False})],dark),
            section("Trend Distribution",
                    [dcc.Graph(figure=fig_tr,  config={"displayModeBar":False})],dark),
            section("Demand Pattern (ADI+CV²)",
                    [dcc.Graph(figure=fig_dp,  config={"displayModeBar":False})],dark),
        ], className="row-flex"),

        section("Actual 2025 vs Predicted 2025 (Model Validation)",
                [dcc.Graph(figure=fig_sc,config={"displayModeBar":False})], dark),

        section("Top 10 Items by 2026 Forecast", [
            html.Table([
                html.Thead(html.Tr([
                    html.Th(h, style={"padding":"7px 12px","color":t["t1"],"fontSize":"11px",
                                      "fontWeight":"700","textTransform":"uppercase",
                                      "borderBottom":f"1px solid {t['border']}"})
                    for h in ["Item","Pred 2025","Pred 2026","Trend","MAPE","ABC"]
                ])),
                html.Tbody(rows)
            ], style={"width":"100%","borderCollapse":"collapse"}),
        ], dark),
    ])

# ══════════════════════════════════════════════════════
# PAGE 4 – INVENTORY
# ══════════════════════════════════════════════════════

def page_inventory(df, dark):
    t = T(dark)

    ok       = int((df["stock_status"]=="OK").sum())
    over     = int((df["stock_status"]=="Overstock").sum())
    dead     = int((df["stock_status"]=="Dead Stock").sum())
    out      = int((df["stock_status"]=="Stockout").sum())
    low      = int((df["stock_status"]=="Low Stock").sum())

    # EOQ scatter
    eoq_df = df[(df["EOQ"]>0)&(df.get("מנה ממוצעת  שנתיים",
                  pd.Series(0,index=df.index)).fillna(0)>0)].head(500)
    cur_qty = eoq_df.get("מנה ממוצעת  שנתיים",
                          pd.Series(0,index=eoq_df.index)).fillna(0)
    fig_eoq = go.Figure()
    fig_eoq.add_trace(go.Scatter(
        x=cur_qty, y=eoq_df["EOQ"],
        mode="markers",
        marker=dict(color=t["gold"],size=4,opacity=0.6),
        name="Items",
    ))
    mx = max(cur_qty.max(), eoq_df["EOQ"].max(), 1)
    fig_eoq.add_trace(go.Scatter(
        x=[0,mx], y=[0,mx],
        mode="lines",
        line=dict(color=t["amber"],dash="dash",width=1.5),
        name="1:1 line",
    ))
    fig_eoq.update_layout(**fig_layout(dark,280),
        xaxis_title="Current Avg Order Qty",
        yaxis_title="EOQ Suggested",
    )

    # Days on hand histogram
    doh = df["days_on_hand"].clip(0,730)
    fig_doh = go.Figure(go.Histogram(
        x=doh, nbinsx=30,
        marker_color=t["gold"], opacity=0.85,
    ))
    fig_doh.update_layout(**fig_layout(dark,240), xaxis_title="Days on Hand")

    # ROP status bar
    rop_c = df["ROP_status"].value_counts()
    rc_cols = {"OK":t["green"],"Low":t["amber"],"High":t["red"]}
    fig_rop = go.Figure(go.Bar(
        x=rop_c.index.tolist(), y=rop_c.values,
        marker_color=[rc_cols.get(x,t["t1"]) for x in rop_c.index],
        text=rop_c.values, textposition="outside",
        textfont=dict(color=t["t0"]),
    ))
    fig_rop.update_layout(**fig_layout(dark,240))

    # Safety stock vs inventory scatter
    inv = df.get("יתרה במלאי", pd.Series(0,index=df.index)).fillna(0)
    fig_ss = go.Figure(go.Scatter(
        x=df["safety_stock"].clip(0,500), y=inv.clip(0,500),
        mode="markers",
        marker=dict(color=df["health"],colorscale="RdYlGn",
                    size=4,opacity=0.6,showscale=True,
                    colorbar=dict(title="Health",thickness=10,len=0.6)),
        text=df.get("שם פריט",""),
    ))
    mx2 = max(df["safety_stock"].clip(0,500).max(), inv.clip(0,500).max(), 1)
    fig_ss.add_trace(go.Scatter(
        x=[0,mx2], y=[0,mx2],
        mode="lines", line=dict(color=t["red"],dash="dash",width=1.5),
        name="Safety Stock = Inventory",showlegend=True,
    ))
    fig_ss.update_layout(**fig_layout(dark,280),
        xaxis_title="Safety Stock Required",
        yaxis_title="Actual Inventory",
    )

    # Items needing reorder
    reorder = df[(df["stock_status"].isin(["Stockout","Low Stock"]))
                 &(df["VED"].isin(["V","E"]))].sort_values("health").head(10)
    rows = []
    for _, r in reorder.iterrows():
        name = str(r.get("שם פריט",r.get("מפתח","")))[:32]
        inv_v = int(r.get("יתרה במלאי",0) or 0)
        ss_v  = int(r.get("safety_stock",0) or 0)
        eoq_v = int(r.get("EOQ",0) or 0)
        rows.append(html.Tr([
            html.Td(name,   style={"padding":"7px 12px","fontSize":"12px","color":t["t0"]}),
            html.Td(badge(r.get("VED","?"),BC.get(r.get("VED","?"),t["t1"])),
                    style={"padding":"7px 8px"}),
            html.Td(str(inv_v), style={"padding":"7px 8px","color":t["red"],
                                        "fontFamily":"Consolas,monospace","fontSize":"12px"}),
            html.Td(str(ss_v),  style={"padding":"7px 8px","color":t["amber"],
                                        "fontFamily":"Consolas,monospace","fontSize":"12px"}),
            html.Td(str(eoq_v), style={"padding":"7px 8px","color":t["green"],
                                        "fontFamily":"Consolas,monospace","fontSize":"12px"}),
            html.Td(html.Span(r.get("action",""),style={
                        "color":AC.get(r.get("action",""),t["t1"]),"fontSize":"11px",
                        "fontWeight":"700"}),
                    style={"padding":"7px 8px"}),
        ], style={"borderBottom":f"1px solid {t['border']}22"}))

    return html.Div([
        html.Div([
            html.H2("Inventory Management", style={"fontSize":"20px","fontWeight":"600",
                                                     "color":t["t0"],"margin":"0"}),
            html.Span("EOQ · Safety Stock · ROP Validation · Days on Hand",
                      style={"fontSize":"13px","color":t["t1"],"marginLeft":"12px"}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"18px",
                  "paddingBottom":"12px","borderBottom":f"1px solid {t['border']}"}),

        html.Div([
            kpi("OK",        ok,   t["green"]),
            kpi("Overstock", over, t["purple"]),
            kpi("Dead Stock",dead, t["red"]),
            kpi("Stockout",  out,  t["red"]),
            kpi("Low Stock", low,  t["amber"]),
        ], style={"display":"flex","gap":"10px","flexWrap":"wrap","marginBottom":"16px"}),

        html.Div([
            section("EOQ vs Current Order Qty",
                    [html.Div("Points above line = ordering more than optimal",
                              style={"fontSize":"11px","color":t["t1"],"marginBottom":"6px"}),
                     dcc.Graph(figure=fig_eoq,config={"displayModeBar":False})],dark,
                    {"flex":"1"}),
            section("Safety Stock vs Actual Inventory (colored by Health)",
                    [html.Div("Points below line = unsafe inventory level",
                              style={"fontSize":"11px","color":t["t1"],"marginBottom":"6px"}),
                     dcc.Graph(figure=fig_ss, config={"displayModeBar":False})],dark,
                    {"flex":"1"}),
        ], className="row-flex"),

        html.Div([
            section("Days on Hand Distribution",
                    [dcc.Graph(figure=fig_doh,config={"displayModeBar":False})],dark),
            section("ROP Status: Current vs Calculated",
                    [dcc.Graph(figure=fig_rop,config={"displayModeBar":False})],dark),
        ], className="row-flex"),

        section("Items Requiring Reorder (VED=V/E + Low/Stockout)", [
            html.Table([
                html.Thead(html.Tr([
                    html.Th(h, style={"padding":"7px 12px","color":t["t1"],"fontSize":"11px",
                                      "fontWeight":"700","textTransform":"uppercase",
                                      "borderBottom":f"1px solid {t['border']}"})
                    for h in ["Item","VED","Inventory","Safety Stock","EOQ","Action"]
                ])),
                html.Tbody(rows if rows else [
                    html.Tr(html.Td("✓ No urgent reorders needed",colSpan=6,
                                    style={"padding":"16px","textAlign":"center",
                                           "color":t["green"],"fontSize":"13px"}))
                ])
            ], style={"width":"100%","borderCollapse":"collapse"}),
        ], dark),
    ])

# ══════════════════════════════════════════════════════
# PAGE 5 – ANYLOGIC EXPORT
# ══════════════════════════════════════════════════════

def page_anylogic(df, dark):
    t = T(dark)

    export_cols = [
        "שם פריט","מפתח","ABC","HML","XYZ","FSN","VED","SDE","GOLF",
        "demand_pattern","ADI","CV2","class_code","health","action","strat_label",
        "trend","pred_2025","pred_2026","MAPE","R2",
        "EOQ","safety_stock","monthly_demand","ROP_calc",
        "stock_status","days_on_hand","turnover",
        "מחיר קניה","יתרה במלאי","מלאי נטו","הז. ספק","הז. מלקוח",
        "total_sales","has_anomaly",
    ]
    avail = [c for c in export_cols if c in df.columns]
    exp   = df[avail].copy()
    exp.rename(columns={
        "שם פריט":"item_name","מפתח":"item_key",
        "מחיר קניה":"unit_cost","יתרה במלאי":"inventory",
        "מלאי נטו":"net_inventory","הז. ספק":"supplier_orders",
        "הז. מלקוח":"customer_orders","total_sales":"total_sales_5yr",
    }, inplace=True)

    csv_bytes = exp.to_csv(index=False, encoding="utf-8-sig")
    b64  = base64.b64encode(csv_bytes.encode("utf-8-sig")).decode()
    href = f"data:text/csv;base64,{b64}"

    mapping = [
        ("productDemandDist – rate",      "monthly_demand",  "Average monthly demand per SKU → productDemandDist in AnyLogic"),
        ("productDemandDist – variability","CV2",             "Coefficient of variation² → demand distribution spread"),
        ("productDemandDist – pattern",   "demand_pattern",  "Stable/Intermittent/Lumpy/Unstable (ADI+CV²) → distribution type"),
        ("stocks",                         "inventory",       "Current physical inventory → initial stock level"),
        ("productROP",                     "ROP_calc",        "Calculated reorder point → trigger for Import flow"),
        ("orderQty",                       "EOQ",             "Economic Order Quantity → Update_Stock_After_Import param"),
        ("safetyStock",                    "safety_stock",    "Buffer stock by XYZ+VED → minimum inventory threshold"),
        ("productCosts",                   "unit_cost",       "Purchase cost per unit → cost calculations"),
        ("SalesClass",                     "ABC",             "A/B/C priority class → SalesClass agent attribute"),
        ("criticalityClass",               "VED",             "V/E/D criticality → urgentBypass routing logic"),
        ("demandPattern",                  "demand_pattern",  "Demand type → select correct distribution in AnyLogic"),
        ("supplierLeadTime",               "supplier_orders", "Pending supplier orders proxy → Waiting_for_Shipment"),
    ]

    rows = []
    for anylogic_var, csv_col, desc in mapping:
        rows.append(html.Tr([
            html.Td(anylogic_var,
                    style={"padding":"8px 12px","color":t["gold"],
                           "fontFamily":"Consolas,monospace","fontSize":"12px",
                           "fontWeight":"700"}),
            html.Td(csv_col,
                    style={"padding":"8px 12px","color":t["blue"],
                           "fontFamily":"Consolas,monospace","fontSize":"12px"}),
            html.Td(desc,
                    style={"padding":"8px 12px","color":t["t1"],"fontSize":"12px"}),
        ], style={"borderBottom":f"1px solid {t['border']}22"}))

    return html.Div([
        html.Div([
            html.H2("AnyLogic Export", style={"fontSize":"20px","fontWeight":"600",
                                               "color":t["t0"],"margin":"0"}),
            html.Span("Parameter file ready for direct injection into simulation model",
                      style={"fontSize":"13px","color":t["t1"],"marginLeft":"12px"}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"18px",
                  "paddingBottom":"12px","borderBottom":f"1px solid {t['border']}"}),

        # Model reference
        section("Your AnyLogic Model – Agent & Parameter Mapping", [
            html.Div([
                html.Div("Your model agents: ",
                         style={"color":t["t1"],"fontSize":"12px","marginBottom":"8px"}),
                html.Div([
                    *[html.Span(a, style={
                        "background":"rgba(88,166,255,.12)","color":t["blue"],
                        "border":"1px solid rgba(88,166,255,.3)","borderRadius":"4px",
                        "padding":"2px 10px","fontSize":"12px","fontFamily":"Consolas,monospace",
                        "margin":"3px","display":"inline-block"
                    }) for a in ["CustomerOrder","LineItem","productDemandDist","stocks",
                                  "SalesClass","productCosts","productPrices","totalProfit"]]
                ], style={"marginBottom":"12px"}),
            ]),
            html.Table([
                html.Thead(html.Tr([
                    html.Th(h, style={"padding":"8px 12px","color":t["t1"],"fontSize":"11px",
                                      "fontWeight":"700","textTransform":"uppercase",
                                      "borderBottom":f"1px solid {t['border']}"})
                    for h in ["AnyLogic Variable","CSV Column","Description"]
                ])),
                html.Tbody(rows),
            ], style={"width":"100%","borderCollapse":"collapse"}),
        ], dark),

        # Export stats + download
        section("Export File", [
            html.Div([
                html.Div([
                    html.Span(f"{len(exp):,}", style={"fontSize":"32px","fontWeight":"700",
                                                        "color":t["gold"],"fontFamily":"Consolas,monospace"}),
                    html.Span(" items", style={"fontSize":"15px","color":t["t1"],"marginLeft":"6px"}),
                    html.Span(f" · {len(exp.columns)} parameters",
                              style={"fontSize":"13px","color":t["t2"],"marginLeft":"4px"}),
                ], style={"marginBottom":"14px"}),
                html.A(
                    html.Div([
                        html.Span("⬇  Download AnyLogic Parameters CSV",
                                  style={"fontSize":"14px","fontWeight":"700"}),
                    ], style={
                        "background":"rgba(201,168,76,.12)",
                        "border":"1px solid rgba(201,168,76,.5)",
                        "borderRadius":"8px","padding":"14px 28px",
                        "cursor":"pointer","color":t["gold"],
                        "display":"inline-block","textAlign":"center",
                    }),
                    href=href, download="anylogic_parameters.csv",
                ),
            ]),
        ], dark),
    ])

# ══════════════════════════════════════════════════════
# PAGE 6 – HELP
# ══════════════════════════════════════════════════════

def page_help(df, dark):
    t = T(dark)

    methods = [
        {
            "title":"ABC — Annual Demand Value",
            "color":BC["A"],
            "paper":"May, Atkinson & Ferrer (2017) – US Navy WNO",
            "desc":"מסווג לפי ערך צריכה שנתי = מחיר × ביקוש ממוצע. הבסיס לכל שיטות MCIC.",
            "items":[
                ("A","20% מהפריטים = 70% מהכסף","בקרה הדוקה, הזמנות תכופות, מעקב יומי"),
                ("B","30% מהפריטים = 20% מהכסף","בקרה בינונית, מעקב שבועי"),
                ("C","50% מהפריטים = 10% מהכסף","הזמנות גדולות ומרווחות, מינימום ניהול"),
            ],
        },
        {
            "title":"XYZ — Demand Variability",
            "color":BC["X"],
            "paper":"Van As & Bührmann (2025)",
            "desc":"מסווג לפי מקדם שונות (CV) שחושב מחדש מהנתונים הגולמיים של 2025. תיקון לעמודה השגויה בדאטה.",
            "items":[
                ("X","CV < 0.5 — ביקוש יציב","תכנון מדויק, JIT, מלאי מינימלי"),
                ("Y","CV 0.5–1.0 — בינוני","Safety Stock מחושב"),
                ("Z","CV > 1.0 — קפריזי","מלאי חירום גדול, שקול להפסיק"),
            ],
        },
        {
            "title":"FSN — Movement Speed",
            "color":BC["F"],
            "paper":"Van As & Bührmann (2025)",
            "desc":"מסווג לפי פעילות מכירות אחרונה. F=חודשים 5-6, S=חודשים 1-4, N=אין מכירות כלל.",
            "items":[
                ("F","Fast — פעיל לאחרונה","שים קדמת המחסן לשליפה מהירה"),
                ("S","Slow — אטי","אזור גישה רגיל"),
                ("N","Non-moving — אין תנועה","⚠ מלאי מת! שקול מכירה/גריטה"),
            ],
        },
        {
            "title":"VED — Operational Criticality",
            "color":BC["V"],
            "paper":"May, Atkinson & Ferrer (2017) – Criticality variable K",
            "desc":"קריטיות תפעולית מבוסס על: חוסר (50%) + מספר לקוחות (30%) + תנועות (20%).",
            "items":[
                ("V","Vital — חוסר עוצר הכל","עתודת ביטחון גדולה, ספק חלופי חובה"),
                ("E","Essential — פוגע ביעילות","Safety Stock בינוני, מעקב שבועי"),
                ("D","Desirable — אין נזק מיידי","הזמנה לפי צורך"),
            ],
        },
        {
            "title":"Demand Pattern (ADI+CV²)",
            "color":BC["Stable"],
            "paper":"Hong et al. (2024) – Intermittent Demand Detection",
            "desc":"סיווג דפוס ביקוש לפי ADI (מרווח בין ביקושים) ו-CV². קריטי לחברת יבוא חלקי חילוף.",
            "items":[
                ("Stable",  "ADI<1.32, CV²<0.49","שיטות קלאסיות עובדות טוב"),
                ("Unstable","ADI<1.32, CV²≥0.49","Safety Stock גבוה"),
                ("Intermittent","ADI≥1.32, CV²<0.49","שיטת Croston מומלצת"),
                ("Lumpy",   "ADI≥1.32, CV²≥0.49","Quantile Forecasting (Lokad 2024)"),
            ],
        },
        {
            "title":"Health Score (AHP + VETO)",
            "color":t["gold"],
            "paper":"Vaccari et al. (2026) – AHP-K-VETO · May et al. (2017) – WNO weights",
            "desc":"ציון 0-100 המשלב את כל הסיווגים. VETO rule: פריט Vital לא יכול לקבל פחות מ-30.",
            "items":[
                ("70+","ירוק — בריא","המשך ניהול רגיל"),
                ("40-70","צהוב — דורש תשומת לב","בדוק פרמטרים ושפר"),
                ("<40","אדום — בעייתי","⚠ נדרש טיפול דחוף"),
            ],
        },
    ]

    cards = []
    for m in methods:
        item_rows = []
        for val, lbl, act in m["items"]:
            c = BC.get(val, m["color"])
            item_rows.append(html.Div([
                html.Span(val, style={
                    "background":f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},.18)",
                    "color":c,"padding":"2px 8px","borderRadius":"4px","fontSize":"11px",
                    "fontWeight":"700","fontFamily":"Consolas,monospace",
                    "marginRight":"8px","flexShrink":"0","display":"inline-block","minWidth":"70px"}),
                html.Div([
                    html.Div(lbl,  style={"fontSize":"12px","color":t["t0"],"fontWeight":"500"}),
                    html.Div(act,  style={"fontSize":"11px","color":t["t1"],"marginTop":"2px",
                                          "direction":"rtl","textAlign":"right"}),
                ])
            ], style={"display":"flex","alignItems":"flex-start","marginBottom":"8px",
                      "gap":"6px"}))

        cards.append(html.Div([
            html.Div(m["title"],
                     style={"fontSize":"13px","fontWeight":"700",
                            "color":m["color"],"marginBottom":"4px"}),
            html.Div(f"📚 {m['paper']}",
                     style={"fontSize":"10px","color":t["t2"],
                            "marginBottom":"8px","fontStyle":"italic"}),
            html.Div(m["desc"],
                     style={"fontSize":"12px","color":t["t1"],
                            "marginBottom":"10px","lineHeight":"1.6",
                            "direction":"rtl","textAlign":"right"}),
            *item_rows,
        ], style={"background":t["bg2"],"borderRadius":"10px","padding":"16px",
                  "border":f"1px solid {t['border']}",
                  "flex":"1","minWidth":"280px"}))

    strategy_rows = []
    for key, s in STRATEGY.items():
        c = s["color"]
        strategy_rows.append(html.Tr([
            html.Td(key,
                    style={"padding":"7px 14px","color":c,"fontFamily":"Consolas,monospace",
                           "fontSize":"14px","fontWeight":"700"}),
            html.Td(s["label"],
                    style={"padding":"7px 12px","color":c,"fontSize":"12px","fontWeight":"600"}),
            html.Td(s["he"],
                    style={"padding":"7px 12px","color":t["t1"],"fontSize":"12px",
                           "direction":"rtl","textAlign":"right"}),
        ], style={"borderBottom":f"1px solid {t['border']}22",
                  "background":f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},.06)"}))

    return html.Div([
        html.Div([
            html.H2("Help & Methodology", style={"fontSize":"20px","fontWeight":"600",
                                                   "color":t["t0"],"margin":"0"}),
            html.Span("All methods sourced from peer-reviewed research",
                      style={"fontSize":"13px","color":t["t1"],"marginLeft":"12px"}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"18px",
                  "paddingBottom":"12px","borderBottom":f"1px solid {t['border']}"}),

        # Papers
        section("📖 Research Foundation", [
            *[html.Div([
                html.Div(title, style={"color":t["t0"],"fontWeight":"600","fontSize":"13px"}),
                html.Div(desc,  style={"color":t["t1"],"fontSize":"12px","marginTop":"2px"}),
            ], style={"marginBottom":"10px"})
              for title, desc in [
                  ("May, Atkinson & Ferrer (2017) — JOSCM",
                   "Applying Inventory Classification to a Large Inventory Management System (US Navy WSS) — WNO multi-criteria model, Random Forest variable selection"),
                  ("Vaccari et al. (2026) — Logistics MDPI",
                   "A Machine Learning and Multi-Criteria Decision-Making Approach to Cycle Counting — AHP-K-VETO achieves 97% classification accuracy"),
                  ("Hong et al. (2024) — Electronics MDPI",
                   "Unsupervised Anomaly Detection of Intermittent Demand for Spare Parts — ADI+CV² demand pattern classification, Tucker tensor decomposition"),
                  ("Van As & Bührmann (2025) — SAIIE",
                   "Improving Inventory Management at an Automotive Company by Applying the ABC-XYZ-FSN Classification Method — dashboard design"),
                  ("Lokad / Vermorel & Steinberg (2024)",
                   "Spare Parts Inventory Management with Quantile Technology — Quantile forecasting for intermittent demand, Pinball loss function"),
              ]]
        ], dark),

        # Classification cards
        html.Div(cards, style={"display":"flex","flexWrap":"wrap","gap":"16px",
                               "marginBottom":"16px"}),

        # ABC×XYZ strategy matrix
        section("ABC × XYZ Strategy Matrix", [
            html.Table([
                html.Thead(html.Tr([
                    html.Th(h, style={"padding":"8px 14px","color":t["t1"],"fontSize":"11px",
                                      "fontWeight":"700","textTransform":"uppercase",
                                      "borderBottom":f"1px solid {t['border']}"})
                    for h in ["Key","Strategy","המלצה (עברית)"]
                ])),
                html.Tbody(strategy_rows),
            ], style={"width":"100%","borderCollapse":"collapse"}),
        ], dark),
    ])

# ══════════════════════════════════════════════════════
# MAIN LAYOUT
# ══════════════════════════════════════════════════════

app.layout = html.Div([
    dcc.Store(id="s-dark",  data=True,   storage_type="session"),
    dcc.Store(id="s-data",  data=None,   storage_type="memory"),
    dcc.Store(id="s-page",  data="overview", storage_type="session"),
    html.Div(id="css-holder"),
    html.Div(id="root"),
])

# ══════════════════════════════════════════════════════
# CALLBACKS
# ══════════════════════════════════════════════════════

# CSS injection
@app.callback(Output("css-holder","children"), Input("s-dark","data"))
def _css(dark):
    css_str = css(dark)
    b64 = base64.b64encode(css_str.encode('utf-8')).decode('utf-8')
    return html.Link(rel='stylesheet', href=f'data:text/css;base64,{b64}')
# Theme toggle
@app.callback(
    Output("s-dark","data"),
    Input("theme-btn","n_clicks"),
    State("s-dark","data"),
    prevent_initial_call=True,
)
def _toggle(n, dark):
    return not dark if n else dark

# Navigation
@app.callback(
    Output("s-page","data"),
    Input({"type":"nav","index":ALL},"n_clicks"),
    prevent_initial_call=True,
)
def _nav(clicks):
    ctx = callback_context
    if not ctx.triggered: return no_update
    raw = ctx.triggered[0]["prop_id"]
    return json.loads(raw.split(".")[0])["index"]

# Upload + process
@app.callback(
    Output("s-data","data"),
    Output("upload-msg","children"),
    Input("upload","contents"),
    State("upload","filename"),
    State("s-dark","data"),
    prevent_initial_call=True,
)
def _upload(contents, filename, dark):
    t = T(dark)
    if not contents: return no_update, no_update
    try:
        _, enc = contents.split(",")
        raw = base64.b64decode(enc)
        df_raw = None
        for enc_try in ["utf-8-sig","utf-8","windows-1255","cp1252","iso-8859-8"]:
            try:
                df_raw = pd.read_csv(io.StringIO(raw.decode(enc_try)))
                break
            except Exception:
                pass
        if df_raw is None:
            raise ValueError("Could not decode file — try saving as UTF-8 CSV")
        df = process(df_raw)
        return (df.to_json(orient="records", force_ascii=False),
                html.Span([
                    html.Span("✓ ", style={"color":t["green"]}),
                    f"{filename} — {len(df):,} items processed"
                ]))
    except Exception as e:
        return no_update, html.Span([
            html.Span("✗ ", style={"color":t["red"]}),
            f"Error: {e}"
        ])

# Main render
@app.callback(
    Output("root","children"),
    Input("s-dark","data"),
    Input("s-data","data"),
    Input("s-page","data"),
)
def _render(dark, data_json, page):
    if not data_json:
        return upload_screen(dark)

    df = pd.read_json(io.StringIO(data_json), orient="records")
    # Restore bool column
    if "has_anomaly" in df.columns:
        df["has_anomaly"] = df["has_anomaly"].astype(bool)
    if "is_critical" in df.columns:
        df["is_critical"] = df["is_critical"].astype(bool)

    pages = {
        "overview":       page_overview,
        "classification": page_classification,
        "ml":             page_ml,
        "inventory":      page_inventory,
        "anylogic":       page_anylogic,
        "help":           page_help,
    }
    content = pages.get(page, page_overview)(df, dark)

    return html.Div([
        sidebar(dark, page),
        html.Div(content, className="main-content"),
    ])

# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    import dash
    app.run(debug=True, port=8050)
