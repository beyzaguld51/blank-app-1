import streamlit as st
import pandas as pd
import plotly.express as px
import re

# ----------------------------------------------------
# STREAMLIT SETUP
# ----------------------------------------------------
st.set_page_config(layout="wide")
st.title("🛩️ Tommy Hilfiger – Flight Tracker")


# ----------------------------------------------------
# CSV AUTOMATISCH BEREINIGEN
# ----------------------------------------------------
def clean_csv(input_file="tommy_hilfiger_flights.csv", output_file="cleaned_flights.csv"):

    typos = {
        "Flroida": "Florida",
        "Orlendo": "Orlando",
        "Seatlle": "Seattle",
        "Bahamas(NAS)": "Bahamas (NAS)",
        "Philipsburg": "Philipsburg",
    }

    def fix_typos(text):
        for wrong, right in typos.items():
            text = text.replace(wrong, right)
        return text

    cleaned = []

    with open(input_file, "r") as f:
        for line in f:
            line = line.strip()
            line = fix_typos(line)

            line = re.sub(r"\((\w{3})\)", r" (\1)", line)
            line = re.sub(r",\s*\(", " (", line)
            line = re.sub(r"\s{2,}", " ", line)

            parts = [p.strip() for p in line.split(",")]

            if len(parts) > 5:
                parts = [parts[0], parts[1], parts[2], " ".join(parts[3:-1]), parts[-1]]

            if len(parts) == 5:
                cleaned.append(",".join(parts))

    with open(output_file, "w") as f:
        f.write("\n".join(cleaned))

    return output_file


clean_file = clean_csv()
df = pd.read_csv(clean_file)
df["date"] = pd.to_datetime(df["date"], errors="coerce")


# ----------------------------------------------------
# IATA EXTRAHIEREN
# ----------------------------------------------------
df["iata_from"] = df["from"].str.extract(r"\((.*?)\)")
df["iata_to"] = df["to"].str.extract(r"\((.*?)\)")

df["iata_from"] = df["iata_from"].str.replace(",", "")
df["iata_to"] = df["iata_to"].str.replace(",", "")


# ----------------------------------------------------
# AIRPORT-KOORDINATEN
# ----------------------------------------------------
airport_coords = {
    "BTL": (42.3073, -85.2515), "PBI": (26.6832, -80.0956),
    "HVN": (41.2637, -72.8868), "VNY": (34.2100, -118.4890),
    "AUS": (30.1945, -97.6699), "SVD": (13.1567, -61.1499),
    "BOS": (42.3656, -71.0096), "VCE": (45.5053, 12.3519),
    "MUC": (48.3538, 11.7861), "ZRH": (47.4581, 8.5555),
    "NCE": (43.6584, 7.2159), "LBG": (48.9695, 2.4418),
    "AMS": (52.3105, 4.7683), "WAL": (37.9402, -75.4666),
    "DAL": (32.8471, -96.8517), "NCO": (41.5972, -71.4121),
    "YYT": (47.6186, -52.7519), "CIA": (41.7999, 12.5949),
    "IOR": (53.1067, -9.6536), "HPN": (41.0670, -73.7076),
    "GJT": (39.1224, -108.5267), "ACY": (39.4576, -74.5772),
    "HIO": (45.5404, -122.9499), "MSO": (46.9163, -114.0906),
    "LAS": (36.0801, -115.1522), "TEB": (40.8501, -74.0608),
    "NAS": (25.0380, -77.4662), "LAX": (33.9416, -118.4085),
    "BFI": (47.5299, -122.3020), "ATL": (33.6407, -84.4277),
    "SXM": (18.0410, -63.1089), "YVT": (52.8214, -108.3073),
}

df["lat_from"] = df["iata_from"].apply(lambda x: airport_coords.get(x, (None, None))[0])
df["lon_from"] = df["iata_from"].apply(lambda x: airport_coords.get(x, (None, None))[1])
df["lat_to"] = df["iata_to"].apply(lambda x: airport_coords.get(x, (None, None))[0])
df["lon_to"] = df["iata_to"].apply(lambda x: airport_coords.get(x, (None, None))[1])

df = df.dropna(subset=["lat_from", "lat_to"])


# ----------------------------------------------------
# DISTANZEN
# ----------------------------------------------------
df["distance_km"] = df["distance_miles"] * 1.60934


