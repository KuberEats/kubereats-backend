from fastapi import HTTPException, status

from app.models.kubereats import MerchantInfo
from app.repo.committee_repo import CommitteeRepository


class CommitteeService:
    AUDIT_PENDING = 0
    AUDIT_APPROVED = 1
    AUDIT_REJECTED = 2

    def __init__(self, committee_repo: CommitteeRepository):
        self.committee_repo = committee_repo

    def list_pending_merchants(self) -> list[MerchantInfo]:
        return self.committee_repo.list_pending_merchants()

    def list_all_merchants(self) -> list[MerchantInfo]:
        return self.committee_repo.list_all_merchants()

    def approve_merchant(self, merchant_id: int) -> dict:
        merchant = self._get_pending_merchant(merchant_id)
        self.committee_repo.update_audit_status(merchant, self.AUDIT_APPROVED)
        self.committee_repo.commit()
        return {
            "id": merchant.id,
            "merchant_name": merchant.merchant_name,
            "audit_status": merchant.audit_status,
            "message": "Merchant approved successfully",
        }

    def reject_merchant(self, merchant_id: int) -> dict:
        merchant = self._get_pending_merchant(merchant_id)
        self.committee_repo.update_audit_status(merchant, self.AUDIT_REJECTED)
        self.committee_repo.commit()
        return {
            "id": merchant.id,
            "merchant_name": merchant.merchant_name,
            "audit_status": merchant.audit_status,
            "message": "Merchant rejected",
        }

    def _get_pending_merchant(self, merchant_id: int) -> MerchantInfo:
        merchant = self.committee_repo.get_merchant_by_id(merchant_id)

        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found",
            )

        if merchant.audit_status != self.AUDIT_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Merchant has already been reviewed",
            )

        return merchant
