from sqlalchemy.orm import Session

from app.models.kubereats import MerchantInfo


class CommitteeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_merchant_by_id(self, merchant_id: int) -> MerchantInfo | None:
        return (
            self.db.query(MerchantInfo).filter(MerchantInfo.id == merchant_id).first()
        )

    def list_pending_merchants(self) -> list[MerchantInfo]:
        return (
            self.db.query(MerchantInfo)
            .filter(MerchantInfo.audit_status == 0)
            .order_by(MerchantInfo.created_at.asc())
            .all()
        )

    def list_all_merchants(self) -> list[MerchantInfo]:
        return (
            self.db.query(MerchantInfo).order_by(MerchantInfo.created_at.desc()).all()
        )

    def update_audit_status(
        self, merchant: MerchantInfo, new_status: int
    ) -> MerchantInfo:
        merchant.audit_status = new_status
        self.db.flush()
        return merchant

    def update_merchant(self, merchant: MerchantInfo, data: dict) -> MerchantInfo:
        for key, value in data.items():
            setattr(merchant, key, value)
        self.db.flush()
        return merchant

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
