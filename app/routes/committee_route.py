from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.core.metrics import committee_merchant_approved_total, committee_merchant_rejected_total
from app.database import get_db
from app.models.kubereats import UserInfo
from app.repo.committee_repo import CommitteeRepository
from app.schemas.committee import AuditResultResponse, MerchantReviewResponse
from app.services.committee_service import CommitteeService

router = APIRouter(prefix="/committee", tags=["Committee"])

committee_role = require_role("committee")


def get_committee_service(db: Session = Depends(get_db)):
    return CommitteeService(committee_repo=CommitteeRepository(db))


@router.get("/merchants/pending", response_model=list[MerchantReviewResponse])
def list_pending_merchants(
    current_user: UserInfo = Depends(committee_role),
    service: CommitteeService = Depends(get_committee_service),
):
    return service.list_pending_merchants()


@router.get("/merchants", response_model=list[MerchantReviewResponse])
def list_all_merchants(
    current_user: UserInfo = Depends(committee_role),
    service: CommitteeService = Depends(get_committee_service),
):
    return service.list_all_merchants()


@router.patch("/merchants/{merchant_id}/approve", response_model=AuditResultResponse)
def approve_merchant(
    merchant_id: int,
    current_user: UserInfo = Depends(committee_role),
    service: CommitteeService = Depends(get_committee_service),
):
    result = service.approve_merchant(merchant_id)
    committee_merchant_approved_total.inc()
    return result


@router.patch("/merchants/{merchant_id}/reject", response_model=AuditResultResponse)
def reject_merchant(
    merchant_id: int,
    current_user: UserInfo = Depends(committee_role),
    service: CommitteeService = Depends(get_committee_service),
):
    result = service.reject_merchant(merchant_id)
    committee_merchant_rejected_total.inc()
    return result
