import xarray as xr
import pandas as pd
import numpy as np
import os
import psycopg2
from psycopg2.extras import execute_values


def extract_ocean_data(netcdf_file_path):
    """
    Extract important oceanographic parameters from NetCDF file into DataFrame.
    """
    try:
        print(f"Opening NetCDF file: {netcdf_file_path}")
        ds = xr.open_dataset(netcdf_file_path)

        core_data = {}
        if 'PLATFORM_NUMBER' in ds.variables:
            core_data['platform_number'] = ds['PLATFORM_NUMBER'].values
        if 'CYCLE_NUMBER' in ds.variables:
            core_data['cycle_number'] = ds['CYCLE_NUMBER'].values
        if 'JULD' in ds.variables:
            core_data['date_time'] = pd.to_datetime(ds['JULD'].values)
        if 'LATITUDE' in ds.variables:
            core_data['latitude'] = ds['LATITUDE'].values
        if 'LONGITUDE' in ds.variables:
            core_data['longitude'] = ds['LONGITUDE'].values

        all_records = []
        n_profiles = ds.dims.get('N_PROF', 1)

        parameters_to_extract = {
            'pressure': ['PRES_ADJUSTED'],
            'temperature': ['TEMP_ADJUSTED'],
            'salinity': ['PSAL_ADJUSTED'],
            'dissolved_oxygen': ['DOXY_ADJUSTED'],
            'chlorophyll': ['CHLA_ADJUSTED'],
            'backscatter': ['BBP700_ADJUSTED']
        }

        if ds.dims.get('N_LEVELS', 0) > 0:
            for profile_idx in range(n_profiles):
                profile_core = {}
                for key, values in core_data.items():
                    if hasattr(values, '__len__') and len(values) > profile_idx:
                        profile_core[key] = values[profile_idx]
                    else:
                        profile_core[key] = values

                for level_idx in range(ds.dims['N_LEVELS']):
                    record = profile_core.copy()
                    record['depth_level'] = level_idx
                    for param_name, var_names in parameters_to_extract.items():
                        value = None
                        for var_name in var_names:
                            if var_name in ds.variables:
                                try:
                                    val = ds[var_name].values[profile_idx, level_idx]
                                    if not np.isnan(val):
                                        value = float(val)
                                        break
                                except:
                                    continue
                        record[param_name] = value
                    all_records.append(record)

        df = pd.DataFrame(all_records)
        ds.close()

        # Drop rows with any null values
        df_clean = df.dropna()
        
        print(f"Extracted {len(df_clean)} complete records")
        return df_clean

    except Exception as e:
        print(f"Error processing NetCDF file: {str(e)}")
        return None


def insert_to_postgres(df):
    """
    Insert DataFrame into PostgreSQL using psycopg2.
    """
    try:
        conn = psycopg2.connect(
        host ='localhost',
        port = 5432,
        database =  'agro',
        user = 'postgres',
        password = '123456'
        )
        cur = conn.cursor()


        table_name = 'agrodata'

        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            platform_number VARCHAR,
            cycle_number INT,
            date_time TIMESTAMP,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            depth_level INT,
            pressure DOUBLE PRECISION,
            temperature DOUBLE PRECISION,
            salinity DOUBLE PRECISION,
            dissolved_oxygen DOUBLE PRECISION,
            chlorophyll DOUBLE PRECISION,
            backscatter DOUBLE PRECISION
        );
        """
        cur.execute(create_table_query)
        conn.commit()

        cols = [
            'platform_number', 'cycle_number', 'date_time', 'latitude', 'longitude',
            'depth_level', 'pressure', 'temperature', 'salinity', 'dissolved_oxygen',
            'chlorophyll', 'backscatter'
        ]
        insert_query = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES %s"

        # Convert DataFrame to list of tuples
        values = [tuple(row) for row in df[cols].values]

        # Bulk insert
        execute_values(cur, insert_query, values)
        conn.commit()

        print(f"Inserted {len(values)} rows into {table_name}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Database insert failed: {str(e)}")

