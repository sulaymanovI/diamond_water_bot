from aiogram import Router, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from states import ConsumptionStates, EditConsumptionStates
from database.crud import (
    generate_consumptions_excel,
    get_all_consumptions,
    get_consumption_by_id,
    get_consumptions_by_owner,
    create_consumption,
    update_consumption,
    delete_consumption,
    get_total_consumptions_by_owner
)
from database.models import Consumptions
from database.utils import async_session
from config import Config
from datetime import datetime
from keyboards.types import (
    CANCEL_EDIT_BTN,
    BACK_TO_MAIN_MENU_BTN,
    FIELD_AMOUNT,
    FIELD_DESCRIPTION,
    FIELD_OWNER
)
from keyboards.builders import main_menu, back_to_main_menu, get_employees_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re

router = Router()

# Define regex patterns
REGEX_AMOUNT = r'^\d+(\.\d{1,2})?$'

# Helper function to format consumption info
def format_consumption_info(consumption: Consumptions) -> str:
    return (
        f"👤 Xarajat egasi: {consumption.consumption_owner}\n"
        f"💵 Summa: {consumption.amount:,}\n"
        f"📝 Tavsifi: {consumption.description}\n"
        f"📅 Sana: {consumption.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"🆔 ID: {consumption.id}\n"
    )

# Helper function to create edit buttons
def create_consumption_edit_buttons(consumption_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_consumption_{consumption_id}"),
        InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"delete_consumption_{consumption_id}")
    )
    return builder.as_markup()

# Common back to main menu handler
@router.message(F.text == BACK_TO_MAIN_MENU_BTN)
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=main_menu)

# Start adding new consumption
@router.message(F.from_user.id.in_(Config.ALLOWED_USERS), F.text == "📝 Yangi xarajat")
async def start_add_consumption(message: types.Message, state: FSMContext):
    await state.set_state(ConsumptionStates.SELECT_OWNER)
    await message.answer(
        "Xarajat egasini tanlang:",
        reply_markup=get_employees_keyboard()
    )

