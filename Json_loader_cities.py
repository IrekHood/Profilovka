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
gdf = gpd.read_file("data/high_quality/political/cities")
READ_DATA = ["NAME_EN", "geometry", "SCALERANK", "FEATURECLA"]

print(gdf.columns)
print(gdf.values)
print(gdf.head())
# Select the relevant columns
gdf = gdf[READ_DATA]
gdf = gdf.reset_index(drop=True)
print(gdf.head())  # View the first five rows

# Convert the GeoDataFrame to a dictionary
data_dict = {}
for _, row in gdf.iterrows():
    city_name = row["NAME_EN"]
    geometry = row["geometry"]
    
    if geometry.geom_type == "Point":

        projected = mercator_projection(geometry.x, geometry.y)
    else:  # Single Polygon
        print(geometry.geom_type)
        exit()
    
    data_dict[city_name] = {
        "geometry": projected,
        "rank": int(row["SCALERANK"]),
        "capital": row["FEATURECLA"] == 'Admin-0 capital'
    }

# Save the dictionary to a JSON file
with open(f"maps/High_quality/cities.json", "w") as json_file:
    json.dump(data_dict, json_file, indent=4)

# View the first five rows