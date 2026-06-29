import polars as pl
import polars.selectors as cs

import os
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import dash_mantine_components as dmc
import dash_ag_grid as dag
import geopandas as gpd
import json
import numpy as np

#
#    TODO:  Use lists of precincts for each district and use them to filter data
#           get list of city name and zip codes for each precint
# 
#

#----- GLOBALS -----------------------------------------------------------------
style_horizontal_thick_line = {'border': 'none', 'height': '4px', 
    'background': 'linear-gradient(to right, #007bff, #ff7b00)', 
    'margin': '10px,', 'fontsize': 32}
style_horizontal_thin_line = {'border': 'none', 'height': '2px', 
    'background': 'linear-gradient(to right, #007bff, #ff7b00)', 
    'margin': '10px,', 'fontsize': 12}
style_h2 = {'text-align': 'center', 'font-size': '40px', 
            'fontFamily': 'Arial','font-weight': 'bold', 'color': 'gray'}
style_h3 = {'text-align': 'center', 'font-size': '24px', 
            'fontFamily': 'Arial','font-weight': 'normal', 'color': 'gray'}
style_card = {'text-align': 'center', 'font-size': '20px', 
            'fontFamily': 'Arial','font-weight': 'normal'}

# Responsive grid span for stat cards
dmc_card_span = {"base": 12, "sm": 6, "md": 2}
dmc_card_span = {"base": 12, "sm": 6, "md": 2}

gov_names = ['BECERRA', 'STEYER', 'HILTON', 'BIANCO']
ag_names = ['BONTA']
da_names = ['ROSEN', 'CHUNG']
bos_names = ['ARENAS', 'MUNSON']
sj_d9_names = ['ALTWER', 'CHESTER']

choro_lw = 0.5 # line width for choropleth precinct borders

dict_election_candidates = {
    'GOV':        gov_names,
    'AG':         ag_names,
    'DA':         da_names,
    'SCC_BOS_D1': bos_names,
    'SJ_CM_D9':   sj_d9_names
}
#----- LOAD AND CLEAN DATA -----------------------------------------------------
root_file = 'df_plot'
if os.path.exists(root_file + '.parquet'):
    print('Loading data from parquet file...')
    df = (
        pl.read_parquet(root_file + '.parquet')
        .with_columns(cs.numeric().fill_null(0))  # Ensure numeric columns have no nulls
    )
else:
    print('parquet file not found...')

# -----------------------------
# 2. Load the shapefile
# -----------------------------

shapefile_path = 'Precinct_Boundaries/Precinct_Boundaries.shp'
try:
    gdf = gpd.read_file(shapefile_path)
except Exception as e:
    print(f"Error reading shapefile: {e}")
    exit(1)

# Simplify geometry (tolerance controls detail)
gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.05, preserve_topology=True)

# -----------------------------
# 3. Ensure CRS is WGS84 (EPSG:4326)
# -----------------------------
if gdf.crs is None:
    print("Warning: No CRS found. Assuming EPSG:4326.")
    gdf.set_crs(epsg=4326, inplace=True)
elif gdf.crs.to_epsg() != 4326:
    gdf = gdf.to_crs(epsg=4326)

gdf['Precinct'] = gdf['Precinct'].astype(np.int32)

# -----------------------------
# 5. Convert to GeoJSON
# -----------------------------
geojson_data = json.loads(gdf.to_json())
 

