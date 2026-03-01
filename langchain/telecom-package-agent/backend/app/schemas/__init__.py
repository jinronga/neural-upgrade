"""Pydantic schemas for API request and response models."""

from .user import (
    UserCreate,
    UserCurrentPackageResponse,
    UserPackageAssignRequest,
    UserPackagePageResponse,
    UserPackageRead,
    UserRead,
    UserUpdate,
)
from .package import (
    PackageCreate,
    PackagePageResponse,
    PackageRead,
    PackageRecommendRequest,
    PackageRecommendResponse,
    PackageUpdate,
)
from .benefit import (
    BenefitRead,
    BenefitClaimRequest,
    BenefitClaimResponse,
    BenefitInventoryResponse,
)
from .usage import UsageCurrentResponse, UsageRecordItem
from .chat import ChatMessageRequest, ChatMessageResponse

__all__ = [
    "UserRead",
    "UserCreate",
    "UserUpdate",
    "UserPackageAssignRequest",
    "UserPackageRead",
    "UserPackagePageResponse",
    "UserCurrentPackageResponse",
    "PackageRead",
    "PackageCreate",
    "PackageUpdate",
    "PackagePageResponse",
    "PackageRecommendRequest",
    "PackageRecommendResponse",
    "BenefitRead",
    "BenefitClaimRequest",
    "BenefitClaimResponse",
    "BenefitInventoryResponse",
    "UsageCurrentResponse",
    "UsageRecordItem",
    "ChatMessageRequest",
    "ChatMessageResponse",
]
