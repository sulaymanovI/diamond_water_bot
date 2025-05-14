from sqlalchemy import select, join, update
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from openpyxl import Workbook
from io import BytesIO
from database.models import Seller, Client, Order
from database.utils import async_session
from .database import AsyncSessionLocal

async def get_seller_by_passport(passport_serial: str):
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Seller).where(Seller.passport_serial == passport_serial)
            )
            return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        print(f"Database error in get_seller_by_passport: {str(e)}")
        return None

async def add_seller_to_db(data: dict):
    async with async_session() as session:
        try:
            seller = Seller(
                full_name=data['full_name'],
                phone=data['phone'],
                passport_serial=data['passport_serial'],
                salary_of_seller=data.get('salary_of_seller'),
                started_job_at=data['started_job_at'],
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)
            return seller
        except Exception as e:
            await session.rollback()
            raise e

async def add_client_to_db(client_data: dict):
    async with AsyncSessionLocal() as session:
        try:
            client = Client(**client_data)
            session.add(client)
            await session.commit()
            await session.refresh(client)
            return client
        except Exception as e:
            await session.rollback()
            raise e

async def get_client_by_passport(passport: str):
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Client).where(Client.passport_serial == passport)
            )
            return result.scalars().first()
    except SQLAlchemyError as e:
        print(f"Database error in get_client_by_passport: {str(e)}")
        return None

async def create_order(order_data: dict):
    async with AsyncSessionLocal() as session:
        try:
            # Добавляем статус по умолчанию
            order_data.setdefault('order_status', 'Ochiq')
            order = Order(**order_data)
            session.add(order)
            await session.commit()
            await session.refresh(order)
            return order
        except Exception as e:
            await session.rollback()
            raise e

async def update_order_return_status(order_id: int, status: bool):
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Order).where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if order:
                order.item_returned = status
                await session.commit()
                return True
            return False
        except Exception as e:
            await session.rollback()
            raise e

async def get_all_orders_with_details():
    async with async_session() as session:
        try:
            query = (
                select(
                    Order.id.label("order_id"),
                    Order.order_status,  # Добавляем статус
                    Order.created_at,
                    Order.item_count,
                    Order.sum_of_item,
                    Order.every_month_should_pay,
                    Order.prepaid,
                    Order.item_returned,
                    Client.full_name.label("client_name"),
                    Client.phone.label("client_phone"),
                    Client.passport_serial.label("client_passport"),
                    Seller.full_name.label("seller_name")
                )
                .select_from(
                    join(Order, Client, Order.client_id == Client.id)
                    .join(Seller, Order.seller_id == Seller.id)
                )
                .order_by(Order.created_at.desc())
            )
            result = await session.execute(query)
            return result.all()
        except Exception as e:
            print(f"Error fetching orders: {str(e)}")
            return None


async def generate_orders_excel():
    orders = await get_all_orders_with_details()
    if not orders:
        return None
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"
    
    headers = [
        "Buyurtma ID", "Status", "Sana", "Mijoz", "Telefon",  # Добавлен Status
        "Passport", "Sotuvchi", "Mahsulot Soni",
        "Umumiy Summa", "Oylik To'lov", "Oldindan To'lov",
        "Qaytarilgan"
    ]
    ws.append(headers)
    
    for order in orders:
        ws.append([
            order.order_id,
            order.order_status,  # Добавлено
            order.created_at.strftime("%Y-%m-%d %H:%M"),
            order.client_name,
            order.client_phone,
            order.client_passport,
            order.seller_name,
            order.item_count,
            order.sum_of_item,
            order.every_month_should_pay,
            order.prepaid,
            "Ha" if order.item_returned else "Yo'q"
        ])
    
    # Header styling
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    
    # Auto-adjust columns
    for column in ws.columns:
        max_length = max(
            len(str(cell.value)) for cell in column
        )
        adjusted_width = (max_length + 2) * 1.2
        ws.column_dimensions[column[0].column_letter].width = adjusted_width
    
    excel_buffer = BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer


async def get_all_sellers_with_details():
    async with async_session() as session:
        try:
            result = await session.execute(
                select(
                    Seller.id.label("seller_id"),
                    Seller.full_name.label("full_name"),
                    Seller.phone,
                    Seller.passport_serial,
                    Seller.started_job_at,
                    Seller.salary_of_seller.label("salary_of_seller")
                )
                .order_by(Seller.full_name)
            )
            return result.all()
        except Exception as e:
            print(f"Error fetching sellers: {str(e)}")
            return None

