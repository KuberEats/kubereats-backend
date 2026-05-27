import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import Settings, get_settings


class EmailProviderError(Exception):
    def __init__(self, code: str, message: str, transient: bool):
        super().__init__(message)
        self.code = code
        self.transient = transient


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    html_body: str
    text_body: str


@dataclass(frozen=True)
class EmailProviderResult:
    provider: str
    message_id: str


class EmailProvider:
    provider_name = "base"

    def send(self, email: Email) -> EmailProviderResult:
        raise NotImplementedError


class LocalSmtpEmailProvider(EmailProvider):
    provider_name = "local-smtp"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def send(self, email: Email) -> EmailProviderResult:
        message = EmailMessage()
        message["From"] = self.settings.smtp_from_email
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.text_body)
        message.add_alternative(email.html_body, subtype="html")

        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as smtp:
                smtp.send_message(message)
        except smtplib.SMTPRecipientsRefused as exc:
            raise EmailProviderError("recipient_refused", "recipient refused", transient=False) from exc
        except OSError as exc:
            raise EmailProviderError("smtp_unavailable", str(exc), transient=True) from exc
        return EmailProviderResult(provider=self.provider_name, message_id=f"local-{uuid.uuid4()}")


class ProductionEmailProviderAdapter(EmailProvider):
    provider_name = "production-adapter"

    def send(self, email: Email) -> EmailProviderResult:
        raise EmailProviderError(
            "provider_not_configured",
            "Production email provider is not configured",
            transient=False,
        )


class InMemoryEmailProvider(EmailProvider):
    provider_name = "in-memory"

    def __init__(self, fail_times: int = 0, transient: bool = True):
        self.fail_times = fail_times
        self.transient = transient
        self.sent: list[Email] = []

    def send(self, email: Email) -> EmailProviderResult:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise EmailProviderError("simulated_failure", "simulated failure", self.transient)
        self.sent.append(email)
        return EmailProviderResult(provider=self.provider_name, message_id=f"test-{len(self.sent)}")


def build_email_provider(settings: Settings | None = None) -> EmailProvider:
    settings = settings or get_settings()
    if settings.email_provider == "local":
        return LocalSmtpEmailProvider(settings)
    if settings.email_provider == "production":
        return ProductionEmailProviderAdapter()
    if settings.email_provider == "memory":
        return InMemoryEmailProvider()
    raise ValueError(f"Unsupported EMAIL_PROVIDER={settings.email_provider}")
