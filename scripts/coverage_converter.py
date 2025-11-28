from shapely import wkb
from shapely.geometry import mapping
import binascii

# Your hex-encoded WKB polygon
wkb_hex = ""  # put your WKB hex string here, e.g. "0103000000..."

# Decode hex to binary
wkb_bytes = binascii.unhexlify(wkb_hex)

# Load Shapely geometry
geom = wkb.loads(wkb_bytes)

# Output as WKT
print("WKT:", geom.wkt)

# Output as GeoJSON
print("GeoJSON:", mapping(geom))
