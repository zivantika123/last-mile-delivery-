import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import folium
from streamlit_folium import folium_static
from scipy import stats

# Page configuration
st.set_page_config(
    page_title="Last-Mile Delivery Analytics",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_data():
    try:
        # Load your original dataset
        df = pd.read_csv("Last mile Delivery Data.csv")
        
        st.sidebar.success(f"✅ Loaded {len(df)} records from CSV")
        
        # Basic cleaning for your specific dataset
        df['Order_Date'] = pd.to_datetime(df['Order_Date'])
        
        # Fix any data issues from your dataset
        df['Agent_Rating'] = pd.to_numeric(df['Agent_Rating'], errors='coerce')
        df['Agent_Rating'] = df['Agent_Rating'].fillna(df['Agent_Rating'].median())
        
        # Standardize column names if needed
        df.columns = df.columns.str.strip()
        
        # Add Distance_km column if you have coordinates
        if all(col in df.columns for col in ['Store_Latitude', 'Store_Longitude', 'Drop_Latitude', 'Drop_Longitude']):
            from math import radians, sin, cos, sqrt, atan2
            
            def calculate_distance(lat1, lon1, lat2, lon2):
                R = 6371  # Earth radius in km
                lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                return R * c
            
            df['Distance_km'] = df.apply(
                lambda row: calculate_distance(
                    row['Store_Latitude'], row['Store_Longitude'],
                    row['Drop_Latitude'], row['Drop_Longitude']
                ), axis=1
            )
        else:
            df['Distance_km'] = 5.0  # placeholder
        
        # Add required calculated columns
        df['Pickup_Delay'] = 15  # Placeholder - calculate actual delay if you have times
        
        # Categorize delivery times
        df['Delivery_Type'] = pd.cut(
            df['Delivery_Time'],
            bins=[0, 60, 120, float('inf')],
            labels=['Fast', 'Medium', 'Slow']
        )
        
        return df
        
    except FileNotFoundError:
        st.error("❌ CSV file not found! Make sure 'Last mile Delivery Data.csv' is in the same folder.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()

# THIS IS CRITICAL - YOU MUST CALL THE FUNCTION!
df = load_data()

# Check if data loaded
if df.empty:
    st.error("No data loaded. Please check your CSV file.")
    st.stop()

# Check if data loaded successfully
if df.empty:
    st.error("No data loaded. Please check your Excel file and try again.")
    st.stop()

# Sidebar filters
st.sidebar.header("🔍 Filters")
st.sidebar.markdown("---")

# Date range filter
min_date = df['Order_Date'].min()
max_date = df['Order_Date'].max()
date_range = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Dynamic filters
weather_options = st.sidebar.multiselect(
    "Weather Conditions",
    options=df['Weather'].unique(),
    default=df['Weather'].unique()
)

traffic_options = st.sidebar.multiselect(
    "Traffic Levels",
    options=df['Traffic'].unique(),
    default=df['Traffic'].unique()
)

vehicle_options = st.sidebar.multiselect(
    "Vehicle Types",
    options=df['Vehicle'].unique(),
    default=df['Vehicle'].unique()
)

area_options = st.sidebar.multiselect(
    "Area Types",
    options=df['Area'].unique(),
    default=df['Area'].unique()
)

category_options = st.sidebar.multiselect(
    "Product Categories",
    options=df['Category'].unique(),
    default=df['Category'].unique()
)

# Apply filters
filtered_df = df[
    (df['Weather'].isin(weather_options)) &
    (df['Traffic'].isin(traffic_options)) &
    (df['Vehicle'].isin(vehicle_options)) &
    (df['Area'].isin(area_options)) &
    (df['Category'].isin(category_options)) &
    (df['Order_Date'] >= pd.to_datetime(date_range[0])) &
    (df['Order_Date'] <= pd.to_datetime(date_range[1]))
]

# Main app
st.title("🚚 Last-Mile Delivery Performance Dashboard")
st.markdown("---")

# KPI Cards
st.subheader("📊 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_orders = len(filtered_df)
    st.metric("Total Orders", f"{total_orders:,}")

with col2:
    avg_delivery_time = filtered_df['Delivery_Time'].mean()
    st.metric("Avg Delivery Time", f"{avg_delivery_time:.1f} min")

with col3:
    on_time_rate = (filtered_df['Delivery_Time'] <= 60).mean() * 100
    st.metric("On-Time Rate", f"{on_time_rate:.1f}%")

with col4:
    avg_rating = filtered_df['Agent_Rating'].mean()
    st.metric("Avg Agent Rating", f"{avg_rating:.2f}")

# Tabs for different analyses
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Overview", 
    "👤 Agent Performance", 
    "🌤️ Weather & Traffic", 
    "🗺️ Geographic", 
    "📋 Recommendations"
])

with tab1:
    st.subheader("Overall Delivery Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Delivery time distribution
        fig = px.histogram(
            filtered_df, 
            x='Delivery_Time',
            nbins=30,
            title='Delivery Time Distribution',
            color_discrete_sequence=['#3366CC']
        )
        fig.update_layout(xaxis_title='Delivery Time (min)', yaxis_title='Count')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Delivery type breakdown
        delivery_type_counts = filtered_df['Delivery_Type'].value_counts()
        fig = px.pie(
            values=delivery_type_counts.values,
            names=delivery_type_counts.index,
            title='Delivery Type Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Category performance
    st.subheader("Category Performance Analysis")
    category_stats = filtered_df.groupby('Category').agg({
        'Delivery_Time': ['mean', 'count'],
        'Agent_Rating': 'mean'
    }).round(2)
    category_stats.columns = ['Avg_Delivery_Time', 'Order_Count', 'Avg_Rating']
    category_stats = category_stats.sort_values('Avg_Delivery_Time', ascending=False)
    
    st.dataframe(category_stats, use_container_width=True)

with tab2:
    st.subheader("Agent Performance Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Age vs Performance
        fig = px.scatter(
            filtered_df,
            x='Agent_Age',
            y='Delivery_Time',
            color='Agent_Rating',
            size='Distance_km',
            title='Agent Age vs Delivery Performance',
            hover_data=['Vehicle', 'Area']
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Rating distribution
        fig = px.histogram(
            filtered_df,
            x='Agent_Rating',
            nbins=20,
            title='Agent Rating Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Top/Bottom performers
    st.subheader("Agent Efficiency Ranking")
    agent_efficiency = filtered_df.groupby('Agent_Age').agg({
        'Delivery_Time': 'mean',
        'Agent_Rating': 'mean',
        'Order_ID': 'count'
    }).rename(columns={'Order_ID': 'Total_Orders'})
    agent_efficiency['Efficiency_Score'] = agent_efficiency['Delivery_Time'] / filtered_df.groupby('Agent_Age')['Distance_km'].mean()
    agent_efficiency = agent_efficiency.sort_values('Efficiency_Score')
    
    st.dataframe(agent_efficiency, use_container_width=True)

with tab3:
    st.subheader("Weather & Traffic Impact Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Weather impact
        weather_impact = filtered_df.groupby('Weather')['Delivery_Time'].mean().sort_values(ascending=False)
        fig = px.bar(
            x=weather_impact.index,
            y=weather_impact.values,
            title='Average Delivery Time by Weather Condition',
            labels={'x': 'Weather', 'y': 'Avg Delivery Time (min)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Traffic impact
        traffic_impact = filtered_df.groupby('Traffic')['Delivery_Time'].mean().sort_values(ascending=False)
        fig = px.bar(
            x=traffic_impact.index,
            y=traffic_impact.values,
            title='Average Delivery Time by Traffic Level',
            labels={'x': 'Traffic', 'y': 'Avg Delivery Time (min)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Weather-Traffic combination heatmap
    st.subheader("Weather-Traffic Combination Impact")
    heatmap_data = filtered_df.pivot_table(
        values='Delivery_Time',
        index='Weather',
        columns='Traffic',
        aggfunc='mean'
    ).fillna(0)
    
    fig = px.imshow(
        heatmap_data,
        title='Delivery Time Heatmap: Weather vs Traffic',
        aspect='auto',
        color_continuous_scale='Reds'
    )
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Geographic Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Store locations map - FIXED
        if all(col in filtered_df.columns for col in ['Store_Latitude', 'Store_Longitude']):
            # Create a copy with the correct column names that Streamlit expects
            map_data = filtered_df[['Store_Latitude', 'Store_Longitude']].dropna().copy()
            map_data = map_data.rename(columns={
                'Store_Latitude': 'lat',
                'Store_Longitude': 'lon'
            })
            st.map(map_data)
            st.caption(f"📍 Showing {len(map_data)} store locations")
        else:
            st.info("📍 Map data not available - missing latitude/longitude columns")
    
    with col2:
        # Distance vs Delivery Time
        if 'Distance_km' in filtered_df.columns:
            fig = px.scatter(
                filtered_df,
                x='Distance_km',
                y='Delivery_Time',
                color='Area',
                title='Distance vs Delivery Time',
                hover_data=['Weather', 'Traffic']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📏 Distance data not available")
    
    # Area performance
    area_performance = filtered_df.groupby('Area').agg({
        'Delivery_Time': 'mean',
        'Agent_Rating': 'mean',
        'Order_ID': 'count'
    }).rename(columns={'Order_ID': 'Order_Count'}).round(2)
    
    st.dataframe(area_performance, use_container_width=True)

with tab5:
    st.subheader("📋 Data-Driven Recommendations")
    
    # Generate recommendations based on analysis
    st.info("**Based on the current filtered data, here are your recommendations:**")
    
    # Recommendation 1: Weather contingencies
    if not filtered_df.empty:
        worst_weather = filtered_df.groupby('Weather')['Delivery_Time'].mean().idxmax()
        st.warning(f"**Weather Alert**: {worst_weather} conditions cause the longest delays. Consider:")
        st.markdown("- Pre-position additional agents during forecasted bad weather")
        st.markdown("- Implement weather-based surge pricing")
        st.markdown("- Adjust delivery time expectations for customers")
        
        # Recommendation 2: Vehicle optimization
        vehicle_efficiency = filtered_df.groupby('Vehicle')['Delivery_Time'].mean()
        best_vehicle = vehicle_efficiency.idxmin()
        worst_vehicle = vehicle_efficiency.idxmax()
        st.success(f"**Vehicle Strategy**: {best_vehicle} performs best. Consider reallocating from {worst_vehicle}")
        
        # Recommendation 3: Category management
        slowest_category = filtered_df.groupby('Category')['Delivery_Time'].mean().idxmax()
        st.error(f"**Category Focus**: {slowest_category} has the longest delivery times. Review:")
        st.markdown("- Packaging requirements")
        st.markdown("- Handling procedures")
        st.markdown("- Customer expectations")
    else:
        st.info("No data available for recommendations")
    
    # Download filtered data
    st.subheader("📥 Export Data")
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name=f"filtered_delivery_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data available for export")

# Footer
st.markdown("---")
st.markdown("📊 *Last-Mile Delivery Analytics Dashboard* | Built with Streamlit")