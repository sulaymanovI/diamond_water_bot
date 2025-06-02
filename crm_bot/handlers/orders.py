from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from typing import Union
from database.utils import async_session
from aiogram.types import BufferedInputFile
from states import OrderStates, ViewOrderStates, EditOrderStates
from aiogram.filters import Command
from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy import select
from aiogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton)
from database.crud import (
    get_all_orders_with_details, 
    get_order_by_id_with_details,
    update_order,
    delete_order)
from keyboards.types import (
    CANCEL_EDIT_BTN, FIELD_ITEM_COUNT, 
    FIELD_TOTAL_SUM, FIELD_MONTHLY_PAY, 
    FIELD_PREPAID, VIEW_ORDER_BTN,
    FIELD_RETURNED, BACK_TO_MAIN_MENU_BTN,
    FIELD_STATUS_ORDER
)  
from keyboards.builders import main_menu, back_to_main_menu
from database.models import Order, Client, Seller
from config import Config
from database.crud import (
    get_seller_by_passport, 
    get_client_by_passport,
    create_order,
    generate_orders_excel
)
import re
from aiogram.utils.keyboard import InlineKeyboardBuilder

ORDER_STATUS_OPTIONS = ["Ochiq", "Yopilgan", "Qaytarilgan"]

router = Router()

# Define regex patterns
REGEX_PASSPORT = r'^[A-Z]{2}\d{7}$'

@router.message(F.text == BACK_TO_MAIN_MENU_BTN)
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum, *Diamond Water CRM* ga xush kelibsiz!\n\n"
        "Yangi funksiya bajarish uchun pastdagi tugmalardan foydalanishingiz mumkin 👇",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == "📝 Yangi buyurtma")
