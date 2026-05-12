我現在在寫一個 micro service，他主要是負責整個系統的財務部分，以下是這個系統的需求
# Requirement
## 商家
- 查看目前的收入狀況 (從 Order table 獲取)
- 查看 payout 結果 (從 Order table 獲取)
- 查看當月總金額

## 員工
- 查看 目前支出 情況 (從 Order table 獲取)
- 查看 薪資扣款 狀態 (從 Order table 獲取)

## 報表系統 (從 Order table 獲取; 寫入 Finance table)
- 讀取歷史記錄
- 產生 PDF / 網頁報表
- 通知商家報表結果
- 將月份資訊定期寫入

## Object Storage
- 給福委會的 pdf 報表
- 給商家的 pdf 報表

# Framework
- **Local dev**：Docker Compose
    - `frontend`：Vue 3 + Vite
    - `backend-api`： FastAPI
    - `worker`：Celery worker
    - `beat`：Celery beat，跑定時任務
    - `postgres`：PostgreSQL
    - `redis`：Redis
- **Frontend**：Vue 3 + Vite + Vue Router + Pinia
    - **Vue 3**：畫 UI
    - **Vite**：前端開發伺服器與打包工具
    - **Vue Router**：頁面切換
    - **Pinia**：登入狀態、使用者資料、清單篩選條件這類共享狀態
    - CSS：daisyUI → 如果這個裡面沒有的用 tailwind
- 套件管理: `uv`

# Database Schema
```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, JSON, Text
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
import datetime

class Base(DeclarativeBase):
    pass

# 1. 商家資訊
class MerchantInfo(Base):
    __tablename__ = "merchant_info"

    id = Column(Integer, primary_key=True, index=True)
    merchant_name = Column(String(100), nullable=False)
    audit_status = Column(Integer, default=0)  # 0: 待審, 1: 通過, 2: 拒絕
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 關聯
    menus = relationship("Menu", back_populates="merchant")
    finances = relationship("Finance", back_populates="merchant")

# 2. 餐點品項
class Menu(Base):
    __tablename__ = "menu"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"))
    item_name = Column(String(100), nullable=False)
    max_daily_quantity = Column(Integer, default=0)
    image_id = Column(String(255))
    price = Column(Numeric(10, 2), nullable=False)

    merchant = relationship("MerchantInfo", back_populates="menus")

# 3. 使用者/員工資訊
class UserInfo(Base):
    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20)) # e.g., "staff", "admin", "merchant"
    history_records = Column(Text) # 若資料量大，建議另外建關聯表
    
    orders = relationship("Order", back_populates="user")

# 4. 訂單表
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_info.id"))
    total_amount = Column(Numeric(10, 2), nullable=False)
    order_status = Column(Integer, default=0) # 0: 處理中, 1: 完成, 2: 取消
    order_time = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserInfo", back_populates="orders")
    finance_records = relationship("Finance", back_populates="order")

# 5. 財務表
class Finance(Base):
    __tablename__ = "finance"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    report_data = Column(JSON) # PostgreSQL 的強項：原生支援 JSONB
    settlement_amount = Column(Numeric(10, 2))

    merchant = relationship("MerchantInfo", back_populates="finances")
    order = relationship("Order", back_populates="finance_records")
```

為了維持高可用性， requirement 裡面的每一個類別都幫我用 class 開出他的功能