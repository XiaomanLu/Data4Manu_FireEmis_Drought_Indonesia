"""
Fast native-grid extraction of daily regional means from Google Earth Engine.

Changes from the previous script:
1. Uses raster masks instead of sampling thousands of native-grid points. [MAKE IT MUCH FASTER!]
2. Aligns masks to each product's native projection.
3. Processes small multi-day chunks per getInfo() request instead of one day per request. [MAKE IT FASTER!]
4. Calculates all, peat, and non-peat means/counts in one reduceRegion call.
5. Saves daily, monthly, and yearly CSV files locally.
"""

### TIP: this data is for Fig. 2 scatterplot, not Fig. 3 binplot!

from calendar import monthrange
from datetime import date
from pathlib import Path
import time
import ee
import pandas as pd


# ============================================================
# INITIALIZE EARTH ENGINE
# ============================================================
PROJECT_ID = "quick-heaven-445214-f5"
def initialize_ee():
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)
initialize_ee()


# ============================================================
# USER SETTINGS
# ============================================================
START_YEAR = 2003
END_YEAR = 2025

PRODUCTS_TO_RUN = [
    "SM_ERA5_LAND",
    "VPD_ERA5_LAND",
    # "SM_SMAP_L4",
    # "SPEI_01",
    # "TWSA",    
]

# SPEI accumulation timescale in months (1-48).
# A 3-month SPEI is used by default; change this value if needed.
SPEI_TIME_SCALE_MONTHS = 1 #It represents the drought conditions accumulated over the previous * months.

KEEP_MONTHS = list(range(7, 12))

# Set to 1 for a one-month test; use None for the full period.
# It takes ~6s for each month each product.
TEST_N_MONTHS = None
# TEST_N_MONTHS = 1 #This variable works for ERA and SMAP daily data, but not for SPEI and TWSA.


# Number of daily aggregations evaluated in one Earth Engine request.
# Start with 5. If "Too many concurrent aggregations" still occurs,
# reduce to 3. If it runs reliably, you can test 7.
# It does not affect result, but affect running speed.
CHUNK_DAYS = 5

OUT_ROOT = Path(
    "/Volumes/LaCie/SDSU_PhDwork/"
    "work10_Inni_Emission_Water/Data"
)

PEAT_ID_ASSET = (
    "projects/quick-heaven-445214-f5/assets/Peat_new"
)
ISLAND_ID_ASSET = (
    "projects/quick-heaven-445214-f5/assets/Island_Polygon_new"
)

WEST, EAST = 95.0, 120.0
SOUTH, NORTH = -6.0, 6.0
INDONESIA_BBOX = ee.Geometry.Rectangle(
    [WEST, SOUTH, EAST, NORTH],
    geodesic=False,
)

TILE_SCALE = 4
MAX_PIXELS = 1e13
MAX_RETRIES = 3
RETRY_SECONDS = 10


