from app.services.recommendation.text import delivery_minutes, tokenize
from app.services.recommendation.types import RankedCandidate


class HeuristicRerankerProvider:
    def rerank(self, candidates, intent, user_context, limit: int):
        ranked_candidates = [
            self._rank_candidate(candidate, intent, user_context)
            for candidate in candidates
        ]

        return sorted(
            ranked_candidates,
            key=lambda ranked: ranked.score,
            reverse=True,
        )[:limit]

    def _rank_candidate(self, candidate, intent, user_context):
        merchant = candidate.merchant
        signals = {
            "matchedTerms": candidate.matched_terms,
            "excludedTerms": intent.must.excluded_terms,
            "avoidRecentRelaxed": candidate.avoid_recent_relaxed,
            "recentlyOrdered": merchant.id in user_context.recent_merchant_ids,
        }
        rating_score = float(merchant.rating) * 10
        popularity_score = min(merchant.order_count, 200) * 0.08
        budget_score = self._budget_score(candidate, intent, user_context)
        delivery_score = self._delivery_score(merchant, intent)
        history_score = self._history_score(candidate, intent, user_context)
        novelty_score = self._novelty_score(candidate, intent, user_context)
        capacity_score = self._capacity_score(candidate)

        score = (
            candidate.search_score
            + rating_score
            + popularity_score
            + budget_score
            + delivery_score
            + history_score
            + novelty_score
            + capacity_score
        )

        signals.update(
            {
                "ratingScore": round(rating_score, 2),
                "popularityScore": round(popularity_score, 2),
                "budgetScore": round(budget_score, 2),
                "deliveryScore": round(delivery_score, 2),
                "historyScore": round(history_score, 2),
                "noveltyScore": round(novelty_score, 2),
                "capacityScore": round(capacity_score, 2),
            }
        )

        return RankedCandidate(
            candidate=candidate,
            score=round(score, 2),
            signals=signals,
        )

    def _budget_score(self, candidate, intent, user_context):
        price = self._candidate_price(candidate)

        if price is None:
            return 0

        if intent.must.max_budget is not None:
            return 10 if price <= intent.must.max_budget else -20

        if user_context.average_spend is None:
            return 0

        difference = abs(price - user_context.average_spend)
        return max(0, 10 - difference * 0.1)

    def _delivery_score(self, merchant, intent):
        minutes = delivery_minutes(merchant.delivery_time)

        if minutes is None:
            return 0

        if intent.prefer.fast_delivery:
            return max(0, 18 - minutes * 0.35)

        return max(0, 6 - minutes * 0.1)

    def _history_score(self, candidate, intent, user_context):
        merchant = candidate.merchant
        candidate_terms = self._candidate_terms(candidate)
        matched_user_terms = candidate_terms & user_context.favorite_terms
        category_match = merchant.category in user_context.favorite_categories

        if intent.prefer.novelty:
            return (len(matched_user_terms) * 1.5) + (2 if category_match else 0)

        score = len(matched_user_terms) * 3

        if intent.prefer.familiar and merchant.id in user_context.favorite_merchant_ids:
            score += 16
        elif merchant.id in user_context.favorite_merchant_ids:
            score += 6

        if category_match:
            score += 5

        return score

    def _novelty_score(self, candidate, intent, user_context):
        if not intent.prefer.novelty:
            return 0

        if candidate.merchant.id in user_context.recent_merchant_ids:
            return -35 if candidate.avoid_recent_relaxed else -18

        return 14

    def _capacity_score(self, candidate):
        if candidate.menu:
            return min(candidate.menu.max_daily_quantity, 100) * 0.04

        return min(candidate.merchant.max_order_quantity, 100) * 0.03

    def _candidate_price(self, candidate):
        if candidate.menu:
            return float(candidate.menu.price)

        prices = [float(menu.price) for menu in candidate.merchant.menus]
        return min(prices) if prices else float(candidate.merchant.min_order)

    def _candidate_terms(self, candidate):
        merchant = candidate.merchant
        terms = tokenize(merchant.merchant_name) | tokenize(merchant.category)

        for tag in merchant.tags or []:
            terms.update(tokenize(tag))

        if candidate.menu:
            terms.update(tokenize(candidate.menu.item_name))
        else:
            for menu in merchant.menus:
                terms.update(tokenize(menu.item_name))

        return terms
