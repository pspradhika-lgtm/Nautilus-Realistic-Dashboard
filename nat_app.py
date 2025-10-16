import streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
from streamlit_folium import st_folium
import folium; from folium.plugins import MarkerCluster

st.set_page_config(page_title="🌊 Nautilus Dashboard", layout="wide")
st.title("🚢 Nautilus Maritime Incidents Dashboard")

@st.cache_data
def load():
    df = pd.read_csv("maritime_incidentsrr.csv")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"], df["Month_Name"] = df["Date"].dt.year, df["Date"].dt.strftime("%b")
    df["Cargo_Loss_Flag"] = df["Cargo_Loss"].map({"Yes":1,"No":0})
    df["Severity"] = pd.cut(df["Casualties"].fillna(0),[-1,10,50,1e6],["Low","Med","High"])
    return df
df = load()

# ---- Filters ----
st.sidebar.header("🔍 Filters")
y = st.sidebar.multiselect("Year", sorted(df.Year.dropna().unique()))
m = st.sidebar.multiselect("Month", sorted(df.Month_Name.dropna().unique()))
c = st.sidebar.multiselect("Country", sorted(df.Country.dropna().unique()))
v = st.sidebar.multiselect("Vessel", sorted(df.Vessel_Type.dropna().unique()))
i = st.sidebar.multiselect("Incident", sorted(df.Incident_Type.dropna().unique()))
r = st.sidebar.slider("Casualty Range", 0, int(df.Casualties.max()), (0, int(df.Casualties.max())))

f = df.copy()
if y: f = f[f["Year"].isin(y)]
if m: f = f[f["Month_Name"].isin(m)]
if c: f = f[f["Country"].isin(c)]
if v: f = f[f["Vessel_Type"].isin(v)]
if i: f = f[f["Incident_Type"].isin(i)]
f = f[(f["Casualties"] >= r[0]) & (f["Casualties"] <= r[1])]
st.sidebar.success(f"📊 {len(f)} records found")

# ---- KPIs ----
c1,c2,c3,c4 = st.columns(4)
c1.metric("Incidents", len(f)); c2.metric("Casualties", int(f.Casualties.sum()))
c3.metric("Cargo Loss", int(f.Cargo_Loss_Flag.sum())); c4.metric("Countries", f.Country.nunique())

# ---- Tabs ----
t1,t2,t3,t4,t5,t6 = st.tabs(["🗺 Map","📅 Timeline","🔗 Sankey","🕸 Radar","📊 Advanced","📈 Monthly"])

with t1:
    if f.empty: st.warning("No data available.")
    else:
        mapp=folium.Map([20,0],2); cl=MarkerCluster().add_to(mapp)
        for _,r in f.iterrows():
            folium.Marker([r.Latitude,r.Longitude],
                popup=f"{r.Incident_Type}-{r.Vessel_Type} ({r.Casualties})",
                icon=folium.Icon(color={"High":"red","Med":"orange"}.get(r.Severity,"green"))).add_to(cl)
        st_folium(mapp, width=800, height=500)

with t2:
    if not f.empty:
        f["YM"]=f["Year"].astype(str)+"-"+f["Month_Name"]
        st.plotly_chart(px.scatter(f,x="Longitude",y="Latitude",color="Incident_Type",size="Casualties",
                                   animation_frame="YM",title="Animated Incidents"), use_container_width=True)

with t3:
    if not f.empty:
        g=f.groupby(["Incident_Type","Vessel_Type"]).size().reset_index(name="n")
        s,t=g.Incident_Type.astype("category"),g.Vessel_Type.astype("category")
        st.plotly_chart(go.Figure(go.Sankey(
            node=dict(label=list(s.cat.categories)+list(t.cat.categories)),
            link=dict(source=s.cat.codes,target=t.cat.codes+len(s.cat.categories),value=g.n)
        )), use_container_width=True)

with t4:
    if not f.empty:
        top=f.Country.value_counts().nlargest(5).index
        g=f[f.Country.isin(top)].groupby("Country").agg({"Casualties":"sum","Cargo_Loss_Flag":"sum","Incident_Type":"count"})
        fig=go.Figure()
        for k,v in g.iterrows():
            fig.add_trace(go.Scatterpolar(r=v.values,theta=g.columns,fill='toself',name=k))
        fig.update_layout(title="Top Countries Comparison")
        st.plotly_chart(fig, use_container_width=True)

with t5:
    if not f.empty:
        st.plotly_chart(px.sunburst(f,path=["Incident_Type","Vessel_Type","Country"],title="Sunburst"),use_container_width=True)
        sev=f["Severity"].value_counts().reindex(["High","Med","Low"]).reset_index()
        sev.columns=["Severity","Count"]
        st.plotly_chart(px.funnel(sev,x="Count",y="Severity",title="Severity Funnel"),use_container_width=True)

with t6:
    if not f.empty:
        order=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        mc=f.groupby("Month_Name").size().reindex(order,fill_value=0).reset_index(name="Count")
        st.plotly_chart(px.bar(mc,x="Month_Name",y="Count",text="Count",title="Incidents per Month"),use_container_width=True)