# ============================================================
# PRODUCT CONFIGURATION
# ============================================================
PRODUCTS = {
    "SM_ERA5_LAND": {
        "collection": "ECMWF/ERA5_LAND/DAILY_AGGR",
        "source_bands": ["volumetric_soil_water_layer_2"],
        "output_band": "volumetric_soil_water_layer_2",
        "daily_method": "first",
        "expected_images_per_day": 1,
        "minimum_date": date(1950, 1, 2),
        "minimum_valid": 1e-6,
        "units": "m3/m3",
    },
    "VPD_ERA5_LAND": {
        "collection": "ECMWF/ERA5_LAND/HOURLY",
        "source_bands": [
            "temperature_2m",
            "dewpoint_temperature_2m",
        ],
        "output_band": "VPD",
        "daily_method": "vpd_hourly_mean",
        "expected_images_per_day": 24,
        "minimum_date": date(1950, 1, 1),
        "minimum_valid": 0.0,
        "units": "kPa",
    },
    "SM_SMAP_L4": {
        "collection": "NASA/SMAP/SPL4SMGP/008",
        "source_bands": ["sm_surface"],
        "output_band": "sm_surface",
        "daily_method": "mean",
        "expected_images_per_day": 8,
        "minimum_date": date(2015, 3, 31),
        "minimum_valid": 1e-6,
        "units": "m3/m3",
    },
    "TWSA": {
        # "collection": "NASA/GRACE/MASS_GRIDS_V04/MASCON",       #Both MASCON AND MASCON_CRI have obvious increasing trend!        
        "collection": "NASA/GRACE/MASS_GRIDS_V04/MASCON_CRI",        
        "source_bands": ["lwe_thickness"],        
        
        # "collection": "NASA/GRACE/MASS_GRIDS_V04/LAND",           #No trend, like old, but short period until 2017.01.      
        # "source_bands": ["lwe_thickness_csr"],            
        
        "output_band": "TWSA",
        "temporal_resolution": "monthly",
        "minimum_date": date(2002, 3, 31),
        "minimum_valid": None,
        "units": "cm equivalent water thickness",
    },
    "SPEI": {
        "collection": "CSIC/SPEI/2_11",
        "source_bands": [
            f"SPEI_{SPEI_TIME_SCALE_MONTHS:02d}_month"
        ],
        "output_band": f"SPEI_{SPEI_TIME_SCALE_MONTHS:02d}",
        "temporal_resolution": "monthly",
        "minimum_date": date(1901, 1, 1),
        "minimum_valid": None,
        "units": "standardized index",
    },
    # Uncomment when needed.
    # "VPD_ERA5": {
    #     "collection": "ECMWF/ERA5/HOURLY",
    #     "source_bands": [
    #         "temperature_2m",
    #         "dewpoint_temperature_2m",
    #     ],
    #     "output_band": "VPD",
    #     "daily_method": "vpd_hourly_mean",
    #     "expected_images_per_day": 24,
    #     "minimum_date": date(1940, 1, 1),
    #     "minimum_valid": 0.0,
    #     "units": "kPa",
    # },
    # "SM_ERA5": {
    #     "collection": "ECMWF/ERA5/HOURLY",
    #     "source_bands": ["volumetric_soil_water_layer_2"],
    #     "output_band": "volumetric_soil_water_layer_2",
    #     "daily_method": "mean",
    #     "expected_images_per_day": 24,
    #     "minimum_date": date(1940, 1, 1),
    #     "minimum_valid": 1e-6,
    #     "units": "m3/m3",
    # },
}


# ============================================================
# VALIDATE SETTINGS
# ============================================================
if START_YEAR > END_YEAR:
    raise ValueError("START_YEAR must be <= END_YEAR")

KEEP_MONTHS = sorted(set(KEEP_MONTHS))
if not KEEP_MONTHS or any(m < 1 or m > 12 for m in KEEP_MONTHS):
    raise ValueError("KEEP_MONTHS must contain integers from 1 through 12")

unknown_products = [
    p for p in PRODUCTS_TO_RUN if p not in PRODUCTS
]
if unknown_products:
    raise ValueError(
        f"Unknown product names: {unknown_products}. "
        f"Available products are {list(PRODUCTS)}"
    )

if TEST_N_MONTHS is not None and TEST_N_MONTHS < 1:
    raise ValueError("TEST_N_MONTHS must be None or a positive integer")

if CHUNK_DAYS < 1:
    raise ValueError("CHUNK_DAYS must be a positive integer")

if SPEI_TIME_SCALE_MONTHS < 1 or SPEI_TIME_SCALE_MONTHS > 48:
    raise ValueError("SPEI_TIME_SCALE_MONTHS must be from 1 through 48")

OUT_ROOT.mkdir(parents=True, exist_ok=True)


# ============================================================
# STATIC CLASSIFICATION MASKS
# ============================================================
island_id = (
    ee.Image(ISLAND_ID_ASSET)
    .select(0)
    .rename("PolyID")
    .unmask(0)
)
peat_id = (
    ee.Image(PEAT_ID_ASSET)
    .select(0)
    .rename("PeatID")
    .unmask(0)
)

regional_mask_source = (
    island_id.eq(1)
    .Or(island_id.eq(3))
    .rename("regional")
)
peat_mask_source = (
    regional_mask_source
    .And(peat_id.eq(1))
    .rename("peat")
)
nonpeat_mask_source = (
    regional_mask_source
    .And(peat_id.eq(0))
    .rename("nonpeat")
)


