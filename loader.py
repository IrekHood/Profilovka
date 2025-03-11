import geopandas as gpd

# Load the shapefile
gdf = gpd.read_file("data/high quality/political/countries/ne_10m_admin_0_countries.shp")

print(gdf[["CONTINENT"]])

# View the first five rows
print(gdf.head())