async def start_add_order(message: types.Message, state: FSMContext):
    await state.set_state(OrderStates.CLIENT_PASSPORT)
    await message.answer(
        "Mijozning pasport seriya va raqamini kiriting (AA1234567 formatida):",
        reply_markup=back_to_main_menu())

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), OrderStates.CLIENT_PASSPORT)
async def process_client_passport(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    passport = message.text.upper()  # Convert to uppercase for consistency
    
    # Validate passport format
    if not re.match(REGEX_PASSPORT, passport):
        await message.answer(
            "❌ Noto'g'ri pasport formati! Iltimos, AA1234567 formatida kiriting (2 ta harf va 7 ta raqam):",
            reply_markup=back_to_main_menu()
        )
        return

    client = await get_client_by_passport(passport)
    
    if client:
        await state.update_data(
            client_id=client.id,
            client_passport=passport,
            client_full_name=client.full_name
        )
    else:
        await state.update_data(client_passport=passport)
    
    await message.answer("Mahsulot miqdorini kiriting:",
    reply_markup=back_to_main_menu())
    await state.set_state(OrderStates.ITEM_COUNT)

def format_location(latitude: float, longitude: float) -> str:
    if latitude and longitude:
        return f"📍 Joylashuv: {latitude:.6f}, {longitude:.6f}\n🌐 Google Maps: https://maps.google.com/?q={latitude},{longitude}"
    return "📍 Joylashuv: Ko'rsatilmagan"


@router.callback_query(ViewOrderStates.CHOOSE_STATUS, F.data.startswith("set_status_"))
async def process_status_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'order_id' not in data:
        await callback.answer("❌ ID заказа не найден")
        return
    
    status = callback.data.replace("set_status_", "").capitalize()
    
    if status not in ORDER_STATUS_OPTIONS:
        await callback.answer("❌ Noto'g'ri holat tanlandi")
        return
    
    success = await update_order(data['order_id'], {'order_status': status})
    
    if success:
        await callback.message.edit_text(f"✅ Buyurtma holati '{status}' ga o'zgartirildi!")
        await show_order_after_edit(data['order_id'], callback.message)
    else:
        await callback.message.edit_text("❌ Xatolik yuz berdi! Holat yangilanmadi.")
    
    await state.clear()

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), OrderStates.ITEM_COUNT)
async def process_item_count(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    try:
        count = int(message.text)
        if count <= 0:
            await message.answer("Iltimos, 0 dan katta son kiriting!")
            return
        await state.update_data(item_count=count)
        await message.answer("Mahsulotning umumiy summasini kiriting:",
        reply_markup=back_to_main_menu())
        await state.set_state(OrderStates.SUM_OF_ITEM)
    except ValueError:
        await message.answer("Iltimos, raqam kiriting!")

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), OrderStates.SUM_OF_ITEM)
async def process_sum_of_item(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    try:
        sum_of_item = int(message.text.replace(" ", "").replace(",", ""))
        if sum_of_item <= 0:
            await message.answer("Iltimos, 0 dan katta summa kiriting!")
            return
        await state.update_data(sum_of_item=sum_of_item)
        await message.answer("Har oy to'lanadigan summani kiriting:",
        reply_markup=back_to_main_menu())
        await state.set_state(OrderStates.MONTHLY_PAYMENT)
    except ValueError:
        await message.answer("Iltimos, raqam kiriting!")

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), OrderStates.MONTHLY_PAYMENT)
async def process_monthly_payment(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    try:
        monthly_payment = int(message.text.replace(" ", "").replace(",", ""))
        if monthly_payment <= 0:
            await message.answer("Iltimos, 0 dan katta summa kiriting!")
            return
        await state.update_data(every_month_should_pay=monthly_payment)
        await message.answer("Oldindan to'lov miqdorini kiriting (0 bo'lsa 0 yozing):",
        reply_markup=back_to_main_menu())
        await state.set_state(OrderStates.PREPAID_AMOUNT)  
    except ValueError:
        await message.answer("Iltimos, raqam kiriting!")

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), OrderStates.PREPAID_AMOUNT)
async def process_prepaid_amount(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    try:
        prepaid = int(message.text.replace(" ", "").replace(",", ""))
        if prepaid < 0:
            await message.answer("Iltimos, musbat son kiriting!")
            return
            
        await state.update_data(prepaid=prepaid)
        
        # Переносим логику показа продавцов сюда
        data = await state.get_data()
        
        if not data.get('client_id') and not data.get('client_passport'):
            await message.answer("❌ Mijoz ma'lumotlari yo'q.")
            await state.clear()
            return

        async with async_session() as session:
            result = await session.execute(select(Seller))
            sellers = result.scalars().all()

        if not sellers:
            await message.answer("❌ Sotuvchilar topilmadi! Iltimos, avval sotuvchi qo'shing.", reply_markup=main_menu)
            await state.clear()
            return

        builder = InlineKeyboardBuilder()
        for seller in sellers:
            builder.button(
                text=f"{seller.full_name} - {seller.passport_serial}",
                callback_data=f"seller_select:{seller.id}"
            )
        builder.adjust(1)
        
        await message.answer(
            "Iltimos, sotuvchini tanlang:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(OrderStates.SELLER_PASSPORT)
            
    except ValueError:
        await message.answer("Iltimos, raqam kiriting!")
    except Exception as e:
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                           reply_markup=back_to_main_menu())
        await state.clear()

@router.callback_query(F.data.startswith("seller_select:"))
async def handle_seller_selection(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        try:
            seller_id = int(callback.data.split(":")[1])
            data = await state.get_data()
            
            # Get seller details
            seller = await session.get(Seller, seller_id)
            if not seller:
                await callback.answer("❌ Sotuvchi topilmadi!")
                return
                
            # Get client details if exists
            client = None
            if data.get('client_id'):
                client = await session.get(Client, data['client_id'])
            
            if client:
                # Create order if client exists
                order_data = {
                    'client_id': client.id,
                    'seller_id': seller.id,
                    'item_count': data['item_count'],
                    'sum_of_item': data['sum_of_item'],
                    'every_month_should_pay': data['every_month_should_pay'],
                    'prepaid': data.get('prepaid', 0),
                    'order_status': 'Ochiq'
                }
                order = Order(**order_data)
                session.add(order)
                
                # Обновляем счетчик
                seller.order_counter += 1
                
                await session.commit()

                # Get client location if available
                location_info = ""
                if client.latitude and client.longitude:
                    location_info = format_location(client.latitude, client.longitude) + "\n\n"

                await callback.message.answer(
                    f"✅ #{order.id}-buyurtma muvaffaqiyatli yaratildi!\n"
                    f"👤 Sotuvchi: {seller.full_name}\n"
                    f"📊 Sotuvchining jami buyurtmalari: {seller.order_counter}\n"
                    f"👤 Mijoz: {client.full_name}\n"
                    f"📞 Mijoz tel: {client.phone}\n"
                    f"{location_info}"
                    f"📦 Mahsulot soni: {data['item_count']} ta\n"
                    f"💰 Umumiy summa: {data['sum_of_item']:,} so'm\n"
                    f"📅 Oylik to'lov: {data['every_month_should_pay']:,} so'm\n"
                    f"💵 Oldindan to'lov: {data.get('prepaid', 0):,} so'm",
                    reply_markup=main_menu
                )
            else:
                # Proceed to collect new client info
                await state.update_data(seller_id=seller.id)
                await callback.message.answer(
                    f"Sotuvchi tanlandi: {seller.full_name}\n"
                    f"📊 Jami buyurtmalar: {seller.order_counter}\n"
                    "Yangi mijozning to'liq ismini kiriting:",
                    reply_markup=back_to_main_menu()
                )
                await state.set_state(OrderStates.CLIENT_FULLNAME)
            
            await callback.answer()
        except Exception as e:
            await session.rollback()
            await callback.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == "📋 Buyurtmalar ro'yxati")
async def send_orders_excel(message: types.Message):
    excel_buffer = await generate_orders_excel()
    
    if not excel_buffer:
        await message.answer("❌ Buyurtmalar topilmadi yoki xatolik yuz berdi", reply_markup=back_to_main_menu())
        return
    
    # Create a filename with current date
    filename = f"orders_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    
    # Send the Excel file with location info in caption
    await message.answer_document(
        document=BufferedInputFile(
            file=excel_buffer.read(),
            filename=filename
        ),
        caption="📊 Barcha buyurtmalar ro'yxati\n📍 Joylashuvlar bilan"
    )


# 2. Обработчик для начала просмотра заказа
@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == VIEW_ORDER_BTN)
async def view_order_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Ko'rish uchun buyurtma ID sini kiriting:",
        reply_markup=back_to_main_menu()  # Кнопка возврата в главное меню
    )
    await state.set_state(ViewOrderStates.ENTER_ORDER_ID)

