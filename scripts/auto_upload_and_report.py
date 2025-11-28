import os
from sqlalchemy.orm import Session
from fastapi import UploadFile
from PIL import Image
import piexif

from api.litter_reports import litter_reports_service
from api.litter_detections.litter_detections_service import create_litter_detection
from database.session import get_db  # Adjust this if your path differs

UPLOADS_DIR = os.path.join(os.getcwd(), "uploads")
USER_ID = 44  # Change as needed


def get_exif_location(img_path):
    try:
        exif_dict = piexif.load(img_path)
        gps = exif_dict.get("GPS", {})
        if not gps:
            return None, None

        def _to_deg(value):
            d = value[0][0] / value[0][1]
            m = value[1][0] / value[1][1]
            s = value[2][0] / value[2][1]
            return d + m / 60 + s / 3600

        lat = _to_deg(gps[piexif.GPSIFD.GPSLatitude])
        lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef, b'N').decode()
        if lat_ref != 'N':
            lat = -lat

        lon = _to_deg(gps[piexif.GPSIFD.GPSLongitude])
        lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef, b'E').decode()
        if lon_ref != 'E':
            lon = -lon

        return lat, lon

    except Exception as e:
        print(f"⚠️ EXIF read error on {os.path.basename(img_path)}: {e}")
        return None, None


class DummyUploadFile:
    def __init__(self, path, filename):
        self.file = open(path, "rb")
        self.filename = filename


def main():
    db: Session = next(get_db())

    for fname in os.listdir(UPLOADS_DIR):
        fpath = os.path.join(UPLOADS_DIR, fname)
        if not os.path.isfile(fpath):
            continue

        lat, lon = get_exif_location(fpath)
        if lat is None or lon is None:
            print(f"No EXIF GPS for {fname}. Skipping.")
            continue

        upload_file = DummyUploadFile(fpath, fname)

        try:
            saved_path = litter_reports_service.save_uploaded_file(upload_file)
        finally:
            upload_file.file.close()

        report_data = {
            "user_id": USER_ID,
            "latitude": lat,
            "longitude": lon,
            "image_path": saved_path,
            "status": "pending"
        }

        try:
            report = litter_reports_service.create_litter_report(db, report_data)
            if report:
                print(f"✅ Report created for {fname} at ({lat}, {lon})")

                try:
                    create_litter_detection(db, report.id)
                    print(f"🧠 Detection completed for report {report.id}")
                except Exception as e:
                    print(f"❌ Detection failed for report {report.id}: {e}")

            else:
                print(f"❌ Failed to create report for {fname}")

        except Exception as e:
            print(f"❌ create_litter_report failed with payload: {report_data}")
            print(f"❌ Exception: {e}")
            print(f"Failed to create report for {fname}")


if __name__ == "__main__":
    main()
