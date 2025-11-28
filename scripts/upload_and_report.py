import os
import csv
import requests
from io import BytesIO
from PIL import Image
import piexif

# EXIF helper
def get_exif_lat_lon(img_path):
    try:
        img = Image.open(img_path)
        exif_dict = piexif.load(img.info.get('exif', b''))
        gps = exif_dict.get('GPS', {})
        if not gps:
            return None, None

        def _convert_to_degrees(value):
            d, m, s = value
            return d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600

        lat = lon = None
        if piexif.GPSIFD.GPSLatitude in gps and piexif.GPSIFD.GPSLatitudeRef in gps:
            lat = _convert_to_degrees(gps[piexif.GPSIFD.GPSLatitude])
            if gps[piexif.GPSIFD.GPSLatitudeRef] != b'N':
                lat = -lat
        if piexif.GPSIFD.GPSLongitude in gps and piexif.GPSIFD.GPSLongitudeRef in gps:
            lon = _convert_to_degrees(gps[piexif.GPSIFD.GPSLongitude])
            if gps[piexif.GPSIFD.GPSLongitudeRef] != b'E':
                lon = -lon
        return lat, lon
    except Exception as e:
        print(f"⚠️ Failed to read EXIF for {img_path}: {e}")
        return None, None

# CONFIG
API_URL       = "http://localhost:8000/api/uploads/{session_id}/full"
SESSION_ID    = "f3f075ee-6b80-44d7-9e5b-804486ba91a3"
TOKEN         = "Bearer eyJxyzisuks2xanUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MjQsInVzZXJuYW1lIjoidXNlciIsInJvbGVzIjpbInVzZXIiXSwicGVybWlzc2lvbnMiOlsidmlld19kYXNoYm9hcmQiLCJjcmVhdGVfcG9zdHMiXSwiZXhwIjoxNzUzMjgyMDk0fQ.8ArNwh5AE0PTGAaftMn5H99WjDoqCkDeUO8G8"
IMAGE_FOLDER  = os.path.abspath("../../EcoCity/images")

print(f"📂 IMAGE_FOLDER: {IMAGE_FOLDER}")
if not os.path.isdir(IMAGE_FOLDER):
    print(f"❌ ERROR: IMAGE_FOLDER does not exist: {IMAGE_FOLDER}")
    exit(1)

image_files = [
    f for f in os.listdir(IMAGE_FOLDER)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]
print(f"📸 Found {len(image_files)} image files")

headers = { "Authorization": TOKEN }
results = []

for filename in image_files:
    img_path = os.path.join(IMAGE_FOLDER, filename)
    print(f"\n📷 Processing {filename}...")

    lat, lon = get_exif_lat_lon(img_path)
    if lat is None or lon is None:
        msg = "No GPS data"
        print(f"⛔ Skipping {filename}: {msg}")
        results.append([filename, "", "", "skipped", msg])
        continue

    with open(img_path, "rb") as f:
        files = {"file": (filename, f, "image/jpeg")}
        data  = {"latitude": lat, "longitude": lon}
        url   = API_URL.format(session_id=SESSION_ID)
        resp  = requests.post(url, headers=headers, files=files, data=data)

    # ——— Handle new endpoint statuses ———
    if resp.status_code == 409:
        # duplicate detected by pHash
        detail = resp.json().get("detail", {})
        ids   = detail.get("ids", [])
        msg   = f"Duplicate (phash) of reports {ids}"
        print(f"⚠️ {filename}: {msg}")
        results.append([filename, lat, lon, "duplicate", msg])

    elif resp.status_code == 202:
        body = resp.json()
        report_id = body.get("id")
        job_id    = body.get("jobId")
        msg = f"Enqueued report {report_id} (job {job_id})"
        print(f"✅ {filename}: {msg}")
        results.append([filename, lat, lon, "enqueued", msg])

    else:
        # any other error
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text
        msg = f"Error {resp.status_code}: {detail}"
        print(f"🚨 {filename} failed: {msg}")
        results.append([filename, lat, lon, "error", msg])

# WRITE CSV SUMMARY
csv_path = os.path.join(IMAGE_FOLDER, "upload_results.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Filename", "Latitude", "Longitude", "Status", "Message"])
    writer.writerows(results)

print(f"\n📄 Upload summary saved to: {csv_path}")
