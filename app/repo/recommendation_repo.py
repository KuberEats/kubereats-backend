from sqlalchemy.orm import Session, joinedload

from app.models.kubereats import Menu, MerchantInfo, UserInfo


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int):
        return (
            self.db.query(UserInfo)
            .options(joinedload(UserInfo.tags))
            .filter(UserInfo.id == user_id)
            .first()
        )

    def list_approved_merchants(self, campus: str | None = None):
        query = self.db.query(MerchantInfo).filter(MerchantInfo.audit_status == 1)

        if campus:
            query = query.filter(MerchantInfo.campus == campus)

        return query.all()

    def list_candidate_menus(
        self,
        campus: str | None = None,
        merchant_id: int | None = None,
    ):
        query = (
            self.db.query(Menu)
            .join(Menu.merchant)
            .options(joinedload(Menu.merchant))
            .filter(MerchantInfo.audit_status == 1)
        )

        if campus:
            query = query.filter(MerchantInfo.campus == campus)

        if merchant_id:
            query = query.filter(Menu.merchant_id == merchant_id)

        return query.all()
