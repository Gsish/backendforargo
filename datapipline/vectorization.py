import xarray as xr

metadata = {}  

def opennetcdf(pat: str):
    global metadata
    ds = xr.open_dataset(pat, engine="netcdf4")  

    variables_dict = {}
    for var_name in ds.variables:
        var = ds[var_name]
        variables_dict[var_name] = {
            "dimensions": var.dims,
            "shape": var.shape,
            "datatype": str(var.dtype),
            "coordinates": {coord: ds[coord].values.tolist() for coord in var.coords}
        }

    
    metadata = variables_dict.copy()
    metadata.update(ds.attrs) 
    

    for key, value in metadata.items():
        print(f"{key}: {value}\n")

