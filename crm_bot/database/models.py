from sqlalchemy import (
                    Column, Integer, String, 
                    Date ,DateTime, TIMESTAMP, 
                    ForeignKey, Identity, Boolean, 
                    CheckConstraint, Index, Float,
                    Numeric
                    )
from sqlalchemy.orm import validates, relationship   
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.sql import func

Base = declarative_base()

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)
    passport_serial = Column(String(20), unique=True)
    created_at = Column(TIMESTAMP, server_default='now()')
    notes = Column(String(500))

class Seller(Base):
    __tablename__ = 'sellers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    passport_serial = Column(String(20), unique=True)
    salary_of_seller = Column(Integer)
    started_job_at = Column(Date)
    order_counter = Column(Integer, default=0, nullable=False)
    orders = relationship("Order", backref="seller")

    @validates('started_job_at')
    def validate_date(self, key, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("❌ Sana noto‘g‘ri formatda! To‘g‘ri format: YYYY-MM-DD")
        return value

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, Identity(), primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    seller_id = Column(Integer, ForeignKey('sellers.id'))
    item_count = Column(Integer)
    prepaid = Column(Integer, default=0)
    every_month_should_pay = Column(Integer)
    sum_of_item = Column(Integer)
    total_paid = Column(Integer, default=0)
    remaining_amount = Column(Integer)
    last_notification_sent = Column(DateTime, nullable=True)
    notification_count = Column(Integer, default=0)
    created_at = Column(DateTime)
    order_status = Column(String(10), default='Ochiq')
    client = relationship("Client", backref="orders")
    
    __table_args__ = (
        Index('ix_orders_created_at', 'created_at'),
        Index('ix_orders_notification_status', 'last_notification_sent'),
        CheckConstraint(
            "order_status IN ('Yopilgan', 'Ochiq', 'Qaytarilgan')",
            name='check_order_status'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_remaining_amount()

    def update_remaining_amount(self):
        self.total_paid = (self.prepaid or 0)
        self.remaining_amount = max(0, (self.sum_of_item or 0) - self.total_paid)
        if self.remaining_amount <= 0:
            self.order_status = 'Yopilgan'

class Consumptions(Base):
    __tablename__ = 'consumptions'

    id = Column(Integer, Identity(), primary_key=True)
    consumption_owner = Column(String(20))
    amount = Column(Numeric(10, 2))  # Сумма расхода
    description = Column(String(255))  # Описание расхода
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        CheckConstraint(
            "consumption_owner IN ('Maxmudho'ja', 'Abdulbosit', 'Bekzod', 'Og'abek', 'Hodimlar')",
            name='check_consumption_owner'
        ),
    )