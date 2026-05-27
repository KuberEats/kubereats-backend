from dataclasses import dataclass
from html import escape
from string import Formatter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class TemplateValidationError(ValueError):
    pass


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrderConfirmedPayload(StrictPayload):
    orderId: str
    vendorName: str
    pickupDate: str
    pickupTime: str
    pickupLocation: str
    amount: int | float
    detailUrl: str


class OrderFailedPayload(StrictPayload):
    orderId: str
    failureReason: str
    retryUrl: str


class OrderCancelledPayload(StrictPayload):
    orderId: str
    cancelledAt: str
    refundDescription: str
    detailUrl: str


class SettlementReviewPayload(StrictPayload):
    settlementPeriod: str
    vendorName: str
    totalAmount: int | float
    reviewUrl: str


class VendorApprovalRequiredPayload(StrictPayload):
    vendorId: str
    vendorName: str
    submittedAt: str
    reviewUrl: str


class MenuReviewRequiredPayload(StrictPayload):
    vendorId: str
    vendorName: str
    menuVersion: str
    reviewUrl: str


class VendorSettlementConfirmedPayload(StrictPayload):
    settlementPeriod: str
    totalAmount: int | float
    status: str
    detailUrl: str


class VendorApprovalResultPayload(StrictPayload):
    vendorName: str
    approvalStatus: str
    reason: str
    detailUrl: str


class VendorMenuChangeResultPayload(StrictPayload):
    vendorName: str
    menuVersion: str
    approvalStatus: str
    detailUrl: str


class Recipient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    id: str = Field(min_length=1)
    email: str = Field(min_length=3)
    name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("invalid email")
        return value


@dataclass(frozen=True)
class EmailTemplate:
    key: str
    version: int
    allowed_source_services: frozenset[str]
    allowed_recipient_types: frozenset[str]
    payload_model: type[StrictPayload]
    subject_template: str
    html_template: str
    text_template: str

    def validate_payload(self, payload: dict[str, Any]) -> StrictPayload:
        try:
            return self.payload_model.model_validate(payload)
        except ValidationError as exc:
            raise TemplateValidationError(str(exc)) from exc

    def render(self, recipient: Recipient, payload: dict[str, Any]) -> dict[str, str]:
        validated = self.validate_payload(payload).model_dump()
        values = {key: escape(str(value), quote=True) for key, value in validated.items()}
        values["recipientName"] = escape(recipient.name or recipient.email, quote=True)
        return {
            "subject": self.subject_template.format(**values),
            "htmlBody": render_template(self.html_template, values),
            "textBody": self.text_template.format(**values),
        }


def render_template(template: str, values: dict[str, str]) -> str:
    formatter = Formatter()
    rendered = []
    for literal, field_name, _format_spec, _conversion in formatter.parse(template):
        rendered.append(literal)
        if field_name is not None:
            rendered.append(values[field_name])
    return "".join(rendered)


BASE_HTML = """
<html>
  <body style="font-family: Arial, sans-serif; color: #1f2937; line-height: 1.6;">
    <h2>{title}</h2>
    <p>{greeting}</p>
    {content}
    <p>請透過下方系統連結查看或處理：</p>
    <p><a href="{actionUrl}">開啟 KuberEats 系統</a></p>
    <p style="color:#6b7280;font-size:12px;">此信由企業訂餐系統自動發送，請勿直接回覆。</p>
  </body>
</html>
"""


def html(title: str, content: str, action_url_field: str) -> str:
    return BASE_HTML.format(
        title=title,
        greeting="您好 {recipientName}：",
        content=content,
        actionUrl="{" + action_url_field + "}",
    )


