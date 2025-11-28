import folium
import binascii
from shapely import wkb
from shapely.geometry import mapping
import json

# Your five WKB‐hex polygons (SRID=4326)
wkb_hex_list = [
    # Your WKB hex strings here
]

# Decode and build GeoJSON features
features = []
for idx, wkb_hex in enumerate(wkb_hex_list, start=1):
    geom = wkb.loads(binascii.unhexlify(wkb_hex))
    geojson = mapping(geom)  # GeoJSON dict
    features.append({
        "type": "Feature",
        "properties": {"cluster_id": idx},
        "geometry": geojson
    })

# Create a FeatureCollection
fc = {"type": "FeatureCollection", "features": features}

# Compute map center as centroid of everything
all_coords = []
for feat in features:
    all_coords.extend(feat["geometry"]["coordinates"][0])
lon_center = sum(pt[0] for pt in all_coords) / len(all_coords)
lat_center = sum(pt[1] for pt in all_coords) / len(all_coords)

# Build Folium map
m = folium.Map(location=(lat_center, lon_center), zoom_start=14)

# Add each cluster Polygon with a popup
for feat in features:
    cluster_id = feat["properties"]["cluster_id"]
    gj = folium.GeoJson(
        feat,
        name=f"Cluster {cluster_id}",
        tooltip=f"Cluster {cluster_id}",
        style_function=lambda x: {
            "fillColor": None, "color": "blue", "weight": 2, "dashArray": "5, 5"
        }
    )
    gj.add_to(m)

folium.LayerControl().add_to(m)

# Save out
m.save("all_clusters.html")
print("Map written to all_clusters.html")
