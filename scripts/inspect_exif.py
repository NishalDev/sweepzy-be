import piexif
from pprint import pprint

path = r""# Path to your image file
exif_dict = piexif.load(path)

print("— GPS IFD —")
pprint(exif_dict.get("GPS", {}))

print("\n— 0th IFD —")
pprint(exif_dict.get("0th", {}))

print("\n— Exif IFD —")
pprint(exif_dict.get("Exif", {}))
