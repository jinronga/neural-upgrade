from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select

from app.api.api_v1.dependencies import DBSessionDep
from app.models import Package
from app.schemas.package import (
    PackageCreate,
    PackagePageResponse,
    PackageRead,
    PackageRecommendRequest,
    PackageRecommendResponse,
    PackageUpdate,
)

router = APIRouter()


@router.get("", response_model=list[PackageRead])
def list_packages(
    db: DBSessionDep,
    include_inactive: bool = Query(default=False),
) -> list[Package]:
    stmt = select(Package)
    if not include_inactive:
        stmt = stmt.where(Package.is_active.is_(True))
    stmt = stmt.order_by(Package.id.asc())
    result = db.execute(stmt).scalars().all()
    return result


@router.get("/paged", response_model=PackagePageResponse)
def list_packages_paged(
    db: DBSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    include_inactive: bool = Query(default=True),
) -> PackagePageResponse:
    filters = []
    if not include_inactive:
        filters.append(Package.is_active.is_(True))

    if keyword:
        keyword_like = f"%{keyword.strip()}%"
        if keyword_like != "%%":
            filters.append(
                or_(
                    Package.name.like(keyword_like),
                    Package.description.like(keyword_like),
                )
            )

    total_stmt = select(func.count(Package.id))
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = db.scalar(total_stmt) or 0

    stmt = select(Package)
    if filters:
        stmt = stmt.where(*filters)
    stmt = (
        stmt.order_by(Package.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(stmt).scalars().all()

    return PackagePageResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=PackageRead, status_code=status.HTTP_201_CREATED)
def create_package(payload: PackageCreate, db: DBSessionDep) -> Package:
    package = Package(**payload.model_dump())
    db.add(package)
    db.commit()
    db.refresh(package)
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


@router.get("/{package_id}", response_model=PackageRead)
def get_package(package_id: int, db: DBSessionDep) -> Package:
    package = db.get(Package, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )
    return package


@router.put("/{package_id}", response_model=PackageRead)
def update_package(
    package_id: int,
    payload: PackageUpdate,
    db: DBSessionDep,
) -> Package:
    package = db.get(Package, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    for field, value in updates.items():
        setattr(package, field, value)

    db.commit()
    db.refresh(package)
    return package


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(package_id: int, db: DBSessionDep) -> Response:
    package = db.get(Package, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )

    db.delete(package)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
