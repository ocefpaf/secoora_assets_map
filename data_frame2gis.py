#!/usr/bin/env python

# conda execute
# env:
#  - fiona
#  - gdal <2.0.0
#  - matplotlib
#  - geojson
#  - pandas
#  - xlrd
# channels:
#  - ioos
# run_with: python

"""
Create GeoJSON Features for SECOORA Assets.

To test the features copy-and-paste the GeoJSON file onto:

http://geojson.io/

Run with,
$ conda execute -v data_frame2gis.py
to ensure same results.

"""

import json
import fiona
import pandas as pd
from matplotlib.patches import Wedge
from geojson import FeatureCollection, Feature, Polygon, Point

url = ("https://raw.githubusercontent.com/ocefpaf/"
       "secoora_assets_map/gh-pages/secoora_icons/")


status_colors = dict(Planned="orange",
                     Operational="green",
                     Permitting="yellow",
                     Construction="yellow")

platforms_icons = dict({"Fixed Surface Buoy": "buoy",
                        "Fixed Bottom Station": "circ",
                        "Fixed Bottom Mount Mooring": "tri",
                        "Fixed Coastal Station": "shore_station",
                        "HFRadar": "hfradar"})

icon = (url + "{platform}-{status}.png").format
# The values are from a GMT script @vembus provided.
# The comments values were used by @kwilcox in
# https://github.com/SECOORA/static_assets/blob/master/hfradar/hfradar_csv_to_gis.py
ranges = dict({5: 190,  # 225
               8: 160,  # 175
               12: 130,  # 124
               16: 100})  # 100


def wedge(radar):
    """
    Make a HF-radar `matplotlib.patches.Wedge` from a StartAngle, SpreadAngle,
    Center (Longitude, Latitude), and Radius (radar range).

    """
    r = ranges[int(radar["MHz"])] / 111.1  # deg2km
    theta1, theta2 = radar["StartAngle"], radar["SpreadAngle"]
    center = radar["Longitude"], radar["Latitude"]
    try:
        return Wedge(center, r, theta1+theta2, theta1)
    except ValueError:
        return None


def mpl_patch2geo_polygon(patch):
    """Close the matplotlib`patch` and return a GeoJSON `Polygon`."""
    p = patch.get_path()
    vertices = p.vertices.tolist()
    return Polygon([vertices + [vertices[-2]]])


def parse_hfradar(df, **kw):
    """
    Expect a pandas.DataFrame with the following columns:
    - ResponsibleParty
    - Type
    - DisplayTitle
    - Abrreviated ID
    - Latitude
    - Longitude
    - MHz Status
    - StartAngle
    - SpreadAngle

    """
    defaults = dict(stroke="#aeccae",
                    stroke_width=1,
                    stroke_opacity=0.5,
                    fill="#deffde",
                    fill_opacity=0.25)
    defaults.update(kw)

    polygons, points = [], []
    for status, group in df.groupby("Status"):
        kw = dict(platform="hfradar", status=status_colors[status])
        for name, row in group.iterrows():
            popupContent = "{} ({} MHz)".format(row["DisplayTitle"],
                                                row["MHz"])
            properties = dict(icon=icon(**kw),
                              name=name,
                              popupContent=popupContent)
            patch = wedge(row)
            if patch:
                polygon = mpl_patch2geo_polygon(patch)
            point = Point([row["Longitude"], row["Latitude"]])

            points.append(Feature(geometry=point, properties=properties))
            polygons.append(Feature(geometry=polygon, properties=defaults))
    return FeatureCollection(points+polygons)


def parse_stations(df):
    """
    Group SECOORA stations spreadsheet into PlatformType+Status.

    Expect a pandas.DataFrame with the following columns:
    - PlatformType
    - Status
    - Longitude
    - Latitude
    - LocationDescription
    - DisplayTitle (name)

    """
    features = []
    for (platformtype, status), group in df.groupby(["PlatformType",
                                                     "Status"]):
        kw = dict(status=status_colors[status],
                  platform=platforms_icons[platformtype])
        for name, row in group.iterrows():
            properties = dict(icon=icon(**kw),
                              name=row["Name"],
                              popupContent=row["LocationDescription"])
            geometry = Point([row["Longitude"], row["Latitude"]])
            feature = Feature(geometry=geometry, properties=properties)
            features.append(feature)
    return FeatureCollection(features)


def save_geojson(geojson, fname):
    """Save to GeoJSON."""
    kw = dict(sort_keys=True, indent=2, separators=(",", ": "))
    with open(fname, "w") as f:
        json.dump(geojson, f, **kw)


def save_shapefile(geojson, fname, geometry="Point"):
    """
    Save one `geometry` type from a geojson of a __geo_interface__ as a
    shapefile`.

    CAVEAT: this is a lossy conversion! I am passing along only the name
    property.

    """
    schema = {"geometry": geometry,
              "properties": {"name": "str:80"}}

    with fiona.open(fname, "w", "ESRI Shapefile", schema) as f:
        for k, feature in enumerate(geojson["features"]):
            if feature["geometry"]["type"] == geometry:
                try:
                    name = feature["properties"]["name"]
                except KeyError:
                    name = k
                f.write({
                    "geometry": feature["geometry"],
                    "properties": {"name": name},
                    })

if __name__ == "__main__":
    import os

    directory = "spreadsheets"
    save = "data"

    # Stations.
    fname = os.path.join(directory, "secoora_station_assets.xlsx")
    df = pd.read_excel(fname, index_col=2)

    geojson = parse_stations(df)
    save_geojson(geojson, fname=os.path.join(save, "stations.geojson"))
    save_shapefile(geojson, fname=os.path.join(save, "stations.shp"),
                   geometry="Point")

    # HFRadar.
    fname = os.path.join(directory, "secoora_hfradar_sites.xlsx")
    df = pd.read_excel(fname, index_col=3)

    geojson = parse_hfradar(df)
    save_geojson(geojson, fname=os.path.join(save, "hfradar.geojson"))
    save_shapefile(geojson, fname=os.path.join(save, "hfradar_point.shp"),
                   geometry="Point")
    save_shapefile(geojson, fname=os.path.join(save, "hfradar_polygon.shp"),
                   geometry="Polygon")
