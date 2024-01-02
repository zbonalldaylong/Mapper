import pandas as pd
import os
import regex as re
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import numpy as np
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point
from os.path import exists
import warnings
import requests
import sys
import plotly.io as pio
from zipfile import ZipFile
from array import array
from pandas import json_normalize


# Configuration for the map being output
map_settings = {
    "nat_toggle": True,  # show specific countries or world
    "nat_label_toggle": False,  # show national labels
    "subnat_toggle": True,  # show subnational regions (provinces, states, eg)
    "subnat_label_toggle": False,  # show subnat labels
    "subnat_highlight_toggle": True,  # specify and highlight a subnat
    "city_toggle": True,  # show cities
    "chloro_toggle": True,  # apply a chloro map
    "csv_toggle": True,  # apply data from a csv file
    "irregular_marker_toggle": False,  # map irregular features onto the map using custom lon/lats (csv or otherwise)
    "irregular_feature_toggle": True
    if exists(Path(__file__).parent / "features/feature_1.geojson")
    else False,  # Draw custom highways, etc.; checks features directory
}

map_content = {
    "country_list": ["Canada"],  # Countries to be displayed
    # Format: [city name, label position]
    "city_list": [],
    # Note: Works with either the name of a province or the name of a country, in which case all provinces of said country will be mapped.
    "subnat_list": ["Ontario"],
    # Format: [label, direction, extent, size_override (0 for unchanged)] / Direction: 'top-right', 'bottom-right', 'right', 'top', etc. / Size: multiplier for adjustment (eg 2 = 2x)
    # Note: For more finicky adjustments run the same country through the list twice.
    "label_adjusts": [[]],
    # CSV list - nats and subnats for which the csv data will apply to.
    "csv_list": ["Canada"],
    # Irregular features comes in dict form for easy importing of outside data sources.
    "irregular_markers": [
        {
            "name": "Taj Mahal",
            "lon": 78.04206,
            "lat": 27.17389,
            "position": "middle right",
        }
    ],
}

map_styling = {
    "background_color": "#ede7f1",
    "nat_border_opacity": 1,
    "nat_border_width": 1,
    "nat_border_color": "#282828",
    "subnat_border_opacity": 0.5,
    "subnat_border_width": 0.5,
    "subnat_border_color": "#282828",
    # CITIES / MARKERS
    "city_text_size": 12,
    "city_text_color": "#241f20",
    "marker_size": 8,
    "marker_color": "#241f20",
    # FEATURES
    "feature_color": "rgba(202, 52, 51, 0.5)",
    "feature_fill_opacity": 0.25,
    "feature_border_opacity": 0.75,
    "feature_border_width": 1,
    "feature_border_color": "#282828",
    # LABELS
    "nat_label_opacity": 0.7,
    "nat_label_size": 30,
    "nat_label_color": "#282828",
    "subnat_label_opacity": 0.5,
    "subnat_label_size": 15,
    "subnat_label_color": "#282828",
}


