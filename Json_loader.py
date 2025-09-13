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
gdf = gpd.read_file("data/Mid_quality/political/contries/ne_50m_admin_0_countries")
READ_DATA = ["ADMIN", "geometry"]

# Select the relevant columns
gdf = gdf[READ_DATA]
gdf = gdf.rename(columns={"ADMIN": "country", "ADM0_A3": "country_code"})
gdf = gdf.reset_index(drop=True)
print(gdf.head())  # View the first five rows


def preprocess_map_data(map_data):
    """
    Add precomputed bounding boxes to each polygon in map_data.
    Each polygon becomes a dict: {"points": [...], "bbox": (min_x, min_y, max_x, max_y)}
    """

    for name in map_data:
        for data in map_data[name]:
            processed_polys = []
            for polygon in map_data[name][data]:
                xs = [p[0] for p in polygon]
                ys = [p[1] for p in polygon]
                bbox = (min(xs), min(ys), max(xs), max(ys))
                processed_polys.append({"points": polygon, "bbox": bbox})
            map_data[name][data] = processed_polys

# Convert the GeoDataFrame to a dictionary
data_dict = {}
for _, row in gdf.iterrows():
    country_name = row["country"]
    geometry = row["geometry"]
    
    if geometry.geom_type == "MultiPolygon":
        polygons = []
        for poly in geometry.geoms:
            projected = [mercator_projection(lon, lat) for lon, lat in poly.exterior.coords]
            polygons.append(projected)
    else:  # Single Polygon
        polygons = [[mercator_projection(lon, lat) for lon, lat in geometry.exterior.coords]]
    
    data_dict[country_name] = {
        "geometry": polygons
    }
preprocess_map_data(data_dict)

out = {"polygons": data_dict}
# Save the dictionary to a JSON file
with open(f"maps/World_m.json", "w") as json_file:
    json.dump(out, json_file, indent=4)

# View the first five rows