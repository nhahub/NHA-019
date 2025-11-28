import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 🎨 Page Configuration
st.set_page_config(
    page_title="Smart Farming Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎯 Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .stButton > button {
        background: linear-gradient(90deg, #007bff, #0056b3);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
    }
    .metric-box {
        background-color: #2a2a2a;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #888;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
    }
    .metric-delta {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# 🎯 Load ALL sensor data from database (NO CACHE, NO LIMIT)
def load_all_data():
    """Load ALL sensor data from database without any limitations"""
    try:
        conn = psycopg2.connect(
            dbname="smart_farming",  # Assuming same DB name; change if different
            user="admin",
            password="password",
            host="postgres"
        )
        # Query to get ALL data - no LIMIT clause
        query = """
        SELECT farm_id, region, temperature, soil_moisture, humidity, 
               sunlight_intensity, soil_ph, pesticide_usage_ml, rainfall, timestamp 
        FROM sensor_data
        ORDER BY timestamp DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Show how many records were loaded
        st.sidebar.success(f"✅ Loaded {len(df)} records from database")
        return df
    except Exception as e:
        st.sidebar.error(f"❌ Database error: {str(e)}")
        return pd.DataFrame()

# 🎯 Process sensor data
def process_sensor_data(df):
    if df.empty:
        return df
    
    try:
        # Convert timestamp (assuming Unix timestamp in seconds)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        
        # Sort by timestamp ascending for trends
        df = df.sort_values("timestamp")
        
        return df
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return df

# 🎯 Generate alerts based on insights
def generate_alerts(latest):
    alerts = []
    
    # Soil moisture alerts
    if latest["soil_moisture"] < 30:
        alerts.append(("critical", "Critical Soil Moisture: Immediate irrigation needed to avoid crop stress!"))
    elif latest["soil_moisture"] < 40:
        alerts.append(("warning", "Warning: Soil moisture below safe limit. Consider irrigation."))
    
    # Soil pH alerts
    if latest["soil_ph"] < 6:
        alerts.append(("warning", "Soil pH too low (acidic). Add lime to balance soil."))
    elif latest["soil_ph"] > 7.5:
        alerts.append(("warning", "Soil pH too high (alkaline). Adjust fertilizers to increase acidity."))
    
    # Temperature alerts
    if latest["temperature"] > 35:
        alerts.append(("warning", "High Temperature Alert: Increase watering frequency."))
    elif latest["temperature"] < 10:
        alerts.append(("warning", "Low Temperature Alert: Decrease watering frequency."))
    
    # Rainfall alert
    if latest["rainfall"] > 0:
        alerts.append(("info", "It's raining now. Avoid pesticide spraying and adjust irrigation."))
    
    # Extreme event detection (simple: very dry, heatwave, heavy rain)
    if latest["temperature"] > 35 and latest["humidity"] < 30 and latest["rainfall"] == 0:
        alerts.append(("critical", "Heatwave detected: High risk of crop stress. Monitor closely."))
    elif latest["rainfall"] > 50:  # Assuming heavy rain threshold
        alerts.append(("warning", "Heavy Rainfall: Potential flooding risk."))
    elif latest["soil_moisture"] < 20 and latest["rainfall"] == 0:
        alerts.append(("critical", "Very Dry Conditions: Emergency irrigation recommended."))
    
    return alerts

# 🎯 Send alert email
def send_alert_email(alerts, farmer_email, sender_email, sender_password, smtp_server="smtp.gmail.com", smtp_port=587):
    try:
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = farmer_email
        message["Subject"] = "Smart Farm Alert Notification"
        
        body = "The following alerts have been generated from your smart farm dashboard:\n\n"
        for level, msg in alerts:
            body += f"[{level.upper()}] {msg}\n"
        message.attach(MIMEText(body, "plain"))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, farmer_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ Failed to send email: {str(e)}")
        return False

# 🎯 Create current sensor readings display
def display_current_readings(latest, previous, total_pesticide):
    st.subheader("Current Sensor Readings")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_moisture = latest["soil_moisture"] - previous["soil_moisture"] if previous is not None else 0
        color = "green" if delta_moisture > 0 else "red" if delta_moisture < 0 else "gray"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Soil Moisture</div>
            <div class="metric-value">{latest["soil_moisture"]:.1f}%</div>
            <div class="metric-delta" style="color: {color};">{delta_moisture:+.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        delta_temp = latest["temperature"] - previous["temperature"] if previous is not None else 0
        color = "red" if delta_temp > 0 else "green" if delta_temp < 0 else "gray"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Temperature</div>
            <div class="metric-value">{latest["temperature"]:.1f}°C</div>
            <div class="metric-delta" style="color: {color};">{delta_temp:+.1f}°C</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Rainfall</div>
            <div class="metric-value">{latest["rainfall"]:.1f} mm</div>
            <div class="metric-delta" style="color: green;">+0.0 mm</div>  <!-- Assuming no delta for rainfall -->
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Pesticide Usage</div>
            <div class="metric-value">{latest["pesticide_usage_ml"]:.1f} ml</div>
            <div class="metric-label">Total (Period)</div>
            <div class="metric-value">{total_pesticide:.1f} ml</div>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_ph = latest["soil_ph"] - previous["soil_ph"] if previous is not None else 0
        color = "green" if delta_ph > 0 else "red" if delta_ph < 0 else "gray"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Soil pH</div>
            <div class="metric-value">{latest["soil_ph"]:.2f}</div>
            <div class="metric-delta" style="color: {color};">{delta_ph:+.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        delta_hum = latest["humidity"] - previous["humidity"] if previous is not None else 0
        color = "green" if delta_hum > 0 else "red" if delta_hum < 0 else "gray"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Humidity</div>
            <div class="metric-value">{latest["humidity"]:.1f}%</div>
            <div class="metric-delta" style="color: {color};">{delta_hum:+.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        delta_sun = latest["sunlight_intensity"] - previous["sunlight_intensity"] if previous is not None else 0
        color = "green" if delta_sun > 0 else "red" if delta_sun < 0 else "gray"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Sunlight Intensity</div>
            <div class="metric-value">{latest["sunlight_intensity"]:.1f} W/m²</div>
            <div class="metric-delta" style="color: {color};">{delta_sun:+.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pass  # Empty for alignment

# 🎯 Create monitoring trends charts
def create_trend_charts(filtered_df):
    st.subheader("Monitoring Trends")
    
    # 1. Soil Moisture Monitoring
    fig_moisture = px.line(
        filtered_df, 
        x="timestamp", 
        y="soil_moisture",
        title="1. Soil Moisture Monitoring",
        labels={"soil_moisture": "Soil Moisture (%)"}
    )
    fig_moisture.add_hline(y=40, line_dash="dash", line_color="orange", annotation_text="Warning Threshold (40%)")
    fig_moisture.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="Critical Threshold (30%)")
    st.plotly_chart(fig_moisture, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Temperature Monitoring
        fig_temp = px.line(
            filtered_df, 
            x="timestamp", 
            y="temperature",
            title="Temperature Monitoring",
            labels={"temperature": "Temperature (°C)"}
        )
        fig_temp.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="High Temp Alert (>35°C)")
        fig_temp.add_hline(y=10, line_dash="dash", line_color="blue", annotation_text="Low Temp Alert (<10°C)")
        st.plotly_chart(fig_temp, use_container_width=True)
        
        # Soil pH Monitoring
        fig_ph = px.line(
            filtered_df, 
            x="timestamp", 
            y="soil_ph",
            title="Soil pH Monitoring",
            labels={"soil_ph": "Soil pH"}
        )
        fig_ph.add_hline(y=6, line_dash="dash", line_color="red", annotation_text="Low pH Alert (<6)")
        fig_ph.add_hline(y=7.5, line_dash="dash", line_color="orange", annotation_text="High pH Alert (>7.5)")
        st.plotly_chart(fig_ph, use_container_width=True)
    
    with col2:
        # Humidity Monitoring
        fig_hum = px.line(
            filtered_df, 
            x="timestamp", 
            y="humidity",
            title="Humidity Monitoring",
            labels={"humidity": "Humidity (%)"}
        )
        st.plotly_chart(fig_hum, use_container_width=True)
        
        # Sunlight Intensity Monitoring
        fig_sun = px.line(
            filtered_df, 
            x="timestamp", 
            y="sunlight_intensity",
            title="Sunlight Intensity Monitoring",
            labels={"sunlight_intensity": "Sunlight Intensity (W/m²)"}
        )
        st.plotly_chart(fig_sun, use_container_width=True)
    
    # Rainfall Monitoring
    fig_rain = px.bar(
        filtered_df, 
        x="timestamp", 
        y="rainfall",
        title="Rainfall Monitoring",
        labels={"rainfall": "Rainfall (mm)"}
    )
    st.plotly_chart(fig_rain, use_container_width=True)
    
    # Pesticide Usage Monitoring
    fig_pest = px.line(
        filtered_df, 
        x="timestamp", 
        y="pesticide_usage_ml",
        title="Pesticide Usage Monitoring",
        labels={"pesticide_usage_ml": "Pesticide Usage (ml)"}
    )
    st.plotly_chart(fig_pest, use_container_width=True)

# 🎯 Display alerts
def display_alerts(alerts):
    if alerts:
        st.subheader("Alerts & Recommendations")
        for level, msg in alerts:
            if level == "critical":
                st.error(msg)
            elif level == "warning":
                st.warning(msg)
            else:
                st.info(msg)

# 🎯 Main application
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🌾 Smart Farming Dashboard</h1>
        <p>Intelligent agriculture monitoring system - real-time insights and alerts</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if "sensor_data" not in st.session_state:
        st.session_state.sensor_data = None
        st.session_state.last_update = None
        st.session_state.data_loaded = False
        st.session_state.alert_sent = False
    
    # Sidebar
    st.sidebar.title("🎛️ Control Panel")
    
    # Email configuration in sidebar
    st.sidebar.subheader("📧 Email Notifications")
    enable_email = st.sidebar.checkbox("Enable Email Alerts", value=True)
    farmer_email = st.sidebar.text_input("Farmer's Email", value="farmer@example.com")
    sender_email = st.sidebar.text_input("Sender Email (e.g., your Gmail)", value="your_email@gmail.com")
    sender_password = st.sidebar.text_input("Sender Password (use app password for Gmail)", type="password", value="")
    st.sidebar.caption("Note: For Gmail, create an app password at https://myaccount.google.com/apppasswords")
    
    # Load data button
    if st.sidebar.button("🔄 Load All Sensor Data", type="primary"):
        with st.spinner("🔄 Loading ALL data from database..."):
            raw_data = load_all_data()
            if not raw_data.empty:
                processed_data = process_sensor_data(raw_data)
                st.session_state.sensor_data = processed_data
                st.session_state.last_update = datetime.now()
                st.session_state.data_loaded = True
                st.session_state.alert_sent = False  # Reset alert sent flag on new data load
                st.sidebar.success(f"✅ Successfully loaded {len(processed_data)} records!")
            else:
                st.sidebar.error("❌ Failed to load data")
                return
    
    # Auto-load data on first run
    if not st.session_state.data_loaded:
        with st.spinner("🔄 Loading initial data..."):
            raw_data = load_all_data()
            if not raw_data.empty:
                processed_data = process_sensor_data(raw_data)
                st.session_state.sensor_data = processed_data
                st.session_state.last_update = datetime.now()
                st.session_state.data_loaded = True
                st.session_state.alert_sent = False
    
    # Show last update info
    if st.session_state.last_update:
        st.sidebar.info(f"🕒 Last Updated: {st.session_state.last_update.strftime('%H:%M:%S')}")
        minutes_ago = int((datetime.now() - st.session_state.last_update).total_seconds() // 60)
        if minutes_ago > 0:
            st.sidebar.caption(f"Updated {minutes_ago} minutes ago")
    
    # Get data
    df = st.session_state.sensor_data

    if df is None or df.empty:
        st.warning("⚠️ No data loaded. Click 'Load All Sensor Data' to start.")
        return

    # Filters
    st.sidebar.subheader("🔍 Filter Options")

    available_farms = sorted(df["farm_id"].unique())
    selected_farm = st.sidebar.selectbox("Select Farm", available_farms, index=available_farms.index("farm_10") if "farm_10" in available_farms else 0)

    available_regions = sorted(df[df["farm_id"] == selected_farm]["region"].unique())
    selected_region = st.sidebar.selectbox("Region", available_regions, index=available_regions.index("Sinai") if "Sinai" in available_regions else 0)

    historical_days = st.sidebar.slider("Historical Data Range (days)", 1, 90, 25)

    # Apply filters
    filtered_df = df[(df["farm_id"] == selected_farm) & (df["region"] == selected_region)]

    if filtered_df.empty:
        st.warning("⚠️ No data for selected farm and region.")
        return


    if filtered_df.empty:
        st.warning(f"⚠️ No data in the last {historical_days} days.")
        return

    st.sidebar.info(f"📊 Displaying: {len(filtered_df)} records")

    # Get latest and previous
    latest = filtered_df.iloc[-1]
    previous = filtered_df.iloc[-2] if len(filtered_df) > 1 else None

    # Calculate total pesticide
    total_pesticide = filtered_df["pesticide_usage_ml"].sum()
    
    # Display current readings
    display_current_readings(latest, previous, total_pesticide)
    
    # Generate and display alerts
    alerts = generate_alerts(latest)
    display_alerts(alerts)
    
    # Send email if alerts exist, email enabled, and not already sent
    if alerts and enable_email and farmer_email and sender_email and sender_password and not st.session_state.alert_sent:
        if send_alert_email(alerts, farmer_email, sender_email, sender_password):
            st.success(f"✅ Alert email sent to {farmer_email}!")
            st.session_state.alert_sent = True
    
    # Trends charts
    create_trend_charts(filtered_df)
    
    # Data table
    st.subheader("📋 Historical Data")
    table_data = filtered_df.copy()
    table_data["timestamp"] = table_data["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(
        table_data,
        use_container_width=True,
        height=400
    )
    
    # Footer
    st.markdown("---")
    st.caption("💡 This dashboard loads ALL sensor data from your database and updates only when you click the button - no auto-refresh!")

if __name__ == "__main__":
    main()