# ============================================================
# DATE HELPERS
# ============================================================
def requested_year_months(minimum_date):
    pairs = []
    for year in range(START_YEAR, END_YEAR + 1):
        for month in KEEP_MONTHS:
            last_day = monthrange(year, month)[1]
            if date(year, month, last_day) < minimum_date:
                continue
            pairs.append((year, month))
    return pairs


def python_dates_for_month(year, month, minimum_date):
    last_day = monthrange(year, month)[1]
    return [
        date(year, month, day)
        for day in range(1, last_day + 1)
        if date(year, month, day) >= minimum_date
    ]


# ============================================================
# VPD CALCULATION (kPa)
# ============================================================
def calculate_hourly_vpd(image):
    image = ee.Image(image)

    temperature_c = image.select("temperature_2m").subtract(273.15)
    dewpoint_c = image.select("dewpoint_temperature_2m").subtract(273.15)

    saturation_vapor_pressure = temperature_c.expression(
        "0.61078 * exp((17.27 * t) / (t + 237.3))",
        {"t": temperature_c},
    )
    actual_vapor_pressure = dewpoint_c.expression(
        "0.61078 * exp((17.27 * td) / (td + 237.3))",
        {"td": dewpoint_c},
    )

    return (
        saturation_vapor_pressure
        .subtract(actual_vapor_pressure)
        .max(0)
        .rename("VPD")
        .copyProperties(image, ["system:time_start"])
    )


# ============================================================
# DAILY IMAGE
# ============================================================
def build_daily_image(within_day, method, output_band, native_projection):
    if method == "first":
        daily_image = ee.Image(within_day.first()).select(output_band)
    elif method == "mean":
        daily_image = within_day.select(output_band).mean()
    elif method == "vpd_hourly_mean":
        daily_image = (
            within_day.map(calculate_hourly_vpd)
            .mean()
            .rename(output_band)
        )
    else:
        raise ValueError(f"Unsupported daily method: {method}")

    return (
        daily_image
        .rename(output_band)
        .setDefaultProjection(native_projection)
    )


