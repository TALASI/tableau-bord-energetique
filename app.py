#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Création d'un tableau de bord interactif avec carte des consommations énergétiques
"""

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import json
import os
import shutil

# Chargement des données
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

# Création de l'application Dash
donnees = charger_donnees()

if donnees is None:
    raise Exception("Erreur : impossible de charger les données. Vérifiez vos fichiers de données.")

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H1("Tableau de Bord de Maintenance Énergétique", style={"textAlign": "center", "marginBottom": "30px"}),

    html.Div([
        html.Div([
            html.H3("Informations Générales", style={"textAlign": "center"}),
            html.Div([
                html.P(f"Surface totale du bâtiment : {donnees['metadata']['surface_totale']} m²"),
                html.P(f"Surface des panneaux photovoltaïques : {donnees['metadata']['surface_pv']} m²"),
                html.P(f"Consommation totale : {donnees['metadata']['consommation_totale']} kWh"),
                html.P(f"Production totale : {donnees['metadata']['production_totale']} kWh"),
                html.P(f"Température moyenne : {donnees['metadata']['temperature_moyenne']} °C"),
                html.P(f"Taux moyen de CO2 : {donnees['metadata']['co2_moyen']} ppm"),
                html.P(f"Date de génération : {donnees['metadata']['date_generation']}")
            ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "5px"})
        ], style={"width": "40%", "display": "inline-block", "verticalAlign": "top"}),

        html.Div([
            html.H3("Filtres", style={"textAlign": "center"}),
            dcc.Dropdown(
                id="niveau-dropdown",
                options=[{"label": niveau, "value": niveau} for niveau in donnees["consommation"]["niveau"].unique()],
                value=donnees["consommation"]["niveau"].unique()[0]
            ),
            dcc.Dropdown(
                id="usage-dropdown",
                options=[{"label": usage, "value": usage} for usage in donnees["consommation"]["usage"].unique()],
                value=donnees["consommation"]["usage"].unique()[0]
            )
        ], style={"width": "55%", "display": "inline-block", "verticalAlign": "top", "marginLeft": "5%"})
    ], style={"marginBottom": "40px"}),

    html.Div([
        html.H3("Graphique Consommation", style={"textAlign": "center"}),
        dcc.Graph(id="graph-consommation")
    ])
])

# Callbacks pour mettre à jour les graphiques
@app.callback(
    Output("graph-consommation", "figure"),
    Input("niveau-dropdown", "value"),
    Input("usage-dropdown", "value")
)
def update_graph(niveau, usage):
    df = donnees["consommation"]
    filtered_df = df[(df["niveau"] == niveau) & (df["usage"] == usage)]

    fig = px.line(
        filtered_df,
        x="date",
        y="consommation",
        title=f"Consommation énergétique - {niveau} - {usage}",
        labels={"date": "Date", "consommation": "Consommation (kWh)"}
    )
    return fig

# Création du dossier assets et copie du fichier carte (si nécessaire)
os.makedirs("assets", exist_ok=True)
if os.path.exists("output/cartes/carte_consommations.html"):
    shutil.copy("output/cartes/carte_consommations.html", "assets/carte_consommations.html")

# Point d'entrée standard pour Gunicorn
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8050))
    app.run(host="0.0.0.0", port=port)
