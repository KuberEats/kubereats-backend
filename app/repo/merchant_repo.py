from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models.kubereats import MerchantInfo


class MerchantRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_approved_by_campus(self, campus: str, target_date: date):
        return (
            self.db.query(MerchantInfo)
            .filter(
                MerchantInfo.campus == campus,
                MerchantInfo.audit_status == 1,
            )
            .all()
        )

    def get_approved_by_id(self, merchant_id: int):
        return (
            self.db.query(MerchantInfo)
            .options(joinedload(MerchantInfo.menus))
            .filter(
                MerchantInfo.id == merchant_id,
                MerchantInfo.audit_status == 1,
            )
            .first()
        )
