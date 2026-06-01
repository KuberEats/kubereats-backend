from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repo.recommendation_repo import RecommendationRepository
from app.schemas.recommendation import (
    Campus,
    MenuRecommendation,
    MenuRecommendationRequest,
    MerchantRecommendation,
    RecommendationRequest,
)
from app.services.recommendation.metrics import recommendation_metrics
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["Recommendations"])


def get_recommendation_service(db: Session = Depends(get_db)):
    return RecommendationService(RecommendationRepository(db))


@router.get("/grafana-check")
def grafana_check():
    return recommendation_metrics.snapshot()


@router.post("/merchants", response_model=list[MerchantRecommendation])
def recommend_merchants_by_prompt(
    request: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
):
    try:
        results = service.recommend_merchants_by_prompt(request)
    except Exception:
        recommendation_metrics.record_prompt_request("merchants", "error")
        raise
    recommendation_metrics.record_prompt_request("merchants", "success")
    recommendation_metrics.record_results("merchants", "prompt", len(results))
    return results


@router.get("/merchants", response_model=list[MerchantRecommendation])
def recommend_merchants(
    user_id: int = Query(alias="userId"),
    campus: Campus | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    service: RecommendationService = Depends(get_recommendation_service),
):
    results = service.recommend_merchants(user_id=user_id, campus=campus, limit=limit)
    recommendation_metrics.record_results("merchants", "history", len(results))
    return results


@router.post("/menus", response_model=list[MenuRecommendation])
def recommend_menus_by_prompt(
    request: MenuRecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
):
    try:
        results = service.recommend_menus_by_prompt(request)
    except Exception:
        recommendation_metrics.record_prompt_request("menus", "error")
        raise
    recommendation_metrics.record_prompt_request("menus", "success")
    recommendation_metrics.record_results("menus", "prompt", len(results))
    return results


@router.get("/menus", response_model=list[MenuRecommendation])
def recommend_menus(
    user_id: int = Query(alias="userId"),
    campus: Campus | None = None,
    merchant_id: int | None = Query(default=None, alias="merchantId"),
    limit: int = Query(default=10, ge=1, le=50),
    service: RecommendationService = Depends(get_recommendation_service),
):
    results = service.recommend_menus(
        user_id=user_id,
        campus=campus,
        merchant_id=merchant_id,
        limit=limit,
    )
    recommendation_metrics.record_results("menus", "history", len(results))
    return results
