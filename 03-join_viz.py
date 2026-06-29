import polars.selectors as cs
import polars as pl
pl.Config().set_float_precision(2)
pl.Config().set_tbl_cols(20)
import geopandas as gpd
import json
import plotly.express as px
import polars as pl
from datetime import datetime
from plotly.subplots import make_subplots
import numpy as np



# -----------------------------
# 1. Load the Election Data
# -----------------------------
df = (
    pl.read_parquet('merged_voter_data.parquet')
    # .filter(~pl.col("PRECINCT").str.contains("Total", literal=True))
)
print(df.head())


# -----------------------------
# 2. Load the shapefile
# -----------------------------

shapefile_path = 'Precinct_Boundaries/Precinct_Boundaries.shp'
try:
    gdf = gpd.read_file(shapefile_path)
except Exception as e:
    print(f"Error reading shapefile: {e}")
    exit(1)

# -----------------------------
# 3. Ensure CRS is WGS84 (EPSG:4326)
# -----------------------------
if gdf.crs is None:
    print("Warning: No CRS found. Assuming EPSG:4326.")
    gdf.set_crs(epsg=4326, inplace=True)
elif gdf.crs.to_epsg() != 4326:
    gdf = gdf.to_crs(epsg=4326)

gdf['Precinct'] = gdf['Precinct'].astype(np.int32)

# ----------------------------
# 5. Convert to GeoJSON
# -----------------------------
geojson_data = json.loads(gdf.to_json())
 

# print(geojson_data)
print(gdf.head())
print(df.to_pandas())

type(gdf)
df_plot = (
    gdf.merge(df.to_pandas(), left_on='Precinct', right_on='PRECINCT', how='left')
    .drop(columns=['PRECINCT'])
    .rename(columns={'Precinct': 'PRECINCT'})
    .assign(
        CITY = lambda x: x['CITY'].ffill(),
        CITY_DIST = lambda x: x['CITY_DIST'].ffill(),
        COUNTY_DIST = lambda x: x['COUNTY_DIST'].ffill().astype(np.int32),
        ZIP_CODE = lambda x: x['ZIP_CODE'].ffill().astype(np.int32)
    )
)
print(f'{type(df_plot) = }')
print(df_plot.shape)
print(df_plot.head())
df_plot.to_parquet('df_plot.parquet')
df_plot.to_excel('df_plot.xlsx')

# -----------------------------
# 6. Create Plotly Choropleth
# -----------------------------
fig = px.choropleth_map(
    df_plot,                              # geopandas DataFrame
    geojson = geojson_data,
    featureidkey="properties.Precinct",
    locations="PRECINCT",
    color="BLUENESS",               # Column to color by
    # map_style="carto-positron",       # Map style
    map_style="open-street-map",       # Map style
    zoom=11,                          # Adjust zoom
    center={'lat': 37.360072115776084,    # Santa Clara County center latitude
            'lon': -121.92686443166403},  # Santa Clara County center longitude
    opacity=0.8,
    color_continuous_scale="Blues",
    range_color=[10, 90], # Adjust color range for better visualization
    # labels={'REDNESS': 'Redness %'},
    labels={'BLUENESS': 'Blueness %'},
)
fig.update_traces(marker_line_color="black", marker_line_width=1)
# fig.update_traces(
#     hovertemplate="<b>Precinct %{customdata[0]}</b><br>Turnout %{z}%<extra></extra>"
# )
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig.show()

print('done')