TEMPLATES: dict[str, EmailTemplate] = {
    "employee.order.confirmed": EmailTemplate(
        key="employee.order.confirmed",
        version=1,
        allowed_source_services=frozenset({"order-service"}),
        allowed_recipient_types=frozenset({"EMPLOYEE"}),
        payload_model=OrderConfirmedPayload,
        subject_template="[KuberEats] 訂餐成功通知 {orderId}",
        html_template=html(
            "訂餐成功通知",
            "<p>您的訂單已成立。商家：{vendorName}，領餐時間：{pickupDate} {pickupTime}，"
            "領餐地點：{pickupLocation}，金額：{amount}。</p>",
            "detailUrl",
        ),
        text_template=(
            "您好 {recipientName}：\n您的訂單已成立。\n訂單：{orderId}\n商家：{vendorName}\n"
            "領餐：{pickupDate} {pickupTime} / {pickupLocation}\n金額：{amount}\n{detailUrl}"
        ),
    ),
    "employee.order.failed": EmailTemplate(
        key="employee.order.failed",
        version=1,
        allowed_source_services=frozenset({"order-service"}),
        allowed_recipient_types=frozenset({"EMPLOYEE"}),
        payload_model=OrderFailedPayload,
        subject_template="[KuberEats] 訂餐失敗通知 {orderId}",
        html_template=html(
            "訂餐失敗通知",
            "<p>您的訂單未能完成。訂單：{orderId}，原因：{failureReason}。</p>",
            "retryUrl",
        ),
        text_template="您好 {recipientName}：\n訂單 {orderId} 未能完成。\n原因：{failureReason}\n{retryUrl}",
    ),
    "employee.order.cancelled": EmailTemplate(
        key="employee.order.cancelled",
        version=1,
        allowed_source_services=frozenset({"order-service"}),
        allowed_recipient_types=frozenset({"EMPLOYEE"}),
        payload_model=OrderCancelledPayload,
        subject_template="[KuberEats] 訂單取消通知 {orderId}",
        html_template=html(
            "訂單取消通知",
            "<p>您的訂單已取消。訂單：{orderId}，取消時間：{cancelledAt}。"
            "退款說明：{refundDescription}。</p>",
            "detailUrl",
        ),
        text_template="您好 {recipientName}：\n訂單 {orderId} 已取消。\n取消時間：{cancelledAt}\n{refundDescription}\n{detailUrl}",
    ),
    "committee.settlement.review_required": EmailTemplate(
        key="committee.settlement.review_required",
        version=1,
        allowed_source_services=frozenset({"finance-service"}),
        allowed_recipient_types=frozenset({"COMMITTEE"}),
        payload_model=SettlementReviewPayload,
        subject_template="[KuberEats] 結算審核通知 {settlementPeriod}",
        html_template=html(
            "結算審核通知",
            "<p>{vendorName} 的 {settlementPeriod} 結算需要審核。彙總金額：{totalAmount}。</p>",
            "reviewUrl",
        ),
        text_template="您好 {recipientName}：\n{vendorName} {settlementPeriod} 結算待審核。\n彙總金額：{totalAmount}\n{reviewUrl}",
    ),
    "committee.vendor.approval_required": EmailTemplate(
        key="committee.vendor.approval_required",
        version=1,
        allowed_source_services=frozenset({"merchant-service"}),
        allowed_recipient_types=frozenset({"COMMITTEE"}),
        payload_model=VendorApprovalRequiredPayload,
        subject_template="[KuberEats] 商家審核通知 {vendorName}",
        html_template=html(
            "商家審核通知",
            "<p>商家 {vendorName}（{vendorId}）已於 {submittedAt} 送出審核申請。</p>",
            "reviewUrl",
        ),
        text_template="您好 {recipientName}：\n商家 {vendorName}（{vendorId}）待審核。\n送出時間：{submittedAt}\n{reviewUrl}",
    ),
    "committee.menu.review_required": EmailTemplate(
        key="committee.menu.review_required",
        version=1,
        allowed_source_services=frozenset({"merchant-service"}),
        allowed_recipient_types=frozenset({"COMMITTEE"}),
        payload_model=MenuReviewRequiredPayload,
        subject_template="[KuberEats] 菜單審核通知 {vendorName}",
        html_template=html(
            "菜單審核通知",
            "<p>商家 {vendorName}（{vendorId}）送出菜單版本 {menuVersion}，需要審核。</p>",
            "reviewUrl",
        ),
        text_template="您好 {recipientName}：\n商家 {vendorName} 菜單版本 {menuVersion} 待審核。\n{reviewUrl}",
    ),
    "vendor.settlement.confirmed": EmailTemplate(
        key="vendor.settlement.confirmed",
        version=1,
        allowed_source_services=frozenset({"finance-service"}),
        allowed_recipient_types=frozenset({"VENDOR"}),
        payload_model=VendorSettlementConfirmedPayload,
        subject_template="[KuberEats] 結算確認通知 {settlementPeriod}",
        html_template=html(
            "結算確認通知",
            "<p>{settlementPeriod} 結算狀態：{status}。彙總金額：{totalAmount}。</p>",
            "detailUrl",
        ),
        text_template="您好 {recipientName}：\n{settlementPeriod} 結算狀態：{status}\n彙總金額：{totalAmount}\n{detailUrl}",
    ),
    "vendor.approval.result": EmailTemplate(
        key="vendor.approval.result",
        version=1,
        allowed_source_services=frozenset({"committee-service"}),
        allowed_recipient_types=frozenset({"VENDOR"}),
        payload_model=VendorApprovalResultPayload,
        subject_template="[KuberEats] 商家審核結果 {vendorName}",
        html_template=html(
            "商家審核結果",
            "<p>{vendorName} 的審核結果：{approvalStatus}。說明：{reason}。</p>",
            "detailUrl",
        ),
        text_template="您好 {recipientName}：\n{vendorName} 審核結果：{approvalStatus}\n說明：{reason}\n{detailUrl}",
    ),
    "vendor.menu.change_result": EmailTemplate(
        key="vendor.menu.change_result",
        version=1,
        allowed_source_services=frozenset({"committee-service"}),
        allowed_recipient_types=frozenset({"VENDOR"}),
        payload_model=VendorMenuChangeResultPayload,
        subject_template="[KuberEats] 菜單審核結果 {vendorName}",
        html_template=html(
            "菜單審核結果",
            "<p>{vendorName} 的菜單版本 {menuVersion} 審核結果：{approvalStatus}。</p>",
            "detailUrl",
        ),
        text_template="您好 {recipientName}：\n{vendorName} 菜單版本 {menuVersion} 審核結果：{approvalStatus}\n{detailUrl}",
    ),
}


def get_template(template_key: str) -> EmailTemplate:
    template = TEMPLATES.get(template_key)
    if template is None:
        raise KeyError(template_key)
    return template
