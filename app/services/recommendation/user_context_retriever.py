from collections import Counter

from app.services.recommendation.text import tokenize
from app.services.recommendation.types import UserContext


class UserContextRetriever:
    def __init__(self, recommendation_repo):
        self.recommendation_repo = recommendation_repo

    def get_context(self, user_id: int, recent_order_limit: int = 10):
        user = self.recommendation_repo.get_user_by_id(user_id)
        orders = self.recommendation_repo.list_recent_orders_by_user(
            user_id,
            recent_order_limit,
        )

        merchant_counter = Counter()
        category_counter = Counter()
        term_counter = Counter()
        totals = []

        for order in orders:
            totals.append(float(order.total_amount))

            for item in order.items:
                menu = item.menu
                merchant = menu.merchant
                merchant_counter[merchant.id] += 1
                category_counter[merchant.category] += 1
                term_counter.update(tokenize(menu.item_name))
                term_counter.update(tokenize(merchant.category))

                for tag in merchant.tags or []:
                    term_counter.update(tokenize(tag))

        tag_terms = {tag.name.lower() for tag in user.tags}
        history_terms = set()
        favorite_categories = {
            category for category, _ in category_counter.most_common(3)
        }
        favorite_terms = {term for term, _ in term_counter.most_common(8)}
        recent_merchant_ids = set(merchant_counter.keys())
        recent_merchant_names = self._recent_merchant_names(orders)
        favorite_merchant_ids = {
            merchant_id for merchant_id, _ in merchant_counter.most_common(3)
        }
        average_spend = sum(totals) / len(totals) if totals else None

        return UserContext(
            user_id=user_id,
            tag_terms=tag_terms,
            history_terms=history_terms,
            recent_merchant_ids=recent_merchant_ids,
            recent_merchant_names=recent_merchant_names,
            favorite_merchant_ids=favorite_merchant_ids,
            favorite_categories=favorite_categories,
            favorite_terms=favorite_terms | tag_terms | history_terms,
            average_spend=average_spend,
        )

    def _recent_merchant_names(self, orders):
        names = set()

        for order in orders:
            for item in order.items:
                names.add(item.menu.merchant.merchant_name)

        return names
