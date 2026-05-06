from sqlalchemy.orm import Session

from app.models.kubereats import Menu


class MenuRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_merchant_id(self, merchant_id: int):
        return self.db.query(Menu).filter(Menu.merchant_id == merchant_id).all()

    def get_by_id(self, menu_id: int):
        return self.db.query(Menu).filter(Menu.id == menu_id).first()
