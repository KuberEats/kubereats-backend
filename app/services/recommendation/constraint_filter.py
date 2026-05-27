from app.services.recommendation.text import contains_term


class ConstraintFilter:
    def apply(self, candidates, intent, user_context, limit: int):
        must_candidates = [
            candidate
            for candidate in candidates
            if self._passes_must_constraints(candidate, intent)
        ]

        if not intent.avoid.recent_merchants:
            return must_candidates

        avoid_filtered = [
            candidate
            for candidate in must_candidates
            if candidate.merchant.id not in user_context.recent_merchant_ids
        ]

        if len(avoid_filtered) >= limit:
            return avoid_filtered

        for candidate in must_candidates:
            candidate.avoid_recent_relaxed = (
                candidate.merchant.id in user_context.recent_merchant_ids
            )

        return must_candidates

    def _passes_must_constraints(self, candidate, intent):
        if intent.must.max_budget is not None:
            candidate_price = self._candidate_price(candidate)

            if candidate_price is not None and candidate_price > intent.must.max_budget:
                return False

        for term in intent.must.excluded_terms:
            if self._matches_term(candidate, term):
                return False

        return True

    def _candidate_price(self, candidate):
        if candidate.menu:
            return float(candidate.menu.price)

        prices = [float(menu.price) for menu in candidate.merchant.menus]
        return min(prices) if prices else float(candidate.merchant.min_order)

    def _matches_term(self, candidate, term: str):
        merchant = candidate.merchant
        pieces = [
            merchant.merchant_name,
            merchant.category,
            " ".join(merchant.tags or []),
        ]

        if candidate.menu:
            pieces.append(candidate.menu.item_name)
        else:
            pieces.extend(menu.item_name for menu in merchant.menus)

        return contains_term(" ".join(pieces), term)
