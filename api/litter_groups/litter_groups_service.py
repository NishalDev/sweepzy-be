from typing import List, Optional
from uuid import UUID
import requests
import time
from sklearn.cluster import DBSCAN
from shapely.ops import transform
import numpy as np
from sqlalchemy import text, or_, func
from sqlalchemy.orm import Session, joinedload, aliased
from shapely import wkb
from shapely.geometry import Point, MultiPoint, mapping, shape
from api.litter_reports.litter_reports_model import LitterReport
from api.litter_groups.litter_groups_model import LitterGroup
from api.litter_groups.litter_groups_schema import (
    ClusterSuggestion,
    LitterGroupCreate,
    LitterGroupUpdate
)
from api.litter_detections.litter_detections_service import determine_severity
import pyproj

# Set up transformer from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)
project_to4326 = pyproj.Transformer.from_crs(
    "EPSG:3857", "EPSG:4326", always_xy=True
).transform
class LitterGroupService:
    def __init__(self, db: Session):
        self.db = db

    # ─── CRUD ──────────────────────────────────────────────────────────────────
    def create_group(
        self,
        data: LitterGroupCreate,
        user_id: int
    ) -> LitterGroup:
        group_data = data.dict()
        # Construct WKT from lat/lng if provided
        lat = group_data.pop('lat', None)
        lng = group_data.pop('lng', None)
        if lat is not None and lng is not None:
            group_data['geom'] = f"SRID=4326;POINT({lng} {lat})"

        group = LitterGroup(**group_data, created_by=user_id)
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def list_groups(self, user_id: int) -> List[LitterGroup]:
        return (
            self.db
                .query(LitterGroup)
                .filter(
                    or_(
                        LitterGroup.created_by == user_id,
                        LitterGroup.group_type == 'public'
                    )
                )
                .all()
        )

    def get_group(
        self,
        group_id: UUID,
        user_id: int
    ) -> Optional[LitterGroup]:
        return (
            self.db
            .query(LitterGroup)
            .filter(
                LitterGroup.id == group_id,
                LitterGroup.created_by == user_id
            )
            .one_or_none()
        )

    def update_group(
        self,
        group_id: UUID,
        data: LitterGroupUpdate,
        user_id: int
    ) -> Optional[LitterGroup]:
        group = self.get_group(group_id, user_id)
        if not group:
            return None

        updates = data.dict(exclude_unset=True)
        lat = updates.pop('lat', None)
        lng = updates.pop('lng', None)
        if lat is not None and lng is not None:
            updates['geom'] = f"SRID=4326;POINT({lng} {lat})"

        for field, value in updates.items():
            setattr(group, field, value)

        self.db.commit()
        self.db.refresh(group)
        return group

    def delete_group(
        self,
        group_id: UUID,
        user_id: int
    ) -> bool:
        group = self.get_group(group_id, user_id)
        if not group:
            return False

        self.db.delete(group)
        self.db.commit()
        return True

    def list_available_groups(self) -> List[LitterGroup]:
        Group = aliased(LitterGroup)
        q = (
            self.db.query(
                Group,
                func.ST_Y(Group.geom).label("centroid_lat"),
                func.ST_X(Group.geom).label("centroid_lng"),
            )
            .filter(Group.is_locked.is_(False))
        )

        rows = q.all()
        results: List[LitterGroup] = []

        for grp, lat, lng in rows:
        # attach the computed lon/lat to each instance
            setattr(grp, "centroid_lat", float(lat) if lat is not None else None)
            setattr(grp, "centroid_lng", float(lng) if lng is not None else None)
            results.append(grp)

        return results

    def get_available_group_by_id(
        self,
        group_id: UUID
    ) -> Optional["LitterGroup"]:
        """
        Fetch an unlocked LitterGroup by ID, eagerly loading its reports and uploads.
        """
        return (
            self.db
              .query(LitterGroup)
              .options(
                  joinedload(LitterGroup.litter_reports)
                    .joinedload(LitterReport.upload)
              )
              .filter(
                  LitterGroup.id == group_id,
                  LitterGroup.is_locked == False
              )
              .one_or_none()
        )
        
    def reverse_geocode_city(lat: float, lon: float) -> Optional[str]:
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
            headers = {"User-Agent": "ecoCity/1.0"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("address", {}).get("city") or data.get("address", {}).get("town") or data.get("address", {}).get("village")
        except Exception as e:
            print("Reverse geocode error:", e)
        return None
    
    # ─── CLUSTERING SUGGESTIONS ───────────────────────────────────────────────
    def get_cluster_suggestions(
    self,
    eps: float = 500.0,
    minpts: int = 3
    ) -> List[ClusterSuggestion]:
        """
        Generate cluster suggestions from litter reports using DBSCAN.

        Handles:
        - No data to cluster
        - Noise filtering
        - Severity computation using determine_severity
        """

    # 1) Fetch all raw report centroids in metric coords (EPSG:3857)
        sql = text("""
            SELECT id,
                ST_X(ST_Transform(geom, 3857)) AS x,
                ST_Y(ST_Transform(geom, 3857)) AS y,
                severity
            FROM litter_reports
        """)
        rows = self.db.execute(sql).fetchall()

        if not rows:
            return []  # Nothing to cluster

        ids, xs, ys, severities = zip(*rows)
        coords = np.column_stack((xs, ys))

    # 2) Run DBSCAN clustering
        db = DBSCAN(eps=eps, min_samples=minpts).fit(coords)
        labels = db.labels_

        suggestions: List[ClusterSuggestion] = []

        for cluster_label in sorted(set(labels)):
            if cluster_label == -1:
                continue  # skip noise

            idx = np.where(labels == cluster_label)[0]
            if len(idx) == 0:
                continue

            points_3857 = [Point(coords[i]) for i in idx]
            multipoint = MultiPoint(points_3857)

            report_count = len(idx)

        # 3) Compute convex hull and bounding box in EPSG:3857
            hull_3857 = multipoint.convex_hull
            bbox_3857 = multipoint.envelope

        # 4) Reproject to EPSG:4326
            hull_4326 = transform(project_to4326, hull_3857)
            bbox_4326 = transform(project_to4326, bbox_3857)

            hull_geojson = mapping(hull_4326)
            bbox_geojson = mapping(bbox_4326)

        # 5) Compute severity using determine_severity
            minx, miny, maxx, maxy = bbox_3857.bounds
            bounding_boxes = [[minx, miny, maxx, maxy]]
            severity_str = determine_severity(
                total_count=report_count,
                bounding_boxes=bounding_boxes,
                image_size=None
            )

        # 6) Reproject member points to lat/lon
            transformer = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
            members = []
            for i in idx:
                try:
                    lon, lat = transformer.transform(xs[i], ys[i])
                    members.append({
                    'id': ids[i],
                    'point': {'type': 'Point', 'coordinates': (lon, lat)},
                    'severity': severities[i]
                    })
                except Exception:
                    continue  # skip failed transforms

        # 7) Assemble suggestion
            suggestions.append(
                ClusterSuggestion(
                    cluster_id=int(cluster_label),
                    report_count=report_count,
                    avg_severity=severity_str,
                        hull=hull_geojson,
                    bbox=bbox_geojson,
                    members=members
                )
            )

        return suggestions

    def reconcile_clusters(
    self,
    eps: float = 500.0,
    minpts: int = 3,
    system_user_id: int = 23
    ) -> List[LitterGroup]:
        """
        1) get_cluster_suggestions might return an empty list if no data matches your eps/minpts filters.
        2) Calling `zip(*rows)` on an empty list causes `ValueError: not enough values to unpack`.
        3) Your query parameters (eps/minpts) may be too restrictive, filtering out all points.
        4) Lack of logging makes it hard to know how many rows you actually fetched.
        """

    # 1) Fetch cluster suggestions (could be empty)
        suggestions = self.get_cluster_suggestions(eps, minpts)

    # 2) Guard against empty suggestions early
        if not suggestions:
        # nothing to cluster—return empty list (or you could raise an error)
            return []

        created: List[LitterGroup] = []

        for s in suggestions:
            geom_shape = shape(s.hull)
            lon, lat = geom_shape.centroid.x, geom_shape.centroid.y
            name = f"Cluster {s.cluster_id}"

            grp = self.db.query(LitterGroup).filter_by(name=name).first()
            if not grp:
                grp = LitterGroup(
                    name=name,
                    description=f"{s.report_count} reports",
                    group_type='public',
                    geom=f"SRID=4326;POINT({lon} {lat})",
                    severity=s.avg_severity,
                    created_by=system_user_id,
                    coverage_area=f"SRID=4326;{geom_shape.wkt}",
                    is_locked=False
                )
                self.db.add(grp)
                self.db.commit()
                self.db.refresh(grp)
            else:
                grp.description = f"{s.report_count} reports"
                self.db.commit()

            # Assign reports to this group
            (self.db.query(LitterReport)
            .filter(LitterReport.id.in_([m['id'] for m in s.members]))
            .update({
                'group_id': grp.id,
                'is_grouped': True
            }, synchronize_session=False)
        )
            self.db.commit()

            # Update group metadata
            grp.report_count = s.report_count
            grp.severity = s.avg_severity
            self.db.add(grp)
            self.db.commit()
            self.db.refresh(grp)

            created.append(grp)
            time.sleep(1)

        return created