# ============================================================
# PROCESS ONE PRODUCT
# ============================================================
def process_product(product_key):
    cfg = PRODUCTS[product_key]

    if cfg.get("temporal_resolution", "daily") != "daily":
        return process_monthly_product(product_key)

    collection_id = cfg["collection"]
    source_bands = cfg["source_bands"]
    output_band = cfg["output_band"]
    output_name = product_key
    product_label = product_key
    daily_method = cfg["daily_method"]
    expected_images = cfg["expected_images_per_day"]
    minimum_date = cfg["minimum_date"]
    minimum_valid = cfg["minimum_valid"]
    units = cfg["units"]

    start_date_ee = max(
        date(START_YEAR, 1, 1),
        minimum_date,
    ).isoformat()
    end_date_ee = date(END_YEAR + 1, 1, 1).isoformat()

    source_collection = (
        ee.ImageCollection(collection_id)
        .filterDate(start_date_ee, end_date_ee)
        .select(source_bands)
    )

    if source_collection.size().getInfo() == 0:
        raise RuntimeError(
            f"No images found for {product_key} during the requested period"
        )

    template_band = source_bands[0]
    native_template = ee.Image(source_collection.first()).select(template_band)
    native_projection = native_template.projection()
    native_scale = native_projection.nominalScale()

    print("\n" + "=" * 70)
    print(f"Product: {product_key}")
    print(f"Collection: {collection_id}")
    print(f"Output variable: {output_name} ({units})")
    print("Native nominal scale (m):", native_scale.getInfo())

    # Align categorical masks to the exact native product grid.
    # Categorical images use nearest-neighbor reprojection by default.
    regional_mask = regional_mask_source.reproject(
        crs=native_projection
    ).rename("regional")
    peat_mask = peat_mask_source.reproject(
        crs=native_projection
    ).rename("peat")
    nonpeat_mask = nonpeat_mask_source.reproject(
        crs=native_projection
    ).rename("nonpeat")

    mask_stack = ee.Image.cat([
        regional_mask.selfMask().rename("all"),
        peat_mask.selfMask().rename("p1"),
        nonpeat_mask.selfMask().rename("p0"),
    ])

    mask_counts = mask_stack.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=INDONESIA_BBOX,
        crs=native_projection,
        scale=native_scale,
        maxPixels=MAX_PIXELS,
        tileScale=TILE_SCALE,
    ).getInfo()

    print("Native-grid mask counts:")
    print("  regional:", mask_counts.get("all", 0))
    print("  peat:", mask_counts.get("p1", 0))
    print("  nonpeat:", mask_counts.get("p0", 0))

    if mask_counts.get("all", 0) == 0:
        raise RuntimeError(
            f"No {product_key} grid cells fall in PolyID 1 or 3"
        )

    mean_count_reducer = ee.Reducer.mean().combine(
        reducer2=ee.Reducer.count(),
        sharedInputs=True,
    )

    def build_one_day_feature(day_value):
        day_string = day_value.isoformat()
        day_ee = ee.Date(day_string)
        next_day_ee = day_ee.advance(1, "day")

        within_day = source_collection.filterDate(day_ee, next_day_ee)
        source_count = within_day.size()

        daily_image = build_daily_image(
            within_day=within_day,
            method=daily_method,
            output_band=output_band,
            native_projection=native_projection,
        )

        valid_image = daily_image.updateMask(
            daily_image.gte(minimum_valid)
        )

        value_stack = ee.Image.cat([
            valid_image.updateMask(regional_mask).rename("all"),
            valid_image.updateMask(peat_mask).rename("p1"),
            valid_image.updateMask(nonpeat_mask).rename("p0"),
        ]).setDefaultProjection(native_projection)

        stats = value_stack.reduceRegion(
            reducer=mean_count_reducer,
            geometry=INDONESIA_BBOX,
            crs=native_projection,
            scale=native_scale,
            maxPixels=MAX_PIXELS,
            tileScale=TILE_SCALE,
        )

        return ee.Feature(None, {
            "Date": day_string,
            "Year": day_value.year,
            "Month": day_value.month,
            "Day": day_value.day,
            "N_source_images": source_count,
            "N_grid_all": stats.get("all_count"),
            "N_grid_p1": stats.get("p1_count"),
            "N_grid_p0": stats.get("p0_count"),
            output_name: stats.get("all_mean"),
            f"{output_name}_p1": stats.get("p1_mean"),
            f"{output_name}_p0": stats.get("p0_mean"),
        })

    def get_date_chunk(date_chunk):
        """
        Evaluate a small group of daily statistics in one request.

        Processing an entire month at once can trigger Earth Engine's
        "Too many concurrent aggregations" limit because each day contains
        a reduceRegion operation. Small chunks retain most of the request-
        overhead savings while avoiding that limit.
        """
        if not date_chunk:
            return []

        chunk_features = ee.FeatureCollection([
            build_one_day_feature(day_value)
            for day_value in date_chunk
        ]).sort("Date")

        chunk_label = (
            f"{date_chunk[0].isoformat()} to "
            f"{date_chunk[-1].isoformat()}"
        )

        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                info = chunk_features.getInfo()

                return [
                    feature.get("properties", {})
                    for feature in info.get("features", [])
                ]

            except Exception as error:
                last_error = error

                print(
                    f"      Attempt {attempt}/{MAX_RETRIES} failed "
                    f"for {chunk_label}: {error}"
                )

                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_SECONDS)

        raise RuntimeError(
            f"Failed to process {chunk_label} "
            f"after {MAX_RETRIES} attempts"
        ) from last_error

    year_months = requested_year_months(minimum_date)
    if TEST_N_MONTHS is not None:
        year_months = year_months[:TEST_N_MONTHS]
    if not year_months:
        raise RuntimeError(
            f"No months satisfy the settings for {product_key}"
        )

    rows = []
    number_of_months = len(year_months)
    overall_start = time.time()

    print(
        f"Processing {number_of_months} months "
        f"in chunks of up to {CHUNK_DAYS} days..."
    )

    for index, (year, month) in enumerate(year_months, start=1):
        month_start_time = time.time()
        print(f"[{index}/{number_of_months}] {year}-{month:02d}")

        month_dates = python_dates_for_month(
            year,
            month,
            minimum_date,
        )

        month_rows = []

        for chunk_start in range(
            0,
            len(month_dates),
            CHUNK_DAYS,
        ):
            date_chunk = month_dates[
                chunk_start:chunk_start + CHUNK_DAYS
            ]

            print(
                f"    Chunk "
                f"{date_chunk[0].isoformat()} to "
                f"{date_chunk[-1].isoformat()}"
            )

            chunk_rows = get_date_chunk(date_chunk)
            month_rows.extend(chunk_rows)

        rows.extend(
            row for row in month_rows
            if row.get("N_source_images", 0) > 0
        )

        month_elapsed = time.time() - month_start_time
        total_elapsed = time.time() - overall_start
        average_elapsed = total_elapsed / index
        remaining_seconds = average_elapsed * (number_of_months - index)

        print(
            f"    Month: {month_elapsed:.2f}s | "
            f"Average: {average_elapsed:.2f}s/month | "
            f"Estimated remaining: {remaining_seconds / 60:.1f} min"
        )

    value_columns = [
        output_name,
        f"{output_name}_p1",
        f"{output_name}_p0",
    ]
    daily_columns = [
        "Date",
        "Year",
        "Month",
        "Day",
        "N_source_images",
        "N_grid_all",
        "N_grid_p1",
        "N_grid_p0",
        *value_columns,
    ]

    daily_df = pd.DataFrame(rows).reindex(columns=daily_columns)
    if daily_df.empty:
        raise RuntimeError(
            f"No daily records returned for {product_key}"
        )

    daily_df["Date"] = pd.to_datetime(daily_df["Date"])
    daily_df = daily_df.sort_values("Date").reset_index(drop=True)

    outdir = OUT_ROOT / product_label
    outdir.mkdir(parents=True, exist_ok=True)

    # month_tag = "_".join(f"{month:02d}" for month in KEEP_MONTHS)
    output_prefix = (
        f"{product_label}_{START_YEAR}-{END_YEAR}_"
        "Jul-Nov"
    )

    daily_file = outdir / f"{output_prefix}_daily.csv"
    daily_df.to_csv(daily_file, index=False)

    
    
    
    ### calculate monthly mean
    # monthly_df = (
    #     daily_df.groupby(["Year", "Month"], as_index=False)
    #     .agg(
    #         N_days=("Date", "count"),
    #         **{
    #             output_name: (output_name, "mean"),
    #             f"{output_name}_p1": (f"{output_name}_p1", "mean"),
    #             f"{output_name}_p0": (f"{output_name}_p0", "mean"),
    #         },
    #     )
    # )
    
    agg_dict = {
        "N_days": ("Date", "count"),
        output_name: (output_name, "mean"),
        f"{output_name}_p1": (f"{output_name}_p1", "mean"),
        f"{output_name}_p0": (f"{output_name}_p0", "mean"),
    }
    
    ## calculate sd(standard deviation) used in Fig. 1, for monthly VPD and SM.
    if product_key in ["SM_ERA5_LAND", "VPD_ERA5_LAND"]:
        agg_dict.update({
            f"{output_name}_sd": (
                output_name, "std"
            ),
            f"{output_name}_p1_sd": (
                f"{output_name}_p1", "std"
            ),
            f"{output_name}_p0_sd": (
                f"{output_name}_p0", "std"
            ),
        })
    
    # Calculate monthly statistics
    monthly_df = (
        daily_df
        .groupby(["Year", "Month"], as_index=False)
        .agg(**agg_dict)
    )       
    
    # add cols
    monthly_df.insert(
        0,
        "YearMonth",
        monthly_df["Year"].astype(int).astype(str)
        + "-"
        + monthly_df["Month"].astype(int).astype(str).str.zfill(2),
    )
    
    ### calculate yearly mean
    yearly_df = (
        daily_df.groupby("Year", as_index=False)
        .agg(
            N_days=("Date", "count"),
            **{
                output_name: (output_name, "mean"),
                f"{output_name}_p1": (f"{output_name}_p1", "mean"),
                f"{output_name}_p0": (f"{output_name}_p0", "mean"),
            },
        )
    )

    monthly_file = outdir / f"{output_prefix}_monthly.csv"
    yearly_file = outdir / f"{output_prefix}_yearly.csv"
    monthly_df.to_csv(monthly_file, index=False)
    yearly_df.to_csv(yearly_file, index=False)

    print(f"Saved: {daily_file}")
    print(f"Saved: {monthly_file}")
    print(f"Saved: {yearly_file}")
    print(f"Daily records: {len(daily_df)}")
    print(f"Monthly records: {len(monthly_df)}")
    print(f"Yearly records: {len(yearly_df)}")

    incomplete = daily_df.loc[
        daily_df["N_source_images"] != expected_images,
        ["Date", "N_source_images"],
    ]
    if not incomplete.empty:
        print(
            f"Warning: dates not containing the expected "
            f"{expected_images} source images:"
        )
        print(incomplete.to_string(index=False))

    return [daily_file, monthly_file, yearly_file]


