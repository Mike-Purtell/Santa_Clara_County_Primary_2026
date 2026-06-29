# Santa Clara County Primary 2026 Dashboard

This project contains a Dash web app for exploring Santa Clara County primary election data by precinct.

## What `app.py` does (high level)

- Loads processed precinct-level election data from `df_plot.parquet` using Polars.
- Loads precinct boundary geometry from `Precinct_Boundaries/Precinct_Boundaries.shp` using GeoPandas.
- Normalizes map geometry (simplifies shapes, ensures WGS84 CRS) and converts it to GeoJSON for Plotly map rendering.
- Defines election/candidate groupings for key races:
  - Governor
  - Attorney General
  - District Attorney
  - County Supervisor District 1
  - San Jose Councilmember District 9
- Builds an interactive Dash UI with Mantine components and Plotly graphs.
- Provides three coordinated controls:
  - Trend selector (e.g., redness/blueness/turnout)
  - Election selector
  - Candidate selector (updated dynamically from election choice)
- Renders two choropleth maps:
  - Trend map by precinct
  - Candidate vote-share map by precinct
- Renders two summary bar charts:
  - City-level trend aggregation
  - Candidate vote-share aggregation for the selected race
- Uses Dash callbacks so all visuals update interactively based on user selections.

## Main app flow

1. Load tabular election data.
2. Load and prepare precinct geometry.
3. Initialize Dash layout and controls.
4. Populate candidate list from selected election.
5. Update candidate map + bar chart from selected candidate.
6. Update trend map + bar chart from selected trend.
7. Run the Dash server in debug mode.

## Run locally

1. Install dependencies:
   - `pip install -r requirements.txt`
2. Make sure required data files are present:
   - `df_plot.parquet`
   - `Precinct_Boundaries/Precinct_Boundaries.shp` and companion shapefile files
3. Start the app:
   - `python app.py`

Then open the local Dash URL printed in the terminal (typically http://127.0.0.1:8050/).
