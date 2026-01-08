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

    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            line = fix_typos(line)

            # Formatierungen glätten
            line = re.sub(r"\((\w{3})\)", r" (\1)", line)
            line = re.sub(r",\s*\(", " (", line)
            line = re.sub(r"\s{2,}", " ", line)

            parts = [p.strip() for p in line.split(",")]

            # Wenn zu viele Kommas: mittlere Teile zusammenziehen
            if len(parts) > 5:
                parts = [parts[0], parts[1], parts[2], " ".join(parts[3:-1]), parts[-1]]

            if len(parts) == 5:
                cleaned.append(",".join(parts))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned))

    return output_file


clean_file = clean_csv()
df = pd.read_csv(clean_file)
df.columns = [c.strip().lower() for c in df.columns]

# Datum + numeric sauber machen
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["distance_miles"] = pd.to_numeric(df["distance_miles"], errors="coerce")
df = df.dropna(subset=["date", "from", "to", "distance_miles"]).copy()

# ----------------------------------------------------
# IATA EXTRAHIEREN
# ----------------------------------------------------
df["iata_from"] = df["from"].str.extract(r"\((.*?)\)")
df["iata_to"] = df["to"].str.extract(r"\((.*?)\)")

df["iata_from"] = df["iata_from"].astype(str).str.replace(",", "").str.strip()
df["iata_to"] = df["iata_to"].astype(str).str.replace(",", "").str.strip()

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

df = df.dropna(subset=["lat_from", "lon_from", "lat_to", "lon_to"]).copy()

# ----------------------------------------------------
# DISTANZEN + CO2
# ----------------------------------------------------
df["distance_km"] = df["distance_miles"] * 1.60934
df["co2_t"] = df["distance_km"] * 2.5 / 1000  # simple Annahme

# ----------------------------------------------------
# DUPLIKATE ZÄHLEN (Route)
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
total_emission = df["co2_t"].sum()

INGOLSTADT_CO2 = 1_500_000  # t/Jahr (Annahme)
INGOLSTADT_EINWOHNER = 140_000

ingolstadt_percent = (total_emission / INGOLSTADT_CO2) * 100 if INGOLSTADT_CO2 else 0
ingolstadt_per_capita = INGOLSTADT_CO2 / INGOLSTADT_EINWOHNER if INGOLSTADT_EINWOHNER else 0
hilfiger_factor = (total_emission / ingolstadt_per_capita) if ingolstadt_per_capita else 0

st.subheader("📊 Statistiken & Vergleich mit Ingolstadt")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Flüge insgesamt", f"{len(df):,}")
c2.metric("Gesamtdistanz (km)", f"{total_distance:,.0f}")
c3.metric("CO₂-Ausstoß (t)", f"{total_emission:.2f}")
c4.metric("Anteil vs. Ingolstadt", f"{ingolstadt_percent:.4f}%")

st.caption(
    f"Ein Einwohner von Ingolstadt verursacht ca. **{ingolstadt_per_capita:.2f} t CO₂/Jahr**. "
    f"Tommy Hilfiger verursacht durch Privatflüge allein **{hilfiger_factor:.2f}×** so viel."
)

# ----------------------------------------------------
# DATUMSLIMITER
# ----------------------------------------------------
min_date, max_date = df["date"].min(), df["date"].max()
selected_date = st.slider(
    "Flüge bis zum Datum anzeigen:",
    min_date.date(),
    max_date.date(),
    max_date.date(),
)

filtered = df[df["date"].dt.date <= selected_date].copy()

# ----------------------------------------------------
# EXTRA STATISTIK (GEFILTERT)  ✅ HINZUGEFÜGT
# ----------------------------------------------------
st.subheader("📌 Zusätzliche Statistiken (gefiltert)")

f_total_distance = filtered["distance_km"].sum()
f_total_emission = filtered["co2_t"].sum()

k1, k2, k3 = st.columns(3)
k1.metric("Flüge (gefiltert)", f"{len(filtered):,}")
k2.metric("Distanz (km, gefiltert)", f"{f_total_distance:,.0f}")
k3.metric("CO₂ (t, gefiltert)", f"{f_total_emission:.2f}")

