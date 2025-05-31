import geopandas as gpd
import json


def continents_to_countries_dict(geofile_path, continent_col='CONTINENT', country_col='ADMIN'):
    """
    Reads a geopandas file and returns a JSON string of a dictionary with
    continents as keys and lists of countries as values.

    Parameters:
    - geofile_path (str): path to the geopandas-compatible file (e.g., .shp, .geojson)
    - continent_col (str): column name for continent
    - country_col (str): column name for country

    Returns:
    - str: JSON-formatted string
    """
    # Read the geopandas file
    gdf = gpd.read_file(geofile_path)

    # Check if expected columns exist
    if continent_col not in gdf.columns or country_col not in gdf.columns:
        raise ValueError(f"Columns '{continent_col}' or '{country_col}' not found in the GeoDataFrame.")

    # Drop rows with missing data in those columns
    gdf = gdf.dropna(subset=[continent_col, country_col])

    # Group countries by continent
    continent_dict = gdf.groupby(continent_col)[country_col].apply(list).to_dict()

    # Optional: sort country names alphabetically
    for continent in continent_dict:
        continent_dict[continent] = sorted(set(continent_dict[continent]))

    return json.dumps(continent_dict, indent=4)


# Example usage
geofile = "data/Mid_quality/political/contries/ne_50m_admin_0_countries/ne_50m_admin_0_countries.shp"  # or .geojson
json_output = continents_to_countries_dict(geofile)
print(json_output)

# Optionally, write to file
with open("data/lists/continents_countries.json", "w") as f:
    f.write(json_output)
