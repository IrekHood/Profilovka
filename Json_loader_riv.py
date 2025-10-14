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
gdf = gpd.read_file("data/low_quality/physical/ne_110m_rivers_lake_centerlines")
gdf = gdf.dissolve(by="name_en").reset_index()
READ_DATA = ["name_en", "geometry"]
print(gdf.head())  # View the first five rows
print(gdf.columns)
# Select the relevant columns
gdf = gdf[READ_DATA]
gdf = gdf.reset_index(drop=True)

# load the json
# Load the original JSON
with open("maps/World_s.json", "r") as f:
    data = json.load(f)



def preprocess_map_data(map_data):
    """
    Add precomputed bounding boxes to each polygon in map_data.
    Each polygon becomes a dict: {"points": [...], "bbox": (min_x, min_y, max_x, max_y)}
    """

    for name in map_data:
        print(name, map_data[name]["geometry"])
        processed_polys = []
        for polygon in map_data[name]["geometry"]:
            print(polygon)
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            processed_polys.append({"points": polygon, "bbox": bbox})
        map_data[name]['geometry'] = processed_polys

# Convert the GeoDataFrame to a dictionary
data_dict = {}
for _, row in gdf.iterrows():
    country_name = row["name_en"]
    print(country_name)
    geometry = row["geometry"]
    if geometry and geometry.geom_type == "LineString":
        points = [[mercator_projection(lon, lat) for lon, lat in list(geometry.coords)]]

    elif geometry and geometry.geom_type == "MultiLineString":
        # list of lists of coordinates
        points = [
            [mercator_projection(lon, lat) for lon, lat in line.coords]
            for line in geometry.geoms
        ]

    elif geometry:
        print(geometry.geom_type)
        exit()

    data_dict[country_name] = {
        "geometry": points
    }
preprocess_map_data(data_dict)
print(data_dict)
out = {"lines": data_dict}
data["lines"] = data_dict

# Save the dictionary to a JSON file
with open(f"maps/World_s.json", "w") as json_file:
    json.dump(data, json_file, indent=4)

# View the first five rows