## Run the Smart Farming Dashboard (Streamlit)

The dashboard provides real-time monitoring, alerts, and interactive visualizations of sensor data.

a. Run the Streamlit app
bashstreamlit run agg_streamlit.py

This will start the dashboard at http://localhost:8501

b. Dashboard Features
Real-time sensor readings (soil moisture, temperature, pH, etc.)
Interactive trend charts with threshold alerts
Critical/Warning alerts based on sensor thresholds
Email notifications for alerts (configurable in sidebar)
Farm & Region filtering
Historical data table
Auto-refresh every 1 second

c. Configure Email Alerts (Optional)
In the sidebar of the dashboard:

Enable "Enable Email Alerts"
Enter:
* Farmer's Email: farmer@example.com
* Sender Email: your_email@gmail.com
* Sender Password: Use App Password (for Gmail)

How to get App Password (Gmail):
Go to: https://myaccount.google.com/apppasswords
Generate a 16-character password and use it here.

d. Dashboard Preview
<img src="images/streamlit dashboard.jpg" alt="dashboard">
<img src="images/dashboard graphs.png" alt="dashboard">

Enjoy real-time smart farming insights!
