# utils/geoutils.py
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from api.user.user_model import User
import numpy as np
import datetime
import faiss
from PIL import Image
import os
import io
import warnings
from concurrent.futures import ThreadPoolExecutor
from geoalchemy2 import Geography
# Suppress any unwanted model warnings
warnings.filterwarnings(
    "ignore",
    message="`input_shape` is undefined or non-square",
    category=UserWarning,
)

# ThreadPool for controlled concurrency
_executor = ThreadPoolExecutor(max_workers=2)

# Eagerly load a lightweight vision model (MobileNetV3Small)
from keras.applications import MobileNetV3Small
from keras.applications.mobilenet_v3 import preprocess_input as m3_pre
_embedding_model = MobileNetV3Small(
    include_top=False,
    pooling='avg',
    weights='imagenet',
    input_shape=(160, 160, 3),  # reduce spatial dims
    alpha=1.0,
    minimalistic=False,                  # shrink width
)
# Dynamically determine embedding dimension
_EMB_DIM: int = _embedding_model.output_shape[-1]

# Singleton for FAISS index
_faiss_index: faiss.Index = None

# Model loader
def load_embedding_model() -> MobileNetV3Small:
    """Return the singleton embedding model."""
    return _embedding_model

# FAISS index loader with dynamic dim
def load_faiss_index(path: str = None) -> faiss.Index:
    """
    Lazy-load (or create) an IndexFlatIP+IDMap2 FAISS index matching the
    embedding dimension. Resets if on-disk index dims mismatch.
    """
    global _faiss_index
    if path is None:
        path = os.getenv('FAISS_INDEX_PATH', 'faiss.index')
    dim = _EMB_DIM

    if _faiss_index is None:
        if os.path.exists(path):
            idx = faiss.read_index(path)
            if getattr(idx, 'd', None) != dim:
                base = faiss.IndexFlatIP(dim)
                idx = faiss.IndexIDMap2(base)
                faiss.write_index(idx, path)
        else:
            base = faiss.IndexFlatIP(dim)
            idx = faiss.IndexIDMap2(base)
        _faiss_index = idx

    return _faiss_index

# Async indexing
def index_embedding_async(report_id: int, emb: np.ndarray, path: str = None):
    """
    Adds a normalized embedding to the FAISS IDMap2 in background,
    tagging it with report_id.
    """
    if path is None:
        path = os.getenv('FAISS_INDEX_PATH', 'faiss.index')

    def worker():
        idx = load_faiss_index(path)
        arr = emb.astype('float32').reshape(1, -1)
        ids = np.array([report_id], dtype='int64')
        idx.add_with_ids(arr, ids)
        faiss.write_index(idx, path)

    _executor.submit(worker)

# Image preprocessing
def preprocess_image(img_data: bytes | io.BytesIO) -> np.ndarray:
    """
    Opens raw image bytes or file-like, resizes to 224x224 RGB,
    applies MobileNetV3 preprocess_input.
    """
    if isinstance(img_data, (bytes, bytearray)):
        img_io = io.BytesIO(img_data)
    else:
        img_io = img_data

    img = Image.open(img_io).resize((160, 160)).convert("RGB")
    arr = np.array(img)
    return m3_pre(arr)

# Geospatial helpers
def get_nearby_users(
    lat: float,
    lng: float,
    db: Session,
    radius_km: float = 5.0
) -> List[User]:
    """Return users within radius_km of (lat, lng)."""
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    return (
        db.query(User)
          .filter(
              func.ST_DWithin(
                  User.location.cast('geography'),
                  point.cast('geography'),
                  radius_km * 1000
              )
          )
          .all()
    )

# Haversine distance
def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute Haversine distance in meters."""
    import math
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Spatio-temporal query
def find_spatio_temporal(
    db: Session,
    model,
    lat: float,
    lng: float,
    ts: datetime.datetime,
    radius_m: float = 50,
    window_s: int = 1800
) -> List[int]:
    """
    Return IDs of reports within `radius_m` meters and ±`window_s` seconds of ts,
    using PostGIS geography for true-meter distances.
    """
    # Create a POINT(lng, lat) in SRID 4326, then cast to Geography
    point_geo = func.ST_SetSRID(
        func.ST_MakePoint(lng, lat),
        4326
    ).cast(Geography())

    start = ts - datetime.timedelta(seconds=window_s)
    end   = ts + datetime.timedelta(seconds=window_s)

    q = (
        db.query(model.id)
          .filter(
              model.created_at.between(start, end),
              # Cast stored geom column to Geography for meter-based ST_DWithin
              func.ST_DWithin(
                  model.geom.cast(Geography()),
                  point_geo,
                  radius_m
              )
          )
    )
    return [r.id for r in q.all()]