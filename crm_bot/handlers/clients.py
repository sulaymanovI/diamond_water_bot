from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from states import OrderStates, ClientStates
from database.crud import add_client_to_db, get_client_by_passport
from database.models import Client
from config import Config
from keyboards.builders import main_menu, back_to_main_menu
from keyboards.types import BACK_TO_MAIN_MENU_BTN

router = Router()

@router.message(F.text == BACK_TO_MAIN_MENU_BTN)
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu
    )

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS) , 
    OrderStates.CLIENT_PASSPORT)
async def process_client_passport(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return

    passport = message.text
    client = await get_client_by_passport(passport)
    
    if client:
        await state.update_data(client_id=client.id)
        await message.answer("✅ Mijoz bazada topildi. Endi mahsulot miqdorini kiriting:", reply_markup=back_to_main_menu())
        await state.set_state(OrderStates.ITEM_COUNT)
    else:
        await state.update_data(client_passport=passport)
        await message.answer("❌ Mijoz topilmadi. Yangi mijozni ro‘yxatdan o‘tkazamiz.", reply_markup=back_to_main_menu())
        await message.answer("Mijozning to‘liq ismini kiriting:", reply_markup=back_to_main_menu())
        await state.set_state(ClientStates.FULL_NAME)

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS) ,
    ClientStates.FULL_NAME)
async def process_client_name(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    await state.update_data(full_name=message.text)
    await state.set_state(ClientStates.PHONE)
    await message.answer("Endi mijozning telefon raqamini kiriting:", reply_markup=back_to_main_menu())

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS) ,
    ClientStates.PHONE)
async def process_client_phone(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return

    await state.update_data(phone=message.text)
    await state.set_state(ClientStates.ADDRESS)
    await message.answer("Mijozning manzilini kiriting:",reply_markup=back_to_main_menu())

@router.message(F.from_user.id.in_(Config.ALLOWED_USERS) ,
    ClientStates.ADDRESS)
async def process_client_address(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    await state.update_data(address=message.text)
    await state.set_state(ClientStates.NOTES)
    await message.answer("Izoh kiriting (majburiy emas):",reply_markup=back_to_main_menu())

@router.message(
    F.from_user.id.in_(Config.ALLOWED_USERS) , 
    ClientStates.NOTES
)
async def process_client_notes(message: types.Message, state: FSMContext):
    if message.text == BACK_TO_MAIN_MENU_BTN:
        await handle_back_to_main_menu(message, state)
        return
    data = await state.get_data()
    
    client_data = {
        'full_name': data['full_name'],
        'phone': data['phone'],
        'address': data['address'],
        'passport_serial': data['client_passport'],
        'notes': message.text
    }
    
    client = await add_client_to_db(client_data)
    
    await state.update_data(client_id=client.id)
    await message.answer("✅ Mijoz muvaffaqiyatli ro‘yxatdan o‘tkazildi!",reply_markup=back_to_main_menu())
    await message.answer("Endi mahsulot miqdorini kiriting:",reply_markup=back_to_main_menu())
    await state.set_state(OrderStates.ITEM_COUNT)

def register_handlers(dp):
    dp.include_router(router)