async def generate_sellers_excel():
    sellers = await get_all_sellers_with_details()
    if not sellers:
        return None
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Sellers"
    
    headers = [
        "ID", "To'liq ismi", "Telefon raqami", 
        "Passport seriyasi", "Ish boshlagan sana", "Maoshi"
    ]
    ws.append(headers)
    
    for seller in sellers:
        ws.append([
            seller.seller_id,
            seller.full_name,
            seller.phone,
            seller.passport_serial,
            seller.started_job_at.strftime("%Y-%m-%d") if seller.started_job_at else "",
            seller.salary_of_seller or ""
        ])
    
    # Header styling
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    
    # Auto-adjust columns
    for column in ws.columns:
        max_length = max(
            len(str(cell.value)) for cell in column
        )
        adjusted_width = (max_length + 2) * 1.2
        ws.column_dimensions[column[0].column_letter].width = adjusted_width
    
    excel_buffer = BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer

async def update_seller(seller_id: int, update_data: dict):
    """Обновление данных продавца с преобразованием типов данных"""
    async with async_session() as session:
        try:
            # Полный маппинг между именами полей
            field_mapping = {
                'full_name': 'full_name',
                'name': 'full_name',
                'phone': 'phone',
                'passport': 'passport_serial',
                'passport_serial': 'passport_serial',
                'salary': 'salary_of_seller',
                'salary_of_seller': 'salary_of_seller',
                'date': 'started_job_at',
                'start_date': 'started_job_at',
                'started_job_at': 'started_job_at'
            }
            
            # Проверяем и преобразуем данные
            db_update_data = {}
            
            for field, value in update_data.items():
                if field in field_mapping:
                    db_field = field_mapping[field]
                    
                    # Специальная обработка для полей даты
                    if db_field == 'started_job_at' and isinstance(value, str):
                        try:
                            db_update_data[db_field] = datetime.strptime(value, '%Y-%m-%d').date()
                        except ValueError:
                            raise ValueError("Noto'g'ri sana formati. To'g'ri format: YYYY-MM-DD")
                    else:
                        db_update_data[db_field] = value
            
            if not db_update_data:
                raise ValueError("Yangilanish uchun hech qanday maydon kiritilmadi")
            
            print(f"🔄 Yangilanish ma'lumotlari: {db_update_data}")
            
            await session.execute(
                update(Seller)
                .where(Seller.id == seller_id)
                .values(**db_update_data)
            )
            await session.commit()
            return True
            
        except ValueError as e:
            await session.rollback()
            raise ValueError(f"Ma'lumotlar formati noto'g'ri: {str(e)}")
        except Exception as e:
            await session.rollback()
            raise Exception(f"Xatolik yuz berdi: {str(e)}")
            
async def update_order(order_id: int, update_data: dict):
    """Обновление данных заказа с полной проверкой полей"""
    async with AsyncSessionLocal() as session:
        try:
            # Добавляем order_status в разрешенные поля
            allowed_fields = {
                'item_count', 'sum_of_item', 'every_month_should_pay',
                'prepaid', 'item_returned', 'order_status'
            }
            
            db_update_data = {
                field: value 
                for field, value in update_data.items() 
                if field in allowed_fields
            }
            
            if not db_update_data:
                raise ValueError("Yangilanish uchun hech qanday maydon kiritilmadi")
            
            # Автоматический пересчет remaining_amount
            if {'sum_of_item', 'prepaid'} & db_update_data.keys():
                order = await session.get(Order, order_id)
                if order:
                    new_sum = db_update_data.get('sum_of_item', order.sum_of_item)
                    new_prepaid = db_update_data.get('prepaid', order.prepaid)
                    db_update_data['remaining_amount'] = max(0, new_sum - new_prepaid)
            
            await session.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(**db_update_data)
            )
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            raise Exception(f"Xatolik yuz berdi: {str(e)}")


async def add_monthly_payment(order_id: int, amount: int):
    """Добавление ежемесячного платежа к заказу"""
    async with AsyncSessionLocal() as session:
        try:
            order = await session.get(Order, order_id)
            if not order:
                return False
                
            order.total_paid += amount
            order.remaining_amount = max(0, order.sum_of_item - order.total_paid)
            
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            raise e

async def get_order_by_id(order_id: int):
    """Получение заказа по ID"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Order).where(Order.id == order_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error getting order: {str(e)}")
            return None

async def get_seller_by_id(seller_id: int):
    """Получение продавца по ID"""
    async with async_session() as session:
        try:
            result = await session.execute(
                select(Seller).where(Seller.id == seller_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error getting seller: {str(e)}")
            return None