# ============================================================
# PROCESS ONE MONTHLY PRODUCT (TWSA OR SPEI)
# ============================================================
def process_monthly_product(product_key):
    """Extract native monthly observations without creating daily files."""
    cfg = PRODUCTS[product_key]

    collection_id = cfg["collection"]
    source_band = cfg["source_bands"][0]
    output_name = cfg["output_band"]
    product_label = product_key
    minimum_date = cfg["minimum_date"]
    minimum_valid = cfg["minimum_valid"]
    units = cfg["units"]

    start_date_ee = max(
        date(START_YEAR, 1, 1),
        minimum_date,
    ).isoformat()
    end_date_ee = date(END_YEAR + 1, 1, 1).isoformat()

    source_collection = (
        ee.ImageCollection(collection_id)
        .filterDate(start_date_ee, end_date_ee)
        .filter(ee.Filter.calendarRange(
            min(KEEP_MONTHS), max(KEEP_MONTHS), "month"
        ))
        .select([source_band])
        .sort("system:time_start")
    )

    # calendarRange above is contiguous; explicitly retain only KEEP_MONTHS
    # in case the user chooses a non-contiguous month list.
    month_filters = [
        ee.Filter.calendarRange(month, month, "month")
        for month in KEEP_MONTHS
    ]
    source_collection = source_collection.filter(ee.Filter.Or(*month_filters))

    if source_collection.size().getInfo() == 0:
        raise RuntimeError(
            f"No images found for {product_key} during the requested period"
        )

    native_template = ee.Image(source_collection.first()).select(source_band)
    native_projection = native_template.projection()
    native_scale = native_projection.nominalScale()

    print("\n" + "=" * 70)
    print(f"Product: {product_key}")
    print(f"Collection: {collection_id}")
    print(f"Output variable: {output_name} ({units})")
    print("Temporal resolution: monthly")
    print("Native nominal scale (m):", native_scale.getInfo())

    regional_mask = regional_mask_source.reproject(
        crs=native_projection
    ).rename("regional")
    peat_mask = peat_mask_source.reproject(
        crs=native_projection
    ).rename("peat")
    nonpeat_mask = nonpeat_mask_source.reproject(
        crs=native_projection
    ).rename("nonpeat")

    mask_stack = ee.Image.cat([
        regional_mask.selfMask().rename("all"),
        peat_mask.selfMask().rename("p1"),
        nonpeat_mask.selfMask().rename("p0"),
    ])

    mask_counts = mask_stack.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=INDONESIA_BBOX,
        crs=native_projection,
        scale=native_scale,
        maxPixels=MAX_PIXELS,
        tileScale=TILE_SCALE,
    ).getInfo()

    print("Native-grid mask counts:")
    print("  regional:", mask_counts.get("all", 0))
    print("  peat:", mask_counts.get("p1", 0))
    print("  nonpeat:", mask_counts.get("p0", 0))

    mean_count_reducer = ee.Reducer.mean().combine(
        reducer2=ee.Reducer.count(),
        sharedInputs=True,
    )

    def image_to_feature(image):
        image = ee.Image(image)
        image_date = image.date()
        value_image = image.select(source_band).rename(output_name)

        if minimum_valid is not None:
            value_image = value_image.updateMask(
                value_image.gte(minimum_valid)
            )

        value_stack = ee.Image.cat([
            value_image.updateMask(regional_mask).rename("all"),
            value_image.updateMask(peat_mask).rename("p1"),
            value_image.updateMask(nonpeat_mask).rename("p0"),
        ]).setDefaultProjection(native_projection)

        stats = value_stack.reduceRegion(
            reducer=mean_count_reducer,
            geometry=INDONESIA_BBOX,
            crs=native_projection,
            scale=native_scale,
            maxPixels=MAX_PIXELS,
            tileScale=TILE_SCALE,
        )

        return ee.Feature(None, {
            "Date": image_date.format("YYYY-MM-dd"),
            "Year": image_date.get("year"),
            "Month": image_date.get("month"),
            "N_source_images": 1,
            "N_grid_all": stats.get("all_count"),
            "N_grid_p1": stats.get("p1_count"),
            "N_grid_p0": stats.get("p0_count"),
            output_name: stats.get("all_mean"),
            f"{output_name}_p1": stats.get("p1_mean"),
            f"{output_name}_p0": stats.get("p0_mean"),
        })

    features = source_collection.map(image_to_feature)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            info = features.getInfo()
            rows = [
                feature.get("properties", {})
                for feature in info.get("features", [])
            ]
            break
        except Exception as error:
            last_error = error
            print(
                f"Attempt {attempt}/{MAX_RETRIES} failed for "
                f"{product_key}: {error}"
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SECONDS)
    else:
        raise RuntimeError(
            f"Failed to process {product_key} after "
            f"{MAX_RETRIES} attempts"
        ) from last_error

    value_columns = [
        output_name,
        f"{output_name}_p1",
        f"{output_name}_p0",
    ]
    monthly_columns = [
        "Date",
        "Year",
        "Month",
        "N_source_images",
        "N_grid_all",
        "N_grid_p1",
        "N_grid_p0",
        *value_columns,
    ]

    monthly_df = pd.DataFrame(rows).reindex(columns=monthly_columns)
    if monthly_df.empty:
        raise RuntimeError(
            f"No monthly records returned for {product_key}"
        )

    monthly_df["Date"] = pd.to_datetime(monthly_df["Date"])
    monthly_df = monthly_df.sort_values("Date").reset_index(drop=True)
    monthly_df.insert(
        0,
        "YearMonth",
        monthly_df["Year"].astype(int).astype(str)
        + "-"
        + monthly_df["Month"].astype(int).astype(str).str.zfill(2),
    )

    yearly_df = (
        monthly_df.groupby("Year", as_index=False)
        .agg(
            N_months=("Date", "count"),
            **{
                output_name: (output_name, "mean"),
                f"{output_name}_p1": (f"{output_name}_p1", "mean"),
                f"{output_name}_p0": (f"{output_name}_p0", "mean"),
            },
        )
    )

    outdir = OUT_ROOT / product_label
    outdir.mkdir(parents=True, exist_ok=True)

    output_prefix = (
        f"{product_label}_{START_YEAR}-{END_YEAR}_"
        "Jul-Nov"
    )
    monthly_file = outdir / f"{output_prefix}_monthly.csv"
    yearly_file = outdir / f"{output_prefix}_yearly.csv"
    monthly_df.to_csv(monthly_file, index=False)
    yearly_df.to_csv(yearly_file, index=False)

    print(f"Saved: {monthly_file}")
    print(f"Saved: {yearly_file}")
    print(f"Monthly records: {len(monthly_df)}")
    print(f"Yearly records: {len(yearly_df)}")

    incomplete_years = yearly_df.loc[
        yearly_df["N_months"] != len(KEEP_MONTHS),
        ["Year", "N_months"],
    ]
    if not incomplete_years.empty:
        print(
            "Warning: years with fewer than the requested "
            f"{len(KEEP_MONTHS)} monthly observations:"
        )
        print(incomplete_years.to_string(index=False))

    return [monthly_file, yearly_file]


# ============================================================
# RUN ALL SELECTED PRODUCTS
# ============================================================
saved_files = []
for selected_product in PRODUCTS_TO_RUN:
    saved_files.extend(process_product(selected_product))

print("\n" + "=" * 70)
print("Finished all selected products.")
print("Saved files:")
for saved_file in saved_files:
    print(" ", saved_file)
