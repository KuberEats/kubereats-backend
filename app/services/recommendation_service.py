from fastapi import HTTPException

from app.schemas.recommendation import (
    MenuRecommendationRequest,
    RecommendationRequest,
)
from app.services.recommendation.constraint_filter import ConstraintFilter
from app.services.recommendation.prompt_interpreter import PromptInterpreter
from app.services.recommendation.reason_generator import TemplateReasonGenerator
from app.services.recommendation.reranker_provider import HeuristicRerankerProvider
from app.services.recommendation.search_provider import SqlSearchProvider
from app.services.recommendation.user_context_retriever import UserContextRetriever


class RecommendationService:
    def __init__(self, recommendation_repo):
        self.recommendation_repo = recommendation_repo
        self.prompt_interpreter = PromptInterpreter()
        self.user_context_retriever = UserContextRetriever(recommendation_repo)
        self.search_provider = SqlSearchProvider(recommendation_repo)
        self.constraint_filter = ConstraintFilter()
        self.reranker = HeuristicRerankerProvider()
        self.reason_generator = TemplateReasonGenerator()

    def recommend_merchants_by_prompt(self, request: RecommendationRequest):
        self._get_user_or_404(request.user_id)
        intent = self.prompt_interpreter.interpret(request.prompt, request.campus)
        user_context = self.user_context_retriever.get_context(
            request.user_id,
            intent.avoid.recent_order_limit,
        )
        candidates = self.search_provider.search_merchants(intent)
        filtered_candidates = self.constraint_filter.apply(
            candidates,
            intent,
            user_context,
            request.limit,
        )
        ranked_candidates = self.reranker.rerank(
            filtered_candidates,
            intent,
            user_context,
            request.limit,
            request.prompt,
        )
        return self.reason_generator.merchant_recommendations(ranked_candidates)

    def recommend_menus_by_prompt(self, request: MenuRecommendationRequest):
        self._get_user_or_404(request.user_id)
        intent = self.prompt_interpreter.interpret(request.prompt, request.campus)
        user_context = self.user_context_retriever.get_context(
            request.user_id,
            intent.avoid.recent_order_limit,
        )
        candidates = self.search_provider.search_menus(intent, request.merchant_id)
        filtered_candidates = self.constraint_filter.apply(
            candidates,
            intent,
            user_context,
            request.limit,
        )
        ranked_candidates = self.reranker.rerank(
            filtered_candidates,
            intent,
            user_context,
            request.limit,
            request.prompt,
        )
        return self.reason_generator.menu_recommendations(ranked_candidates)

    def recommend_merchants(
        self,
        user_id: int,
        campus: str | None,
        limit: int,
    ):
        request = RecommendationRequest(
            userId=user_id,
            campus=campus,
            prompt="系統推薦",
            limit=limit,
        )
        return self.recommend_merchants_by_prompt(request)

    def recommend_menus(
        self,
        user_id: int,
        campus: str | None,
        merchant_id: int | None,
        limit: int,
    ):
        request = MenuRecommendationRequest(
            userId=user_id,
            campus=campus,
            merchantId=merchant_id,
            prompt="系統推薦",
            limit=limit,
        )
        return self.recommend_menus_by_prompt(request)

    def _get_user_or_404(self, user_id: int):
        user = self.recommendation_repo.get_user_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user