if len(filtered) > 0:
    median_distance = filtered["distance_km"].median()
    p95_distance = filtered["distance_km"].quantile(0.95)
    min_distance = filtered["distance_km"].min()
    max_distance = filtered["distance_km"].max()
    avg_co2_flight = filtered["co2_t"].mean()

    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Median Distanz (km)", f"{median_distance:,.0f}")
    a2.metric("95%-Quantil Distanz (km)", f"{p95_distance:,.0f}")
    a3.metric("Kürzester Flug (km)", f"{min_distance:,.0f}")
    a4.metric("Längster Flug (km)", f"{max_distance:,.0f}")
    a5.metric("Ø CO₂ pro Flug (t)", f"{avg_co2_flight:.2f}")

    # Monatliche Trends
    monthly = (
        filtered.assign(month=filtered["date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month")
        .agg(
            flights=("date", "count"),
            distance_km=("distance_km", "sum"),
            co2_t=("co2_t", "sum"),
        )
        .reset_index()
    )

    st.subheader("📈 Trends & Verteilungen (gefiltert)")

    t1, t2 = st.columns(2)
    fig_flights = px.bar(monthly, x="month", y="flights", title="Flüge pro Monat")
    t1.plotly_chart(fig_flights, use_container_width=True)

    fig_co2 = px.line(monthly, x="month", y="co2_t", title="CO₂ pro Monat (t)")
    t2.plotly_chart(fig_co2, use_container_width=True)

    v1, v2 = st.columns(2)
    fig_hist = px.histogram(filtered, x="distance_km", nbins=20, title="Verteilung der Flugdistanz (km)")
    v1.plotly_chart(fig_hist, use_container_width=True)

    fig_box = px.box(filtered, y="distance_km", title="Distanz-Boxplot (Ausreißer sichtbar)")
    v2.plotly_chart(fig_box, use_container_width=True)

    # Rankings
    st.subheader("🏁 Rankings (gefiltert)")

    top_routes = (
        filtered.groupby(["from", "to"])
        .agg(
            flights=("date", "count"),
            distance_km=("distance_km", "sum"),
            co2_t=("co2_t", "sum"),
        )
        .reset_index()
        .sort_values("flights", ascending=False)
        .head(10)
    )

    dep = filtered["from"].value_counts().rename_axis("location").reset_index(name="departures")
    arr = filtered["to"].value_counts().rename_axis("location").reset_index(name="arrivals")
    top_locations = dep.merge(arr, on="location", how="outer").fillna(0)
    top_locations["total_movements"] = top_locations["departures"] + top_locations["arrivals"]
    top_locations = top_locations.sort_values("total_movements", ascending=False).head(10)

    r1, r2 = st.columns(2)
    r1.markdown("**Top 10 Routen (nach Anzahl Flüge)**")
    r1.dataframe(top_routes, use_container_width=True)

    r2.markdown("**Top 10 Orte (Starts + Landungen)**")
    r2.dataframe(top_locations, use_container_width=True)

    short_often = (
        filtered[filtered["distance_km"] < 500]
        .groupby(["from", "to"])
        .size()
        .reset_index(name="flights")
        .sort_values("flights", ascending=False)
        .head(10)
    )
    st.markdown("**Bonus: Kurz aber oft (< 500 km) – Top 10**")
    st.dataframe(short_often, use_container_width=True)
else:
    st.info("Keine Daten im gewählten Zeitraum für die Zusatz-Statistiken.")

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
max_lat = filtered[["lat_from", "lat_to"]].max().max()
min_lon = filtered[["lon_from", "lon_to"]].min().min()
max_lon = filtered[["lon_from", "lon_to"]].max().max()

fig.update_geos(
    lataxis_range=[min_lat - 2, max_lat + 2],
    lonaxis_range=[min_lon - 2, max_lon + 2],
    showcountries=True,
    showcoastlines=True
)

# ----------------------------------------------------
# LEGENDE (Kasten)
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
st.dataframe(filtered[["date", "from", "to", "distance_miles", "distance_km", "count", "co2_t"]])
