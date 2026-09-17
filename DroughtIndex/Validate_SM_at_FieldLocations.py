#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 26 23:00:57 2026

@author: x5l
"""
import os
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import re
from scipy.stats import linregress

def Plot_product_vs_field(product_data, field_data,
                          product_name, field_sm_column,
                          output_figure):
    """Merge product and field monthly observations and make a scatter plot."""
    product_data = product_data.copy()
    field_data = field_data.copy()

    product_data[site_id_column] = product_data[site_id_column].astype(str)
    field_data[site_id_column] = field_data[site_id_column].astype(str)    
    
    product_data["month"] = pd.to_datetime(product_data["month"])
    field_data["month"] = pd.to_datetime(field_data["month"])

    if timescale == "monthly":
        product_data["month"] = product_data["month"].dt.to_period("M").dt.to_timestamp()
        field_data["month"] = field_data["month"].dt.to_period("M").dt.to_timestamp()    

    comparison = field_data.merge(
        product_data[[site_id_column, "month", product_name]],
        on=[site_id_column, "month"],
        how="inner",
    )

    comparison = comparison.dropna(subset=[field_sm_column, product_name])

    if len(comparison) < 2:
        print(f"Not enough matched observations to plot {product_name}.")
        return comparison

    x = comparison[field_sm_column].astype(float).to_numpy()
    y = comparison[product_name].astype(float).to_numpy()

    # Linear regression and significance test
    regression = linregress(x, y)
    
    slope = regression.slope
    intercept = regression.intercept
    correlation = regression.rvalue
    p_value = regression.pvalue
    # r2 = correlation ** 2    
    # predicted = slope * x + intercept
    
    rmse = np.sqrt(np.mean((y - x) ** 2))
    bias = np.mean(y - x)

    xy_min = np.nanmin(np.concatenate([x, y]))
    xy_max = np.nanmax(np.concatenate([x, y]))
    xy_min, xy_max = 0,1    
    line_x = np.linspace(xy_min, xy_max, 100)    

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(x, y, alpha=0.75)
    ax.plot(line_x, line_x, linestyle="--", label="1:1 line")
    ax.plot(line_x, slope * line_x + intercept,
            label=f"Fit: y = {slope:.2f}x + {intercept:.2f}")

    ax.set_xlabel("Field soil moisture (m³/m³)")
    ax.set_ylabel(f"{product_name} soil moisture (m³/m³)")
    ax.set_title(f"{product_name} versus field observations")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.6)
    ax.legend()
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(xy_min, xy_max)
    ax.set_ylim(xy_min, xy_max)    

    if p_value < 0.001:
        p_text = "p < 0.001"
    else:
        p_text = f"p = {p_value:.3f}"
    
    stats_text = (
        f"n = {len(comparison)}\n"
        # f"R² = {r2:.3f}\n"
        f"r = {correlation:.3f}\n"
        f"{p_text}\n"
        f"RMSE = {rmse:.3f}\n"
        f"Bias = {bias:.3f}"
    )
    
    ax.text(
        0.04, 0.96, stats_text,
        transform=ax.transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
    )

    output_figure.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_figure, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close(fig)

    return comparison





def Extract_SM_at_Fieldlocations(sites, ds, data, 
                                 product_name, variable_name, lon_name, lat_name, time_name):
    # ============================================================
    # Match the longitude convention
    # ============================================================
    netcdf_lon_min = float(ds[lon_name].min())
    netcdf_lon_max = float(ds[lon_name].max())
    
    site_longitudes = sites[site_lon_column].astype(float).to_numpy()
    
    # Convert field longitudes to 0–360 when the NetCDF uses 0–360
    if netcdf_lon_min >= 0 and netcdf_lon_max > 180:
        site_longitudes = np.mod(site_longitudes, 360)
    
    # Convert field longitudes to -180–180 when the NetCDF uses that convention
    elif netcdf_lon_min < 0 and np.any(site_longitudes > 180):
        site_longitudes = (
            (site_longitudes + 180) % 360
        ) - 180
    
    sites = sites.copy()
    sites["_matched_longitude"] = site_longitudes
    
    
    # ============================================================
    # Create site-indexed xarray coordinate arrays
    # ============================================================
    site_lon = xr.DataArray(
        sites["_matched_longitude"].to_numpy(),
        dims="site",
        coords={"site": sites[site_id_column].astype(str).to_numpy()},
    )
    site_lat = xr.DataArray(
        sites[site_lat_column].astype(float).to_numpy(),
        dims="site",
        coords={"site": sites[site_id_column].astype(str).to_numpy()},
    )
    
    
    # ============================================================
    # Extract nearest grid cell for every site
    # ============================================================
    extracted = data.sel(
        {
            lon_name: site_lon,
            lat_name: site_lat,
        },
        method="nearest",
    )
    
    # Arrange dimensions as time × site when possible
    extracted = extracted.transpose(time_name, "site", ...)
    # print(extracted)
    
    
    # ============================================================
    # Convert to a long-format table
    # ============================================================
    result = (
        extracted
        .to_dataframe(name=variable_name)
        .reset_index()
    )
    
    # ============================================================
    # Add site information
    # ============================================================    
    site_metadata = sites[
        [
            site_id_column,
            site_lon_column,
            site_lat_column,
        ]
    ].copy()
    
    site_metadata[site_id_column] = (
        site_metadata[site_id_column].astype(str)
    )
    
    result["site"] = result["site"].astype(str)
    
    result = result.merge(
        site_metadata,
        left_on="site",
        right_on=site_id_column,
        how="left",
    )
    
    # Keep only desired columns
    result = result[
        [
            site_id_column,
            time_name,
            site_lon_column,
            site_lat_column,
            variable_name,
        ]
    ]
    
    # Rename columns
    result = result.rename(
        columns={
            time_name: "month",  #to match column name in '2023_Inni_field soil moisture_DATA.csv'
            variable_name: product_name,
        }
    )
    
    return(result)


#---- MAIN
os.chdir('/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data')


### read field locations
location_file = Path("SM_field_observation/field_locations.csv")
sites = pd.read_csv(location_file)

site_id_column = "Code"
site_lon_column = "Longitude"
site_lat_column = "Latitude"


### read field soil moisture monthly data
def Read_fielddata(timescale):
    if timescale == "monthly":
        field_data_file = Path("SM_field_observation/2023_Inni_field soil moisture_monthly_v1.csv")
        field_data = pd.read_csv(field_data_file)
        field_data = field_data.rename(columns={'station_code': 'Code'})
    elif timescale == "daily":
        field_data_file = Path("SM_field_observation/2023_Inni_field soil moisture_daily_v3.csv")
        field_data = pd.read_csv(field_data_file)    
        field_data['vwc (%vol)'] = field_data['sm (%)'] / 100
        field_data = field_data.drop(columns=["sm (%)"])    
        field_data = field_data.rename(columns={"code": "Code", "datetime": "month"})
    
    field_data["month"] = pd.to_datetime(field_data["month"])
    
    return field_data
field_sm_column = "vwc (%vol)"

    
#%% Extract and Plot: local SM (native grid; netcdf)
    # 1. agg all ERA data from Oct 2018 to Dec 2019, to match field observations
    # 2. get monthly mean 
    # 3. extract at field locations
    # 4. plot: Scatter_SM_ERA5_vs_field
    # 5. apply 1-3 to other products
    
## extract values from daily netcdf first and then average
def Extract_product_from_daily_localfiles(sites, ncfiles, product_name, variable_name,
                               lon_name, lat_name, time_name,
                               start_date="2018-10-01",
                               end_date="2019-12-31"):
    """Extract one product from multiple NetCDF files and aggregate monthly."""
    all_results = []

    if len(ncfiles) == 0:
        raise FileNotFoundError(f"No NetCDF files found for {product_name}")

    for i, netcdf_file in enumerate(ncfiles, start=1):
        print(f"{product_name}: reading {i}/{len(ncfiles)}: {netcdf_file.name}")

        with xr.open_dataset(netcdf_file) as ds:
            if variable_name not in ds:
                raise KeyError(
                    f"{variable_name!r} not found in {netcdf_file}. "
                    f"Available variables: {list(ds.data_vars)}"
                )
                
            
            # If no time dim, add one from filename
            if time_name not in ds.dims:
                # example: netcdf_file = 'SM_RE07_MIR_CDF3SA_20191210T000000_20191210T235959_200_001_B.DBL.nc',
                filename_str = Path(netcdf_file).name
                match = re.search(r"(\d{8}T\d{6})", filename_str)
                
                if match:
                    # Convert '20191210T000000' to a pandas Timestamp
                    file_date = pd.to_datetime(match.group(1), format="%Y%m%dT%H%M%S")
                else:
                    raise ValueError(f"Could not parse timestamp from filename: {filename_str}")                
                
                ds = ds.expand_dims(time=[file_date])                
                

            # Keep only Oct 2018–Dec 2019 before extraction
            ds_period = ds.sel({time_name: slice(start_date, end_date)})
            if ds_period.sizes.get(time_name, 0) == 0:
                continue

            data = ds_period[variable_name]
            result_tmp = Extract_SM_at_Fieldlocations(
                sites, ds_period, data,
                product_name, variable_name,
                lon_name, lat_name, time_name,
            )
            all_results.append(result_tmp)

    if len(all_results) == 0:
        raise ValueError(
            f"No {product_name} observations found between "
            f"{start_date} and {end_date}."
        )

    # 1. Aggregate all files
    result_daily = pd.concat(all_results, ignore_index=True)
    result_daily["month"] = pd.to_datetime(result_daily["month"])

    # Remove duplicate site/date rows, if overlapping NetCDF files exist
    result_daily = (
        result_daily
        .groupby(
            [site_id_column, "month", site_lon_column, site_lat_column],
            as_index=False,
        )[product_name]
        .mean()
    )
    result_daily_rawdate = result_daily.copy()

    # 2. Monthly mean at each field location
    result_daily["month"] = result_daily["month"].dt.to_period("M").dt.to_timestamp()
    result_monthly = (
        result_daily
        .groupby(
            [site_id_column, "month", site_lon_column, site_lat_column],
            as_index=False,
        )[product_name]
        .mean()
    )

    return result_daily_rawdate, result_monthly
        
    

#----MAIN
products = [       
    # ### SMOS ACS
    # {
    #     "product_name": "SM_SMOS_ACS",  
    #     "folder": Path("SM_SMOS/ACS"),  
    #     "pattern": "SM_*_MIR_CDF3S*_*.nc", 
    #     "variable_name": "Soil_Moisture", 
    #     "lon_name": "lon",
    #     "lat_name": "lat",
    #     "time_name": "time" #If no time dim, default is time.
    # },
    # ### SMOS DES
    # {
    #     "product_name": "SM_SMOS_DES",  
    #     "folder": Path("SM_SMOS/DES"),  
    #     "pattern": "SM_*_MIR_CDF3S*_*.nc", 
    #     "variable_name": "Soil_Moisture", 
    #     "lon_name": "lon",
    #     "lat_name": "lat",
    #     "time_name": "time" #If no time dim, default is time.
    # },
    # ### SMAP_MT-DCA
    # {
    #     "product_name": "SM_SMAP_MT-DCA",  
    #     "folder": Path("SM_SMAP_MT-DCA/MTDCA_9km_V5_nc"),  
    #     "pattern": "MTDCA*.nc", 
    #     "variable_name": "soil_moisture", 
    #     "lon_name": "lon",
    #     "lat_name": "lat",
    #     "time_name": "time" #If no time dim, default is time.
    # }
]

for product in products:
    product_name = product["product_name"]
    ncfiles = sorted(product["folder"].glob(product["pattern"]))
    
    # check filenames
    basenames = [os.path.basename(f) for f in ncfiles]
    print(basenames)    
    
    result_daily, result_monthly = Extract_product_from_daily_localfiles(  
        sites=sites,
        ncfiles=ncfiles,
        product_name=product_name,
        variable_name=product["variable_name"],
        lon_name=product["lon_name"],
        lat_name=product["lat_name"],
        time_name=product["time_name"],
        start_date="2018-10-01",        
        end_date="2019-12-31",
    )
    
    timescales = ["daily"] #"monthly", 
    for timescale in timescales: 
        field_data = Read_fielddata(timescale)
        output_dir = Path(f"../Figures/FigS_SM_Validate_2018-2019/{timescale}")
        
        if timescale == "monthly":
            result_data = result_monthly
        elif timescale == "daily":
            result_data = result_daily
    
        # Save extracted time series      
        result_data.to_csv(
            output_dir / f"{product_name}_at_fieldlocations_{timescale}.csv",
            index=False,
        )
    
        # Scatter plot against field observations
        comparison = Plot_product_vs_field(
            product_data=result_data,
            field_data=field_data,
            product_name=product_name,
            field_sm_column=field_sm_column,
            output_figure=output_dir / f"Scatter_{product_name}_vs_field_{timescale}.png",
        )
    
        comparison.to_csv(
            output_dir / f"Comparison_{product_name}_vs_field_{timescale}.csv",
            index=False,
        )    


#%% Extract and Plot: GEE SM (native grid)
# This section validates both:
#   1. SMAP L4 surface soil moisture
#   2. ERA5-Land layer-2 soil moisture
#
# Daily SMAP-L4 values are calculated by averaging the 3-hourly images.
# ERA5-Land DAILY_AGGR already contains one image per day.
# Monthly values for both products are calculated locally from the
# extracted daily values so that the monthly workflow is identical.

import ee
def initialize_ee():
    """Initialize Earth Engine and authenticate if needed."""
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)
PROJECT_ID = "quick-heaven-445214-f5"
initialize_ee()

def Extract_product_from_GEE_nativegrid(
        sites,
        collection_id,
        product_name,
        variable_name,
        daily_method,
        start_date="2018-10-01",
        end_date="2020-01-01",
        scale=None):
    """
    Extract daily and monthly soil moisture from a GEE ImageCollection
    at field locations using the product's native grid.

    Parameters
    ----------
    sites : pandas.DataFrame
        Field-site table.

    collection_id : str
        Earth Engine ImageCollection ID.

    product_name : str
        Output column name.

    variable_name : str
        Soil-moisture band name.

    daily_method : {"mean", "first"}
        "mean" averages all source images within each UTC day.
        "first" uses the first image for products that already contain
        one daily image.

    start_date, end_date : str
        Requested period. The end date is exclusive.

    scale : float or None
        Optional sampling scale. When None, the native nominal scale
        of the product is used.

    Returns
    -------
    result_daily : pandas.DataFrame
        Daily values at field locations.

    result_monthly : pandas.DataFrame
        Monthly means calculated locally from result_daily.
    """

    if daily_method not in {"mean", "first"}:
        raise ValueError(
            "daily_method must be either 'mean' or 'first'."
        )

    # Ensure scalar date strings.
    if isinstance(start_date, (list, tuple)):
        start_date = start_date[0]

    if isinstance(end_date, (list, tuple)):
        end_date = end_date[0]

    start_date = str(start_date)
    end_date = str(end_date)

    # ============================================================
    # 1. Load the selected product
    # ============================================================
    collection = (
        ee.ImageCollection(collection_id)
        .filterDate(
            ee.Date(start_date),
            ee.Date(end_date),
        )
        .select(variable_name)
    )

    image_count = collection.size().getInfo()

    if image_count == 0:
        raise ValueError(
            f"No {product_name} images found between "
            f"{start_date} and {end_date}."
        )

    print(
        f"{product_name}: found {image_count} source images."
    )

    # Use the first source image to obtain the exact native grid.
    template_image = (
        ee.Image(collection.first())
        .select(variable_name)
    )

    native_projection = template_image.projection()
    native_scale = native_projection.nominalScale()

    print(
        f"{product_name} native projection:",
        native_projection.getInfo(),
    )

    print(
        f"{product_name} native nominal scale:",
        native_scale.getInfo(),
    )

    # Use the native nominal scale unless another scale is explicitly
    # requested. For exact agreement with the source grid, scale=None
    # is recommended.
    sampling_scale = (
        native_scale
        if scale is None
        else scale
    )

    # ============================================================
    # 2. Create field-location FeatureCollection
    # ============================================================
    features = []

    for _, row in sites.iterrows():

        feature = ee.Feature(
            ee.Geometry.Point(
                [
                    float(row[site_lon_column]),
                    float(row[site_lat_column]),
                ]
            ),
            {
                site_id_column:
                    str(row[site_id_column]),

                site_lon_column:
                    float(row[site_lon_column]),

                site_lat_column:
                    float(row[site_lat_column]),
            },
        )

        features.append(feature)

    site_fc = ee.FeatureCollection(features)

    # ============================================================
    # 3. Extract one image at all field locations
    # ============================================================
    def extract_image_at_sites(image, observation_date):

        # Force evaluation on the original product grid.
        image = (
            ee.Image(image)
            .setDefaultProjection(native_projection)
        )

        sampled = image.reduceRegions(
            collection=site_fc,
            reducer=ee.Reducer.first(),
            crs=native_projection,
            scale=sampling_scale,
            tileScale=4,
        )

        sampled_info = sampled.getInfo()
        extracted_rows = []

        for feature in sampled_info["features"]:

            properties = feature["properties"]

            extracted_rows.append(
                {
                    site_id_column:
                        properties.get(site_id_column),

                    # Keep "month" for compatibility with the rest
                    # of your validation code.
                    "month":
                        observation_date,

                    site_lon_column:
                        properties.get(site_lon_column),

                    site_lat_column:
                        properties.get(site_lat_column),

                    product_name:
                        properties.get("first"),
                }
            )

        return extracted_rows

    # ============================================================
    # 4. Calculate and extract daily soil moisture
    # ============================================================
    day_starts = pd.date_range(
        start=pd.Timestamp(start_date),
        end=pd.Timestamp(end_date),
        freq="D",
        inclusive="left",
    )

    all_daily_results = []

    for i, day_start in enumerate(day_starts, start=1):

        day_end = day_start + pd.Timedelta(days=1)

        print(
            f"{product_name}: extracting daily value "
            f"{i}/{len(day_starts)}: "
            f"{day_start:%Y-%m-%d}"
        )

        daily_collection = collection.filterDate(
            ee.Date(day_start.strftime("%Y-%m-%d")),
            ee.Date(day_end.strftime("%Y-%m-%d")),
        )

        daily_count = daily_collection.size().getInfo()

        if daily_count == 0:
            print("    No source image; skipped.")
            continue

        if (
            collection_id == "ECMWF/ERA5/HOURLY"
            and daily_count != 24
        ):
            print(
                f"    Warning: found {daily_count} ERA5 images; "
                "expected 24."
            )

        if daily_method == "mean":

            # Temporal averaging only. Restore the native projection
            # after ImageCollection.mean().
            daily_image = (
                daily_collection
                .mean()
                .rename(product_name)
                .setDefaultProjection(native_projection)
            )

        elif daily_method == "first":

            # For an existing daily product such as
            # ERA5-Land DAILY_AGGR.
            daily_image = (
                ee.Image(daily_collection.first())
                .select(variable_name)
                .rename(product_name)
                .setDefaultProjection(native_projection)
            )

        daily_rows = extract_image_at_sites(
            image=daily_image,
            observation_date=day_start,
        )

        all_daily_results.extend(daily_rows)

    # ============================================================
    # 5. Convert daily results to a DataFrame
    # ============================================================
    result_daily = pd.DataFrame(all_daily_results)

    if result_daily.empty:
        raise ValueError(
            f"No daily {product_name} values were extracted."
        )

    result_daily[site_id_column] = (
        result_daily[site_id_column].astype(str)
    )

    result_daily["month"] = pd.to_datetime(
        result_daily["month"]
    )

    result_daily[product_name] = pd.to_numeric(
        result_daily[product_name],
        errors="coerce",
    )

    # Remove duplicate site-date rows, if any.
    result_daily = (
        result_daily
        .groupby(
            [
                site_id_column,
                "month",
                site_lon_column,
                site_lat_column,
            ],
            as_index=False,
            dropna=False,
        )[product_name]
        .mean()
        .sort_values(
            [site_id_column, "month"]
        )
        .reset_index(drop=True)
    )

    # ============================================================
    # 6. Calculate monthly means from daily output
    # ============================================================
    result_monthly = result_daily.copy()

    result_monthly["month"] = (
        result_monthly["month"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    result_monthly = (
        result_monthly
        .groupby(
            [
                site_id_column,
                "month",
                site_lon_column,
                site_lat_column,
            ],
            as_index=False,
            dropna=False,
        )[product_name]
        .mean()
        .sort_values(
            [site_id_column, "month"]
        )
        .reset_index(drop=True)
    )

    print(
        f"{product_name}: extracted "
        f"{len(result_daily)} daily site observations and "
        f"{len(result_monthly)} monthly site observations."
    )

    print(
        f"{product_name} daily value summary:"
    )
    print(result_daily[product_name].describe())

    return result_daily, result_monthly




#----MAIN
# ============================================================
# PRODUCTS TO VALIDATE
# ============================================================
gee_sm_products = [
    {
        "collection_id":
            "NASA/SMAP/SPL4SMGP/008",

        "product_name":
            "SM_SMAP_L4_surface",

        "variable_name":
            "sm_surface",

        "daily_method":
            "mean",

        "scale":
            None,
    },
    
    {
        "collection_id":
            "ECMWF/ERA5_LAND/DAILY_AGGR",

        "product_name":
            "SM_ERA5_Land",

        "variable_name":
            "volumetric_soil_water_layer_2",

        "daily_method":
            "first",

        "scale":
            None,
    },
        
    # {
    #     "collection_id":
    #         "ECMWF/ERA5/HOURLY",
    
    #     "product_name":
    #         "SM_ERA5",
    
    #     "variable_name":
    #         "volumetric_soil_water_layer_2",
    
    #     "daily_method":
    #         "mean",
    
    #     "scale":
    #         None,
    # },
        
    # {
    #     "collection_id":
    #         "NASA/SMAP/SPL4SMGP/008",

    #     "product_name":
    #         "SM_SMAP_L4_rootzone",

    #     "variable_name":
    #         "sm_rootzone",

    #     "daily_method":
    #         "mean",

    #     "scale":
    #         None,
    # },
]


# ============================================================
# EXTRACT, SAVE, AND VALIDATE EACH PRODUCT
# ============================================================
for product_cfg in gee_sm_products:
    product_name = product_cfg["product_name"]
    variable_name = product_cfg["variable_name"]

    result_daily, result_monthly = Extract_product_from_GEE_nativegrid(
        sites=sites,
        collection_id=product_cfg["collection_id"],
        product_name=product_name,
        variable_name=variable_name,
        daily_method=product_cfg["daily_method"],
        start_date="2018-10-01",
        end_date="2020-01-01",
        # end_date="2018-11-11",
        scale=product_cfg["scale"],
    )

    timescales = ["daily", "monthly"]
    for timescale in timescales:

        field_data = Read_fielddata(timescale)

        output_dir = Path(
            f"../Figures/FigS_SM_Validate_2018-2019/"
            f"{timescale}"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        if timescale == "monthly":
            result_data = result_monthly

        elif timescale == "daily":
            result_data = result_daily

        # Save extracted time series.
        result_data.to_csv(
            output_dir
            / (
                f"{product_name}_at_fieldlocations_"
                f"{timescale}.csv"
            ),
            index=False,
        )

        # Scatter plot against field observations.
        comparison = Plot_product_vs_field(
            product_data=result_data,
            field_data=field_data,
            product_name=product_name,
            field_sm_column=field_sm_column,
            output_figure=(
                output_dir
                / (
                    f"Scatter_{product_name}_vs_field_"
                    f"{timescale}.png"
                )
            ),
        )

        comparison.to_csv(
            output_dir
            / (
                f"Comparison_{product_name}_vs_field_"
                f"{timescale}.csv"
            ),
            index=False,
        )    


    
#%% (not used) Extract and Plot: GEE SM (resample)
# This section validates both:
#   1. SMAP L4 surface soil moisture
#   2. ERA5-Land layer-2 soil moisture
#
# Daily SMAP-L4 values are calculated by averaging the 3-hourly images.
# ERA5-Land DAILY_AGGR already contains one image per day.
# Monthly values for both products are calculated locally from the
# extracted daily values so that the monthly workflow is identical.

import ee
def initialize_ee():
    """Initialize Earth Engine and authenticate if needed."""
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)
PROJECT_ID = "quick-heaven-445214-f5"
initialize_ee()


def Extract_product_from_GEE_resample(
        sites,
        collection_id,
        product_name,
        variable_name,
        daily_method,
        start_date="2018-10-01",
        end_date="2020-01-01",
        scale=11000):    

    if daily_method not in {"mean", "first"}:
        raise ValueError(
            "daily_method must be either 'mean' or 'first'."
        )

    # ============================================================
    # 1. Load the selected product
    # ============================================================
    collection = (
        ee.ImageCollection(collection_id)
        .filterDate(start_date, end_date)        
        .select(variable_name)
    )
    image_count = collection.size().getInfo()

    if image_count == 0:
        raise ValueError(
            f"No {product_name} images found between "
            f"{start_date} and {end_date}."
        )

    print(
        f"{product_name}: found {image_count} source images."
    )

    # ============================================================
    # 2. Create field-location FeatureCollection
    # ============================================================
    features = []

    for _, row in sites.iterrows():

        feature = ee.Feature(
            ee.Geometry.Point(
                [
                    float(row[site_lon_column]),
                    float(row[site_lat_column]),
                ]
            ),
            {
                site_id_column:
                    str(row[site_id_column]),

                site_lon_column:
                    float(row[site_lon_column]),

                site_lat_column:
                    float(row[site_lat_column]),
            },
        )

        features.append(feature)

    site_fc = ee.FeatureCollection(features)

    # ============================================================
    # 3. Extract one daily image at all field locations
    # ============================================================
    def extract_image_at_sites(image, observation_date):

        sampled = image.reduceRegions(
            collection=site_fc,
            reducer=ee.Reducer.first(),
            scale=scale,
            tileScale=4,
        )

        sampled_info = sampled.getInfo()
        extracted_rows = []

        for feature in sampled_info["features"]:

            properties = feature["properties"]

            extracted_rows.append(
                {
                    site_id_column:
                        properties.get(site_id_column),

                    # Keep "month" for compatibility with the
                    # existing field-data and plotting functions.
                    "month":
                        observation_date,

                    site_lon_column:
                        properties.get(site_lon_column),

                    site_lat_column:
                        properties.get(site_lat_column),

                    product_name:
                        properties.get("first"),
                }
            )

        return extracted_rows

    # ============================================================
    # 4. Calculate and extract daily soil moisture
    # ============================================================
    day_starts = pd.date_range(
        start=pd.Timestamp(start_date),
        end=pd.Timestamp(end_date),
        freq="D",
        inclusive="left",
    )

    all_daily_results = []

    for i, day_start in enumerate(day_starts, start=1):

        day_end = day_start + pd.Timedelta(days=1)

        print(
            f"{product_name}: extracting daily value "
            f"{i}/{len(day_starts)}: "
            f"{day_start:%Y-%m-%d}"
        )

        daily_collection = collection.filterDate(
            day_start.strftime("%Y-%m-%d"),
            day_end.strftime("%Y-%m-%d"),
        )

        daily_count = daily_collection.size().getInfo()

        if daily_count == 0:
            print("    No source image; skipped.")
            continue

        if daily_method == "mean":
            # SMAP L4: average all 3-hourly images in the UTC day.
            daily_image = (
                daily_collection
                .mean()
                .rename(product_name)
            )

        elif daily_method == "first":
            # ERA5-Land DAILY_AGGR: one image already represents
            # one daily aggregate.
            daily_image = (
                ee.Image(daily_collection.first())
                .select(variable_name)
                .rename(product_name)
            )

        daily_rows = extract_image_at_sites(
            image=daily_image,
            observation_date=day_start,
        )

        all_daily_results.extend(daily_rows)

    # ============================================================
    # 5. Convert daily results to a DataFrame
    # ============================================================
    result_daily = pd.DataFrame(all_daily_results)

    if result_daily.empty:
        raise ValueError(
            f"No daily {product_name} values were extracted."
        )

    result_daily[site_id_column] = (
        result_daily[site_id_column].astype(str)
    )

    result_daily["month"] = pd.to_datetime(
        result_daily["month"]
    )

    result_daily[product_name] = pd.to_numeric(
        result_daily[product_name],
        errors="coerce",
    )   

    # Remove duplicate site-date records, if any.
    result_daily = (
        result_daily
        .groupby(
            [
                site_id_column,
                "month",
                site_lon_column,
                site_lat_column,
            ],
            as_index=False,
        )[product_name]
        .mean()
        .sort_values([site_id_column, "month"])
        .reset_index(drop=True)
    )
   

    # ============================================================
    # 6. Calculate monthly values from the daily output
    # ============================================================
    result_monthly = result_daily.copy()

    result_monthly["month"] = (
        result_monthly["month"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    result_monthly = (
        result_monthly
        .groupby(
            [
                site_id_column,
                "month",
                site_lon_column,
                site_lat_column,
            ],
            as_index=False,
        )[product_name]
        .mean()
        .sort_values([site_id_column, "month"])
        .reset_index(drop=True)
    )

    print(
        f"{product_name}: extracted "
        f"{len(result_daily)} daily site observations and "
        f"{len(result_monthly)} monthly site observations."
    )

    return result_daily, result_monthly


#----MAIN
# ============================================================
# PRODUCTS TO VALIDATE
# ============================================================
gee_sm_products = [
    # {
    #     "collection_id":
    #         "NASA/SMAP/SPL4SMGP/008",

    #     "product_name":
    #         "SM_SMAP_L4_surface",

    #     "variable_name":
    #         "sm_surface",

    #     "daily_method":
    #         "mean",

    #     "scale":
    #         11000,
    # },
    # {
    #     "collection_id":
    #         "ECMWF/ERA5_LAND/DAILY_AGGR",

    #     "product_name":
    #         "SM_ERA5_Land",

    #     "variable_name":
    #         "volumetric_soil_water_layer_2",

    #     "daily_method":
    #         "first",

    #     "scale":
    #         11132,
    # },
    {
        "collection_id":
            "ECMWF/ERA5/HOURLY",
    
        "product_name":
            "SM_ERA5",
    
        "variable_name":
            "volumetric_soil_water_layer_2",
    
        "daily_method":
            "mean",
    
        "scale":
            27830,
    },
]


# ============================================================
# EXTRACT, SAVE, AND VALIDATE EACH PRODUCT
# ============================================================
for product_cfg in gee_sm_products:
    product_name = product_cfg["product_name"]
    variable_name = product_cfg["variable_name"]

    result_daily, result_monthly = Extract_product_from_GEE_resample(
        sites=sites,
        collection_id=product_cfg["collection_id"],
        product_name=product_name,
        variable_name=variable_name,
        daily_method=product_cfg["daily_method"],
        start_date="2018-10-01",
        end_date="2020-01-01",
        # end_date="2018-11-11",
        scale=product_cfg["scale"],
    )

    timescales = ["daily", "monthly"]
    for timescale in timescales:

        field_data = Read_fielddata(timescale)

        output_dir = Path(
            f"../Figures/FigS_SM_Validate_2018-2019/"
            f"{timescale}"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        if timescale == "monthly":
            result_data = result_monthly

        elif timescale == "daily":
            result_data = result_daily

        # Save extracted time series.
        result_data.to_csv(
            output_dir
            / (
                f"{product_name}_at_fieldlocations_"
                f"{timescale}.csv"
            ),
            index=False,
        )

        # Scatter plot against field observations.
        comparison = Plot_product_vs_field(
            product_data=result_data,
            field_data=field_data,
            product_name=product_name,
            field_sm_column=field_sm_column,
            output_figure=(
                output_dir
                / (
                    f"Scatter_{product_name}_vs_field_"
                    f"{timescale}.png"
                )
            ),
        )

        comparison.to_csv(
            output_dir
            / (
                f"Comparison_{product_name}_vs_field_"
                f"{timescale}.csv"
            ),
            index=False,
        )    

#%% Plot scatter: SMOS mean across ACS and DES
product_name = "SM_SMOS"

# timescales = ["monthly", "daily"]
timescales = ["daily"]
for timescale in timescales:
    print(timescale)    
     
    field_data = Read_fielddata(timescale)
    output_dir = Path(f"../Figures/FigS_SM_Validate_2018-2019/{timescale}")

    # Read the two previously generated comparison tables
    smos_acs_file = output_dir / f"Comparison_SM_SMOS_ACS_vs_field_{timescale}.csv"
    smos_des_file = output_dir / f"Comparison_SM_SMOS_DES_vs_field_{timescale}.csv"
    
    smos_acs = pd.read_csv(smos_acs_file)
    smos_des = pd.read_csv(smos_des_file)
    
    # Standardize month and site-ID formats before matching
    smos_acs[site_id_column] = smos_acs[site_id_column].astype(str)
    smos_des[site_id_column] = smos_des[site_id_column].astype(str)    
    
    smos_acs["month"] = pd.to_datetime(smos_acs["month"])
    smos_des["month"] = pd.to_datetime(smos_des["month"])

    if timescale == "monthly":
        smos_acs["month"] = smos_acs["month"].dt.to_period("M").dt.to_timestamp()
        smos_des["month"] = smos_des["month"].dt.to_period("M").dt.to_timestamp()      
    
    # Keep all site-month records from ACS and DES
    SMOS_data = smos_acs[
        [site_id_column, "month", "SM_SMOS_ACS"]
    ].merge(
        smos_des[
            [site_id_column, "month", "SM_SMOS_DES"]
        ],
        on=[site_id_column, "month"],
        how="outer",
    )
    
    # Mean when both are available;
    # otherwise keep whichever value is available
    SMOS_data[product_name] = SMOS_data[
        ["SM_SMOS_ACS", "SM_SMOS_DES"]
    ].mean(axis=1, skipna=True)    
    
    
    # Keep the same product-table format used by Plot_product_vs_field()
    SMOS_data = SMOS_data[
        [site_id_column, "month", product_name]
    ].dropna(subset=[product_name])
    
    # Save the averaged monthly SMOS product
    SMOS_data.to_csv(
        output_dir / f"{product_name}_at_fieldlocations_{timescale}.csv",
        index=False,
    )
    
    # Plot the mean of ACS and DES against field observations
    comparison = Plot_product_vs_field(
        product_data=SMOS_data,
        field_data=field_data,
        product_name=product_name,
        field_sm_column=field_sm_column,
        output_figure=output_dir / f"Scatter_{product_name}_vs_field_{timescale}.png",
    )   
    
    comparison.to_csv(
            output_dir /
            f"Comparison_{product_name}_vs_field_{timescale}.csv",
            index=False,
    )
    

#%% Plot lineplot: monthly only
product_color_dict = {
    # Field Observations 
    "Field_Obs": "#111111",
    # ERA5 Products 
    "SM_ERA5": "pink",  
    "SM_ERA5_Land": "red",  
    # SMOS Product 
    "SM_SMOS": "orange",  
    # SMAP Products 
    "SM_SMAP_MT-DCA": "lightblue",  
    "SM_SMAP_L4_surface": "green",  
    "SM_SMAP_L4_rootzone": "gray",  
}

#----main
field_data = Read_fielddata("monthly")
output_dir = Path("../Figures/FigS_SM_Validate_2018-2019/monthly")


# Dictionary keys exactly match the soil-moisture column names in each Comparison_*.csv file.
comparison_files = {
    "SM_ERA5": output_dir / "Comparison_SM_ERA5_vs_field_monthly.csv",
    "SM_ERA5_Land": output_dir / "Comparison_SM_ERA5_Land_vs_field_monthly.csv",
    "SM_SMOS": output_dir / "Comparison_SM_SMOS_vs_field_monthly.csv",        
    "SM_SMAP_MT-DCA": output_dir / "Comparison_SM_SMAP_MT-DCA_vs_field_monthly.csv",
    "SM_SMAP_L4_surface": output_dir / "Comparison_SM_SMAP_L4_surface_vs_field_monthly.csv",
    "SM_SMAP_L4_rootzone": output_dir / "Comparison_SM_SMAP_L4_rootzone_vs_field_monthly.csv",
}


# ============================================================
# 1. Calculate monthly mean field soil moisture
# ============================================================
field_data_plot = field_data.copy()

field_data_plot["month"] = (
    pd.to_datetime(field_data_plot["month"])
    .dt.to_period("M")
    .dt.to_timestamp()
)

field_data_plot[field_sm_column] = pd.to_numeric(
    field_data_plot[field_sm_column],
    errors="coerce",
)

# Keep this conversion only if field data are still in %vol.
field_data_plot[field_sm_column] = (
    field_data_plot[field_sm_column] 
)

field_mean = (
    field_data_plot
    .groupby("month", as_index=False)[field_sm_column]
    .mean()
    .rename(columns={field_sm_column: "Field"})
    .sort_values("month")
)


# ============================================================
# 2. Read each product and calculate its monthly spatial mean
# ============================================================
monthly_products = []

for product_name, filename in comparison_files.items():

    df = pd.read_csv(filename)

    df["month"] = (
        pd.to_datetime(df["month"])
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    df[product_name] = pd.to_numeric(
        df[product_name],
        errors="coerce",
    )

    monthly_mean = (
        df
        .groupby("month", as_index=False)[product_name]
        .mean()
    )

    monthly_products.append(monthly_mean)


# ============================================================
# 3. Merge all product means and field means
# ============================================================
monthly_all = monthly_products[0]

for monthly_mean in monthly_products[1:]:

    monthly_all = monthly_all.merge(
        monthly_mean,
        on="month",
        how="outer",
    )

monthly_all = monthly_all.merge(
    field_mean,
    on="month",
    how="outer",
)

monthly_all = (
    monthly_all
    .sort_values("month")
    .reset_index(drop=True)
)


# ============================================================
# 4. Calculate correlation between each product and field mean
# ============================================================
product_correlations = {}

for product_name in comparison_files:

    matched = monthly_all[
        ["Field", product_name]
    ].dropna()

    if len(matched) >= 2:
        correlation = matched["Field"].corr(
            matched[product_name]
        )
    else:
        correlation = np.nan

    product_correlations[product_name] = correlation


# Print correlations
for product_name, correlation in product_correlations.items():
    print(
        f"{product_name}: "
        f"monthly correlation with field = {correlation:.3f}"
    )


# ============================================================
# 5. Save monthly means and correlations
# ============================================================
if False:
    monthly_all.to_csv(
        output_dir / "Monthly_mean_SM_all_products_and_field.csv",
        index=False,
    )
    
    correlation_table = pd.DataFrame(
        {
            "Product": list(product_correlations.keys()),
            "Correlation": list(product_correlations.values()),
        }
    )
    
    correlation_table.to_csv(
        output_dir / "Correlation_monthly_SM_products_vs_field.csv",
        index=False,
    )


# ============================================================
# 6. Plot monthly product means and field observations
# ============================================================
fig, ax = plt.subplots(figsize=(9, 5.5))

for product_name in comparison_files:

    correlation = product_correlations[product_name]
    DEFAULT_COLOR = "#888888"
    color = product_color_dict.get(product_name, DEFAULT_COLOR)

    if np.isnan(correlation):
        legend_label = f"{product_name} (r=NA)"
    else:
        legend_label = f"{product_name} (r={correlation:.2f})"

    ax.plot(
        monthly_all["month"],
        monthly_all[product_name],
        marker="o",
        linewidth=2,
        markersize=4,
        label=legend_label,
        color=color
    )

# Add field observations as points
ax.scatter(
    monthly_all["month"],
    monthly_all["Field"],
    color="blue",
    marker="*",
    s=120,
    label="Field observations",
    zorder=10,
)

ax.set_xlabel("Month")
ax.set_ylabel("Soil moisture (m³/m³)")
ax.set_title("Monthly mean soil moisture across field locations")
ax.set_ylim(0, 0.95)

ax.grid(
    True,
    linestyle="--",
    linewidth=0.6,
    alpha=0.6,
)

ax.legend(
    ncol=2,
    fontsize=9,
)

fig.autofmt_xdate()
fig.tight_layout()

fig.savefig(
    output_dir / "Lineplot_monthly_SM_products_vs_field.png",
    dpi=300,
    bbox_inches="tight",
)

plt.show()
plt.close(fig)

#%% Look for product attributes
### SMOS
example_file = Path("SM_SMOS/ACS/SM_RE07_MIR_CDF3SA_20150701T000000_20150701T235959_200_001_B.DBL.nc")
### SMAP_MT-DCA
example_file = Path("SM_SMAP_MT-DCA/MTDCA_9km_V5_nc/MTDCA_201707_201709_9km_V5.nc")


example_ds = xr.open_dataset(example_file)

#%%(test) Extract SM_ERA5 at field locations
netcdf_file = Path("SM_ERA5/raw/ERA5_SM2_2015_07_daily.nc") 
output_file = Path("../Figures/FigS_SM_Validate_2018-2019/SM_ERA5_daily_at_fieldlocations_onefile.csv")

product_name = "SM_ERA5"
variable_name = "swvl2"
lon_name = "longitude"
lat_name = "latitude"
time_name = "valid_time"

ds = xr.open_dataset(netcdf_file)
data = ds[variable_name]

## extract sm
result = Extract_SM_at_Fieldlocations(sites, ds, data, 
                                      product_name, variable_name, lon_name, lat_name, time_name)
result.to_csv(output_file, index=False)
ds.close()


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    



