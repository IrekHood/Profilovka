import geopandas as gpd
import json
import math


# load the json
with open("maps/World_s.json", "r") as f:
    data = json.load(f)

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


data["new_polygons"] = {}
# Save the dictionary to a JSON file
with open(f"maps/World_s.json", "w") as json_file:
    json.dump(data, json_file, indent=4)

# View the first five rows