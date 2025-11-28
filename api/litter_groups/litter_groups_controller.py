from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from sqlalchemy import text
from api.litter_groups.litter_groups_service import LitterGroupService
from api.litter_groups.litter_groups_schema import (
    ClusterSuggestion,
    LitterGroupRead,
    LitterGroupCreate,
    LitterGroupUpdate,
)
from api.litter_reports.litter_reports_schema import LitterReportResponse
from config.database import get_db
class LitterGroupController:

    @staticmethod
    def list_groups(
        db: Session,
        user_id: int
    ) -> List[LitterGroupRead]:
        svc = LitterGroupService(db)
        groups = svc.list_groups(user_id)
        return [LitterGroupRead.from_orm(g) for g in groups]

    @staticmethod
    def get_group(
        group_id: UUID,
        db: Session,
        user_id: int
    ) -> LitterGroupRead:
        svc = LitterGroupService(db)
        group = svc.get_group(group_id, user_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        return LitterGroupRead.from_orm(group)

    @staticmethod
    def create_group(
        payload: LitterGroupCreate,
        db: Session,
        user_id: int
    ) -> LitterGroupRead:
        svc = LitterGroupService(db)
        group = svc.create_group(payload, user_id)
        return LitterGroupRead.from_orm(group)

    @staticmethod
    def update_group(
        group_id: UUID,
        payload: LitterGroupUpdate,
        db: Session,
        user_id: int
    ) -> LitterGroupRead:
        svc = LitterGroupService(db)
        group = svc.update_group(group_id, payload, user_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found or not yours")
        return LitterGroupRead.from_orm(group)

    @staticmethod
    def delete_group(
        group_id: UUID,
        db: Session,
        user_id: int
    ):
        svc = LitterGroupService(db)
        success = svc.delete_group(group_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Group not found or not yours")
        return {"detail": "Group deleted"}

    # ─── Clustering suggestions ────────────────────────────────────────────────

    @staticmethod
    def list_suggestions(
        db: Session
    ) -> List[ClusterSuggestion]:
        svc = LitterGroupService(db)
        return svc.get_cluster_suggestions()

    @staticmethod
    def create_from_suggestion(
        cluster_id: int,
        payload: LitterGroupCreate,
        db: Session,
        user_id: int
    ) -> LitterGroupRead:
        svc = LitterGroupService(db)
        group = svc.create_group_from_suggestion(cluster_id, payload, user_id)
        if not group:
            raise HTTPException(status_code=404, detail="Cluster not found")
        return LitterGroupRead.from_orm(group)

    @staticmethod
    def list_available_groups(db: Session) -> List[LitterGroupRead]:
        svc = LitterGroupService(db)
        groups = svc.list_available_groups()
        return [LitterGroupRead.from_orm(g) for g in groups]

    @staticmethod
    def get_available_group_by_id(
        group_id: UUID,
        db: Session = Depends(get_db)
    ) -> LitterGroupRead:
        svc = LitterGroupService(db)
        group = svc.get_available_group_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Available group not found")

        reports = group.litter_reports or []
        report_ids = [r.id for r in reports]
        total_count = len(report_ids)

        # Sum detections
        if report_ids:
            total_litter_count = db.execute(
                text("""
                    SELECT COALESCE(SUM(total_litter_count), 0)
                      FROM litter_detections
                     WHERE litter_report_id = ANY(:report_ids)
                """), {"report_ids": report_ids}
            ).scalar()
        else:
            total_litter_count = 0

        # Inject image_url
        for r in reports:
            if r.upload and getattr(r.upload, 'file_url', None):
                setattr(r, 'image_url', r.upload.file_url)

        # Build DTOs
        litter_report_responses = [
            LitterReportResponse.from_orm(r)
                .model_copy(update={"image_url": getattr(r, 'image_url', None)})
            for r in reports
        ]

        # Return
        return LitterGroupRead.from_orm(group).model_copy(
            update={
                "litter_reports": litter_report_responses,
                "total_count": total_count,
                "total_litter_count": total_litter_count
            }
        )