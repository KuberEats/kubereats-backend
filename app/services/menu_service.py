from fastapi import HTTPException

from app.repo.menu_repo import MenuRepository
from app.repo.merchant_repo import MerchantRepository


class MenuService:
    def __init__(
        self,
        menu_repo: MenuRepository,
        merchant_repo: MerchantRepository,
    ):
        self.menu_repo = menu_repo
        self.merchant_repo = merchant_repo

    def list_menu_items(self, merchant_id: int):
        merchant = self.merchant_repo.get_approved_by_id(merchant_id)

        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")

        return self.menu_repo.list_by_merchant_id(merchant_id)
