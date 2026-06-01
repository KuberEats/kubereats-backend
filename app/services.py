from sqlalchemy.orm import Session
from sqlalchemy import func, text
from . import models, schemas
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from fpdf import FPDF

class MerchantFinanceService:
    @staticmethod
    def get_income_status(db: Session, merchant_id: int):
        total = db.query(func.sum(models.Finance.settlement_amount)).filter(
            models.Finance.merchant_id == merchant_id
        ).scalar() or Decimal("0")
        
        count = db.query(models.Finance).filter(
            models.Finance.merchant_id == merchant_id
        ).count()
        
        return {"total_income": total, "order_count": count}

    @staticmethod
    def get_payouts(db: Session, merchant_id: int):
        records = db.query(models.Finance).filter(
            models.Finance.merchant_id == merchant_id
        ).all()
        
        results = []
        for r in records:
            status = "pending"
            if r.report_data and isinstance(r.report_data, dict):
                status = r.report_data.get("status", "pending")
            
            results.append({
                "id": r.id,
                "order_id": r.order_id,
                "settlement_amount": r.settlement_amount,
                "status": status
            })
        return results

    @staticmethod
    def get_monthly_total(db: Session, merchant_id: int):
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        
        total = db.query(func.sum(models.Finance.settlement_amount)).join(models.Order).filter(
            models.Finance.merchant_id == merchant_id,
            models.Order.order_time >= month_start
        ).scalar() or Decimal("0")
        
        return {"monthly_total": total, "month": now.month, "year": now.year}

    @staticmethod
    def get_monthly_item_distribution(db: Session, merchant_id: int):
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        
        # Query items for this merchant in finished orders this month
        items_data = db.query(
            models.Menu.item_name,
            func.sum(models.OrderItem.subtotal).label("total_amount")
        ).join(
            models.OrderItem, models.Menu.id == models.OrderItem.menu_id
        ).join(
            models.Order, models.OrderItem.order_id == models.Order.id
        ).filter(
            models.Menu.merchant_id == merchant_id,
            models.Order.order_status == 1, # Finished
            models.Order.order_time >= month_start
        ).group_by(
            models.Menu.item_name
        ).all()
        
        total_revenue = sum(item.total_amount for item in items_data) or Decimal("1") # Avoid division by zero
        
        results = []
        for item in items_data:
            percentage = (float(item.total_amount) / float(total_revenue)) * 100
            results.append({
                "itemName": item.item_name,
                "totalAmount": float(item.total_amount),
                "percentage": round(percentage, 1)
            })
            
        return results

class StaffFinanceService:
    @staticmethod
    def get_expenses(db: Session, user_id: int):
        total = db.query(func.sum(models.Order.total_amount)).filter(
            models.Order.user_id == user_id,
            models.Order.order_status == 1 # Finished
        ).scalar() or Decimal("0")
        
        count = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_status == 1
        ).count()
        
        return {"total_expense": total, "order_count": count}

    @staticmethod
    def get_salary_deductions(db: Session, user_id: int):
        orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_status == 1
        ).all()
        
        return orders

class MonitoringService:
    @staticmethod
    def health_check(db: Session):
        now = datetime.now()
        try:
            # Check DB connection
            db.execute(text("SELECT 1"))
            db_status = "connected"

            # Get today's total settlement amount
            today_start = datetime(now.year, now.month, now.day)
            today_total = db.query(func.sum(models.Finance.settlement_amount)).filter(
                models.Finance.created_at >= today_start
            ).scalar() or Decimal("0")

            return {
                "status": "ok",
                "database": db_status,
                "today_total_settlement": float(today_total),
                "timestamp": now.isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "database": f"disconnected: {str(e)}",
                "today_total_settlement": 0.0,
                "timestamp": now.isoformat()
            }


class ReportService:
    REPORT_DIR = Path("reports")

    @staticmethod
    def get_history(db: Session):
        """讀取歷史記錄"""
        return db.query(models.Finance).all()

    @staticmethod
    def list_reports(base_url: str):
        ReportService.REPORT_DIR.mkdir(exist_ok=True)
        return [
            {
                "filename": path.name,
                "url": f"{base_url.rstrip('/')}/{path.name}",
            }
            for path in sorted(ReportService.REPORT_DIR.glob("*.pdf"))
        ]

    @staticmethod
    def get_report_path(filename: str):
        if "/" in filename or "\\" in filename or filename in {"", ".", ".."}:
            return None

        path = (ReportService.REPORT_DIR / filename).resolve()
        report_dir = ReportService.REPORT_DIR.resolve()
        if report_dir not in path.parents:
            return None
        if not path.exists() or not path.is_file():
            return None
        return path

    @staticmethod
    def trigger_report_generation(db: Session, merchant_id: int, base_url: str):
        """Generate a report immediately for the API pod.

        The Celery worker path is not available in the current dev deployment, so
        the API generates the PDF synchronously and returns a downloadable URL.
        """
        path = ReportService.generate_report_file(db, merchant_id)
        return {
            "filename": path.name,
            "url": f"{base_url.rstrip('/')}/{path.name}",
        }

    @staticmethod
    def generate_report_file(db: Session, merchant_id: int):
        merchant = db.query(models.MerchantInfo).filter(
            models.MerchantInfo.id == merchant_id
        ).first()
        if not merchant:
            raise ValueError("Merchant not found")

        records = db.query(models.Finance).filter(
            models.Finance.merchant_id == merchant_id
        ).all()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(
            200,
            10,
            text=f"Financial Report for {merchant.merchant_name}",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        pdf.cell(
            200,
            10,
            text=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(10)

        pdf.cell(40, 10, "Order ID", 1)
        pdf.cell(60, 10, "Settlement Amount", 1)
        pdf.cell(60, 10, "Status", 1)
        pdf.ln()

        total_settlement = 0
        for record in records:
            status = (
                record.report_data.get("status", "N/A")
                if record.report_data
                else "N/A"
            )
            pdf.cell(40, 10, str(record.order_id), 1)
            pdf.cell(60, 10, f"${record.settlement_amount}", 1)
            pdf.cell(60, 10, status, 1)
            pdf.ln()
            total_settlement += float(record.settlement_amount)

        pdf.ln(10)
        pdf.cell(
            200,
            10,
            text=f"Total Settlement: ${total_settlement}",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        ReportService.REPORT_DIR.mkdir(exist_ok=True)
        file_path = ReportService.REPORT_DIR / (
            f"report_merchant_{merchant_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        )
        pdf.output(file_path)
        return file_path

    @staticmethod
    def notify_merchant(merchant_id: int, report_url: str):
        """通知商家報表結果 (Placeholder)"""
        # Logic to send notification (email/push)
        print(f"Notifying merchant {merchant_id} about report at {report_url}")
        return True

    @staticmethod
    def save_monthly_summary(db: Session, merchant_id: int, report_data: dict, amount: Decimal):
        """將月份資訊定期寫入"""
        new_record = models.Finance(
            merchant_id=merchant_id,
            report_data=report_data,
            settlement_amount=amount,
            order_id=0 # Placeholder for summary records
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record