# ----------------------------------------------------
# DUPLIKATE ZÄHLEN
# ----------------------------------------------------
route_counts = df.groupby(["iata_from", "iata_to"]).size().reset_index(name="count")
df = df.merge(route_counts, on=["iata_from", "iata_to"], how="left")


# ----------------------------------------------------
# NEUES FARBSYSTEM
# ----------------------------------------------------
def get_color(count):
    if count >= 5:
        return "green"     # 5+
    elif count == 4:
        return "yellow"
    elif count == 3:
        return "purple"
    elif count == 2:
        return "blue"
    else:
        return "red"       # 1

df["color"] = df["count"].apply(get_color)
df["line_width"] = 3


# ----------------------------------------------------
# GESAMTSTATISTIK & INGOLSTADT VERGLEICH
# ----------------------------------------------------
total_distance = df["distance_km"].sum()
total_emission = total_distance * 2.5 / 1000  # t CO₂

# Ingolstadt Werte
INGOLSTADT_CO2 = 1_500_000  # t/Jahr (realistischer Wert)
INGOLSTADT_EINWOHNER = 140_000

ingolstadt_percent = (total_emission / INGOLSTADT_CO2) * 100
ingolstadt_per_capita = INGOLSTADT_CO2 / INGOLSTADT_EINWOHNER
hilfiger_factor = total_emission / ingolstadt_per_capita

st.subheader("📊 Statistiken & Vergleich mit Ingolstadt")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Flüge insgesamt", len(df))
c2.metric("Gesamtdistanz (km)", f"{total_distance:,.0f}")
c3.metric("CO₂-Ausstoß (t)", f"{total_emission:.2f}")
c4.metric("Anteil vs. Ingolstadt", f"{ingolstadt_percent:.4f}%")

st.caption(
    f"Ein Einwohner von Ingolstadt verursacht ca. **{ingolstadt_per_capita:.1f} t CO₂/Jahr**. "
    f"Tommy Hilfiger verursacht durch Privatflüge allein **{hilfiger_factor:.2f}×** so viel."
)


# ----------------------------------------------------
# DATUMSLIMITER
# ----------------------------------------------------
min_date, max_date = df["date"].min(), df["date"].max()
selected_date = st.slider("Flüge bis zum Datum anzeigen:",
                          min_date.date(), max_date.date(), max_date.date())

filtered = df[df["date"].dt.date <= selected_date]


# ----------------------------------------------------
# KARTE
# ----------------------------------------------------
st.subheader("🌍 Flugrouten – farbcodiert nach Häufigkeit")

fig = px.scatter_geo()

# Fluglinien zeichnen
for _, row in filtered.iterrows():
    fig.add_trace(px.line_geo(
        lat=[row["lat_from"], row["lat_to"]],
        lon=[row["lon_from"], row["lon_to"]],
    ).data[0].update(
        line=dict(width=row["line_width"], color=row["color"])
    ))

# ZOOM berechnen
min_lat = filtered[["lat_from", "lat_to"]].min().min()
max_lat = filtered[["lat_from", "lat_to"]].max().min()
min_lon = filtered[["lon_from", "lon_to"]].min().min()
max_lon = filtered[["lon_from", "lon_to"]].max().max()

fig.update_geos(
    lataxis_range=[min_lat - 2, max_lat + 2],
    lonaxis_range=[min_lon - 2, max_lon + 2],
    showcountries=True,
    showcoastlines=True
)

# ----------------------------------------------------
# SCHÖNE LEGENDE IM WEISSEN KASTEN AUF DER KARTE
# ----------------------------------------------------
legend_html = (
    "<b>Flughäufigkeit</b><br>"
    "<span style='color:red;'>⬤</span> 1 Flug<br>"
    "<span style='color:blue;'>⬤</span> 2 Flüge<br>"
    "<span style='color:purple;'>⬤</span> 3 Flüge<br>"
    "<span style='color:yellow;'>⬤</span> 4 Flüge<br>"
    "<span style='color:green;'>⬤</span> 5+ Flüge<br>"
)

fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))

fig.add_annotation(
    x=0.98, y=0.02,
    xanchor="right", yanchor="bottom",
    text=legend_html,
    showarrow=False,
    align="left",
    bgcolor="white",
    bordercolor="black",
    borderwidth=1,
    opacity=0.85
)

st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------
# DATENTABELLE
# ----------------------------------------------------
st.subheader("📋 Gefilterte Flugdaten")
st.dataframe(filtered[["date", "from", "to", "distance_miles", "distance_km", "count"]])
