"""Create GeoJSON Features for SECOORA Stations Assets."""

import json
import fiona
from geojson import FeatureCollection, Feature, Point

url = ("https://raw.githubusercontent.com/ocefpaf/"
       "secoora_assets_map/gh-pages/secoora_icons/")

icon = (url + '{platform}-{status}.png').format

status_colors = dict(Planned="orange",
                     Operational="green",
                     Permitting="yellow",
                     Construction="yellow")

platforms_icons = dict({"Fixed Surface Buoy": "buoy",
                        "Fixed Bottom Station": "circ",
                        "Fixed Bottom Mount Mooring": "tri",
                        "Fixed Coastal Station": "shore_station"})


def df2features(df):
    """
    Group SECOORA stations spreadsheet into PlatformType+Status.

    Expect a pandas.DataFrame with the columns:
    - PlatformType
    - Status
    - Longitude
    - Latitude
    - LocationDescription
    - DisplayTitle (name)

    Returns a GeoJSON features representation of the stations.
    To test the features copy-and-paste the GeoJSON file on:
    http://geojson.io/

    """
    features = []
    for (platformtype, status), group in df.groupby(["PlatformType",
                                                     "Status"]):
        kw = dict(status=status_colors[status],
                  platform=platforms_icons[platformtype])
        for name, row in group.iterrows():
            properties = dict(icon=icon(**kw),
                              name=row['Name'],
                              popupContent=row['LocationDescription'])
            geometry = Point([row['Longitude'], row['Latitude']])
            feature = Feature(geometry=geometry, properties=properties)
            features.append(feature)
    return FeatureCollection(features)


def save_json(geojson, fname='stations.geojson'):
    """Save to GeoJSON."""
    kw = dict(sort_keys=True, indent=2, separators=(',', ': '))
    with open(fname, 'w') as f:
        json.dump(geojson, f, **kw)


def save_shapefile(geojson, fname='stations.shp'):
    """
    This is a lossy conversion!
    I am passing along only the station name.
    Someone with more GIS skills can modify the schema to add more metadata.

    """
    schema = {'geometry': 'Point',
              'properties': {'name': 'str:80'}}

    with fiona.open(fname, 'w', 'ESRI Shapefile', schema) as f:
        for feature in geojson['features']:
            f.write({
                'geometry': feature['geometry'],
                'properties': {'name': feature['properties']['name']},
                })

if __name__ == '__main__':
    import os
    import pandas as pd

    fname = os.path.join("spreadsheets",
                         "secoora_station_assets.xlsx")
    df = pd.read_excel(fname, index_col=2)

    geojson = df2features(df)

    save_json(geojson, fname='stations.geojson')
    save_shapefile(geojson, fname='stations.shp')
