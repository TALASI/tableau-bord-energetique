#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Création d'un tableau de bord interactif avec carte des consommations énergétiques
"""

import dash
from dash import dcc, html, callback, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import os
import folium
from folium.plugins import HeatMap
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Chargement des données
def charger_donnees():
    try:
        # Chargement des données de consommation
        df_consommation = pd.read_csv("output/data/consommation.csv")
        
        # Chargement des données de production
        df_production = pd.read_csv("output/data/production.csv")
        
        # Chargement des données de température
        df_temperature = pd.read_csv("output/data/temperature.csv")
        
        # Chargement des données de CO2
        df_co2 = pd.read_csv("output/data/co2.csv")
        
        # Chargement des métadonnées
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

# Création d'une carte interactive des consommations
def creer_carte_consommations(df_consommation):
    # Création d'un répertoire pour les cartes
    os.makedirs("output/cartes", exist_ok=True)
    
    # Coordonnées fictives pour le bâtiment (centre de Paris)
    latitude_base = 48.856614
    longitude_base = 2.3522219
    
    # Création d'une carte centrée sur le bâtiment
    m = folium.Map(location=[latitude_base, longitude_base], zoom_start=18, tiles="CartoDB positron")
    
    # Ajout d'un marqueur pour le bâtiment
    folium.Marker(
        location=[latitude_base, longitude_base],
        popup="Immeuble de bureaux",
        icon=folium.Icon(color="blue", icon="building", prefix="fa")
    ).add_to(m)
    
    # Création d'un DataFrame avec les coordonnées des zones
    zones = []
    
    # Calcul des coordonnées relatives pour chaque zone
    offsets = {
        "RDC": {"z": 0},
        "Étage 1": {"z": 0.0001},
        "Étage 2": {"z": 0.0002},
        "Étage 3": {"z": 0.0003}
    }
    
    orientations = {
        "Nord": {"x": 0, "y": 0.0002},
        "Sud": {"x": 0, "y": -0.0002},
        "Est": {"x": 0.0002, "y": 0},
        "Ouest": {"x": -0.0002, "y": 0}
    }
    
    # Agrégation des consommations par zone
    consommation_par_zone = df_consommation.groupby(["zone_id", "zone_nom", "niveau", "orientation"])["consommation"].sum().reset_index()
    
    # Normalisation des consommations pour la carte de chaleur (0-1)
    consommation_max = consommation_par_zone["consommation"].max()
    consommation_par_zone["consommation_normalisee"] = consommation_par_zone["consommation"] / consommation_max
    
    # Création des coordonnées pour chaque zone
    for _, zone in consommation_par_zone.iterrows():
        niveau = zone["niveau"]
        orientation = zone["orientation"]
        
        # Calcul des coordonnées
        lat = latitude_base + orientations[orientation]["y"] + offsets[niveau]["z"]
        lon = longitude_base + orientations[orientation]["x"] + offsets[niveau]["z"]
        
        # Ajout à la liste des zones
        zones.append({
            "zone_id": zone["zone_id"],
            "zone_nom": zone["zone_nom"],
            "niveau": niveau,
            "orientation": orientation,
            "consommation": zone["consommation"],
            "consommation_normalisee": zone["consommation_normalisee"],
            "latitude": lat,
            "longitude": lon
        })
    
    # Création d'un DataFrame pour les zones
    df_zones = pd.DataFrame(zones)
    
    # Création d'une carte de chaleur avec un gradient fixé
    heat_data = [[row["latitude"], row["longitude"], row["consommation_normalisee"]] for _, row in df_zones.iterrows()]
    
    # Utilisation d'un gradient sans les clés numériques problématiques
    gradient_map = {
        'min': 'blue',
        'mid1': 'lime',
        'mid2': 'yellow',
        'max': 'red'
    }
    
    HeatMap(heat_data, radius=15).add_to(m)
    
    # Ajout de marqueurs pour chaque zone
    for _, zone in df_zones.iterrows():
        folium.CircleMarker(
            location=[zone["latitude"], zone["longitude"]],
            radius=8,
            popup=f"{zone['zone_nom']}<br>Consommation: {zone['consommation']:.2f} kWh",
            color="black",
            fill=True,
            fill_color=get_color_for_value(zone["consommation_normalisee"]),
            fill_opacity=0.7
        ).add_to(m)
    
    # Sauvegarde de la carte
    m.save("output/cartes/carte_consommations.html")
    
    # Sauvegarde des données des zones pour le tableau de bord
    df_zones.to_csv("output/data/zones_geo.csv", index=False)
    
    print("Carte des consommations créée avec succès.")
    
    return df_zones

# Fonction pour obtenir une couleur en fonction d'une valeur normalisée
def get_color_for_value(value):
    if value < 0.4:
        return "blue"
    elif value < 0.65:
        return "lime"
    elif value < 0.8:
        return "yellow"
    else:
        return "red"

# Création du tableau de bord Dash
def creer_tableau_bord(donnees):
    # Extraction des DataFrames
    df_consommation = donnees["consommation"]
    df_production = donnees["production"]
    df_temperature = donnees["temperature"]
    df_co2 = donnees["co2"]
    metadata = donnees["metadata"]
    
    # Création de l'application Dash
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server
    
    # Définition de la mise en page
    app.layout = html.Div([
        html.H1("Tableau de Bord de Maintenance Énergétique", style={"textAlign": "center", "marginBottom": "30px"}),
        
        html.Div([
            html.Div([
                html.H3("Informations Générales", style={"textAlign": "center"}),
                html.Div([
                    html.P(f"Surface totale du bâtiment: {metadata['surface_totale']} m²"),
                    html.P(f"Surface des panneaux photovoltaïques: {metadata['surface_pv']} m²"),
                    html.P(f"Consommation totale: {metadata['consommation_totale']:.2f} kWh"),
                    html.P(f"Production totale: {metadata['production_totale']:.2f} kWh"),
                    html.P(f"Température moyenne: {metadata['temperature_moyenne']:.1f} °C"),
                    html.P(f"Niveau de CO2 moyen: {metadata['co2_moyen']:.0f} ppm"),
                    html.P(f"Date de génération: {metadata['date_generation']}")
                ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "5px"})
            ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top", "padding": "10px"}),
            
            html.Div([
                html.H3("Filtres", style={"textAlign": "center"}),
                html.Label("Niveau:"),
                dcc.Dropdown(
                    id="niveau-dropdown",
                    options=[{"label": niveau, "value": niveau} for niveau in df_consommation["niveau"].unique()],
                    value=df_consommation["niveau"].unique()[0],
                    clearable=False
                ),
                html.Label("Usage:"),
                dcc.Dropdown(
                    id="usage-dropdown",
                    options=[{"label": usage, "value": usage} for usage in df_consommation["usage"].unique()],
                    value=df_consommation["usage"].unique()[0],
                    clearable=False
                ),
                html.Label("Période:"),
                dcc.RangeSlider(
                    id="periode-slider",
                    min=0,
                    max=len(df_consommation["date"].unique()) - 1,
                    value=[0, len(df_consommation["date"].unique()) - 1],
                    marks={i: date.split("-")[1] + "/" + date.split("-")[0][2:] for i, date in enumerate(sorted(df_consommation["date"].unique()))},
                    step=1
                )
            ], style={"width": "65%", "display": "inline-block", "verticalAlign": "top", "padding": "10px"})
        ], style={"marginBottom": "30px"}),
        
        html.Div([
            html.Div([
                html.H3("Consommation par Orientation", style={"textAlign": "center"}),
                dcc.Graph(id="graph-consommation-orientation")
            ], style={"width": "48%", "display": "inline-block", "verticalAlign": "top"}),
            
            html.Div([
                html.H3("Évolution de la Consommation", style={"textAlign": "center"}),
                dcc.Graph(id="graph-evolution-consommation")
            ], style={"width": "48%", "display": "inline-block", "verticalAlign": "top"})
        ], style={"marginBottom": "30px"}),
        
        html.Div([
            html.Div([
                html.H3("Production Photovoltaïque", style={"textAlign": "center"}),
                dcc.Graph(id="graph-production-pv")
            ], style={"width": "48%", "display": "inline-block", "verticalAlign": "top"}),
            
            html.Div([
                html.H3("Température Intérieure", style={"textAlign": "center"}),
                dcc.Graph(id="graph-temperature")
            ], style={"width": "48%", "display": "inline-block", "verticalAlign": "top"})
        ], style={"marginBottom": "30px"}),
        
        html.Div([
            html.H3("Carte Interactive des Consommations", style={"textAlign": "center"}),
            html.Iframe(
                id="carte-iframe",
                src="/assets/carte_consommations.html",
                style={"width": "100%", "height": "500px", "border": "none"}
            )
        ], style={"marginBottom": "30px"}),
        
        html.Div([
            html.H3("Tableau des Consommations par Zone", style={"textAlign": "center"}),
            html.Div(id="tableau-consommations")
        ])
    ], style={"margin": "0 auto", "maxWidth": "1200px", "padding": "20px"})
    
    # Callback pour mettre à jour le graphique de consommation par orientation
    @app.callback(
        Output("graph-consommation-orientation", "figure"),
        [Input("niveau-dropdown", "value"),
         Input("usage-dropdown", "value"),
         Input("periode-slider", "value")]
    )
    def update_consommation_orientation(niveau, usage, periode):
        dates_triees = sorted(df_consommation["date"].unique())
        date_debut = dates_triees[periode[0]]
        date_fin = dates_triees[periode[1]]
        
        filtered_df = df_consommation[
            (df_consommation["niveau"] == niveau) &
            (df_consommation["usage"] == usage) &
            (df_consommation["date"] >= date_debut) &
            (df_consommation["date"] <= date_fin)
        ]
        
        consommation_par_orientation = filtered_df.groupby("orientation")["consommation"].sum().reset_index()
        
        fig = px.bar(
            consommation_par_orientation,
            x="orientation",
            y="consommation",
            color="orientation",
            labels={"orientation": "Orientation", "consommation": "Consommation (kWh)"},
            title=f"Consommation pour {usage} au {niveau}"
        )
        
        return fig
    
    # Callback pour mettre à jour le graphique d'évolution de la consommation
    @app.callback(
        Output("graph-evolution-consommation", "figure"),
        [Input("niveau-dropdown", "value"),
         Input("usage-dropdown", "value")]
    )
    def update_evolution_consommation(niveau, usage):
        filtered_df = df_consommation[
            (df_consommation["niveau"] == niveau) &
            (df_consommation["usage"] == usage)
        ]
        
        consommation_par_date = filtered_df.groupby(["date", "orientation"])["consommation"].sum().reset_index()
        
        fig = px.line(
            consommation_par_date,
            x="date",
            y="consommation",
            color="orientation",
            labels={"date": "Date", "consommation": "Consommation (kWh)", "orientation": "Orientation"},
            title=f"Évolution de la consommation pour {usage} au {niveau}"
        )
        
        return fig
    
    # Callback pour mettre à jour le graphique de production PV
    @app.callback(
        Output("graph-production-pv", "figure"),
        [Input("periode-slider", "value")]
    )
    def update_production_pv(periode):
        dates_triees = sorted(df_production["date"].unique())
        date_debut = dates_triees[periode[0]] if periode[0] < len(dates_triees) else dates_triees[-1]
        date_fin = dates_triees[periode[1]] if periode[1] < len(dates_triees) else dates_triees[-1]
        
        filtered_df = df_production[
            (df_production["date"] >= date_debut) &
            (df_production["date"] <= date_fin)
        ]
        
        fig = px.bar(
            filtered_df,
            x="date",
            y="production",
            labels={"date": "Date", "production": "Production (kWh)"},
            title="Production Photovoltaïque",
            color_discrete_sequence=["green"]
        )
        
        return fig
    
    # Callback pour mettre à jour le graphique de température
    @app.callback(
        Output("graph-temperature", "figure"),
        [Input("niveau-dropdown", "value"),
         Input("periode-slider", "value")]
    )
    def update_temperature(niveau, periode):
        dates_triees = sorted(df_temperature["date"].unique())
        date_debut = dates_triees[periode[0]] if periode[0] < len(dates_triees) else dates_triees[-1]
        date_fin = dates_triees[periode[1]] if periode[1] < len(dates_triees) else dates_triees[-1]
        
        filtered_df = df_temperature[
            (df_temperature["niveau"] == niveau) &
            (df_temperature["date"] >= date_debut) &
            (df_temperature["date"] <= date_fin)
        ]
        
        temperature_par_date = filtered_df.groupby(["date", "orientation"])["temperature"].mean().reset_index()
        
        fig = px.line(
            temperature_par_date,
            x="date",
            y="temperature",
            color="orientation",
            labels={"date": "Date", "temperature": "Température (°C)", "orientation": "Orientation"},
            title=f"Température intérieure au {niveau}"
        )
        
        return fig
    
    # Callback pour mettre à jour le tableau des consommations
    @app.callback(
        Output("tableau-consommations", "children"),
        [Input("niveau-dropdown", "value"),
         Input("usage-dropdown", "value"),
         Input("periode-slider", "value")]
    )
    def update_tableau_consommations(niveau, usage, periode):
        dates_triees = sorted(df_consommation["date"].unique())
        date_debut = dates_triees[periode[0]]
        date_fin = dates_triees[periode[1]]
        
        filtered_df = df_consommation[
            (df_consommation["niveau"] == niveau) &
            (df_consommation["usage"] == usage) &
            (df_consommation["date"] >= date_debut) &
            (df_consommation["date"] <= date_fin)
        ]
        
        consommation_par_zone = filtered_df.groupby(["zone_nom", "orientation"])["consommation"].sum().reset_index()
        
        # Création d'un tableau HTML
        table_header = [
            html.Thead(html.Tr([html.Th("Zone"), html.Th("Orientation"), html.Th("Consommation (kWh)")]))
        ]
        
        rows = []
        for _, row in consommation_par_zone.iterrows():
            rows.append(html.Tr([
                html.Td(row["zone_nom"]),
                html.Td(row["orientation"]),
                html.Td(f"{row['consommation']:.2f}")
            ]))
        
        table_body = [html.Tbody(rows)]
        
        return html.Table(table_header + table_body, style={"width": "100%", "textAlign": "center", "margin": "auto"})
    
    return app

# Fonction principale
def main():
    # Chargement des données
    donnees = charger_donnees()
    
    if donnees is None:
        print("Erreur: Impossible de charger les données. Vérifiez que les fichiers existent.")
        return
    
    # Création de la carte des consommations
    df_zones = creer_carte_consommations(donnees["consommation"])
    
    # Copie de la carte dans le dossier assets pour Dash
    os.makedirs("assets", exist_ok=True)
    import shutil
    shutil.copy("output/cartes/carte_consommations.html", "assets/carte_consommations.html")
    
    # Création et lancement du tableau de bord
    app = creer_tableau_bord(donnees)
    
    print("\nTableau de bord démarré. Ouvrez votre navigateur à l'adresse: http://localhost:8050")
    app.run(debug=True)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8050))
    app.run(debug=False, host='0.0.0.0', port=port)