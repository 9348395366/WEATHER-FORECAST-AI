# Glass Weather AI - 8-Slide Deck

## Slide 1 - Title
Glass Weather AI
Weather analytics with local ML + glassmorphism UI
Date: 2026-03-27

## Slide 2 - Problem & Objectives
- Most weather apps show raw forecasts without transparent analytics
- Goal: combine live data, local ML, and interactive exploration
- Provide a reproducible, student-friendly pipeline

## Slide 3 - Flowchart & Libraries
Flowchart (text):
Start -> Open Streamlit App -> Select Module -> Live Weather / AI Forecast / Data Lab / Chat Agent -> Visualize -> End

Libraries:
- streamlit, pandas, numpy, scikit-learn, requests
- plotly, joblib, folium, streamlit-folium

## Slide 4 - Data & APIs
- Open-Meteo Forecast API (current + hourly + daily)
- Open-Meteo Archive API (historical data)
- Open-Meteo Air Quality API (AQI)
- Optional OpenWeather One Call + Air Pollution (API key)
- Nominatim Search + Reverse for geocoding
- Local dataset cached in data/historical_weather.csv

## Slide 5 - Feature Engineering & Model
- Inputs: temperature, humidity, wind, precipitation
- Time features: hour, day-of-year, month
- Lag features: 1-hour and 24-hour temperature
- Rolling 24-hour temperature mean
- Model: HistGradientBoostingRegressor
- Metric: Mean Absolute Error (MAE)

## Slide 6 - App Features
- Modules: Live Weather, AI Forecast, Data Lab, Chat Agent
- Live Weather: current conditions + short-term forecast
- AI Forecast: predicted temperatures + MAE display
- AI AQI Forecast: AQI prediction graph
- Data Lab: charts + map exploration
- AQI dataset: map view + graph view
- Chat Agent: routes requests to tools
- Glassmorphism UI with light/dark modes

## Slide 7 - Reliability & Testing
- Graceful fallbacks when APIs fail
- Synthetic data generation when historical fetch is unavailable
- Chronological train/test split
- Functional requirements mapped to test cases

## Slide 8 - Summary & Next Steps
- End-to-end weather analytics in a compact stack
- Transparent data + model workflow
- Next steps: refresh dataset, add features, retrain model
