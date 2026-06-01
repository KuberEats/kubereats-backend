from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.schemas.committee import MerchantApprovalRequest, MerchantSuspendRequest


# ── List ──


def test_list_pending_merchants_returns_only_pending(
    committee_service, pending_merchant, approved_merchant
):
    result = committee_service.list_pending_merchants()
    ids = [m.id for m in result]
    assert pending_merchant.id in ids
    assert approved_merchant.id not in ids


def test_list_all_merchants_returns_all(
    committee_service, pending_merchant, approved_merchant
):
    result = committee_service.list_all_merchants()
    ids = [m.id for m in result]
    assert pending_merchant.id in ids
    assert approved_merchant.id in ids


# ── Approve ──


def test_approve_merchant_success(committee_service, pending_merchant):
    start_date = date.today()
    end_date = start_date + timedelta(days=365)

    result = committee_service.approve_merchant(
        pending_merchant.id,
        MerchantApprovalRequest(
            cooperation_start_date=start_date,
            cooperation_end_date=end_date,
        ),
    )

    assert result["audit_status"] == 1
    assert pending_merchant.audit_status == 1
    assert pending_merchant.cooperation_start_date == start_date
    assert pending_merchant.cooperation_end_date == end_date


def test_approve_merchant_not_found_raises_404(committee_service):
    with pytest.raises(HTTPException) as exc:
        committee_service.approve_merchant(
            99999,
            MerchantApprovalRequest(
                cooperation_start_date=date.today(),
                cooperation_end_date=date.today() + timedelta(days=365),
            ),
        )
    assert exc.value.status_code == 404


def test_approve_merchant_already_reviewed_raises_400(
    committee_service, approved_merchant
):
    with pytest.raises(HTTPException) as exc:
        committee_service.approve_merchant(
            approved_merchant.id,
            MerchantApprovalRequest(
                cooperation_start_date=date.today(),
                cooperation_end_date=date.today() + timedelta(days=365),
            ),
        )
    assert exc.value.status_code == 400


# ── Reject ──


def test_reject_merchant_success(committee_service, pending_merchant):
    result = committee_service.reject_merchant(pending_merchant.id)
    assert result["audit_status"] == 2
    assert pending_merchant.audit_status == 2


def test_reject_merchant_not_found_raises_404(committee_service):
    with pytest.raises(HTTPException) as exc:
        committee_service.reject_merchant(99999)
    assert exc.value.status_code == 404


def test_reject_merchant_already_reviewed_raises_400(
    committee_service, approved_merchant
):
    with pytest.raises(HTTPException) as exc:
        committee_service.reject_merchant(approved_merchant.id)
    assert exc.value.status_code == 400


# ── Suspend ──


def test_suspend_merchant_success(committee_service, approved_merchant):
    result = committee_service.suspend_merchant(
        approved_merchant.id,
        MerchantSuspendRequest(reason="Food safety documentation expired"),
    )

    assert result["audit_status"] == 3
    assert approved_merchant.audit_status == 3
    assert approved_merchant.suspension_reason == "Food safety documentation expired"
    assert approved_merchant.suspended_at is not None


def test_suspend_merchant_requires_approved_status(committee_service, pending_merchant):
    with pytest.raises(HTTPException) as exc:
        committee_service.suspend_merchant(
            pending_merchant.id,
            MerchantSuspendRequest(reason="Missing updated documents"),
        )
    assert exc.value.status_code == 400
