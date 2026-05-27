from sqlalchemy.orm import Session, joinedload

from app.models.kubereats import Menu, MerchantInfo, Order, OrderItem, UserInfo


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

    def list_recent_orders_by_user(self, user_id: int, limit: int = 10):
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.items)
                .joinedload(OrderItem.menu)
                .joinedload(Menu.merchant),
            )
            .filter(Order.user_id == user_id)
            .order_by(Order.order_time.desc())
            .limit(limit)
            .all()
        )

    def list_candidate_merchants(self, campus: str | None = None):
        query = (
            self.db.query(MerchantInfo)
            .options(joinedload(MerchantInfo.menus))
            .filter(MerchantInfo.audit_status == 1)
        )

        if campus:
            query = query.filter(MerchantInfo.campus == campus)

        return query.all()

    def list_approved_merchants(self, campus: str | None = None):
        return self.list_candidate_merchants(campus)

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