class MapBuilder:
    def __init__(self, token: str, settings: dict, content: dict, styling: dict):
        # Mapbox token from environmental variable
        self.token = token
        self.config = settings
        self.content = content
        self.styling = styling

        # Label DF (For all labeled features including nat, subnat, cities, irregular features)
        self.label_df = pd.DataFrame(
            columns=["name", "centroid", "size", "position", "code", "type"]
        )

        # Load Natural Earth data (serves as template for custom maps)
        map_path = Path(__file__).parent / "maps/"
        city_db_path = Path(__file__).parent / "city_db/"
        with open(
            map_path / "naturalearth.geojson", "r", encoding="utf-8"
        ) as geojson_file:
            self.countries = json.load(geojson_file)
        with open(
            map_path / "naturalearth_countries.geojson", "r", encoding="utf-8"
        ) as geojson_file:
            self.borders = json.load(geojson_file)

        # Store a collection of the specific geojson data we're using so as to avoid re-iterating the NaturalEarth set.
        init_slice = []
        for i in self.borders["features"]:
            if i["properties"]["ADMIN"] in self.content["country_list"]:
                init_slice.append(i)
        self.nat_db = {"type": ["FeatureCollection"], "features": init_slice}

        init_slice = []
        for i in self.countries["features"]:
            if i["properties"]["admin"] in self.content["country_list"]:
                init_slice.append(i)
        self.subnat_db = {"type": ["FeatureCollection"], "features": init_slice}

        # Loads geojsons from the features directory
        if self.config["irregular_feature_toggle"] == True:
            self.features = []
            files = os.listdir(Path(__file__).parent / "features")
            for x in files:
                if "feature_" in x:
                    with open(
                        Path(__file__).parent / f"features/{x}", "r", encoding="utf-8"
                    ) as geojson_file:
                        self.features.append(json.load(geojson_file))

        # Loads csv file(s) from csv directory
        if self.config["chloro_toggle"] == True:
            self.csvs = []
            files = os.listdir(Path(__file__).parent / "csv")
            for x in files:
                if "csv_" in x:
                    with open(
                        Path(__file__).parent / f"csv/{x}", "r", encoding="utf-8-sig"
                    ) as csv_file:
                        self.csvs.append(pd.read_csv(csv_file, sep=","))
            # Loads geojson file(s) from features directory
            self.geojsons = []
            geoj_path = Path(__file__).parent / "features"
            files = os.listdir(geoj_path)
            for x in files:
                if "geojson_" in x:
                    with open(
                        geoj_path / "geojson_1.geojson", "r", encoding="utf-8"
                    ) as geojson_file:
                        self.geojsons.append(json.load(geojson_file))

        # CITY DATA
        def city_data_builder():
            def _iso_code_grabber():
                """Initializes necessary data for mapping of cities"""
                # List of ISO codes to be used for mapping cities and notable locations (city_list)
                self.iso_list = pd.read_csv(
                    city_db_path / "cities.csv", encoding="utf-8"
                )
                self.iso_codes = []

                # Get ISO codes if cities being displayed
                if (
                    self.config["city_toggle"] == True
                    and self.config["nat_toggle"] == True
                ):
                    for column, row in self.iso_list.iterrows():
                        if row["Name"] in self.content["country_list"]:
                            self.iso_codes.append(row["Code"])

            def _city_loader():
                """Checks for local municipal geodata and if missing downloads it. Lean=True to save load times by only importing major settlements"""

                def __city_db_formatter(input_csv):
                    """Formats and loads municipal data as a full df. Returns feature class P (populated places)"""
                    df = pd.read_csv(
                        input_csv,
                        encoding="utf-8",
                        sep="\t",
                        low_memory=False,
                        names=columns,
                    )
                    df = df.drop(
                        columns=[
                            "geonameid",
                            "elevation",
                            "dem",
                            "timezone",
                            "modification date",
                            "admin4 code",
                        ]
                    )
                    return df.loc[df["feature class"] == "P"]

                def __city_extractor(input_df):
                    """Gets the specific cities required and saves them to the class method"""
                    city_list = [x[0] for x in self.content["city_list"]]
                    input_df = input_df[input_df["asciiname"].isin(city_list)]
                    return input_df

                columns = [
                    "geonameid",
                    "name",
                    "asciiname",
                    "alternatenames",
                    "latitude",
                    "longitude",
                    "feature class",
                    "feature code",
                    "country code",
                    "cc2",
                    "admin1 code",
                    "admin2 code",
                    "admin3 code",
                    "admin4 code",
                    "population",
                    "elevation",
                    "dem",
                    "timezone",
                    "modification date",
                ]

                out_df = pd.DataFrame(columns=columns).drop(
                    columns=[
                        "geonameid",
                        "elevation",
                        "dem",
                        "timezone",
                        "modification date",
                        "admin4 code",
                    ]
                )

                for i in range(0, len(self.iso_codes)):
                    fname = str(self.iso_codes[i]) + ".zip"
                    save_dir = city_db_path / self.iso_codes[i]
                    full_path = save_dir / fname
                    # Check for pre-existing dictionary
                    if exists(save_dir):
                        pass
                    # Download data if not found
                    else:
                        download_url = (
                            "https://download.geonames.org/export/dump/"
                            + str(self.iso_codes[i])
                            + ".zip"
                        )
                        save_dir = city_db_path / self.iso_codes[i]
                        os.mkdir(city_db_path / self.iso_codes[i])

                        # Download the zip
                        r = requests.get(download_url, stream=True)
                        with open(full_path, "wb") as file:
                            for chunk in r.iter_content(chunk_size=128):
                                file.write(chunk)

                        # Extract the zip
                        with ZipFile(save_dir / fname, "r") as zf:
                            zf.extractall(save_dir)
                        os.remove(save_dir / fname)

                    # Extract and instantiate specific city data in content settings
                    c_fname = str(self.iso_codes[i]) + ".txt"
                    entry = __city_extractor(__city_db_formatter(save_dir / c_fname))
                    if entry.shape[0] > 0:
                        out_df = pd.concat([out_df, entry], axis=0)
                    else:
                        pass

                return out_df

            # Initialize city data
            _iso_code_grabber()
            self.city_db = (
                _city_loader()
            )  # This will be setting the class-instantiated city db (for later plotting)

        # Initialize relevant functions
        if self.config["city_toggle"] == True:
            city_data_builder()

    def draw_map(self, in_df=None, in_geo=None):
        """Main function to output final map"""

        def _lat_cruncher(input: json):
            """Converts geojson to list of lon/lat"""
            points = []
            out_list = []
            for feature in input["features"]:
                if feature["geometry"]["type"] == "Polygon":
                    points.extend(feature["geometry"]["coordinates"][0])
                    points.append([None, None])  # Marks the end of a polygon
                elif feature["geometry"]["type"] == "MultiPolygon":
                    for polyg in feature["geometry"]["coordinates"]:
                        points.extend(polyg[0])
                        points.append([None, None])  # End of polygon
                elif feature["geometry"]["type"] == "MultiLineString":
                    points.extend(feature["geometry"]["coordinates"])
                    points.append([None, None])
                elif feature["geometry"]["type"] == "LineString":
                    points.extend(feature["geometry"]["coordinates"])
                    points.append([None, None])
                else:
                    pass
            lons, lats = zip(*points)
            out_list = [lons, lats]
            return out_list

        def _get_geodata(input_json: json):
            """Get center position in a given feature (generally a country) for label placement; coordinate stored in-class"""
            gpd_df = gpd.GeoDataFrame.from_features(input_json["features"])
            area = float(gpd_df.area)
            points = gpd_df.centroid
            lon = float(points.x)
            lat = float(points.y)
            points = [lon, lat]
            return points, area

        def _draw_labels():

            # Clean up label df
            self.label_df.index = self.label_df["name"]
            self.label_df.drop(columns=["name"], inplace=True)

            if self.config["nat_label_toggle"] == True:
                for index, row in self.label_df.iterrows():
                    if row["type"] == "nat":
                        fig.add_scattermapbox(
                            lat=[row["centroid"][1]],
                            lon=[row["centroid"][0]],
                            showlegend=False,
                            mode="text",
                            text=index.upper(),
                            fillcolor=self.styling["nat_label_color"],
                            opacity=self.styling["nat_label_opacity"],
                            textposition="middle center",
                            # Adjusts on the basis of country size
                            textfont=dict(
                                size=self.styling["nat_label_size"] * 1.5
                                if row["size"] > 150
                                else self.styling["nat_label_size"]
                                if row["size"] > 110
                                else (self.styling["nat_label_size"] * 0.8)
                                if row["size"] > 80
                                else (self.styling["nat_label_size"] * 0.65)
                                if row["size"] > 50
                                else (self.styling["nat_label_size"] * 0.45)
                                if row["size"] > 30
                                else (self.styling["nat_label_size"] * 0.35)
                                if row["size"] > 10
                                else 10,
                                color=self.styling["nat_label_color"],
                            ),
                        ),

            if self.config["subnat_label_toggle"] == True:
                for x in self.content["subnat_list"]:
                    if x not in self.content["country_list"]:
                        fig.add_scattermapbox(
                            lat=[self.label_df.loc[x]["centroid"][1]],
                            lon=[self.label_df.loc[x]["centroid"][0]],
                            showlegend=False,
                            mode="text",
                            text=x.upper(),
                            fillcolor=self.styling["subnat_label_color"],
                            opacity=self.styling["subnat_label_opacity"],
                            textposition="middle center",
                            # Adjusts on the basis of country size
                            textfont=dict(
                                size=self.styling["subnat_label_size"] * 1.5
                                if self.label_df.loc[x]["size"] > 150
                                else self.styling["subnat_label_size"]
                                if self.label_df.loc[x]["size"] > 110
                                else (self.styling["subnat_label_size"] * 0.8)
                                if self.label_df.loc[x]["size"] > 80
                                else (self.styling["subnat_label_size"] * 0.65)
                                if self.label_df.loc[x]["size"] > 50
                                else (self.styling["subnat_label_size"] * 0.45)
                                if self.label_df.loc[x]["size"] > 30
                                else (self.styling["subnat_label_size"] * 0.35)
                                if self.label_df.loc[x]["size"] > 10
                                else 10,
                                color=self.styling["subnat_label_color"],
                            ),
                        ),

        def _draw_countries():
            """Draws external (national) borders."""

            def __crunch_countries():
                """Crunch the data for countries to be drawn; derives lon/lat pairs from geojson"""
                countries_slice = []
                labels_slice = []
                exclusion_list = []
                for i in self.nat_db["features"]:
                    # Outputs the lon/lat pairs for countries in the country_list and also stores their centroid point in-class for future reference

                    if (
                        i["properties"]["ADMIN"] in self.content["country_list"]
                        and i["properties"]["ADMIN"] not in exclusion_list
                    ):
                        i["id"] = i["properties"]["ADMIN"]
                        countries_slice.append(i)

                        # Store centroids in class df for labels
                        points, area = _get_geodata(
                            {"type": ["FeatureCollection"], "features": [i]}
                        )
                        new_entry = {
                            "name": str(i["properties"]["ADMIN"]),
                            "centroid": points,
                            "size": area,
                            "position": "middle-right",
                            "type": "nat",
                        }

                        labels_slice.append(new_entry)

                        # Avoid double-counting when multiple countries in country_list
                        exclusion_list.append(i["properties"]["ADMIN"])

                self.label_df = pd.concat(
                    [self.label_df, pd.DataFrame(labels_slice)],
                    ignore_index=True,
                    axis=0,
                )

                # Return a json containing geometry of specified countries
                return _lat_cruncher(
                    {"type": "FeatureCollection", "features": countries_slice}
                )

            self.external_borders = __crunch_countries()

            # Add external borders to overall figure
            fig.add_scattermapbox(
                lat=self.external_borders[1],
                lon=self.external_borders[0],
                showlegend=False,
                mode="lines",
                fillcolor=self.styling["background_color"],
                fill="toself"
                if self.config["chloro_toggle"] == False
                and self.config["subnat_toggle"] == False
                else "none",
                opacity=self.styling["nat_border_opacity"],
                line=dict(
                    width=self.styling["nat_border_width"],
                    color=self.styling["nat_border_color"],
                ),
            )

        def _draw_subnats():
            """Draws sub-national (regional/provincial/state) borders"""

            def __crunch_subnats():
                """Crunch the data for countries to be drawn; derives lon/lat pairs from geojson"""
                subnats_slice = []
                exclusion_list = []
                labels_slice = []
                for i in self.subnat_db["features"]:
                    if len(self.content["subnat_list"]) > 0:
                        if (
                            i["properties"]["name"] in self.content["subnat_list"]
                            or i["properties"]["admin"] in self.content["subnat_list"]
                        ) and i["properties"]["name"] not in exclusion_list:
                            i["id"] = i["properties"]["admin"]
                            subnats_slice.append(i)
                            # Store centroids in class df for labels
                            points, area = _get_geodata(
                                {"type": ["FeatureCollection"], "features": [i]}
                            )

                            new_entry = {
                                "name": i["properties"]["name_en"],
                                "centroid": points,
                                "size": area,
                                "position": "middle-right",
                                "code": i["properties"]["iso_3166_2"].replace("-", ""),
                                "type": "subnat",
                            }

                            labels_slice.append(new_entry)
                    else:
                        if (
                            i["properties"]["admin"] in self.content["country_list"]
                            and i["properties"]["name"] not in exclusion_list
                        ):
                            i["id"] = i["properties"]["admin"]
                        subnats_slice.append(i)

                    # Avoid double-counting when multiple countries in country_list
                    exclusion_list.append(i["properties"]["name"])

                self.label_df = pd.concat(
                    [self.label_df, pd.DataFrame(labels_slice)],
                    ignore_index=False,
                    axis=0,
                )

                # Return a json containing geometry of specified countries
                return _lat_cruncher(
                    {"type": "FeatureCollection", "features": subnats_slice}
                )

            internal_borders = __crunch_subnats()

            # Add internal borders to figure
            fig.add_scattermapbox(
                lat=internal_borders[1],
                lon=internal_borders[0],
                showlegend=False,
                mode="lines",
                fillcolor=self.styling["background_color"],
                fill="toself" if self.config["chloro_toggle"] == False else "none",
                opacity=self.styling["subnat_border_opacity"],
                line=dict(
                    width=self.styling["subnat_border_width"],
                    color=self.styling["subnat_border_color"],
                ),
            )

        def _draw_markers():
            """Draws cities and other notable features"""

            def __crunch_markers():
                """Crunch the data for cities to be drawn; derives lon/lat pairs from custom db initialized at class init (self.city_db)"""
                out_df = pd.DataFrame(
                    columns=["name", "type", "lon", "lat", "position"]
                )
                cities_slice = []

                for x in self.content["city_list"]:
                    # The city DB contains a variety of feature codes based on size of a population center. This goes for the largest one by moving down the hierarchy

                    if any(
                        self.city_db.loc[self.city_db["name"] == x[0]]["feature code"]
                        == "PPLC"
                    ):
                        cities_slice.append(
                            {
                                "name": x[0],
                                "type": "city",
                                "lon": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLC")
                                    ]["longitude"]
                                ),
                                "lat": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLC")
                                    ]["latitude"]
                                ),
                                "position": x[1],
                            }
                        )
                        continue

                    if any(
                        self.city_db.loc[self.city_db["name"] == x[0]]["feature code"]
                        == "PPLA"
                    ):
                        cities_slice.append(
                            {
                                "name": x[0],
                                "type": "city",
                                "lon": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLA")
                                    ]["longitude"]
                                ),
                                "lat": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLA")
                                    ]["latitude"]
                                ),
                                "position": x[1],
                            }
                        )
                        continue

                    if any(
                        self.city_db.loc[self.city_db["name"] == x[0]]["feature code"]
                        == "PPLA2"
                    ):
                        cities_slice.append(
                            {
                                "name": x[0],
                                "type": "city",
                                "lon": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLA2")
                                    ]["longitude"]
                                ),
                                "lat": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLA2")
                                    ]["latitude"]
                                ),
                                "position": x[1],
                            }
                        )
                        continue

                    if any(
                        self.city_db.loc[self.city_db["name"] == x[0]]["feature code"]
                        == "PPLA3"
                    ):
                        cities_slice.append(
                            {
                                "name": x[0],
                                "type": "city",
                                "lon": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLA3")
                                    ]["longitude"]
                                ),
                                "lat": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLA3")
                                    ]["latitude"]
                                ),
                                "position": x[1],
                            }
                        )
                        continue

                    if any(
                        self.city_db.loc[self.city_db["name"] == x[0]]["feature code"]
                        == "PPLA4"
                    ):
                        cities_slice.append(
                            {
                                "name": x[0],
                                "type": "city",
                                "lon": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLA4")
                                    ]["longitude"]
                                ),
                                "lat": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPLA4")
                                    ]["latitude"]
                                ),
                                "position": x[1],
                            }
                        )
                        continue

                    if any(
                        self.city_db.loc[self.city_db["name"] == x[0]]["feature code"]
                        == "PPL"
                    ):
                        cities_slice.append(
                            {
                                "name": x[0],
                                "type": "city",
                                "lon": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPL")
                                    ]["longitude"]
                                ),
                                "lat": float(
                                    self.city_db.loc[
                                        (self.city_db["name"] == x[0])
                                        & (self.city_db["feature code"] == "PPL")
                                    ]["latitude"]
                                ),
                                "position": x[1],
                            }
                        )
                        continue

                out_df = pd.concat(
                    [out_df, pd.DataFrame(cities_slice)], ignore_index=False, axis=0
                )

                return out_df

            city_coords = __crunch_markers()

            for index, row in city_coords.iterrows():

                fig.add_scattermapbox(
                    lat=[row["lat"]],
                    lon=[row["lon"]],
                    showlegend=False,
                    mode="markers+text",
                    marker=go.scattermapbox.Marker(
                        size=self.styling["marker_size"],
                        symbol="circle",
                        allowoverlap=False,
                        color=self.styling["marker_color"],
                    ),
                    textposition=row["position"],
                    text=row["name"],
                    textfont=dict(
                        size=self.styling["city_text_size"],
                        color=self.styling["city_text_color"],
                    ),
                    fillcolor=self.styling["background_color"],
                )

            # Map irregular features if there are any
            if self.config["irregular_marker_toggle"] == True:
                for x in self.content["irregular_markers"]:

                    fig.add_scattermapbox(
                        lat=[x["lat"]],
                        lon=[x["lon"]],
                        showlegend=False,
                        mode="markers+text",
                        marker=go.scattermapbox.Marker(
                            size=self.styling["marker_size"],
                            symbol="circle",
                            allowoverlap=False,
                            color=self.styling["marker_color"],
                        ),
                        textposition=x["position"],
                        text=x["name"],
                        textfont=dict(
                            size=self.styling["city_text_size"],
                            color=self.styling["city_text_color"],
                        ),
                        fillcolor=self.styling["background_color"],
                    )

            else:
                pass

        def _draw_irregulars():
            """Draws irregular features (imported geojson files from the features sub-directory)"""

            def __crunch_irregulars():
                """Prepares geojson data; takes a class list of geojsons (self.features) and outputs list of lon/lat pairs"""
                features_out = []
                for geo in self.features:
                    features_out.append(
                        _lat_cruncher(
                            {"type": "FeatureCollection", "features": geo["features"]}
                        )
                    )
                return features_out

            # Map irregulars (allows for multiple features
            for x in __crunch_irregulars():
                fig.add_scattermapbox(
                    lat=x[1],
                    lon=x[0],
                    showlegend=False,
                    mode="lines",
                    fillcolor=self.styling["feature_color"],
                    fill="toself",
                    opacity=self.styling["feature_border_opacity"],
                    line=dict(
                        width=self.styling["feature_border_width"],
                        color=self.styling["feature_border_color"],
                    ),
                )

            # Draw an additional top layer of external borders to clean the map up; thickens the borders to hide imperfections
            fig.add_scattermapbox(
                lat=self.external_borders[1],
                lon=self.external_borders[0],
                showlegend=False,
                mode="lines",
                fillcolor=self.styling["background_color"],
                fill="none",
                opacity=self.styling["nat_border_opacity"],
                line=dict(
                    width=(self.styling["nat_border_width"] * 1.5),
                    color=self.styling["nat_border_color"],
                ),
            )

        def _draw_chloro():
            """Uses data from csv files located in csv directory to draw a chloro layer. Assumption that the csv file has the following headers: admin, admin1, date.  Code col is what to match, date col is date"""

            working_geo = in_geo
            working_df = in_df

            trace = go.Figure(
                go.Choroplethmapbox(
                    geojson=in_geo,
                    locations=in_df.index,
                    z=in_df["mw"],
                    colorscale="YlOrRd",
                )
            )

            fig.add_traces(trace.data[0])

        def _label_adjuster():
            """As a final step, this function iterates over the fig object and adjusts labels specified in self.content['label_adjusts']"""

            def __shifter(in_lon, in_lat, direction, degree):
                """Adjusts lon, lat pairs for labels based on direction and degree"""

                diagonals = degree / 2

                if direction == "top":
                    in_lat += degree
                elif direction == "top-left":
                    in_lat += diagonals
                    in_lon -= diagonals
                elif direction == "top-right":
                    in_lat += diagonals
                    in_lon += diagonals
                elif direction == "bottom":
                    in_lat -= degree
                elif direction == "bottom-left":
                    in_lat -= diagonals
                    in_lon -= diagonals
                elif direction == "bottom-right":
                    in_lat -= diagonals
                    in_lon += diagonals
                elif direction == "right":
                    in_lon += degree
                elif direction == "left":
                    in_lon -= degree
                return in_lon, in_lat

            if len(self.content["label_adjusts"]) > 0:
                exclusion_list = []
                for no, x in enumerate(fig.data):
                    if x.mode == "text" and x.text not in exclusion_list:
                        for y in self.content["label_adjusts"]:
                            if y[0].upper() == x.text:
                                adjusted_lon, adjusted_lat = __shifter(
                                    fig.data[no].lon[0], fig.data[no].lat[0], y[1], y[2]
                                )
                                fig.data[no].lon = [adjusted_lon]
                                fig.data[no].lat = [adjusted_lat]
                                if y[3] != 0:
                                    fig.data[no].textfont["size"] = (
                                        fig.data[no].textfont["size"] * y[3]
                                    )
                                else:
                                    pass
                            else:
                                pass

                        exclusion_list.append(x.text)

            else:
                pass

        # Initialize base template (uses a mapbox style for background)
        fig = go.Figure()

        # Execute drawing functions to build the map
        if self.config["chloro_toggle"] == False:
            _draw_subnats()
            _draw_countries()
            _draw_labels(nat=True)
            _draw_irregulars()
            _draw_markers()
            _label_adjuster()

        if self.config["chloro_toggle"] == True:
            _draw_subnats()
            _draw_countries()
            _draw_labels()
            _draw_chloro()

            fig.update_layout(
                coloraxis_showscale=True,
                margin={"l": 0, "r": 0, "b": 0, "t": 25},
                title="<b><i>Ontario Renewables Pipeline, Generation by District (2022, MW)<i><b>",
                title_x=0.5,
                font_family="Helvetica",
                showlegend=True,
                legend_title=dict(text="MW"),
                mapbox=go.layout.Mapbox(
                    style="mapbox://styles/zbon/ckshpu8fb091a17p951bwv9hx",
                    zoom=4.12,
                    accesstoken=self.token,
                    center_lat=self.label_df.loc[
                        self.content["country_list"][0], "centroid"
                    ][1],
                    center_lon=self.label_df.loc[
                        self.content["country_list"][0], "centroid"
                    ][0],
                ),
            )

        fig.show()


