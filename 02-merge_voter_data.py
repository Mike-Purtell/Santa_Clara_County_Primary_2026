import polars.selectors as cs
import polars as pl
pl.Config().set_float_precision(2)
pl.Config().set_tbl_cols(20)

from datetime import datetime
import plotly.express as px
#
#   Elections of interest:  GOV, AG, SCC_DA, SJ_D9_REP, SCC_BOS_D1
#


data_source = 'detail_2026_06_28.xlsx'

def read_excel(file, sheet_name, has_header=True, read_options=None):
    return pl.read_excel(file, sheet_name=sheet_name, has_header=has_header, read_options=read_options)


df = (  # join worksheets from 5 important races by Precinct
    # Governor's race
    read_excel(data_source, sheet_name='2', has_header=True,
        read_options={"header_row": 2}
    )
    .filter(~pl.col("Precinct").str.contains("Total", literal=True))
    .select(
        PRECINCT = pl.col("Precinct").cast(pl.Int32),
        REG_VOTERS = pl.col("Registered Voters"),
        ACT_VOTERS = pl.col("Total"),
        TURNOUT_PCT = (100.0 * pl.col("Total") / pl.col("Registered Voters")).round(2),
        BLUENESS = (
            100 * (pl.col("Total Votes") +  pl.col("Total Votes_1")) / pl.col("Total")
        ),
        REDNESS = (
            100 * (pl.col("Total Votes_2") +  pl.col("Total Votes_5")) / pl.col("Total")
        ),
        GOV_BECERRA = pl.col("Total Votes"),
        GOV_STEYER = pl.col("Total Votes_1"),
        GOV_HILTON = pl.col("Total Votes_2"),
        GOV_BIANCO = pl.col("Total Votes_5"),
    )
    .with_columns(
        GOV_BECERRA_PCT = (100 * pl.col("GOV_BECERRA") / pl.col("ACT_VOTERS")).round(2),
        GOV_STEYER_PCT = (100 * pl.col("GOV_STEYER") / pl.col("ACT_VOTERS")).round(2),
        GOV_HILTON_PCT = (100 * pl.col("GOV_HILTON") / pl.col("ACT_VOTERS")).round(2),
        GOV_BIANCO_PCT = (100 * pl.col("GOV_BIANCO") / pl.col("ACT_VOTERS")).round(2),
    )
    
    .join(   # Attorney General's race
        read_excel(data_source, sheet_name='7', has_header=True,
            read_options={"header_row": 2}
        )
        .filter(~pl.col("Precinct").str.contains("Total", literal=True))
        .select(
            PRECINCT = pl.col("Precinct").cast(pl.Int32),
            AG_BONTA = pl.col("Total Votes"),
            AG_ALL = pl.col("Total"),
        ),
        on = 'PRECINCT', how = 'left',
    )
    .with_columns(
        AG_BONTA_PCT = (100 * pl.col("AG_BONTA") / pl.col("AG_ALL")).round(2),
    )
    .join(  #  District Attorney race
        read_excel(data_source, sheet_name='27', has_header=True,
            read_options={"header_row": 2}
        )
        .filter(~pl.col("Precinct").str.contains("Total", literal=True))
        .select(
            PRECINCT = pl.col("Precinct").cast(pl.Int32),
            DA_ROSEN = pl.col("Total Votes"),
            DA_CHUNG = pl.col("Total Votes_1"),
            DA_ALL = pl.col("Total"),
        ),
        on = 'PRECINCT', how = 'left',
    )
    .with_columns(
        DA_ROSEN_PCT = (100 * pl.col("DA_ROSEN") / pl.col("DA_ALL")).round(2),
        DA_CHUNG_PCT = (100 * pl.col("DA_CHUNG") / pl.col("DA_ALL")).round(2),
    )
    .join(  #  Santa Clara County Supervisor District 1
        read_excel(data_source, sheet_name='24', has_header=True,
            read_options={"header_row": 2}
        )
        .filter(~pl.col("Precinct").str.contains("Total", literal=True))
        .select(
            PRECINCT = pl.col("Precinct").cast(pl.Int32),
            SCC1_ARENAS = pl.col("Total Votes"),
            SCC1_MUNSON = pl.col("Total Votes_1"),
            SCC1_ALL = pl.col("Total"),
        ),
        on = 'PRECINCT', how = 'left',
    )
    .with_columns(
        SCC1_ARENAS_PCT = (100 * pl.col("SCC1_ARENAS") / pl.col("SCC1_ALL")).round(2),
        SCC1_MUNSON_PCT = (100 * pl.col("SCC1_MUNSON") / pl.col("SCC1_ALL")).round(2),
    )
    .join( #  San Jose District 9
        read_excel(data_source, sheet_name='33', has_header=True,
            read_options={"header_row": 2}
        )
        .filter(~pl.col("Precinct").str.contains("Total", literal=True))
        .select(
            PRECINCT = pl.col("Precinct").cast(pl.Int32),
            SJD9_ALTWER = pl.col("Total Votes"),
            SJD9_CHESTER = pl.col("Total Votes_1"),
            SJD9_ALL_VOTES = pl.col("Total"),
        ),
        on = 'PRECINCT', how = 'left',
    )
    .with_columns(
        SJD9_ALTWER_PCT = (100 * pl.col("SJD9_ALTWER") / pl.col("SJD9_ALL_VOTES")).round(2),
        SJD9_CHESTER_PCT = (100 * pl.col("SJD9_CHESTER") / pl.col("SJD9_ALL_VOTES")).round(2),
    )
    .filter(pl.col('REG_VOTERS') > 0)  # filter out precincts with no registered voters
    .filter(pl.col('ACT_VOTERS') > 0)  # filter out precincts with no registered voters
    .join(
        pl.read_parquet('precinct_params.parquet'),
        on = 'PRECINCT', how = 'left',
    )
)
print(df)
# print(df.filter(pl.col('SCC1_ALL') > 0).sort('PRECINCT', descending = False))
df.write_excel(
    'merged_voter_data.xlsx', 
    autofit =True,
    freeze_panes = (1, 0),
    autofilter = True,
    table_style = 'Table Style Medium 2',
    column_formats = {'ZIP_CODE': '0'}
)
df.write_parquet('merged_voter_data.parquet')
print('Done')

