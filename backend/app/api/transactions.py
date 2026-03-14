from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.db import get_db
from app.schemas.summary import SummaryQueryParams, SummaryResponse
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services.summary import get_expense_summary
from app.services.transaction import create_transaction

router = APIRouter(prefix="/transactions", dependencies=[Depends(require_api_key)])


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    params: Annotated[SummaryQueryParams, Query()],
    db: AsyncSession = Depends(get_db),
) -> SummaryResponse:
    return await get_expense_summary(db, params.month, params.year, params.group_by)


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction_route(
    body: TransactionCreate,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    try:
        return await create_transaction(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