# 3. Получение ID заказа и отображение информации
@router.message(ViewOrderStates.ENTER_ORDER_ID)
async def get_order_by_id(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return

    try:
        order_id = int(message.text)
        # Assuming get_order_by_id_with_details returns an Order object with joined client info
        order = await get_order_by_id_with_details(order_id)
        
        if not order:
            await message.answer("❌ Buyurtma topilmadi", reply_markup=back_to_main_menu())
            return

        # Format order information
        location_info = ""
        if hasattr(order.client, 'latitude') and order.client.latitude:
            location_info = format_location(order.client.latitude, order.client.longitude) + "\n\n"

        # Format order information
        order_info = (
            f"📋 Buyurtma #{order.id}\n"
            f"👤 Mijoz: {order.client.full_name}\n"
            f"📞 Tel: {order.client.phone}\n"
            f"{location_info}"
            f"📦 Mahsulot soni: {order.item_count}\n"
            f"💰 Umumiy summa: {order.sum_of_item:,}\n"
            f"💳 To'langan: {order.total_paid:,}\n"
            f"🔄 Har oy to'lashi kerak: {order.every_month_should_pay}\n"
            f"🔄 Qoldiq: {order.remaining_amount:,}\n"
            f"🔄 Holat: {order.order_status}\n"
            f"📅 Sana: {order.created_at.strftime('%Y-%m-%d %H:%M')}"
        )

        # Create inline buttons
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"order_edit_{order.id}"),
            InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"delete_order_{order.id}")
        )
        builder.row(
            InlineKeyboardButton(text="➕ To'langan summasiga qo'shish", callback_data=f"add_total_paid_{order.id}")
        )
        
        await message.answer(
            order_info,
            reply_markup=builder.as_markup()
        )
        await state.set_state(ViewOrderStates.VIEW_ORDER)
        await state.update_data(order_id=order_id)

    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.", reply_markup=back_to_main_menu())

@router.callback_query(F.data.startswith("add_total_paid_"))
async def add_total_paid_handler(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[-1])
    await state.update_data(order_id=order_id)
    await callback.message.answer(
        "💵 Qo'shimcha to'lov miqdorini kiriting:",
        reply_markup=back_to_main_menu()
    )
    await state.set_state(ViewOrderStates.ADD_PAYMENT)

