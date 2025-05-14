from aiogram import Router, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from states import SellerStates, EditSellerStates
from sqlalchemy import select
from database.crud import (
    generate_sellers_excel, 
    get_all_sellers_with_details, 
    update_seller,
    add_seller_to_db
)
from database.models import Seller
from database.utils import async_session
from config import Config
from datetime import datetime
from keyboards.types import (
    EDIT_SELLER_BTN, CANCEL_EDIT_BTN,
    FIELD_FULL_NAME, FIELD_PHONE,
    FIELD_SALARY, FIELD_START_DATE,
    BACK_TO_MAIN_MENU_BTN
)
from keyboards.builders import main_menu, back_to_main_menu

router = Router()

@router.message(F.text == BACK_TO_MAIN_MENU_BTN)
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(   
        "Asosiy menyu:",
        reply_markup=main_menu
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == "➕ Yangi sotuvchi")
async def start_add_seller(message: types.Message, state: FSMContext):
    await state.set_state(SellerStates.FULL_NAME)
    await message.answer(
        "Sotuvchining to'liq ismini kiriting:",
        reply_markup=back_to_main_menu())

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), SellerStates.FULL_NAME)
async def process_seller_name(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    await state.update_data(full_name=message.text)
    await state.set_state(SellerStates.PHONE)
    await message.answer(
        "Endi sotuvchining telefon raqamini kiriting:",
        reply_markup=back_to_main_menu()
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), SellerStates.PHONE)
async def process_seller_phone(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    await state.update_data(phone=message.text)
    await state.set_state(SellerStates.PASSPORT)
    await message.answer(
        "Sotuvchining pasport seriya va raqamini kiriting:",
        reply_markup=back_to_main_menu()
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), SellerStates.PASSPORT)
async def process_seller_passport(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    passport = message.text
    
    async with async_session() as session:
        result = await session.execute(
            select(Seller).where(Seller.passport_serial == passport)
        )
        existing_seller = result.scalar_one_or_none()
    
    if existing_seller:
        await message.answer(
            "❌ Ushbu pasport seriyali sotuvchi allaqachon mavjud!\n"
            f"To'liq ismi: {existing_seller.full_name}\n"
            f"Telefon raqami: {existing_seller.phone}\n"
            f"Ishga kirgan sanasi: {existing_seller.started_job_at}\n"
            f"Maoshi: {existing_seller.salary_of_seller}\n",
            reply_markup=back_to_main_menu()
        )
        await state.clear()
        return
    
    await state.update_data(passport_serial=passport)
    await state.set_state(SellerStates.SALARY)
    await message.answer(
        "Sotuvchining maoshini kiriting:",
        reply_markup=back_to_main_menu()
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), SellerStates.SALARY)
async def process_seller_salary(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    try:
        salary = int(message.text)
        await state.update_data(salary_of_seller=salary)
        await state.set_state(SellerStates.START_DATE)
        await message.answer(
            "Ishga kirgan sanasini kiriting (YYYY-MM-DD):",
            reply_markup=back_to_main_menu()
        )
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri format! Faqat raqam kiriting:",
            reply_markup=back_to_main_menu()
        )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), SellerStates.START_DATE)
async def process_seller_start_date(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    try:
        datetime.strptime(message.text, '%Y-%m-%d')
        await state.update_data(started_job_at=message.text)
        data = await state.get_data()
        await add_seller_to_db(data)
        await state.clear()
        await message.answer(
            "✅ Sotuvchi muvaffaqiyatli qo'shildi!",
            reply_markup=main_menu
        )
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri sana formati! Iltimos, YYYY-MM-DD formatida kiriting:",
            reply_markup=back_to_main_menu()
        )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == "📋 Sotuvchilar ro'yxati")
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
    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == EDIT_SELLER_BTN)
async def edit_seller_start(message: types.Message, state: FSMContext):
    sellers = await get_all_sellers_with_details()
    if not sellers:
        await message.answer(
            "❌ Sotuvchilar topilmadi",
            reply_markup=back_to_main_menu()
        )
        return
    
    keyboard = []
    for seller in sellers:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{seller.full_name} - {seller.phone}",
                callback_data=f"edit_seller_{seller.seller_id}"
            )
        ])
    
    await message.answer(
        "Tahrirlash uchun sotuvchini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(EditSellerStates.SELECT_SELLER)

@router.callback_query(EditSellerStates.SELECT_SELLER, F.data.startswith("edit_seller_"))
async def select_seller_to_edit(callback: types.CallbackQuery, state: FSMContext):
    seller_id = int(callback.data.split("_")[-1])
    await state.update_data(seller_id=seller_id)
    
    keyboard = [
        [InlineKeyboardButton(text=FIELD_FULL_NAME, callback_data="field_full_name")],
        [InlineKeyboardButton(text=FIELD_PHONE, callback_data="field_phone")],
        [InlineKeyboardButton(text=FIELD_SALARY, callback_data="field_salary")],
        [InlineKeyboardButton(text=FIELD_START_DATE, callback_data="field_start_date")],
        [InlineKeyboardButton(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")]
    ]
    
    await callback.message.edit_text(
        "Qaysi maydonni tahrirlamoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(EditSellerStates.SELECT_FIELD)

@router.callback_query(EditSellerStates.SELECT_FIELD, F.data.startswith("field_"))
async def select_seller_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[-1]
    await state.update_data(field=field)
    
    field_names = {
        'full_name': "To'liq ism",
        'phone': "Telefon raqami",
        'salary': "Maosh",
        'start_date': "Ish boshlagan sana (YYYY-MM-DD)"
    }
    
    await callback.message.edit_text(
        f"Yangi {field_names.get(field, field)} qiymatini kiriting:",
        reply_markup=back_to_main_menu()
    )
    await state.set_state(EditSellerStates.ENTER_NEW_VALUE)

@router.message(EditSellerStates.ENTER_NEW_VALUE)
async def save_seller_changes(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    data = await state.get_data()
    seller_id = data['seller_id']
    field = data['field']
    
    try:
        if field == 'salary':
            value = int(message.text)
            field_name = 'salary_of_seller'
        elif field == 'start_date':
            datetime.strptime(message.text, '%Y-%m-%d')
            value = message.text
            field_name = 'started_job_at'
        elif field == 'full_name':
            value = message.text
            field_name = 'full_name'
        elif field == 'phone':
            value = message.text
            field_name = 'phone'
        else:
            raise ValueError("Noma'lum maydon turi")
        
        update_data = {field_name: value}
        success = await update_seller(seller_id, update_data)
        
        if success:
            await message.answer(
                "✅ Sotuvchi ma'lumotlari muvaffaqiyatli yangilandi!",
                reply_markup=main_menu
            )
        else:
            await message.answer(
                "❌ Xatolik yuz berdi!",
                reply_markup=main_menu
            )
    except ValueError as e:
        error_msg = "❌ Noto'g'ri format! "
        if field == 'salary':
            error_msg += "Maosh uchun raqam kiriting."
        elif field == 'start_date':
            error_msg += "Sana YYYY-MM-DD formatida bo'lishi kerak."
        else:
            error_msg += str(e)
        
        await message.answer(error_msg, reply_markup=back_to_main_menu())
    except Exception as e:
        await message.answer(
            f"❌ Kutilmagan xatolik: {str(e)}",
            reply_markup=back_to_main_menu()
        )
    
    await state.clear()

@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Tahrirlash bekor qilindi.")

def register_handlers(dp):
    dp.include_router(router)