# Process owner selection
@router.message(ConsumptionStates.SELECT_OWNER)
async def process_owner_selection(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    valid_owners = ["Maxmudho'ja", "Bositxon", "Bekzod", "Og'abek", "Hodimlar"]
    if message.text not in valid_owners:
        await message.answer(
            "❌ Iltimos, ro'yxatdagi xodimlardan birini tanlang!",
            reply_markup=get_employees_keyboard()
        )
        return
        
    await state.update_data(owner=message.text)
    await state.set_state(ConsumptionStates.ENTER_AMOUNT)
    await message.answer(
        "Xarajat miqdorini kiriting (masalan: 150000 yoki 125000.50):",
        reply_markup=back_to_main_menu()
    )

# Process amount input
@router.message(ConsumptionStates.ENTER_AMOUNT)
async def process_amount_input(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    if not re.match(REGEX_AMOUNT, message.text):
        await message.answer(
            "❌ Noto'g'ri format! Faqat raqam kiriting (masalan: 150000 yoki 125000.50):",
            reply_markup=back_to_main_menu()
        )
        return
        
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await state.set_state(ConsumptionStates.ENTER_DESCRIPTION)
        await message.answer(
            "Xarajat tavsifini kiriting:",
            reply_markup=back_to_main_menu()
        )
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri format! Faqat raqam kiriting:",
            reply_markup=back_to_main_menu()
        )

# Process description input
@router.message(ConsumptionStates.ENTER_DESCRIPTION)
async def process_description_input(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    description = message.text
    if len(description) < 3:
        await message.answer(
            "❌ Tavsif juda qisqa! Kamida 3 belgi kiriting:",
            reply_markup=back_to_main_menu()
        )
        return
        
    data = await state.get_data()
    
    # Create consumption in database
    consumption = await create_consumption(
        owner=data['owner'],
        amount=data['amount'],
        description=description
    )
    
    if consumption:
        await message.answer(
            f"✅ Xarajat muvaffaqiyatli qo'shildi!\n{format_consumption_info(consumption)}",
            reply_markup=main_menu
        )
    else:
        await message.answer(
            "❌ Xatolik yuz berdi!",
            reply_markup=main_menu
        )
    await state.clear()

# Send consumptions list as Excel
@router.message(F.text == "📋 Xarajatlar ro'yxati")
async def send_consumptions_excel(message: types.Message):
    excel_buffer = await generate_consumptions_excel()
    
    if not excel_buffer:
        await message.answer(
            "❌ Xarajatlar topilmadi yoki xatolik yuz berdi",
            reply_markup=back_to_main_menu()
        )
        return
    
    filename = f"consumptions_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    
    await message.answer_document(
        document=BufferedInputFile(
            file=excel_buffer.read(),
            filename=filename
        ),
        caption="📋 Barcha xarajatlar hisoboti"
    )

# View consumption details
@router.message(F.text == "👁 Xarajatni ko'rish")
async def start_view_consumption(message: types.Message, state: FSMContext):
    await state.set_state(ConsumptionStates.ENTER_ID)
    await message.answer(
        "Xarajat ID sini kiriting:",
        reply_markup=back_to_main_menu()
    )

# Process consumption ID input
@router.message(ConsumptionStates.ENTER_ID)
async def process_consumption_id(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
        
    try:
        consumption_id = int(message.text)
        consumption = await get_consumption_by_id(consumption_id)
        
        if not consumption:
            await message.answer(
                "❌ Xarajat topilmadi!",
                reply_markup=back_to_main_menu()
            )
            await state.clear()
            return
            
        await message.answer(
            format_consumption_info(consumption),
            reply_markup=create_consumption_edit_buttons(consumption.id)
        )
        await state.update_data(consumption_id=consumption.id)
        await state.set_state(ConsumptionStates.VIEW_CONSUMPTION)
        
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri ID formati! Faqat raqam kiriting:",
            reply_markup=back_to_main_menu()
        )

# Edit consumption handler
@router.callback_query(F.data.startswith("edit_consumption_"))
async def edit_consumption_handler(callback: types.CallbackQuery, state: FSMContext):
    consumption_id = int(callback.data.split("_")[-1])
    await state.update_data(consumption_id=consumption_id)
    
    keyboard = [
        [InlineKeyboardButton(text=FIELD_OWNER, callback_data="edit_owner")],
        [InlineKeyboardButton(text=FIELD_AMOUNT, callback_data="edit_amount")],
        [InlineKeyboardButton(text=FIELD_DESCRIPTION, callback_data="edit_description")],
        [InlineKeyboardButton(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")]
    ]
    
    await callback.message.edit_text(
        "Qaysi maydonni tahrirlamoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(EditConsumptionStates.SELECT_FIELD)

# Select field to edit
@router.callback_query(EditConsumptionStates.SELECT_FIELD, F.data.startswith("edit_"))
async def select_field_to_edit(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_", "")
    await state.update_data(edit_field=field)
    
    data = await state.get_data()
    consumption_id = data['consumption_id']
    
    # Get current consumption info
    consumption = await get_consumption_by_id(consumption_id)
    if not consumption:
        await callback.answer("❌ Xarajat topilmadi!")
        return
    
    current_value = getattr(consumption, field, "Noma'lum")
    
    if field == "owner":
        await callback.message.edit_text(
            f"Yangi egasini tanlang:\nHozirgi egasi: {current_value}",
            reply_markup=get_employees_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"Yangi qiymatni kiriting:\nHozirgi qiymat: {current_value}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=CANCEL_EDIT_BTN, callback_data="cancel_edit")]
            ])
        )
    
    await state.set_state(EditConsumptionStates.ENTER_NEW_VALUE)

# Process new value for editing
@router.message(EditConsumptionStates.ENTER_NEW_VALUE)
async def process_new_value(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    
    data = await state.get_data()
    consumption_id = data['consumption_id']
    field = data['edit_field']
    
    try:
        # Validate input based on field type
        if field == "amount":
            if not re.match(REGEX_AMOUNT, message.text):
                raise ValueError("Noto'g'ri summa formati! Raqam kiriting (masalan: 150000 yoki 125000.50)")
            new_value = float(message.text)
            db_field = "amount"
        elif field == "description":
            if len(message.text) < 3:
                raise ValueError("Tavsif juda qisqa! Kamida 3 belgi kiriting")
            new_value = message.text
            db_field = "description"
        elif field == "owner":
            valid_owners = ["Maxmudho'ja", "Bositxon", "Bekzod", "Og'abek", "Hodimlar"]
            if message.text not in valid_owners:
                raise ValueError("Noto'g'ri xodim tanlandi! Ro'yxatdagi xodimlardan birini tanlang")
            new_value = message.text
            db_field = "consumption_owner"
        
        # Update consumption in database
        success = await update_consumption(consumption_id, {db_field: new_value})
        
        if success:
            # Show updated consumption info
            consumption = await get_consumption_by_id(consumption_id)
            await message.answer(
                "✅ Muvaffaqiyatli yangilandi!\n" + format_consumption_info(consumption),
                reply_markup=create_consumption_edit_buttons(consumption.id)
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

# Delete consumption handler
@router.callback_query(F.data.startswith("delete_consumption_"))
async def delete_consumption_handler(callback: types.CallbackQuery, state: FSMContext):
    consumption_id = int(callback.data.split("_")[-1])
    await state.update_data(consumption_id=consumption_id)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm__consumption_delete_{consumption_id}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_delete")
    )
    
    await callback.message.edit_text(
        f"⚠️ Xarajatni o'chirib tashlamoqchimisiz? (ID: {consumption_id})",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("confirm__consumption_delete_"))
async def confirm_delete_handler(callback: types.CallbackQuery, state: FSMContext):
    consumption_id = int(callback.data.split("_")[-1])
    
    try:
        success = await delete_consumption(consumption_id)
        if success:
            await callback.message.edit_text(
                f"✅ Xarajat #{consumption_id} o'chirib tashlandi!",
                reply_markup=main_menu
            )
        else:
            await callback.answer("❌ Xarajat topilmadi yoki o'chirib bo'lmadi!", show_alert=True)
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
    finally:
        await state.clear()
        await callback.answer()

# Cancel delete
@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ O'chirish bekor qilindi.")
    await state.clear()

# View totals by owner
@router.message(F.text == "📊 Xarajatlar statistikasi")
async def view_consumption_stats(message: types.Message):
    totals = await get_total_consumptions_by_owner()
    
    if not totals:
        await message.answer(
            "❌ Xarajatlar topilmadi!",
            reply_markup=back_to_main_menu()
        )
        return
    
    response = ["📊 Xarajatlar statistikasi:\n"]
    for total in totals:
        response.append(f"👤 {total.consumption_owner}: {total.total_amount:,} so'm")
    
    response.append("\n💰 Umumiy xarajatlar")
    await message.answer("\n".join(response))

def register_handlers(dp):
    dp.include_router(router)