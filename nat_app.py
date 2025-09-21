import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster

# -------------------------------
# Title & Config
# -------------------------------
st.set_page_config(page_title="🌊 Nautilus Dashboard", layout="wide")
st.title("🚢 Nautilus Maritime Incidents – Interactive Dashboard")

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
    df["Month_Name"] = df["Month"].apply(lambda x: pd.to_datetime(str(x), format="%m").strftime("%b"))
    return df

data = load_data()

# -------------------------------
# Sidebar Filters
# -------------------------------
st.sidebar.header("🔍 Filters")
years = st.sidebar.multiselect("Select Year(s):", sorted(data["Year"].dropna().unique()))
months = st.sidebar.multiselect("Select Month(s):", ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
countries = st.sidebar.multiselect("Select Country:", sorted(data["Country"].dropna().unique()))
vessels = st.sidebar.multiselect("Select Vessel Type:", sorted(data["Vessel_Type"].dropna().unique()))
incidents = st.sidebar.multiselect("Select Incident Type:", sorted(data["Incident_Type"].dropna().unique()))

# Range slider for interactive selection
cas_range = st.sidebar.slider("Select Casualty Range", 
                              int(data["Casualties"].min()), 
                              int(data["Casualties"].max()), 
                              (0, 50))

filtered = data.copy()
if years: filtered = filtered[filtered["Year"].isin(years)]
if months: filtered = filtered[filtered["Month_Name"].isin(months)]
if countries: filtered = filtered[filtered["Country"].isin(countries)]
if vessels: filtered = filtered[filtered["Vessel_Type"].isin(vessels)]
if incidents: filtered = filtered[filtered["Incident_Type"].isin(incidents)]
filtered = filtered[(filtered["Casualties"] >= cas_range[0]) & (filtered["Casualties"] <= cas_range[1])]

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
# Tabs for Visualizations
# -------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🗺 Map", "📅 Timeline", "🔗 Sankey",
    "🕸 Country Radar", "📊 Advanced Charts", "📈 Monthly Analysis"
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

# 2. Animated / Interactive Scatter Timeline
with tab2:
    st.subheader("🎥 Animated Scatter Timeline: Incidents Over Months")
    if not filtered.empty:
        # Ensure Month_Name is sorted correctly for animation
        month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        filtered["Month_Name"] = pd.Categorical(filtered["Month_Name"], categories=month_order, ordered=True)
        
        # Create a combined frame: Year-Month
        filtered["Year_Month"] = filtered["Year"].astype(str) + "-" + filtered["Month_Name"].astype(str)
        
        # Animated scatter
        fig_scatter = px.scatter(
            filtered,
            x="Longitude",
            y="Latitude",
            color="Incident_Type",
            size="Casualties",
            hover_name="Country",
            hover_data=["Vessel_Type","Cargo_Loss","Year","Month_Name"],
            animation_frame="Year_Month",  # Animate by Year-Month
            animation_group="Incident_Type",
            title="Animated Incidents by Location Over Months",
            size_max=30,
            width=900,
            height=600
        )
        fig_scatter.update_layout(
            clickmode='event+select',
            xaxis_title="Longitude",
            yaxis_title="Latitude"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
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

# 4. Radar Chart
with tab4:
    st.subheader("🕸 Country Comparison (Radar)")
    if not filtered.empty:
        # Select top 5 countries by number of incidents
        top_countries = filtered["Country"].value_counts().nlargest(5).index
        
        radar_data = filtered[filtered["Country"].isin(top_countries)].groupby("Country").agg({
            "Casualties": "sum",
            "Cargo_Loss_Flag": "sum",
            "Incident_Type": "count"
        }).reset_index()
        
        categories = ["Casualties", "Cargo_Loss_Flag", "Incident_Type"]
        
        fig = go.Figure()
        for _, row in radar_data.iterrows():
            # Scale small values for visibility
            scaled_values = row[categories].values * 1.0  # you can multiply if needed
            fig.add_trace(go.Scatterpolar(
                r=scaled_values,
                theta=categories,
                fill='toself',
                name=row["Country"]
            ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, radar_data[categories].values.max()*1.2])),
            showlegend=True,
            title="Country Comparison by Casualties, Cargo Loss, and Incidents"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data for selected filters.")


# 5. Advanced Charts (Sunburst, Bubble, Funnel)
with tab5:
    st.subheader("📊 Advanced Interactive Visualizations")
    if not filtered.empty:
        # Sunburst Chart
        sun_data = filtered.groupby(["Incident_Type","Vessel_Type","Country"]).size().reset_index(name="Count")
        fig_sun = px.sunburst(
            sun_data,
            path=["Incident_Type","Vessel_Type","Country"],
            values="Count",
            color="Count",
            color_continuous_scale="Viridis",
            title="Sunburst: Incident → Vessel → Country"
        )
        st.plotly_chart(fig_sun, use_container_width=True)

        # Bubble Map
        fig_bubble = px.scatter_geo(filtered, lat="Latitude", lon="Longitude",
                                    color="Severity", size="Casualties",
                                    hover_name="Country",
                                    hover_data={"Vessel_Type":True, "Incident_Type":True, "Cargo_Loss":True},
                                    projection="natural earth",
                                    title="Global Maritime Incidents: Casualties & Cargo Loss",
                                    size_max=25)
        fig_bubble.update_layout(legend_title_text='Severity / Cargo Loss', clickmode='event+select')
        st.plotly_chart(fig_bubble, use_container_width=True)

        # Funnel Chart: Severity
        funnel_data = filtered["Severity"].value_counts().reindex(["High","Medium","Low"]).reset_index()
        funnel_data.columns = ["Severity","Count"]
        fig_funnel = px.funnel(funnel_data, x="Count", y="Severity", title="Funnel: Incident Severity Distribution")
        st.plotly_chart(fig_funnel, use_container_width=True)

        # Histogram with selected casualty range
        st.subheader(f"Histogram: Casualties in Selected Range ({cas_range[0]}-{cas_range[1]})")
        fig_hist = px.histogram(filtered, x="Casualties", nbins=20, title="Casualties Distribution")
        st.plotly_chart(fig_hist, use_container_width=True)

# 6. Month-Wise Analysis
with tab6:
    st.subheader("📈 Monthly Analysis")
    if not filtered.empty:
        # Bar Chart
        month_count = filtered.groupby("Month_Name").size().reindex(
            ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], fill_value=0
        ).reset_index(name="Count")
        fig_bar = px.bar(month_count, x="Month_Name", y="Count", text="Count", title="Incidents per Month")
        st.plotly_chart(fig_bar, use_container_width=True)

        # Line Chart
        month_casualties = filtered.groupby("Month_Name")["Casualties"].sum().reindex(
            ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], fill_value=0
        ).reset_index()
        fig_line = px.line(month_casualties, x="Month_Name", y="Casualties", markers=True, title="Total Casualties per Month")
        st.plotly_chart(fig_line, use_container_width=True)



