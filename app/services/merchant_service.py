from datetime import date

from fastapi import HTTPException

from app.repo.merchant_repo import MerchantRepository
from app.schemas.merchant import MerchantSortKey


class MerchantService:
    def __init__(self, merchant_repo: MerchantRepository):
        self.merchant_repo = merchant_repo

    def list_restaurants_for_order_page(
        self,
        campus: str,
        target_date: date,
        sort_by: MerchantSortKey,
    ):
        merchants = self.merchant_repo.list_approved_by_campus(campus, target_date)

        if sort_by == "people":
            return sorted(merchants, key=lambda merchant: merchant.order_count, reverse=True)

        if sort_by == "popular":
            return sorted(merchants, key=lambda merchant: merchant.rating, reverse=True)

        return sorted(
            merchants,
            key=lambda merchant: float(merchant.rating) * 20 + merchant.order_count,
            reverse=True,
        )

    def get_merchant_detail(self, merchant_id: int):
        merchant = self.merchant_repo.get_approved_by_id(merchant_id)

        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")

        return merchant
