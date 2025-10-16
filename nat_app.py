import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster

# --- PAGE SETUP ---
st.set_page_config(page_title="🌊 Nautilus Dashboard", layout="wide")
st.title("🚢 Nautilus Maritime Incidents Dashboard")

# --- LOAD DATA ---
@st.cache_data
def load():
    df = pd.read_csv("maritime_incidentsrr.csv")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"] = df["Date"].dt.year
    df["Month_Name"] = df["Date"].dt.strftime("%b")
    df["Cargo_Loss_Flag"] = df["Cargo_Loss"].map({"Yes": 1, "No": 0})
    df["Severity"] = pd.cut(df["Casualties"].fillna(0),
                            [-1, 10, 50, 1e6],
                            labels=["Low", "Med", "High"])
    return df

df = load()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Filters")

y = st.sidebar.multiselect("Year", sorted(df.Year.dropna().unique()))
m = st.sidebar.multiselect("Month", df.Month_Name.unique())
c = st.sidebar.multiselect("Country", sorted(df.Country.dropna().unique()))
v = st.sidebar.multiselect("Vessel", sorted(df.Vessel_Type.dropna().unique()))
i = st.sidebar.multiselect("Incident", sorted(df.Incident_Type.dropna().unique()))
r = st.sidebar.slider("Casualty Range", 0, int(df.Casualties.max()), (0, 50))

# Apply filters
f = df.query(
    "(@y==[] or Year in @y) and (@m==[] or Month_Name in @m) and "
    "(@c==[] or Country in @c) and (@v==[] or Vessel_Type in @v) and "
    "(@i==[] or Incident_Type in @i) and "
    "@r[0] <= Casualties <= @r[1]"
)

st.sidebar.success(f"📊 {len(f)} records found")

# --- KPIs ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Incidents", len(f))
c2.metric("Casualties", int(f.Casualties.sum()))
c3.metric("Cargo Loss", int(f.Cargo_Loss_Flag.sum()))
c4.metric("Countries", f.Country.nunique())

# --- TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs(
    ["🗺 Map", "📅 Timeline", "🔗 Sankey", "🕸 Radar", "📊 Advanced", "📈 Monthly"]
)

# --- TAB 1: MAP ---
with t1:
    if f.empty:
        st.warning("No data available.")
    else:
        m = folium.Map([20, 0], zoom_start=2)
        cl = MarkerCluster().add_to(m)
        for _, row in f.iterrows():
            folium.Marker(
                [row.Latitude, row.Longitude],
                popup=f"{row.Incident_Type} - {row.Vessel_Type} ({row.Casualties})",
                icon=folium.Icon(
                    color={"High": "red", "Med": "orange"}.get(row.Severity, "green")
                ),
            ).add_to(cl)
        st_folium(m, width=800, height=500)

# --- TAB 2: TIMELINE ---
with t2:
    if not f.empty:
        f["YM"] = f["Year"].astype(str) + "-" + f["Month_Name"]
        st.plotly_chart(
            px.scatter(
                f,
                x="Longitude",
                y="Latitude",
                color="Incident_Type",
                size="Casualties",
                animation_frame="YM",
                title="Animated Incidents Over Time",
            ),
            use_container_width=True,
        )

# --- TAB 3: SANKEY DIAGRAM ---
with t3:
    if not f.empty:
        g = f.groupby(["Incident_Type", "Vessel_Type"]).size().reset_index(name="n")
        s = g.Incident_Type.astype("category")
        t = g.Vessel_Type.astype("category")

        fig = go.Figure(
            go.Sankey(
                node=dict(label=list(s.cat.categories) + list(t.cat.categories)),
                link=dict(
                    source=s.cat.codes,
                    target=t.cat.codes + len(s.cat.categories),
                    value=g.n,
                ),
            )
        )
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 4: RADAR CHART (FIXED) ---
with t4:
    if not f.empty:
        top = f.Country.value_counts().nlargest(5).index
        g = (
            f[f.Country.isin(top)]
            .groupby("Country")
            .agg(
                {
                    "Casualties": "sum",
                    "Cargo_Loss_Flag": "sum",
                    "Incident_Type": "count",
                }
            )
        )

        fig = go.Figure()
        for k, v in g.iterrows():
            fig.add_trace(
                go.Scatterpolar(
                    r=v.values.tolist(),
                    theta=g.columns.tolist(),
                    fill="toself",
                    name=k,
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            showlegend=True,
            title="Top 5 Countries – Radar View",
        )
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 5: ADVANCED CHARTS ---
with t5:
    if not f.empty:
        st.plotly_chart(
            px.sunburst(
                f,
                path=["Incident_Type", "Vessel_Type", "Country"],
                title="Sunburst of Incidents",
            ),
            use_container_width=True,
        )

        st.plotly_chart(
            px.funnel(
                f.Severity.value_counts().reset_index(),
                x="count",
                y="index",
                title="Severity Funnel",
            ),
            use_container_width=True,
        )

# --- TAB 6: MONTHLY TREND ---
with t6:
    if not f.empty:
        order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        mc = (
            f.groupby("Month_Name")
            .size()
            .reindex(order, fill_value=0)
            .reset_index(name="Count")
        )

        st.plotly_chart(
            px.bar(
                mc,
                x="Month_Name",
                y="Count",
                text="Count",
                title="Incidents per Month",
            ),
            use_container_width=True,
        )









