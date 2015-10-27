"""Create GeoJSON Features for SECOORA HF-Radar ssets."""

import json
import fiona
from matplotlib.patches import Wedge
from geojson import FeatureCollection, Feature, Polygon, Point

url = ("https://raw.githubusercontent.com/ocefpaf/"
       "secoora_assets_map/gh-pages/secoora_icons/")

icon = (url + 'hfradar-{status}.png').format

status_colors = dict(Planned="orange",
                     Operational="green",
                     Permitting="yellow",
                     Construction="yellow")

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
    r = ranges[int(radar['MHz'])] / 111.1  # deg2km
    theta1, theta2 = radar['StartAngle'], radar['SpreadAngle']
    center = radar['Longitude'], radar['Latitude']
    try:
        return Wedge(center, r, theta1+theta2, theta1)
    except ValueError:
        return None


def mpl_patch2geo_polygon(patch):
    p = patch.get_path()
    vertices = p.vertices.tolist()
    return Polygon([vertices + [vertices[-2]]])


def df2features(df, **kw):
    """
    Expect a pandas.DataFrame with the columns:
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
        kw = dict(status=status_colors[status])
        for name, row in group.iterrows():
            popupContent = '{} ({} MHz)'.format(row['DisplayTitle'],
                                                row['MHz'])
            properties = dict(icon=icon(**kw),
                              name=name,
                              popupContent=popupContent)
            patch = wedge(row)
            if patch:
                polygon = mpl_patch2geo_polygon(patch)
            point = Point([row['Longitude'], row['Latitude']])

            points.append(Feature(geometry=point, properties=properties))
            polygons.append(Feature(geometry=polygon, properties=defaults))
    return FeatureCollection(points+polygons)


def save_json(geojson, fname='hfradar.geojson'):
    """Save to GeoJSON."""
    kw = dict(sort_keys=True, indent=2, separators=(',', ': '))
    with open(fname, 'w') as f:
        json.dump(geojson, f, **kw)


def save_shapefile(geojson, fname='hfradar_points.shp', geometry='Point'):
    """
    This is a lossy conversion!
    I am passing along only the station name.
    Someone with more GIS skills can modify the schema to add more metadata.

    """
    schema = {'geometry': geometry,
              'properties': {'name': 'str:80'}}

    with fiona.open(fname, 'w', 'ESRI Shapefile', schema) as f:
        for k, feature in enumerate(geojson['features']):
            if feature['geometry']['type'] == geometry:
                try:
                    name = feature['properties']['name']
                except KeyError:
                    name = k
                f.write({
                    'geometry': feature['geometry'],
                    'properties': {'name': name},
                    })

if __name__ == '__main__':
    import os
    import pandas as pd
    fname = os.path.join("spreadsheets",
                         "secoora_hfradar_sites.xlsx")
    df = pd.read_excel(fname, index_col=3)
    geojson = df2features(df)
    save_json(geojson, fname='hfradar.geojson')
