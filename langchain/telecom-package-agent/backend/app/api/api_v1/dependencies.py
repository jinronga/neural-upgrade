from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db


DBSessionDep = Annotated[Session, Depends(get_db)]

