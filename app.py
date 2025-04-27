import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import json
import os
import shutil

# Chargement des donnees
def charger_donnees():
    try:
        df_consommation = pd.read_csv("output/data/consommation.csv")
        df_production = pd.read_csv("output/data/production.csv")
        df_temperature = pd.read_csv("output/data/temperature.csv")
        df_co2 = pd.read_csv("output/data/co2.csv")
        with open("output/data/metadata.json", "r") as f:
            metadata = json.load(f)
        print("Données chargées avec succès.")
        return {
            "consommation": df_consommation,
            "production": df_production,
            "temperature": df_temperature,
            "co2": df_co2,
            "metadata": metadata
        }
    except Exception as e:
        print(f"Erreur lors du chargement des données: {e}")
        return None

# Initialisation des donnees
donnees = charger_donnees()

if donnees is None:
    raise Exception("Erreur : Impossible de charger les données.")

# Initialisation de l'app Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Layout de l'application
app.layout = html.Div([
    html.H1("Tableau de Bord de Maintenance Énergétique", style={"textAlign": "center", "marginBottom": "30px"}),

    html.Div([
        html.Div([
            html.H3("Informations Générales", style={"textAlign": "center"}),
            html.Div([
                html.P(f"Surface totale du bâtiment : {donnees['metadata']['surface_totale']} m²"),
                html.P(f"Surface des panneaux photovoltaïques : {donnees['metadata']['surface_pv']} m²"),
                html.P(f"Consommation totale : {donnees['metadata']['consommation_totale']:.2f} kWh"),
                html.P(f"Production totale : {donnees['metadata']['production_totale']:.2f} kWh"),
                html.P(f"Température moyenne : {donnees['metadata']['temperature_moyenne']:.1f} °C"),
                html.P(f"Taux moyen de CO2 : {donnees['metadata']['co2_moyen']} ppm"),
                html.P(f"Date de génération : {donnees['metadata']['date_generation']}")
            ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "5px"})
        ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top", "padding": "10px"}),

        html.Div([
            html.H3("Filtres", style={"textAlign": "center"}),
            html.Label("Niveau :"),
            dcc.Dropdown(
                id="niveau-dropdown",
                options=[{"label": niveau, "value": niveau} for niveau in donnees["consommation"]["niveau"].unique()],
                value=donnees["consommation"]["niveau"].unique()[0],
                clearable=False
            ),
            html.Label("Usage :"),
            dcc.Dropdown(
                id="usage-dropdown",
                options=[{"label": usage, "value": usage} for usage in donnees["consommation"]["usage"].unique()],
                value=donnees["consommation"]["usage"].unique()[0],
                clearable=False
            ),
            html.Label("Période :"),
            dcc.RangeSlider(
                id="periode-slider",
                min=0,
                max=len(donnees["consommation"]["date"].unique()) - 1,
                value=[0, len(donnees["consommation"]["date"].unique()) - 1],
                marks={i: date[:5] for i, date in enumerate(sorted(donnees["consommation"]["date"].unique()))},
                step=1
            )
        ], style={"width": "65%", "display": "inline-block", "verticalAlign": "top", "padding": "10px"})
    ], style={"marginBottom": "30px"}),

    html.Div([
        dcc.Graph(id="graph-consommation-orientation"),
        dcc.Graph(id="graph-evolution-consommation"),
        dcc.Graph(id="graph-production-pv"),
        dcc.Graph(id="graph-temperature")
    ], style={"marginBottom": "30px"}),

    html.Div([
        html.H3("Carte Interactive des Consommations", style={"textAlign": "center"}),
        html.Iframe(
            id="carte-iframe",
            src="/assets/carte_consommations.html",
            style={"width": "100%", "height": "500px", "border": "none"}
        )
    ], style={"marginBottom": "30px"})
])

# Callbacks
def enregistrer_callbacks(app, donnees):
    @app.callback(
        Output("graph-consommation-orientation", "figure"),
        [Input("niveau-dropdown", "value"),
         Input("usage-dropdown", "value"),
         Input("periode-slider", "value")]
    )
    def update_graph_orientation(niveau, usage, periode):
        df = donnees["consommation"]
        dates = sorted(df["date"].unique())
        selected_dates = dates[periode[0]:periode[1]+1]
        filtered_df = df[(df["niveau"] == niveau) & (df["usage"] == usage) & (df["date"].isin(selected_dates))]
        fig = px.bar(
            filtered_df.groupby("orientation")["consommation"].sum().reset_index(),
            x="orientation",
            y="consommation",
            color="orientation",
            labels={"orientation": "Orientation", "consommation": "Consommation (kWh)"}
        )
        return fig

    @app.callback(
        Output("graph-evolution-consommation", "figure"),
        [Input("niveau-dropdown", "value"),
         Input("usage-dropdown", "value"),
         Input("periode-slider", "value")]
    )
    def update_graph_evolution(niveau, usage, periode):
        df = donnees["consommation"]
        dates = sorted(df["date"].unique())
        selected_dates = dates[periode[0]:periode[1]+1]
        filtered_df = df[(df["niveau"] == niveau) & (df["usage"] == usage) & (df["date"].isin(selected_dates))]
        fig = px.line(
            filtered_df,
            x="date",
            y="consommation",
            color="orientation",
            labels={"date": "Date", "consommation": "Consommation (kWh)"}
        )
        return fig

    @app.callback(
        Output("graph-production-pv", "figure"),
        [Input("niveau-dropdown", "value")]
    )
    def update_graph_production(niveau):
        df = donnees["production"]
        fig = px.bar(df, x="date", y="production", labels={"date": "Date", "production": "Production (kWh)"})
        return fig

    @app.callback(
        Output("graph-temperature", "figure"),
        [Input("niveau-dropdown", "value")]
    )
    def update_graph_temperature(niveau):
        df = donnees["temperature"]
        filtered_df = df[df["niveau"] == niveau]
        fig = px.line(
            filtered_df,
            x="date",
            y="temperature",
            color="orientation",
            labels={"date": "Date", "temperature": "Température (°C)"}
        )
        return fig

# Enregistrement des callbacks
enregistrer_callbacks(app, donnees)

# Copie de la carte folium dans assets
os.makedirs("assets", exist_ok=True)
if os.path.exists("output/cartes/carte_consommations.html"):
    shutil.copy("output/cartes/carte_consommations.html", "assets/carte_consommations.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)
