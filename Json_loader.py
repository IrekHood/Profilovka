import geopandas as gpd
import json
import math

# --- Mercator projection function ---
def mercator_projection(lon, lat):
    R = 6378137  # Radius of Earth in meters
    x = R * math.radians(lon)
    if lat == -90.0:
        lat = -89.9
    y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x/ 100000, y / 100000  # Scale down for better visualization


# Load the shapefile
gdf = gpd.read_file("data/high_quality/political/countries")
READ_DATA = ["CONTINENT", "ADMIN", "ADM0_A3", "geometry"]
CONTINENT = "Europe"

# Select the relevant columns
gdf = gdf[READ_DATA]
#gdf = gdf[gdf["CONTINENT"] == CONTINENT]
#gdf = gdf.drop(columns=["CONTINENT"])
gdf = gdf.rename(columns={"ADMIN": "country", "ADM0_A3": "country_code"})
gdf = gdf.reset_index(drop=True)
print(gdf.head())  # View the first five rows

# Convert the GeoDataFrame to a dictionary
data_dict = {}
for _, row in gdf.iterrows():
    country_name = row["country"]
    geometry = row["geometry"]
    continent = row["CONTINENT"]
    
    if geometry.geom_type == "MultiPolygon":
        polygons = []
        for poly in geometry.geoms:
            projected = [mercator_projection(lon, lat) for lon, lat in poly.exterior.coords]
            polygons.append(projected)
    else:  # Single Polygon
        polygons = [[mercator_projection(lon, lat) for lon, lat in geometry.exterior.coords]]
    
    data_dict[country_name] = {
        "country_code": row["country_code"],
        "continent": continent,
        "geometry": polygons
    }


# Save the dictionary to a JSON file
with open(f"maps/World_h.json", "w") as json_file:
    json.dump(data_dict, json_file, indent=4)

# View the first five rows