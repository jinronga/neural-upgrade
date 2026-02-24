from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.api_v1.dependencies import DBSessionDep
from app.models import Package
from app.schemas.package import (
    PackageRead,
    PackageRecommendRequest,
    PackageRecommendResponse,
)

router = APIRouter()


@router.get("", response_model=list[PackageRead])
def list_packages(db: DBSessionDep) -> list[Package]:
    stmt = select(Package).where(Package.is_active.is_(True))
    result = db.execute(stmt).scalars().all()
    return result


@router.get("/{package_id}", response_model=PackageRead)
def get_package(package_id: int, db: DBSessionDep) -> Package:
    package = db.get(Package, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )
    return package


@router.post("/recommend", response_model=PackageRecommendResponse)
def recommend_packages(
    payload: PackageRecommendRequest, db: DBSessionDep
) -> PackageRecommendResponse:
    stmt = select(Package).where(Package.is_active.is_(True))

    if payload.min_data_gb is not None:
        stmt = stmt.where(Package.data_quota_gb >= payload.min_data_gb)

    if payload.monthly_budget is not None:
        stmt = stmt.where(Package.monthly_fee <= payload.monthly_budget)

    stmt = stmt.order_by(Package.monthly_fee.asc()).limit(payload.limit)

    packages = db.execute(stmt).scalars().all()
    return PackageRecommendResponse(recommendations=packages)

