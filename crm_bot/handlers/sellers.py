from aiogram import Router, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from states import SellerStates, EditSellerStates, SearchSellerStates
from sqlalchemy import select
from database.crud import (
    generate_sellers_excel, 
    get_all_sellers_with_details, 
    update_seller,
    add_seller_to_db,
    get_seller_by_id_or_passport,
    delete_seller
)
from database.models import Seller
from database.utils import async_session
from config import Config
from datetime import datetime
from keyboards.types import (
    CANCEL_EDIT_BTN, VIEW_SELLER_BTN,
    FIELD_FULL_NAME, FIELD_PHONE,
    FIELD_SALARY, FIELD_START_DATE,
    BACK_TO_MAIN_MENU_BTN, SEARCH_BY_ID_BTN, SEARCH_BY_PASSPORT_BTN
)
from keyboards.builders import main_menu, back_to_main_menu
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re

router = Router()

# Define regex patterns
REGEX_PHONE = r'^\d{9}$'
REGEX_PASSPORT = r'^[A-Z]{2}\d{7}$'

# Helper function to format seller info
def format_seller_info(seller: Seller) -> str:
    return (
        f"👤 Sotuvchi: {seller.full_name}\n"
        f"📱 Telefon: {seller.phone}\n"
        f"🆔 ID: {seller.id}\n"
        f"📇 Passport: {seller.passport_serial}\n"
        f"💰 Maosh: {seller.salary_of_seller:,}\n"
        f"📅 Ish boshlagan sana: {seller.started_job_at}\n"
        f"🧮 Sotgan mahsulotlari soni: {seller.order_counter}\n"
    )

# Helper function to create edit buttons
def create_seller_edit_buttons(seller_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_seller_{seller_id}"),
        InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"delete_seller_{seller_id}")
    )
    return builder.as_markup()

# Common back to main menu handler
@router.message(F.text == BACK_TO_MAIN_MENU_BTN)
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=main_menu)

# Start adding new seller
@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == "📝 Yangi sotuvchi")
async def start_add_seller(message: types.Message, state: FSMContext):
    await state.set_state(SellerStates.FULL_NAME)
    await message.answer(
        "Sotuvchining to'liq ismini kiriting:",
        reply_markup=back_to_main_menu()
    )

