from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.api_v1.dependencies import DBSessionDep
from app.models import Benefit, Package, User, UserBenefit, UserPackage
from app.schemas.user import UserRead
from app.schemas.benefit import BenefitRead
from app.schemas.package import PackageRead

router = APIRouter()


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DBSessionDep) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/{user_id}/packages", response_model=list[PackageRead])
def get_user_packages(user_id: int, db: DBSessionDep) -> list[Package]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    stmt = (
        select(Package)
        .join(UserPackage, UserPackage.package_id == Package.id)
        .where(UserPackage.user_id == user_id)
    )
    result = db.execute(stmt).scalars().all()
    return result


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