#-----  FUNCTIONS --------------------------------------------------------------
def stat_card(title, value, id_prefix=None):
    '''Accessible, responsive stat card.
    title: label shown at top-left
    value: initial value string (can be empty, will show N/A)
    id_prefix: sets the value text id as f'{id_prefix}-info' to match callbacks
    '''
    value_txt = (
        f'{value:,}' if isinstance(value, (int, float)) 
        else (value if value not in (None, '') else 'N/A')
    )
    value_id = f'{id_prefix}-info' if id_prefix else None

    header = dmc.Group(
        justify='space-between',
        align='flex-start',
        children=[
            dmc.Text(title, size='xl', fw=600, c='dimmed'),
        ]
    )

    # Right-side content stack (title + value)
    content_stack = dmc.Stack([
        header,
        dmc.Space(h=4),
        dmc.Text(
            value_txt, 
            id=value_id, 
            size='xl', 
            style={'lineHeight': '1.1', 'color': 'blue'}
        ),
    ], gap=0)

    # Left vertical accent bar
    accent_bar = html.Div(style={
        'width': '15px',
        'borderRadius': '4px',
        'background': 'repeating-linear-gradient(to bottom, #666666, #999999, #666666)'
    })

    # Row layout with accent bar + content
    row = html.Div([
        accent_bar,
        html.Div(content_stack, style={'flex': '1 1 auto'})
    ], style={'display': 'flex', 'gap': '12px', 'alignItems': 'stretch'})

    return dmc.Card(
        withBorder=True,
        shadow='sm',
        radius='md',
        padding='md',
        **{'aria-label': f'{title} statistic'},
        children=row
    )

def normalize_selection(selected_value, all_values_list):
    ''' Normalize dropdown/multiselect to handle ALL and ensure list type
    Input Args:
        selected_value: from dropdown/multiselect (can be string, list, or None)
        all_values_list: list of all possible values
    Returns:
        A list of selected values with 'ALL' properly handled
    '''
    # Handle None or empty list
    if selected_value is None or selected_value == []:
        return all_values_list
    
    # Handle 'ALL' as a string or as the only member of a list
    if selected_value == 'ALL' or selected_value == ['ALL']:
        return all_values_list
    
    # Handle list with 'ALL' in it
    if isinstance(selected_value, list):
        if 'ALL' in selected_value:
            # If list has ALL and other items, remove ALL
            filtered = [s for s in selected_value if s != 'ALL']
            return filtered if filtered else all_values_list
        return selected_value
    
    # Handle single string value
    return [selected_value]

def get_timeline_plot(df_filtered):
    # Create a timeline plot of dog postings over time
    df_time = (
        df_filtered
        .sort('DATE')             # sort before dynamic_group_by is a must
        .group_by_dynamic(
            index_column='DATE',  # specify the datetime column
            every='1mo',          # interval size
            period='1mo',         # window size
            closed='left'         # interval includes the left endpoint
        )
        .agg(pl.col('ID').count().alias('Dog Count'))   
    )
    fig = px.line(
        df_time,
        x='DATE', 
        y='Dog Count',
        title='Dog Postings Over Time',
        labels={'DATE': 'Month', 'Dog Count': 'Number of Dogs Posted'},
        markers=True
    )
    fig.update_layout(template='plotly_white', yaxis_type='log')
    # Extract last timeline point as Python scalars (Polars -> Python)
    last_date = df_time.select(pl.col('DATE').last()).item()
    last_count = int(df_time.select(pl.col('Dog Count').last()).item())

    # Add a marker + label using Plotly Graph Objects
    fig.add_trace(
        go.Scatter(
            x=[last_date],
            y=[last_count],
            mode='markers+text',
            text=[f'{last_count:,}  '],
            textposition='middle left',
            textfont=dict(size=16, color='blue'),
            marker=dict(size=8, color='gray'),
            hoverinfo='skip',
            showlegend=False,
            name=''
        )
    )
    return fig

def get_top_age_group(df):
    if df.height:
        return(
            df.get_column('AGE')
            .value_counts()
            .sort('count', descending=True)
            .item(0, 'AGE')
        )
    else:
        return('N/A')

