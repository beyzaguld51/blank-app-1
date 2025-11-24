import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# CSV einlesen
# -----------------------------
df = pd.read_csv("tommy_hilfiger_flights.csv")
df["date"] = pd.to_datetime(df["date"])

# Miles -> Kilometer
df["distance_km"] = df["distance_miles"] * 1.60934

# -----------------------------
# IATA-Koordinaten (alle Codes aus deiner CSV)
# -----------------------------
iata_coords = {
    "BTL": (42.3073, -85.2515),   # Michigen (Battle Creek)
    "PBI": (26.6832, -80.0956),   # Florida (Palm Beach)
    "HVN": (41.2637, -72.8868),   # Connecticut (New Haven)
    "VNY": (34.2098, -118.4890),  # California (Van Nuys)
    "AUS": (30.1945, -97.6699),   # Texas (Austin)
    "SVD": (13.1567, -61.1499),   # Kingstown (St. Vincent)
    "BOS": (42.3656, -71.0096),   # Boston
    "VCE": (45.5053, 12.3519),    # Venice
    "MUC": (48.3538, 11.7861),    # Germany (Munich)
    "ZRH": (47.4581, 8.5555),     # Switzerland (Zurich)
    "NCE": (43.6584, 7.2159),     # France (Nice)
    "LBG": (48.9695, 2.4412),     # Paris Le Bourget
    "AMS": (52.3105, 4.7683),     # Amsterdam
    "WAL": (37.9402, -75.4666),   # Virginia (Wallops)
    "DAL": (32.8471, -96.8518),   # Dallas Love Field
    "NCO": (41.5971, -71.4121),   # Kingstown (Quonset State)
    "YYT": (47.6186, -52.7519),   # Canada (St. John's)
    "CIA": (41.7999, 12.5949),    # Rome Ciampino
    "IOR": (53.1067, -9.6536),    # Ireland (Inishmore)
    "HPN": (41.0670, -73.7076),   # New York (Westchester)
    "GJT": (39.1224, -108.5270),  # Colorado (Grand Junction)
    "ACY": (39.4576, -74.5772),   # New Jersey (Atlantic City)
    "HIO": (45.5404, -122.9490),  # Oregon (Hillsboro)
    "MSO": (46.9163, -114.0906),  # Montana (Missoula)
    "LAS": (36.0840, -115.1537),  # Las Vegas
    "TEB": (40.8501, -74.0608),   # New Jersey (Teterboro)
    "NAS": (25.0390, -77.4662),   # Bahamas (Nassau)
    "LAX": (33.9416, -118.4085),  # Los Angeles
    "BFI": (47.5290, -122.3010),  # Seattle Boeing Field
    "ISM": (28.2898, -81.4371),   # Orlendo (Kissimmee)
    "SXM": (18.0410, -63.1089),   # Sint Maarten
    "ATL": (33.6407, -84.4277),   # Atlanta
}

# -----------------------------
# IATA-Codes aus dem Text ziehen
# -----------------------------
df["iata_from"] = df["from"].str.extract(r"\((.*?)\)")
df["iata_to"]   = df["to"].str.extract(r"\((.*?)\)")

# Koordinaten zuordnen
df["lat_from"] = df["iata_from"].map(lambda x: iata_coords.get(x, (None, None))[0])
df["lon_from"] = df["iata_from"].map(lambda x: iata_coords.get(x, (None, None))[1])
df["lat_to"]   = df["iata_to"].map(lambda x: iata_coords.get(x, (None, None))[0])
df["lon_to"]   = df["iata_to"].map(lambda x: iata_coords.get(x, (None, None))[1])

# Zeilen ohne Koordinaten entfernen (falls es doch mal einen unbekannten Code gibt)
df = df.dropna(subset=["lat_from", "lon_from", "lat_to", "lon_to"])

# -----------------------------
# Doppelte Routen erkennen und Linien dicker machen
# -----------------------------
route_counts = df.groupby(["from", "to"]).size().reset_index(name="count")
df = df.merge(route_counts, on=["from", "to"], how="left")
df["line_width"] = df["count"].apply(lambda x: 2 + (x - 1) * 2)

# -----------------------------
# Statistik
# -----------------------------
total_distance = df["distance_km"].sum()
total_emission = total_distance * 2.5 / 1000  # Tonnen CO₂
avg_distance   = df["distance_km"].mean()

pfaffenhofen_emission = 5000  # t CO₂/Jahr (angenommener Wert für Vergleich)
pfaffenhofen_percent = total_emission / pfaffenhofen_emission * 100

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Tommy Hilfiger Jet Tracker", layout="wide")

st.title("🛩️ Privatjet-Tracker – Tommy Hilfiger")

st.write("""
Diese App visualisiert die Flüge von **Tommy Hilfiger** auf Basis einer CSV-Datei,
berechnet Distanz und CO₂-Emissionen und vergleicht sie mit den jährlichen Emissionen
der Stadt **Pfaffenhofen a.d.Ilm**. Mehrfach geflogene Strecken werden auf der Karte
**dicker** dargestellt.
""")

col1, col2, col3 = st.columns(3)
col1.metric("Anzahl Flüge", len(df))
col2.metric("Gesamtdistanz (km)", f"{total_distance:,.0f}")
col3.metric("CO₂-Ausstoß (t)", f"{total_emission:.2f}")

st.caption(
    f"Das entspricht etwa **{pfaffenhofen_percent:.2f}%** der jährlichen "
    "CO₂-Emissionen von Pfaffenhofen a.d.Ilm (≈ 5.000 t/Jahr)."
)

# -----------------------------
# Datum-Filter
# -----------------------------
min_date, max_date = df["date"].min(), df["date"].max()

selected_date = st.slider(
    "Flüge bis zu folgendem Datum anzeigen:",
    min_value=min_date.date(),
    max_value=max_date.date(),
    value=max_date.date()
)

filtered = df[df["date"].dt.date <= selected_date]

# -----------------------------
# Weltkarte mit dicken Linien
# -----------------------------
st.subheader("🌍 Flugroutenkarte (doppelte Strecken dicker)")

fig = px.scatter_geo()

for _, row in filtered.iterrows():
    fig.add_trace(
        px.line_geo(
            lat=[row["lat_from"], row["lat_to"]],
            lon=[row["lon_from"], row["lon_to"]],
        ).data[0].update(
            line=dict(width=row["line_width"], color="red"),
            hovertext=f"{row['from']} → {row['to']} ({row['distance_km']:.0f} km, {row['count']}x geflogen)"
        )
    )

fig.update_layout(
    height=650,
    showlegend=False,
    margin=dict(l=0, r=0, t=30, b=0),
    title="Flugrouten von Tommy Hilfiger"
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Tabelle
# -----------------------------
st.subheader("📋 Flugdaten (gefiltert)")
st.dataframe(filtered[[
    "date", "from", "to", "distance_miles", "distance_km", "count"
]])

st.info("Dicke Linien = Strecken, die mehrfach geflogen wurden.")
