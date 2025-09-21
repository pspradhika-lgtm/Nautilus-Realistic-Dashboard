import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium

# -------------------------------
# Title & Config
# -------------------------------
st.set_page_config(page_title="🌊 Nautilus Realistic Dashboard", layout="wide")
st.title("🚢 Nautilus Maritime Incidents – Realistic Interactive Dashboard")

# -------------------------------
# Load Data
# -------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("maritime_incidents_realistic.csv")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Day"] = df["Date"].dt.day
    df["Cargo_Loss_Flag"] = df["Cargo_Loss"].map({"Yes":1, "No":0})
    df["Severity"] = pd.cut(df["Casualties"].fillna(0),
                             bins=[-1,10,50,1000],
                             labels=["Low","Medium","High"])
    return df

data = load_data()

# -------------------------------
# Sidebar Filters
# -------------------------------
st.sidebar.header("🔍 Filters")
years = st.sidebar.multiselect("Select Year(s):", sorted(data["Year"].dropna().unique()))
countries = st.sidebar.multiselect("Select Country:", sorted(data["Country"].dropna().unique()))
vessels = st.sidebar.multiselect("Select Vessel Type:", sorted(data["Vessel_Type"].dropna().unique()))
incidents = st.sidebar.multiselect("Select Incident Type:", sorted(data["Incident_Type"].dropna().unique()))

filtered = data.copy()
if years: filtered = filtered[filtered["Year"].isin(years)]
if countries: filtered = filtered[filtered["Country"].isin(countries)]
if vessels: filtered = filtered[filtered["Vessel_Type"].isin(vessels)]
if incidents: filtered = filtered[filtered["Incident_Type"].isin(incidents)]

st.sidebar.success(f"📊 Showing {len(filtered)} records")

# -------------------------------
# KPI Metrics
# -------------------------------
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Incidents", len(filtered))
c2.metric("Total Casualties", int(filtered["Casualties"].fillna(0).sum()))
c3.metric("Cargo Loss Events", int(filtered["Cargo_Loss_Flag"].fillna(0).sum()))
c4.metric("Countries Involved", filtered["Country"].nunique())

# -------------------------------
# Tabs for Interactive Visuals
# -------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺 Map", "📅 Timeline", "🔗 Sankey",
    "🕸 Radar Chart", "🔥 Heatmap"
])

# 1. Folium Interactive Map
with tab1:
    st.subheader("🗺 Incident Locations")
    if not filtered.empty:
        m = folium.Map(location=[20,0], zoom_start=2)
        marker_cluster = MarkerCluster().add_to(m)
        for _, row in filtered.iterrows():
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=f"{row['Incident_Type']} - {row['Vessel_Type']} ({row['Casualties']} casualties)",
                icon=folium.Icon(color="red" if row['Severity']=="High" else "orange" if row['Severity']=="Medium" else "green")
            ).add_to(marker_cluster)
        st_folium(m, width=800, height=500)
    else:
        st.warning("No data for selected filters.")

# 2. Animated Timeline
with tab2:
    st.subheader("📅 Animated Timeline")
    if not filtered.empty:
        fig = px.scatter(
            filtered,
            x="Longitude", y="Latitude",
            animation_frame="Year",
            animation_group="Incident_Type",
            size="Casualties", color="Severity",
            hover_name="Country",
            title="Incidents Over Time",
            size_max=30
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data for selected filters.")

# 3. Sankey Diagram
with tab3:
    st.subheader("🔗 Incident vs Vessel Type")
    if not filtered.empty:
        sankey_data = filtered.groupby(["Incident_Type","Vessel_Type"]).size().reset_index(name="Count")
        sources = list(filtered["Incident_Type"].unique())
        targets = list(filtered["Vessel_Type"].unique())
        label = sources + targets
        source_idx = [sources.index(i) for i in sankey_data["Incident_Type"]]
        target_idx = [targets.index(v)+len(sources) for v in sankey_data["Vessel_Type"]]

        fig = go.Figure(go.Sankey(
            node=dict(label=label, pad=15, thickness=20),
            link=dict(source=source_idx, target=target_idx, value=sankey_data["Count"])
        ))
        fig.update_layout(title_text="Incident Types vs Vessel Types")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data for selected filters.")

# 4. Radar Chart
with tab4:
    st.subheader("🕸 Top 5 Countries Comparison")
    if not filtered.empty:
        top_countries = filtered["Country"].value_counts().nlargest(5).index
        radar_data = filtered[filtered["Country"].isin(top_countries)].groupby("Country").agg({
            "Casualties":"sum",
            "Cargo_Loss_Flag":"sum",
            "Incident_Type":"count"
        }).reset_index()
        categories = ["Casualties","Cargo_Loss_Flag","Incident_Type"]
        fig = go.Figure()
        for _, row in radar_data.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=row[categories].values,
                theta=categories,
                fill="toself",
                name=row["Country"]
            ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data for selected filters.")

# 5. Heatmap
# 5. Heatmap
with tab5:
    st.subheader("🔥 Incident Heatmap")
    if not filtered.empty:
        # Drop rows with missing coordinates
        heat_data = filtered[["Latitude","Longitude"]].dropna().values.tolist()
        if heat_data:  # Only create heatmap if there is data
            m2 = folium.Map(location=[20,0], zoom_start=2)
            HeatMap(heat_data, radius=8, blur=4).add_to(m2)
            st_folium(m2, width=800, height=500)
        else:
            st.warning("No valid coordinates to show HeatMap.")
    else:
        st.warning("No data for selected filters.")


