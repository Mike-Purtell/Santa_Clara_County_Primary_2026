import polars as pl

source_folder = (
    '../SCC_Voter_Data_Up_To_Primary_2024/' +
    'SCC_Voter_Data_Oct_13_2024_Dashboard/parquet'
)
source_file = 'MVMJ004_Cust_20240909_101659_SantaClaraCounty_JK.parquet'


df = (
    pl.scan_parquet(f"{source_folder}/{source_file}")
    .select('PRECINCT', 'ZIP_CODE', 'CITY', 'CITY_DIST', 'COUNTY_DIST')
    .unique(['PRECINCT','CITY', 'CITY_DIST', 'COUNTY_DIST'])
    .unique(['PRECINCT'])
    .sort('PRECINCT')
    .with_columns(pl.col('PRECINCT').cast(pl.Int32))
    .with_columns(
        pl.col('ZIP_CODE')
        .cast(pl.String)    # categorical to string
        .cast(pl.Int32)     # string to integer
        .fill_null(strategy='forward')
    )
    .with_columns(
        pl.col('CITY')
        .cast(pl.String)    # categorical to string
        .fill_null(strategy='forward')
    )
    .with_columns(
        pl.col('CITY_DIST')
        .cast(pl.String)    # categorical to string
        .fill_null(strategy='forward')
    )
    .with_columns(
        pl.col('COUNTY_DIST')
        .cast(pl.String)    # categorical to string
        .fill_null(strategy='forward')
        .cast(pl.Int32)     # string to integer
    )
    .collect()
)
print(df.glimpse())
df.write_excel(
    'precinct_params.xlsx',
    freeze_panes='A2',
    autofit=True,
    table_style='TableStyleMedium2',
    column_formats={'PRECINCT': '0', 'ZIP_CODE': '0', 'CITY_DIST': '0', 'COUNTY_DIST': '0'}
)
df.write_parquet('precinct_params.parquet')
print('Done')   