# Process seller name
@router.message(SellerStates.FULL_NAME)
async def process_seller_name(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    await state.update_data(full_name=message.text)
    await state.set_state(SellerStates.PHONE)
    await message.answer(
        "Telefon raqamini kiriting (9 raqam, masalan: 901234567):",
        reply_markup=back_to_main_menu()
    )

# Process seller phone
@router.message(SellerStates.PHONE)
async def process_seller_phone(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    if not re.match(REGEX_PHONE, message.text):
        await message.answer(
            "❌ Noto'g'ri format! 9 ta raqam kiriting (901234567):",
            reply_markup=back_to_main_menu()
        )
        return
        
    await state.update_data(phone=message.text)
    await state.set_state(SellerStates.PASSPORT)
    await message.answer(
        "Pasport seriya va raqamini kiriting (AA1234567 formatida):",
        reply_markup=back_to_main_menu()
    )

# Process seller passport
@router.message(SellerStates.PASSPORT)
async def process_seller_passport(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    passport = message.text.upper()
    
    if not re.match(REGEX_PASSPORT, passport):
        await message.answer(
            "❌ Noto'g'ri format! AA1234567 formatida kiriting:",
            reply_markup=back_to_main_menu()
        )
        return
    
    # Check if passport already exists
    async with async_session() as session:
        result = await session.execute(
            select(Seller).where(Seller.passport_serial == passport)
        )
        existing_seller = result.scalar_one_or_none()
    
    if existing_seller:
        await message.answer(
            f"❌ Ushbu pasport seriyali sotuvchi mavjud:\n{format_seller_info(existing_seller)}",
            reply_markup=back_to_main_menu()
        )
        await state.clear()
        return
    
    await state.update_data(passport_serial=passport)
    await state.set_state(SellerStates.SALARY)
    await message.answer(
        "Maoshni kiriting:",
        reply_markup=back_to_main_menu()
    )

# Process seller salary
@router.message(SellerStates.SALARY)
async def process_seller_salary(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    try:
        salary = int(message.text)
        await state.update_data(salary_of_seller=salary)
        await state.set_state(SellerStates.START_DATE)
        await message.answer(
            "Ish boshlagan sanani kiriting (YYYY-MM-DD):",
            reply_markup=back_to_main_menu()
        )
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri format! Faqat raqam kiriting:",
            reply_markup=back_to_main_menu()
        )

# Process seller start date
@router.message(SellerStates.START_DATE)
async def process_seller_start_date(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    try:
        datetime.strptime(message.text, '%Y-%m-%d')
        await state.update_data(started_job_at=message.text)
        data = await state.get_data()
        
        # Add seller to database
        success = await add_seller_to_db(data)
        
        if success:
            await message.answer(
                "✅ Sotuvchi muvaffaqiyatli qo'shildi!",
                reply_markup=main_menu
            )
        else:
            await message.answer(
                "❌ Xatolik yuz berdi!",
                reply_markup=main_menu
            )
        await state.clear()
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri sana formati! YYYY-MM-DD formatida kiriting:",
            reply_markup=back_to_main_menu()
        )

# Send sellers list as Excel
@router.message(F.text == "📋 Sotuvchilar ro'yxati")
async def send_sellers_excel(message: types.Message):
    excel_buffer = await generate_sellers_excel()
    
    if not excel_buffer:
        await message.answer(
            "❌ Sotuvchilar topilmadi yoki xatolik yuz berdi",
            reply_markup=back_to_main_menu()
        )
        return
    
    filename = f"sellers_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    
    await message.answer_document(
        document=BufferedInputFile(
            file=excel_buffer.read(),
            filename=filename
        ),
        caption="📋 Barcha sotuvchilar ro'yxati"
    )

# Start seller search
@router.message(F.text == VIEW_SELLER_BTN)
async def start_search_seller(message: types.Message, state: FSMContext):
    await message.answer(
        "Qanday usulda qidirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=SEARCH_BY_ID_BTN, callback_data="search_by_id")],
            [InlineKeyboardButton(text=SEARCH_BY_PASSPORT_BTN, callback_data="search_by_passport")]
        ])
    )
    await state.set_state(SearchSellerStates.SELECT_SEARCH_METHOD)

# Handle search method selection
@router.callback_query(SearchSellerStates.SELECT_SEARCH_METHOD)
async def handle_search_method(callback: types.CallbackQuery, state: FSMContext):
    search_type = callback.data.split("_")[-1]
    await state.update_data(search_type=search_type)
    
    if search_type == "id":
        await callback.message.answer(
            "Sotuvchi ID sini kiriting:",
            reply_markup=back_to_main_menu()
        )
    else:  # passport
        await callback.message.answer(
            "Sotuvchi passport seriyasini kiriting (AA1234567 formatida):",
            reply_markup=back_to_main_menu()
        )
    
    await state.set_state(SearchSellerStates.ENTER_SEARCH_QUERY)
    await callback.answer()

# Process search query
@router.message(SearchSellerStates.ENTER_SEARCH_QUERY)
async def process_search_query(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    
    data = await state.get_data()
    search_type = data.get('search_type')
    
    try:
        if search_type == "id":
            seller_id = int(message.text)
            seller = await get_seller_by_id_or_passport(seller_id=seller_id)
        else:
            passport = message.text.upper()
            if not re.match(REGEX_PASSPORT, passport):
                await message.answer(
                    "❌ Noto'g'ri passport formati! AA1234567 formatida kiriting:",
                    reply_markup=back_to_main_menu()
                )
                return
            seller = await get_seller_by_id_or_passport(passport_serial=passport)
        
        if not seller:
            await message.answer(
                "❌ Sotuvchi topilmadi!",
                reply_markup=back_to_main_menu()
            )
            await state.clear()
            return
        
        await message.answer(
            format_seller_info(seller),
            reply_markup=create_seller_edit_buttons(seller.id)
        )
        await state.update_data(seller_id=seller.id)
        await state.set_state(SearchSellerStates.VIEW_SELLER)
        
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri ID formati! Faqat raqam kiriting:",
            reply_markup=back_to_main_menu()
        )

# Edit seller handler
@router.callback_query(F.data.startswith("edit_seller_"))
async def edit_seller_handler(callback: types.CallbackQuery, state: FSMContext):
    seller_id = int(callback.data.split("_")[-1])
    await state.update_data(seller_id=seller_id)
    
    keyboard = [
        [InlineKeyboardButton(text=FIELD_FULL_NAME, callback_data="edit_full_name")],
        [InlineKeyboardButton(text=FIELD_PHONE, callback_data="edit_phone")],
        [InlineKeyboardButton(text=FIELD_SALARY, callback_data="edit_salary")],
        [InlineKeyboardButton(text=FIELD_START_DATE, callback_data="edit_start_date")],
        [InlineKeyboardButton(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")]
    ]
    
    await callback.message.edit_text(
        "Qaysi maydonni tahrirlamoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(EditSellerStates.SELECT_FIELD)

# Select field to edit
@router.callback_query(EditSellerStates.SELECT_FIELD, F.data.startswith("edit_"))
async def select_field_to_edit(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_", "")
    await state.update_data(edit_field=field)
    
    data = await state.get_data()
    seller_id = data['seller_id']
    
    # Get current seller info
    seller = await get_seller_by_id_or_passport(seller_id=seller_id)
    if not seller:
        await callback.answer("❌ Sotuvchi topilmadi!")
        return
    
    current_value = getattr(seller, field, "Noma'lum")
    
    await callback.message.edit_text(
        f"Yangi qiymatni kiriting:\nHozirgi qiymat: {current_value}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")]
        ])
    )
    await state.set_state(EditSellerStates.ENTER_NEW_VALUE)

# Process new value for editing
@router.message(EditSellerStates.ENTER_NEW_VALUE)
async def process_new_value(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    
    data = await state.get_data()
    seller_id = data['seller_id']
    field = data['edit_field']
    
    try:
        # Validate and convert input based on field type
        if field == 'salary':
            new_value = int(message.text)
            db_field = 'salary_of_seller'
        elif field == 'start_date':
            datetime.strptime(message.text, '%Y-%m-%d')  # Validate date format
            new_value = message.text
            db_field = 'started_job_at'
        elif field == 'phone':
            if not re.match(REGEX_PHONE, message.text):
                raise ValueError("Telefon raqami 9 ta raqamdan iborat bo'lishi kerak")
            new_value = message.text
            db_field = 'phone'
        else:  # full_name
            new_value = message.text
            db_field = 'full_name'
        
        # Update seller in database
        success = await update_seller(seller_id, {db_field: new_value})
        
        if success:
            # Show updated seller info
            seller = await get_seller_by_id_or_passport(seller_id=seller_id)
            await message.answer(
                "✅ Muvaffaqiyatli yangilandi!\n" + format_seller_info(seller),
                reply_markup=create_seller_edit_buttons(seller.id)
            )
        else:
            await message.answer(
                "❌ Yangilashda xatolik yuz berdi!",
                reply_markup=back_to_main_menu()
            )
        
        await state.clear()
    
    except ValueError as e:
        await message.answer(
            f"❌ Noto'g'ri format! {str(e)}",
            reply_markup=back_to_main_menu()
        )
    except Exception as e:
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=back_to_main_menu()
        )

# Delete seller handler
@router.callback_query(F.data.startswith("delete_seller_"))
async def delete_seller_handler(callback: types.CallbackQuery, state: FSMContext):
    seller_id = int(callback.data.split("_")[-1])
    await state.update_data(seller_id=seller_id)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_seller_delete_{seller_id}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_delete")
    )   
    
    await callback.message.edit_text(
        f"⚠️ Sotuvchini o'chirib tashlamoqchimisiz? (ID: {seller_id})",
        reply_markup=builder.as_markup()
    )

# Confirm delete
@router.callback_query(F.data.startswith("confirm_seller_delete_"))
async def confirm_delete_handler(callback: types.CallbackQuery, state: FSMContext):
    seller_id = int(callback.data.split("_")[-1])
    
    success = await delete_seller(seller_id)
    
    if success:
        await callback.message.edit_text(f"✅ Sotuvchi #{seller_id} o'chirib tashlandi!", reply_markup=main_menu)
    else:
        await callback.message.edit_text("❌ Xatolik yuz berdi!")
    
    await state.clear()

# Cancel delete
@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ O'chirish bekor qilindi.")
    await state.clear()

def register_handlers(dp):
    dp.include_router(router)