@router.message(ViewOrderStates.ADD_PAYMENT)
async def process_add_payment(message: types.Message, state: FSMContext):
    async with async_session() as session: 
        if message.text == BACK_TO_MAIN_MENU_BTN:
            await handle_back_to_main_menu(message, state)
            return

        try:
            payment_amount = int(message.text)
            if payment_amount <= 0:
                raise ValueError
            
            data = await state.get_data()
            order_id = data.get('order_id')
            
            # Получаем заказ из БД
            order = await session.get(Order, order_id)
            if not order:
                await message.answer("❌ Buyurtma topilmadi")
                return

            # Обновляем суммы
            order.total_paid += payment_amount
            order.remaining_amount = max(0, order.sum_of_item - order.total_paid)
            
            # Обновляем статус если полностью оплачено
            if order.remaining_amount <= 0:
                order.order_status = 'Yopilgan'

            await session.commit()
            
            # Формируем обновленную информацию о заказе
            order_info = (
                f"✅ {payment_amount:,} so'm qo'shildi!\n\n"
                f"📋 Buyurtma #{order.id}\n"
                f"💰 Umumiy summa: {order.sum_of_item:,}\n"
                f"💳 To'langan: {order.total_paid:,}\n"
                f"🔄 Qoldiq: {order.remaining_amount:,}\n"
                f"🔄 Holat: {order.order_status}"
            )
            
            await message.answer(order_info, reply_markup=back_to_main_menu())
            await state.clear()

        except ValueError:
            await message.answer(
                "❌ Noto'g'ri format! Faqat musbat butun son kiriting.",
                reply_markup=back_to_main_menu()
            )
@router.callback_query(F.data.startswith("order_edit_"))
async def edit_order_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "edit_order_status":
        data = await state.get_data()
        if 'order_id' not in data:
            await callback.answer("❌ Сначала выберите заказ")
            return
        order_id = data['order_id']
    else:
        try:
            order_id = int(callback.data.split("_")[-1])
        except (ValueError, IndexError):
            await callback.answer("❌ Неверный ID заказа")
            return
    
    await state.update_data(order_id=order_id)
    
    keyboard = [
        [InlineKeyboardButton(text=FIELD_ITEM_COUNT, callback_data="edit_item_count")],
        [InlineKeyboardButton(text=FIELD_TOTAL_SUM, callback_data="edit_sum_of_item")],
        [InlineKeyboardButton(text=FIELD_MONTHLY_PAY, callback_data="edit_every_month_should_pay")],
        [InlineKeyboardButton(text=FIELD_PREPAID, callback_data="edit_prepaid")],
        # Removed FIELD_RETURNED since it's now part of status
        [InlineKeyboardButton(text=FIELD_STATUS_ORDER, callback_data="edit_order_status")],
        [InlineKeyboardButton(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")]
    ]
    
    await callback.message.edit_text(
        "Qaysi maydonni tahrirlamoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ViewOrderStates.SELECT_FIELD)

@router.callback_query(ViewOrderStates.SELECT_FIELD, F.data == "edit_order_status")
async def edit_order_status_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'order_id' not in data:
        await callback.answer("❌ ID заказа не найден")
        return
    
    order = await get_order_by_id_with_details(data['order_id'])
    
    # Create keyboard with status options
    keyboard = InlineKeyboardBuilder()
    for status in ORDER_STATUS_OPTIONS:
        keyboard.button(text=status, callback_data=f"set_status_{status.lower()}")
    keyboard.button(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        f"Joriy holat: {order.order_status}\n"
        "Yangi holatni tanlang:",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(ViewOrderStates.CHOOSE_STATUS)

# 5. Обработчик выбора поля для редактирования (исправленная версия)
@router.callback_query(ViewOrderStates.SELECT_FIELD, F.data.startswith("edit_"))
async def select_field_to_edit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'order_id' not in data:
        await callback.answer("❌ ID заказа не найден")
        return
    
    field = callback.data.replace("edit_", "")
    await state.update_data(edit_field=field)
    
    # Получаем текущее значение поля
    order = await get_order_by_id_with_details(data['order_id'])
    current_value = getattr(order, field, "Noma'lum")
    
    await callback.message.edit_text(
        f"Yangi qiymatni kiriting:\n"
        f"Hozirgi qiymat: {current_value}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")]
        ])
    )
    await state.set_state(ViewOrderStates.ENTER_NEW_VALUE)

