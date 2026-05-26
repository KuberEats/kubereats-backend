import re

from fastapi import HTTPException

from app.repo.recommendation_repo import RecommendationRepository


class RecommendationService:
    def __init__(self, recommendation_repo: RecommendationRepository):
        self.recommendation_repo = recommendation_repo

    def recommend_merchants(
        self,
        user_id: int,
        campus: str | None,
        limit: int,
    ):
        user = self._get_user_or_404(user_id)
        merchants = self.recommendation_repo.list_approved_merchants(campus)
        user_terms = self._build_user_terms(user)

        ranked_merchants = [
            self._serialize_merchant(merchant, user_terms) for merchant in merchants
        ]

        return sorted(
            ranked_merchants,
            key=lambda merchant: merchant["score"],
            reverse=True,
        )[:limit]

    def recommend_menus(
        self,
        user_id: int,
        campus: str | None,
        merchant_id: int | None,
        limit: int,
    ):
        user = self._get_user_or_404(user_id)
        menus = self.recommendation_repo.list_candidate_menus(campus, merchant_id)
        user_terms = self._build_user_terms(user)

        ranked_menus = [self._serialize_menu(menu, user_terms) for menu in menus]

        return sorted(
            ranked_menus,
            key=lambda menu: menu["score"],
            reverse=True,
        )[:limit]

    def _get_user_or_404(self, user_id: int):
        user = self.recommendation_repo.get_user_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    def _build_user_terms(self, user):
        tag_terms = {tag.name.lower() for tag in user.tags}
        history_terms = self._tokenize(user.history_records or "")
        return tag_terms | history_terms

    def _serialize_merchant(self, merchant, user_terms: set[str]):
        merchant_terms = self._merchant_terms(merchant)
        matched_terms = sorted(user_terms & merchant_terms)
        score = self._merchant_score(merchant, matched_terms)

        return {
            "id": merchant.id,
            "merchant_name": merchant.merchant_name,
            "campus": merchant.campus,
            "category": merchant.category,
            "rating": float(merchant.rating),
            "order_count": merchant.order_count,
            "delivery_time": merchant.delivery_time,
            "tags": merchant.tags,
            "score": score,
            "reason": self._reason(matched_terms, merchant),
        }

    def _serialize_menu(self, menu, user_terms: set[str]):
        merchant = menu.merchant
        menu_terms = self._tokenize(menu.item_name) | self._merchant_terms(merchant)
        matched_terms = sorted(user_terms & menu_terms)
        score = self._merchant_score(merchant, matched_terms) + min(
            menu.max_daily_quantity,
            100,
        ) * 0.05

        return {
            "id": menu.id,
            "merchant_id": menu.merchant_id,
            "merchant_name": merchant.merchant_name,
            "item_name": menu.item_name,
            "price": float(menu.price),
            "max_daily_quantity": menu.max_daily_quantity,
            "score": round(score, 2),
            "reason": self._reason(matched_terms, merchant),
        }

    def _merchant_score(self, merchant, matched_terms: list[str]):
        base_score = float(merchant.rating) * 10 + merchant.order_count * 0.1
        preference_score = len(matched_terms) * 15
        return round(base_score + preference_score, 2)

    def _merchant_terms(self, merchant):
        terms = self._tokenize(merchant.category)
        terms.update(self._tokenize(merchant.merchant_name))

        for tag in merchant.tags or []:
            terms.update(self._tokenize(tag))

        return terms

    def _tokenize(self, value: str):
        normalized = value.lower()
        return {
            token
            for token in re.split(r"[\s,，、/|;；:：()（）-]+", normalized)
            if token
        }

    def _reason(self, matched_terms: list[str], merchant):
        if matched_terms:
            return f"Matched preferences: {', '.join(matched_terms)}"

        return f"Popular in {merchant.campus} with rating {float(merchant.rating):.1f}"