def get_dog_name_pareto(df, gender):
    df_gender = (
        df
        .filter(pl.col('SEX') == gender)
        .group_by('NAME')
        .agg(NAME_COUNT = pl.col('ID').len())
        .select('NAME', 'NAME_COUNT')
        .sort('NAME_COUNT', descending=True)
    )
    if len(df_gender) > 10:
        df_gender = df_gender.head(10)

    fig = px.bar(
        df_gender, # .sort('NAME_COUNT'),
        y='NAME',
        x='NAME_COUNT',
        orientation='h',
        template='simple_white',
        title=f'Top 10 {gender} dog names',
        text=df_gender['NAME_COUNT'],
        labels={'NAME': '',}
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(
        showticklabels=False,
        ticks='',
        showline=False,
        title_text=''
    )
    return fig

def get_choropleth_trend(trend_name):
    if type(trend_name) == list:
        trend_name = trend_name[0]

    # Create a choropleth map of dog counts by state
    print(f'{trend_name = }')   
    print(f'{type(gdf) = }')
    print(f'{type(df) = }')
    color_scale = "Blues" if trend_name == 'BLUENESS' else "Reds"
    if trend_name == 'TURNOUT_PCT':
        color_scale = "Greens"
        range_color=[10, 50]
    else:
        range_color=[1, 90]
    fig = px.choropleth_map(
        df,  # .with_columns(cs.numeric().fill_null(0)),        # geopandas DataFrame
            geojson = geojson_data,
            featureidkey="properties.Precinct",
            locations="PRECINCT",
            color=trend_name,               # Column to color by
            # map_style="carto-positron",       # Map style
            map_style="open-street-map",       # Map style
            zoom=9,                          # Adjust zoom
            center={'lat': 37.360072115776084,    # Santa Clara County center latitude
                    'lon': -121.92686443166403},  # Santa Clara County center longitude
            opacity=0.8,
            color_continuous_scale=color_scale,
            range_color=range_color, # Adjust color range to exclude 0
            labels={trend_name: f'{trend_name} %'},
            custom_data=['PRECINCT', 'CITY','ZIP_CODE', 'REG_VOTERS', 'ACT_VOTERS', trend_name]   
        )
    fig.update_traces(marker_line_color="black", marker_line_width=choro_lw)
    fig.update_traces(hovertemplate=
        '<b>Precinct %{customdata[0]:.0f}</b><br>' + 
        '%{customdata[1]}, ' +
        '%{customdata[2]}<br>' +
        'Reg. Voters:  %{customdata[3]}<br>' +
        'Act. Voters:  %{customdata[4]}<br>' +
        f'{trend_name}: ' +  ' %{customdata[5]:.1f}<br>' +
        '<extra></extra>'
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

def get_choropleth_candidate(candidate_name):
    if type(candidate_name) == list:
        candidate_name = candidate_name[0]
    custom_data_common = ['PRECINCT', 'CITY','ZIP_CODE', 'REG_VOTERS', 'ACT_VOTERS']
    my_color = ''
    if candidate_name in ['BECERRA', 'STEYER', 'CHESTER', 'BONTA', 'ROSEN', 'ARENAS', 'CHESTER', 'MUNSON']:
        my_color_scale = 'Blues'
        my_color = 'blue'
    elif candidate_name in ['HILTON', 'BIANCO', 'CHUNG','ALTWER', 'MUNSON', ]:
        my_color_scale = 'Reds'
        my_color = 'red'
    else:
        my_color_scale = 'gray'  # default, means candidate is not listed here
        my_color = 'gray'

    my_color = ''
    if candidate_name in gov_names:
        candidate_pct = 'GOV_' + candidate_name + '_PCT'
        my_color = 'GOV_' + candidate_name
        candidate_votes = 'GOV_' + candidate_name
        my_custom_data=(
            custom_data_common + 
            [candidate_pct] +
            ['GOV_BECERRA', 'GOV_STEYER', 'GOV_HILTON', 'GOV_BIANCO']
            )
        my_hovertemplate= (
            '<b>Precinct %{customdata[0]:.0f}</b><br>' + 
            '%{customdata[1]}, ' +
            '%{customdata[2]}<br>' +
            'Reg. Voters:  %{customdata[3]}<br>' +
            'Act. Voters:  %{customdata[4]}<br>' +
            f'{candidate_pct}: ' +  ' %{customdata[5]:.1f}<br>' +
            'Becerra:  %{customdata[6]}<br>' +
            'Steyer:  %{customdata[7]}<br>' +
            'Hilton:  %{customdata[8]}<br>' +
            'Bianco:  %{customdata[9]}<br>' +
            '<extra></extra>'
        )


    elif candidate_name in ag_names:    
        candidate_pct= 'AG_' + candidate_name + '_PCT'
        candidate_votes = 'AG_' + candidate_name
        my_color = 'AG_' + candidate_name
        my_custom_data=(
            custom_data_common + 
            [candidate_pct] +
            ['AG_BONTA']
            )
        my_hovertemplate= (
            '<b>Precinct %{customdata[0]:.0f}</b><br>' + 
            '%{customdata[1]}, ' +
            '%{customdata[2]}<br>' +
            'Reg. Voters:  %{customdata[3]}<br>' +
            'Act. Voters:  %{customdata[4]}<br>' +
            f'{candidate_pct}: ' +  ' %{customdata[5]:.1f}<br>' +
            'Bonta:  %{customdata[6]}<br>' +
            '<extra></extra>'
        )

    elif candidate_name in da_names:    
        candidate_pct= 'DA_' + candidate_name + '_PCT'
        candidate_list = da_names
        my_color = 'DA_' + candidate_name
        my_custom_data=(
            custom_data_common + 
            [candidate_pct] +
            ['DA_ROSEN', 'DA_CHUNG']
            )
        my_hovertemplate= (
            '<b>Precinct %{customdata[0]:.0f}</b><br>' + 
            '%{customdata[1]}, ' +
            '%{customdata[2]}<br>' +
            'Reg. Voters:  %{customdata[3]}<br>' +
            'Act. Voters:  %{customdata[4]}<br>' +
            f'{candidate_pct}: ' +  ' %{customdata[5]:.1f}<br>' +
            'Rosen:  %{customdata[6]}<br>' +
            'Chung:  %{customdata[7]}<br>' +
            '<extra></extra>'
        )

    elif candidate_name in bos_names:
        candidate_pct= 'SCC1_' + candidate_name + '_PCT'
        candidate_list = bos_names
        my_color = 'SCC1_' + candidate_name

        my_custom_data=(
            custom_data_common + 
            [candidate_pct] +
            ['SCC1_ARENAS', 'SCC1_MUNSON']
            )
        my_hovertemplate= (
            '<b>Precinct %{customdata[0]:.0f}</b><br>' + 
            '%{customdata[1]}, ' +
            '%{customdata[2]}<br>' +
            'Reg. Voters:  %{customdata[3]}<br>' +
            'Act. Voters:  %{customdata[4]}<br>' +
            f'{candidate_pct}: ' +  ' %{customdata[5]:.1f}<br>' +
            'Arenas:  %{customdata[6]}<br>' +
            'Munson:  %{customdata[7]}<br>' +
            '<extra></extra>'
        )

    elif candidate_name in sj_d9_names:
        candidate_pct= 'SJD9_' + candidate_name + '_PCT'
        candidate_list = sj_d9_names
        my_color = 'SJD9_' + candidate_name
        my_custom_data=(
            custom_data_common + 
            [candidate_pct] +
            ['SJD9_CHESTER', 'SJD9_ALTWER']
            )
        my_hovertemplate= (
            '<b>Precinct %{customdata[0]:.0f}</b><br>' + 
            '%{customdata[1]}, ' +
            '%{customdata[2]}<br>' +
            'Reg. Voters:  %{customdata[3]}<br>' +
            'Act. Voters:  %{customdata[4]}<br>' +
            f'{candidate_pct}: ' +  ' %{customdata[5]:.1f}<br>' +
            'Chester:  %{customdata[6]}<br>' +
            'Altwer:  %{customdata[7]}<br>' +
            '<extra></extra>'
        )

    print(df.head())
    df_map = (
        df
    )
    print(df_map.head())
    if candidate_name.startswith('SJD9'):
        df_map = (
            df_map
            .filter(pl.col('CITY_DIST') == 'San Jose 9')
        )
    if candidate_name.startswith('SCC1_'):
        df_map = (
            df_map
            .filter(pl.col('COUNTY_DIST') == 1)
        )
    print(df_map.head())

    # Create a choropleth map of trend value by precinct
    print(f'{candidate_name = }')   
    print(f'{type(gdf) = }')
    print(f'{type(df_map) = }')
    # color_scale = "Blues" if candidate_name == 'BLUENESS' else "Reds"
    range_color = [10, 50]
    print(f'{my_color_scale = }')
    
    
    candidate_min_pct = (
        df_map
        .filter(pl.col(my_color) > 2 )
        .select(my_color)
        .min()
        .item(0, my_color)
    )   
    print(f'{candidate_min_pct = }')
    

    candidate_max_pct = (
        df_map
        .filter(pl.col(my_color) < 50 )
        .select(my_color)
        .max()
        .item(0, my_color)
    )  
    print(f'{candidate_max_pct = }')
    
    candidate_median_pct = (
        df_map
        .filter(pl.col(my_color).is_between(candidate_min_pct, candidate_max_pct) )
        .select(my_color)
        .median()
        .item(0, my_color)
    ) 
    print(f'{candidate_median_pct = }')

    pct_span = candidate_max_pct - candidate_min_pct
    print(f'{pct_span = }')
    my_color_range = [
        candidate_median_pct-5, # 0.25*pct_span, 
        candidate_median_pct+5, # 0.25*pct_span
    ]
 
    print(f'{my_color_range = }')

    fig = px.choropleth_map(    
        df_map,  # .with_columns(cs.numeric().fill_null(0)),        # geopandas DataFrame
            geojson = geojson_data,
            featureidkey="properties.Precinct",
            locations="PRECINCT",
            color=my_color,               # Column to color by
            map_style="open-street-map",       # Map style
            zoom=9,                          # Adjust zoom
            center={'lat': 37.360072115776084,    # Santa Clara County center latitude
                    'lon': -121.92686443166403},  # Santa Clara County center longitude
            opacity=0.8,
            color_continuous_scale=my_color_scale,
            range_color=my_color_range, # Adjust color to exclude 0
            custom_data=my_custom_data
        )
    fig.update_traces(marker_line_color="black", marker_line_width=choro_lw)

    fig.update_traces(hovertemplate=my_hovertemplate
        # '<b>Precinct %{customdata[0]:.0f}</b><br>' + 
        # '%{customdata[1]}, ' +
        # '%{customdata[2]}<br>' +
        # 'Reg. Voters:  %{customdata[3]}<br>' +
        # 'Act. Voters:  %{customdata[4]}<br>' +
        # f'{candidate_name}: ' +  ' %{customdata[5]:.1f}<br>' +
        # '<extra></extra>'
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig, my_color

def get_candidate_bar_chart(my_color):
    if isinstance(my_color, list):
        my_color = my_color[0]
    if my_color is None:
        return go.Figure()

    if my_color.startswith('GOV_'):
        prefix = 'GOV_'
        names = gov_names
        df_bar = df
    elif my_color.startswith('AG_'):
        prefix = 'AG_'
        names = ag_names
        df_bar = df
    elif my_color.startswith('DA_'):
        prefix = 'DA_'
        names = da_names
        df_bar = df
    elif my_color.startswith('SCC1_'):
        prefix = 'SCC1_'
        names = bos_names
        df_bar = df.filter(pl.col('COUNTY_DIST') == 1)
    elif my_color.startswith('SJD9_'):
        prefix = 'SJD9_'
        names = sj_d9_names
        df_bar = df.filter(pl.col('CITY_DIST') == 'San Jose 9')
    else:
        return go.Figure()

    vote_cols = [prefix + n for n in names]
    totals = df_bar.select([pl.col(c).sum().alias(c) for c in vote_cols])
    total_votes = sum(totals.row(0))
    row = totals.row(0)
    pcts = [round(v / total_votes * 100, 1) if total_votes else 0.0 for v in row]

    df_agg = (
        pl.DataFrame({'Candidate': names, 'Pct': pcts})
        .sort('Pct', descending=False)  # ascending → lowest at bottom, highest at top
    )

    fig = px.bar(
        df_agg,
        y='Candidate',
        x='Pct',
        orientation='h',
        template='simple_white',
        text='Pct',
        labels={'Pct': 'Vote %', 'Candidate': ''},
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(
        margin={'r': 60, 't': 10, 'l': 10, 'b': 30},
        xaxis=dict(showticklabels=False, showgrid=False, title=''),
    )
    return fig

def get_trend_bar_chart(trend_name):
    if isinstance(trend_name, list):
        trend_name = trend_name[0]
    if trend_name is None:
        return go.Figure()

    df_agg = (
        df
        .group_by('CITY')
        .agg(pl.col(trend_name).mean().round(1).alias('Value'))
        .sort('Value', descending=False)  # ascending → lowest at bottom, highest at top
    )

    fig = px.bar(
        df_agg,
        y='CITY',
        x='Value',
        orientation='h',
        template='simple_white',
        text='Value',
        labels={'Value': f'{trend_name} %', 'CITY': ''},
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(
        margin={'r': 60, 't': 10, 'l': 10, 'b': 30},
        xaxis=dict(showticklabels=False, showgrid=False, title=''),
    )
    return fig

#----- GLOBAL LISTS ------------------------------------------------------------

#----- DASH COMPONENTS------ ---------------------------------------------------

election_list = ['Governor', 'Attorney General', 'District Attorney',
    'Santa Clara County Supervisor District 1', 
    'San Jose Councilmember District 9']
dcc_select_trend = (
    dcc.Dropdown(
        id='id_select_trend',
        options=['REDNESS', 'BLUENESS', 'TURNOUT_PCT'],
        value=['TURNOUT_PCT'],    # Default selected values
        multi=False,           # Enable multiple selection
        placeholder="Select one of these elections...",
        style={"width": "50%"}
    ),
)

dcc_select_election = (
    dcc.Dropdown(
        id='id_select_election',
        options=[
            {'label': 'Governor', 'value': 'GOV'},
            {'label': 'Attorney General', 'value': 'AG'},
            {'label': 'District Attorney', 'value': 'DA'},
            {'label': 'County Supervisor District 1', 'value': 'SCC_BOS_D1'},
            {'label': 'San Jose Councilmember District 9', 'value': 'SJ_CM_D9'},
        ],
        value='GOV',    # Default selected values
        multi=False,           # Enable multiple selection
        placeholder="Select one of these elections...",
        style={"width": "50%"}
    ),
)

dcc_select_candidate = (
    dcc.Dropdown(
        id='id_select_candidate',
        options=[],
        # value=[],    # Default selected values
        multi=False,           # Enable multiple selection
        placeholder="Select one of these elections...",
        style={"width": "50%"}
    ),
)

#----- DASH APPLICATION STRUCTURE ----------------------------------------------

app = Dash(__name__)
server = app.server
app.layout =  dmc.MantineProvider([
    html.Hr(style=style_horizontal_thick_line),
    dmc.Text('Santa Clara County Primary, June 2, 2026', ta='center', style=style_h2),
    dmc.Text(
        'Analysis of election results, voter turnout, and location-based trends', 
        ta='center', style=style_h3
    ),
    dmc.Space(h=30),
    html.Hr(style=style_horizontal_thick_line),
    dmc.Space(h=30),
    dmc.Grid(children =  [
        dmc.GridCol(dmc.Text('Trend', ta='left'), span=3, offset=1),
        dmc.GridCol(dmc.Text('Election', ta='left'), span=3, offset=3),
        dmc.GridCol(dmc.Text('Candidate', ta='left'), span=2, offset=0),
    ]),
    dmc.Space(h=10),
    dmc.Grid(
        children = [  
            dmc.GridCol(dcc_select_trend, span=3, offset=1),
            dmc.GridCol(dcc_select_election, span=3, offset=3),
            dmc.GridCol(dcc_select_candidate, span=2, offset=0),
        ],
    ),
    dmc.Space(h=30),
    # dmc.Grid(children = [      # Summary cards row (responsive spans)
    #     dmc.GridCol(stat_card('Dog Count', '', id_prefix='dog-count'), span=dmc_card_span, offset=1),
    #     dmc.GridCol(stat_card('Top Age Group', '', id_prefix='top-age-group'), span=dmc_card_span),
    #     dmc.GridCol(stat_card('Fixed', '', id_prefix='fixed'), span=dmc_card_span),
    #     dmc.GridCol(stat_card('Shots Current', '', id_prefix='shots-current'), span=dmc_card_span),
    #     dmc.GridCol(stat_card('Organizations', '', id_prefix='organizations'), span=dmc_card_span),
    # ]),
    dmc.Space(h=30),
    # html.Hr(style=style_horizontal_thin_line),
    #     dmc.Grid(children =  [
    #     dmc.GridCol(dmc.Text('Visualizations filtered by the selections above.', 
    #         ta='center'), span=10, offset=1),
    # ]),
    dmc.Grid(children = [
        dmc.GridCol(dcc.Graph(id='choropleth-trend'), span=5, offset=1), 
        dmc.GridCol(dcc.Graph(id='choropleth-candidate'), span=5, offset=1),           
    ]),
    dmc.Space(h=10),
    dmc.Grid(children = [
        dmc.GridCol(dcc.Graph(id='bar-trend'), span=5, offset=1),
        dmc.GridCol(dcc.Graph(id='bar-candidate'), span=5, offset=1),
    ]),
    # dmc.Grid(children = [
    #     dmc.GridCol(dcc.Graph(id='pareto-female'), span=5, offset=1),    
    #     dmc.GridCol(dcc.Graph(id='pareto-male'), span=5, offset=1),      
    # ]),
    # html.Hr(style=style_horizontal_thin_line),
    #     dmc.Grid(children =  [
    #     dmc.GridCol(dmc.Text('Raw data table with floating filters', 
    #         ta='center'), span=10, offset=1),
    # ]),
    # dmc.Grid(children = [
    #     dmc.GridCol(get_ag_grid_table(df), span=10, offset=1),        
    # ]),

])

# Callback # 1: Populate candidate list from selected election
@app.callback(
    Output('id_select_candidate', 'options'),
    Output('id_select_candidate', 'value'),
    Input('id_select_election', 'value')
    )
def callback_election(election):  #selected_states, selected_animal_age, selected_primary_breed, selected_dog_name):
    print(f'{election = }')
    candidate_list = dict_election_candidates.get(election)
    print(f'{candidate_list = }')
    def_candidate = candidate_list[0] if type(candidate_list) == list else candidate_list
    return candidate_list, def_candidate

# Callback # 2:   Update choropleth map + bar chart based on selected candidate
@app.callback(
    Output('choropleth-candidate', 'figure'),
    Output('bar-candidate', 'figure'),
    Input('id_select_candidate', 'value')
    )
def callback_candidate_map(candidate):
    print(f'{candidate = }')
    fig_map, my_color = get_choropleth_candidate(candidate)
    return fig_map, get_candidate_bar_chart(my_color)

# Callback # 3:   Update choropleth map + bar chart based on selected trend
@app.callback(
    Output('choropleth-trend', 'figure'),
    Output('bar-trend', 'figure'),
    Input('id_select_trend', 'value')
    )
def callback(trend):
    print(f'{trend = }')
    return get_choropleth_trend(trend), get_trend_bar_chart(trend)
if __name__ == '__main__':
    app.run(debug=True)