# 6. Обработка ввода нового значения
@router.message(ViewOrderStates.ENTER_NEW_VALUE)
async def process_new_value(message: types.Message, state: FSMContext):
    if message.text == CANCEL_EDIT_BTN:
        await handle_cancel_edit(message, state)
        return
    
    data = await state.get_data()
    order_id = data['order_id']
    field = data['edit_field']
    
    try:
        # Преобразуем значение в правильный тип
        if field in ['item_count', 'sum_of_item', 'every_month_should_pay', 'prepaid']:
            new_value = int(message.text)
        elif field == 'order_status':
            status = message.text.strip().capitalize()
            if status not in ORDER_STATUS_OPTIONS:
                await message.answer(f"❌ Noto'g'ri status! Faqat {', '.join(ORDER_STATUS_OPTIONS)} kiriting.")
                return
            new_value = status
        else:
            new_value = message.text
        
        # Обновляем заказ в базе данных
        success = await update_order(order_id, update_data={field: new_value})
        
        if success:
            await message.answer("✅ Buyurtma muvaffaqiyatli yangilandi!")
            await show_order_after_edit(order_id, message)
        else:
            await message.answer("❌ Xatolik yuz berdi! Buyurtma yangilanmadi.")
        
        await state.clear()
    
    except ValueError as e:
        await message.answer(f"❌ Noto'g'ri format! {str(e)}")

# 7. Отмена редактирования
@router.callback_query(F.data == "cancel_edit")
async def cancel_edit_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'order_id' in data:
        await show_order_after_edit(data['order_id'], callback.message)
    await state.clear()
    await callback.answer("❌ Tahrirlash bekor qilindi.")

async def show_order_after_edit(order_id: int, message: Union[types.Message, types.CallbackQuery]):
    if isinstance(message, types.CallbackQuery):
        message = message.message
    
    order = await get_order_by_id_with_details(order_id)
    
    # Get client location if available
    location_info = ""
    if hasattr(order.client, 'latitude') and order.client.latitude:
        location_info = format_location(order.client.latitude, order.client.longitude) + "\n\n"

    order_info = (
        f"📋 Buyurtma #{order.id}\n"
        f"👤 Mijoz: {order.client.full_name}\n"
        f"📞 Tel: {order.client.phone}\n"
        f"{location_info}"
        f"📦 Mahsulot soni: {order.item_count}\n"
        f"💰 Umumiy summa: {order.sum_of_item:,}\n"
        f"💳 To'langan: {order.total_paid:,}\n"
        f"🔄 Har oy to'lashi kerak: {order.every_month_should_pay:,}\n"
        f"🔄 Qoldiq: {order.remaining_amount:,}\n"
        f"🔄 Holat: {order.order_status}\n"
        f"📅 Sana: {order.created_at.strftime('%Y-%m-%d %H:%M')}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"order_edit_{order.id}"),
        InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"delete_order_{order.id}")
    )
    
    await message.answer(
        order_info,
        reply_markup=builder.as_markup()
    )

# 6. Обработка кнопки удаления
@router.callback_query(F.data.startswith("delete_order_"))
async def delete_order_handler(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[-1])
    await state.update_data(order_id=order_id)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_order_delete_{order_id}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_delete")
    )
    
    await callback.message.edit_text(
        f"⚠️ Buyurtmani o'chirib tashlamoqchimisiz? (ID: {order_id})",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("confirm_order_delete_"))
async def confirm_delete_handler(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        order_id = int(callback.data.split("_")[-1])
        
        try:
            # Явно загружаем продавца вместе с заказом
            order = await session.get(Order, order_id, options=[joinedload(Order.seller)])
            if not order:
                await callback.message.edit_text(
                    "❌ Buyurtma topilmadi!",
                    reply_markup=main_menu  # Добавляем reply_markup
                )
                return
            
            seller = order.seller
            
            # Удаляем заказ и обновляем счетчик
            await session.delete(order)
            seller.order_counter = max(0, seller.order_counter - 1)
            
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ Buyurtma #{order_id} o'chirib tashlandi!\n"
                f"📊 Sotuvchi {seller.full_name}ning buyurtmalar soni: {seller.order_counter}",
                reply_markup=main_menu
            )
            
        except Exception as e:
            await session.rollback()
            # Добавляем reply_markup в сообщение об ошибке
            await callback.message.edit_text(
                f"❌ Xatolik yuz berdi: {str(e)}",
                reply_markup=main_menu
            )
            
        finally:
            await state.clear()

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ O'chirish bekor qilindi.")
    await state.clear()

def register_handlers(dp):
    dp.include_router(router)