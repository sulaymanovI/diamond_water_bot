from sqlalchemy import Column, Integer, String, Date ,DateTime, TIMESTAMP, ForeignKey, Identity, Boolean, CheckConstraint
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
    address = Column(String(200))
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
    prepaid = Column(Integer, default=0)  # Первоначальный взнос
    every_month_should_pay = Column(Integer)  # Ежемесячный платеж
    sum_of_item = Column(Integer)  # Общая сумма товара
    total_paid = Column(Integer, default=0)  # Всего уже оплачено (prepaid + ежемесячные)
    remaining_amount = Column(Integer)  # Остаток долга (sum_of_item - total_paid)
    created_at = Column(DateTime, default=func.now())
    item_returned = Column(Boolean, default=False)
    order_status = Column(String(10), default='Ochiq')
    
    __table_args__ = (
        CheckConstraint(
            "order_status IN ('Yopilgan', 'Ochiq')",
            name='check_order_status'
        ),
    )
    
    client = relationship("Client", backref="orders")
    seller = relationship("Seller", backref="orders")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_remaining_amount()

    def update_remaining_amount(self):
        """Обновляет остаток долга"""
        self.total_paid = (self.prepaid or 0)
        self.remaining_amount = max(0, (self.sum_of_item or 0) - self.total_paid)

    def add_monthly_payment(self, amount):
        """Добавляет ежемесячный платеж"""
        if self.remaining_amount <= 0:
            raise ValueError("Долг уже полностью погашен")
        
        self.total_paid += amount
        self.remaining_amount = max(0, self.sum_of_item - self.total_paid)