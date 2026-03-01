from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_, select

from app.api.api_v1.dependencies import DBSessionDep
from app.models import Benefit, Package, User, UserBenefit, UserPackage
from app.schemas.benefit import BenefitRead
from app.schemas.package import PackageRead
from app.schemas.user import (
    UserCreate,
    UserCurrentPackageResponse,
    UserPackageAssignRequest,
    UserPackagePageResponse,
    UserPackageRead,
    UserPageResponse,
    UserRead,
    UserUpdate,
)
from app.services import user_package_service

router = APIRouter()


def _to_user_package_read(
    relation: UserPackage,
    user: User,
    now: datetime | None = None,
) -> UserPackageRead:
    package = relation.package
    if not package:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Package relation is missing",
        )

    return UserPackageRead(
        id=relation.id,
        user_id=relation.user_id,
        phone_number=user.phone_number,
        package_id=package.id,
        package_name=package.name,
        monthly_fee=float(package.monthly_fee),
        data_quota_gb=float(package.data_quota_gb),
        validity_days=int(package.validity_days),
        start_date=relation.start_date,
        end_date=relation.end_date,
        status=relation.status,
        auto_renew=bool(relation.auto_renew),
        is_current=user_package_service.is_current_user_package(relation, at=now),
    )


def _clean_user_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for key, value in payload.items():
        if isinstance(value, str):
            normalized = value.strip()
            cleaned[key] = normalized or None
        else:
            cleaned[key] = value
    return cleaned


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DBSessionDep) -> User:
    data = _clean_user_payload(payload.model_dump())
    phone_number = data.get("phone_number")
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is required"
        )
    if not data.get("status"):
        data["status"] = "active"

    if data.get("registered_at") is None:
        data["registered_at"] = datetime.utcnow()

    user = User(**data)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number or email already exists",
        )
    db.refresh(user)
    return user


@router.get("/", response_model=UserPageResponse)
def list_users(
    db: DBSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
) -> UserPageResponse:
    filters = []
    if keyword:
        keyword_like = f"%{keyword.strip()}%"
        if keyword_like != "%%":
            filters.append(
                or_(
                    User.phone_number.like(keyword_like),
                    User.name.like(keyword_like),
                )
            )

    total_stmt = select(func.count(User.id))
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = db.scalar(total_stmt) or 0

    stmt = select(User)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size)
    items = db.execute(stmt).scalars().all()

    return UserPageResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DBSessionDep) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DBSessionDep,
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    updates = _clean_user_payload(payload.model_dump(exclude_unset=True))
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    if "phone_number" in updates and not updates["phone_number"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is required"
        )
    if "status" in updates and not updates["status"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Status cannot be empty"
        )

    for field, value in updates.items():
        setattr(user, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number or email already exists",
        )
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DBSessionDep) -> Response:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{user_id}/packages", response_model=list[PackageRead])
def get_user_packages(
    user_id: int,
    db: DBSessionDep,
    include_history: bool = Query(default=False),
) -> list[Package]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    stmt = select(Package).join(UserPackage, UserPackage.package_id == Package.id).where(
        UserPackage.user_id == user_id
    )
    if not include_history:
        stmt = stmt.where(*user_package_service.active_user_package_filters())
    stmt = stmt.order_by(UserPackage.start_date.desc(), UserPackage.id.desc())
    result = db.execute(stmt).scalars().all()
    return result


@router.get("/{user_id}/packages/current", response_model=UserCurrentPackageResponse)
def get_current_user_package(
    user_id: int,
    db: DBSessionDep,
) -> UserCurrentPackageResponse:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    now = user_package_service.utc_now()
    relation = user_package_service.get_current_user_package(db, user_id, at=now)
    if not relation:
        return UserCurrentPackageResponse(item=None)
    return UserCurrentPackageResponse(item=_to_user_package_read(relation, user, now))


@router.get("/{user_id}/packages/history", response_model=UserPackagePageResponse)
def get_user_package_history(
    user_id: int,
    db: DBSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> UserPackagePageResponse:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    now = user_package_service.utc_now()
    items, total = user_package_service.list_user_packages_history(
        db, user_id=user_id, page=page, page_size=page_size
    )
    return UserPackagePageResponse(
        items=[_to_user_package_read(item, user, now) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/{user_id}/packages/assign",
    response_model=UserPackageRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_user_package(
    user_id: int,
    payload: UserPackageAssignRequest,
    db: DBSessionDep,
) -> UserPackageRead:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    package = db.get(Package, payload.package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )
    if not package.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Package is inactive and cannot be assigned",
        )

    relation = user_package_service.assign_package_to_user(
        db,
        user=user,
        package=package,
        effective_from=payload.effective_from,
        auto_renew=payload.auto_renew,
    )
    db.commit()
    db.refresh(relation)
    return _to_user_package_read(relation, user, user_package_service.utc_now())


@router.get("/{user_id}/benefits", response_model=list[BenefitRead])
def get_user_benefits(user_id: int, db: DBSessionDep) -> list[Benefit]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    stmt = (
        select(Benefit)
        .join(UserBenefit, UserBenefit.benefit_id == Benefit.id)
        .where(UserBenefit.user_id == user_id)
    )
    result = db.execute(stmt).scalars().all()
    return result
