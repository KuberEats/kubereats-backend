class TemplateReasonGenerator:
    def merchant_recommendations(self, ranked_candidates):
        return [
            self._merchant_response(ranked_candidate)
            for ranked_candidate in ranked_candidates
        ]

    def menu_recommendations(self, ranked_candidates):
        return [
            self._menu_response(ranked_candidate)
            for ranked_candidate in ranked_candidates
        ]

    def _merchant_response(self, ranked_candidate):
        merchant = ranked_candidate.candidate.merchant

        return {
            "id": merchant.id,
            "merchant_name": merchant.merchant_name,
            "campus": merchant.campus,
            "category": merchant.category,
            "rating": float(merchant.rating),
            "order_count": merchant.order_count,
            "delivery_time": merchant.delivery_time,
            "tags": merchant.tags,
            "score": ranked_candidate.score,
            "reason": self._reason(ranked_candidate),
            "signals": ranked_candidate.signals,
        }

    def _menu_response(self, ranked_candidate):
        candidate = ranked_candidate.candidate
        merchant = candidate.merchant
        menu = candidate.menu

        return {
            "id": menu.id,
            "merchant_id": menu.merchant_id,
            "merchant_name": merchant.merchant_name,
            "item_name": menu.item_name,
            "price": float(menu.price),
            "max_daily_quantity": menu.max_daily_quantity,
            "score": ranked_candidate.score,
            "reason": self._reason(ranked_candidate),
            "signals": ranked_candidate.signals,
        }

    def _reason(self, ranked_candidate):
        signals = ranked_candidate.signals
        reasons = []

        if signals["matchedTerms"]:
            reasons.append(f"符合你提到的 {', '.join(signals['matchedTerms'])}")

        if signals["recentlyOrdered"] and signals["avoidRecentRelaxed"]:
            reasons.append("這家最近吃過，但因為可選結果較少所以保留")
        elif not signals["recentlyOrdered"] and signals["noveltyScore"] > 0:
            reasons.append("不在你最近的訂單店家中")

        if signals["budgetScore"] > 0:
            reasons.append("價格接近你的需求或常見消費")

        if signals["deliveryScore"] > 6:
            reasons.append("配送時間相對合適")

        if signals["historyScore"] > 0:
            reasons.append("和你的歷史偏好有相近訊號")

        if not reasons:
            merchant = ranked_candidate.candidate.merchant
            return (
                f"在 {merchant.campus} 評分 {float(merchant.rating):.1f}，整體排序較高"
            )

        return "，".join(reasons) + "。"
