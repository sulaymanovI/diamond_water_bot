from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from database.utils import async_session
from aiogram.types import BufferedInputFile
from states import OrderStates
from aiogram.filters import Command
from datetime import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.crud import get_all_orders_with_details, update_order
from keyboards.types import (
    CANCEL_EDIT_BTN, FIELD_ITEM_COUNT, 
    FIELD_TOTAL_SUM, FIELD_MONTHLY_PAY, 
    FIELD_PREPAID, EDIT_ORDER_BTN,
    FIELD_RETURNED, BACK_TO_MAIN_MENU_BTN
    )  
from states import EditOrderStates
from keyboards.builders import main_menu, back_to_main_menu
from database.models import Order, Client
from config import Config
from database.crud import (
    get_seller_by_passport, 
    get_client_by_passport,
    create_order,
    generate_orders_excel
)

router = Router()

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
        "Mijozning pasport seriya va raqamini kiriting:",
        reply_markup=back_to_main_menu())

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), OrderStates.CLIENT_PASSPORT)
async def process_client_passport(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    passport = message.text
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

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), OrderStates.ITEM_COUNT)
async def process_item_count(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    try:
        count = int(message.text)
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
        sum_of_item = int(message.text)
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
        monthly_payment = int(message.text)
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
        prepaid = int(message.text)
        if prepaid < 0:
            await message.answer("Iltimos, musbat son kiriting!")
            return
            
        await state.update_data(prepaid=prepaid)
        await message.answer("Sotuvchining pasport seriya va raqamini kiriting:",
        reply_markup=back_to_main_menu())
        await state.set_state(OrderStates.SELLER_PASSPORT)
    except ValueError:
        await message.answer("Iltimos, raqam kiriting!")

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), OrderStates.SELLER_PASSPORT)
async def process_seller_passport(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    try:
        data = await state.get_data()
        print("Current state data:", data)
        
        client_id = data.get('client_id')
        client_passport = data.get('client_passport')
        
        if not client_id and not client_passport:
            await message.answer("❌ Mijoz ma'lumotlari yo'q.")
            await state.clear()
            return

        seller = await get_seller_by_passport(message.text)
        if not seller:
            await message.answer("❌ Sotuvchi topilmadi! Uni ro'yxatdan o'tkazing.", reply_markup=back_to_main_menu())
            await state.clear()
            return

        if client_id:
            async with async_session() as session:
                client = await session.get(Client, client_id)
                
            order_data = {
                'client_id': client.id,
                'seller_id': seller.id,
                'item_count': data['item_count'],
                'sum_of_item': data['sum_of_item'],
                'every_month_should_pay': data['every_month_should_pay'],
                'prepaid': data.get('prepaid', 0),
                'item_returned': False,
                'order_status': 'Ochiq'  # Добавлено
            }
            order = await create_order(order_data)

            await message.answer(
                f"✅ #{order.id}-buyurtma yaratildi!\n"
                f"Mijoz: {client.full_name}\n"
                f"Mahsulot: {data['item_count']} ta\n"
                f"Umumiy summa: {data['sum_of_item']} so'm\n"
                f"Har oy to'lov: {data['every_month_should_pay']} so'm\n"
                f"Oldindan to'lov: {data.get('prepaid', 0)} so'm"
            )
            await state.clear()
            
        else: 
            await state.update_data(seller_id=seller.id)
            await message.answer("Yangi mijozning to'liq ismini kiriting:",
            reply_markup=back_to_main_menu())
            await state.set_state(OrderStates.CLIENT_FULLNAME)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        await message.answer("❌ Tizimda xatolik yuz berdi. Qayta urinib ko'ring.",
        reply_markup=back_to_main_menu())
        await state.clear()

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == "📊 Buyurtmalar ro'yxati")
async def send_orders_excel(message: types.Message):
    excel_buffer = await generate_orders_excel()
    
    if not excel_buffer:
        await message.answer("❌ Buyurtmalar topilmadi yoki xatolik yuz berdi", reply_markup=back_to_main_menu())
        return
    
    # Create a filename with current date
    filename = f"orders_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    
    # Send the Excel file
    await message.answer_document(
        document=BufferedInputFile(
            file=excel_buffer.read(),
            filename=filename
        ),
        caption="📊 Barcha buyurtmalar ro'yxati"
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == EDIT_ORDER_BTN)
async def edit_order_start(message: types.Message, state: FSMContext):
    orders = await get_all_orders_with_details()
    if not orders:
        await message.answer("❌ Buyurtmalar topilmadi",
        reply_markup=back_to_main_menu())
        return
    
    keyboard = []
    for order in orders:
        keyboard.append([
            InlineKeyboardButton(
                text=f"#{order.order_id} - {order.client_name}",
                callback_data=f"edit_order_{order.order_id}"
            )
        ])
    
    await message.answer(
        "Tahrirlash uchun buyurtmani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(EditOrderStates.SELECT_ORDER)


FIELD_STATUS = "Status (Ochiq/Yopilgan)"

@router.callback_query(EditOrderStates.SELECT_ORDER, F.data.startswith("edit_order_"))
async def select_order_to_edit(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[-1])
    await state.update_data(order_id=order_id)
    
    keyboard = [
        [InlineKeyboardButton(text=FIELD_ITEM_COUNT, callback_data="field_item_count")],
        [InlineKeyboardButton(text=FIELD_TOTAL_SUM, callback_data="field_sum_of_item")],
        [InlineKeyboardButton(text=FIELD_MONTHLY_PAY, callback_data="field_monthly_pay")],
        [InlineKeyboardButton(text=FIELD_PREPAID, callback_data="field_prepaid")],
        [InlineKeyboardButton(text=FIELD_RETURNED, callback_data="field_returned")],
        [InlineKeyboardButton(text=FIELD_STATUS, callback_data="field_order_status")],  # Добавлено
        [InlineKeyboardButton(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")]
    ]
    
    await callback.message.edit_text(
        "Qaysi maydonni tahrirlamoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(EditOrderStates.SELECT_FIELD)

@router.callback_query(EditOrderStates.SELECT_FIELD, F.data.startswith("field_"))
async def select_order_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[-1]
    await state.update_data(field=field)
    
    if field == 'returned':
        text = "Mahsulot qaytarilganmi? (Ha/Yo'q)"
    else:
        text = "Yangi qiymatni kiriting:"
    
    await callback.message.edit_text(text)
    await state.set_state(EditOrderStates.ENTER_NEW_VALUE)

@router.message(EditOrderStates.ENTER_NEW_VALUE)
async def save_order_changes(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return

    data = await state.get_data()
    order_id = data['order_id']
    field = data['field']
    print(field)

    try:
        if field == 'status':  # Обработка статуса
            status = message.text.strip().capitalize()
            if status not in ('Yopilgan', 'Ochiq'):
                raise ValueError("Status must be 'Yopilgan' or 'Ochiq'")
            value = status
            field_name = 'order_status'
        elif field == 'count':
            value = int(message.text)
            field_name = 'item_count'
        elif field == 'item':
            value = int(message.text.replace(" ", "").replace(",", ""))
            field_name = 'sum_of_item'
        elif field == 'pay':
            value = int(message.text.replace(" ", "").replace(",", ""))
            field_name = 'every_month_should_pay'
        elif field == 'prepaid':
            value = int(message.text.replace(" ", "").replace(",", ""))
            field_name = 'prepaid'
        elif field == 'returned':
            value = message.text.lower() in ('ha', 'yes', 'true', '1', 'да')
            field_name = 'item_returned'
        else:
            raise ValueError("Noma'lum maydon turi")
        
        update_data = {field_name: value}
        success = await update_order(order_id, update_data)
        
        if success:
            await message.answer("✅ Buyurtma muvaffaqiyatli yangilandi!", reply_markup=back_to_main_menu())
        else:
            await message.answer("❌ Xatolik yuz berdi!", reply_markup=back_to_main_menu())
            
    except ValueError as e:
        error_msg = "❌ Noto'g'ri format! "
        if field == 'order_status':
            error_msg += "Faqat 'Yopilgan' yoki 'Ochiq' kiriting!"
        elif field == 'item_count':
            error_msg += "Mahsulot soni butun son bo'lishi kerak."
        elif field in ['sum_of_item', 'monthly_pay', 'prepaid']:
            error_msg += "Butun son kiriting (masalan: 125000)."
        elif field == 'returned':
            error_msg += "Iltimos, 'Ha' yoki 'Yo'q' kiriting."
        
        await message.answer(error_msg, reply_markup=back_to_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}", reply_markup=back_to_main_menu())
    
    await state.clear()

@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Tahrirlash bekor qilindi.")

def register_handlers(dp):
    dp.include_router(router)