if __name__ == "__main__":
    # load config
    map_token = os.getenv("MAP_TOKEN")

    if not map_token:
        print("Missing env values for MAP_TOKEN")
        sys.exit(1)

    pd.set_option("mode.chained_assignment", None)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_colwidth", None)
    warnings.filterwarnings("ignore")

    m = MapBuilder(map_token, map_settings, map_content, map_styling)

    # Prepare CSV FILE/DF for mapping --> Requires an 'id' column to be matched with custom geojson
    def regexer(string, input):
        try:
            return re.search(string, input).group(0)
        except:
            return "NaN"

    csv_df = m.csvs[0]
    csv_df = csv_df.loc[csv_df["Application status"] != "Refused"]
    csv_df["id"] = 0
    csv_df["Location"] = csv_df["Location"].apply(lambda x: x.strip())
    csv_df["mw"] = csv_df["Project description"].apply(
        lambda x: regexer("(\d+\.\d+|\d+)\s?MW", x).replace("MW", "").strip()
    )
    csv_df = csv_df.astype({"mw": float})
    csv_df["mw"] = csv_df["mw"].apply(lambda x: round(x, 2))

    location_grouped = csv_df.groupby("Location")["mw"].aggregate("sum")

    # Prepare custom GEOJSON FILE/GEOJSON (Ontario) for mapping --> requires insertion of 'id' to be matched with above df (csv_df)
    counter = 0
    out_slice = []
    for i in m.geojsons[0]["features"]:
        counter += 1
        i["id"] = counter
        out_slice.append(i)
    ontario = {"type": "FeatureCollection", "features": out_slice}

    # Necessary formatting to adjust for disparate naming conventions on districts
    def formatter(input):
        if input != None:
            if input["OFFICIAL_M"] != None:
                if "leeds and grenville" in input["OFFICIAL_M"].lower():
                    return (
                        input["OFFICIAL_M"]
                        .lower()
                        .replace("and", "&")
                        .replace("county", "")
                        .replace("united counties of", "")
                        .strip()
                    )
                if "city" in input["OFFICIAL_M"].lower():
                    return input["OFFICIAL_M"].lower().split(" of ")[-1]
                if (
                    "county" in input["OFFICIAL_M"].lower()
                    or "counties" in input["OFFICIAL_M"].lower()
                ):
                    return (
                        input["OFFICIAL_M"]
                        .lower()
                        .replace("county of", "")
                        .replace("united", "")
                        .replace("counties", "")
                        .replace("county", "")
                        .strip()
                    )
                if "district" in input["OFFICIAL_M"].lower():
                    try:
                        return (
                            input["OFFICIAL_M"]
                            .lower()
                            .replace("district of", "")
                            .strip()
                        )
                    except:
                        return (
                            input["OFFICIAL_M"].lower().replace("district", "").strip()
                        )
                if "region" in input["OFFICIAL_M"].lower():
                    return (
                        input["OFFICIAL_M"]
                        .lower()
                        .replace("regional municipality of", "")
                        .replace("region", "")
                        .strip()
                    )
                if "municipality" in input["OFFICIAL_M"].lower():
                    return (
                        input["OFFICIAL_M"]
                        .lower()
                        .replace("municipality of", "")
                        .strip()
                    )
                else:
                    return input["OFFICIAL_M"].lower()
            else:
                if "leeds and grenville" in input["MUN_NAME"].lower():
                    return (
                        input["MUN_NAME"]
                        .lower()
                        .replace("and", "&")
                        .replace("county", "")
                        .replace("united counties of", "")
                        .strip()
                    )
                if "city" in input["MUN_NAME"].lower():
                    return input["MUN_NAME"].lower().split(" of ")[-1]
                if (
                    "county" in input["MUN_NAME"].lower()
                    or "counties" in input["MUN_NAME"].lower()
                ):
                    if "stormont" in input["MUN_NAME"].lower():
                        return (
                            input["MUN_NAME"]
                            .lower()
                            .replace("counties of", "")
                            .replace("and", "&")
                            .replace("united", "")
                            .strip()
                        )
                    else:
                        return (
                            input["MUN_NAME"]
                            .lower()
                            .replace("county of", "")
                            .replace("united", "")
                            .replace("counties of", "")
                            .replace("county", "")
                            .strip()
                        )
                if "district" in input["MUN_NAME"].lower():
                    try:
                        return (
                            input["MUN_NAME"].lower().replace("district of", "").strip()
                        )
                    except:
                        return input["MUN_NAME"].lower().replace("district", "").strip()
                if "region" in input["MUN_NAME"].lower():
                    return (
                        input["MUN_NAME"]
                        .lower()
                        .replace("regional municipality of", "")
                        .replace("region", "")
                        .strip()
                    )
                if "municipality of" in input["MUN_NAME"].lower():
                    return (
                        input["MUN_NAME"].lower().replace("municipality of", "").strip()
                    )
                else:
                    return input["MUN_NAME"].lower()

        else:
            return "NaN"

    # Create a dictionary for easy reference of the name + id in the geojson
    test_dict = {x["id"]: formatter(x["properties"]) for x in ontario["features"]}

    # Adjust the dataframe to insert an 'id' value that matches the custom geojson
    for index, row in csv_df.iterrows():
        match_term = (
            row["Location"]
            .lower()
            .replace("county of", "")
            .replace("united counties of", "")
            .replace("regional municipality of", "")
            .replace("district of", "")
            .replace("county", "")
            .replace("region", "")
            .replace("district", "")
            .strip()
        )
        if match_term in list(test_dict.values()):
            csv_df.at[index, "id"] = list(test_dict.keys())[
                list(test_dict.values()).index(match_term)
            ]

    grouped = csv_df.groupby("id")[["mw"]].aggregate("sum")

    grouped = grouped.loc[1:]

    m.draw_map(grouped, ontario)
