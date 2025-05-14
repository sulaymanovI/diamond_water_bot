from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from .types import (
    ADD_ORDER_BTN,
    ADD_SELLER_BTN,
    ADD_LIST_OF_ORDERS_BTN,
    ADD_LIST_OF_SELLERS_BTN,
    EDIT_ORDER_BTN,
    EDIT_SELLER_BTN,
    BACK_TO_MAIN_MENU_BTN 
)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=ADD_ORDER_BTN), KeyboardButton(text=ADD_SELLER_BTN)],
        [KeyboardButton(text=ADD_LIST_OF_ORDERS_BTN), KeyboardButton(text=ADD_LIST_OF_SELLERS_BTN)],
        [KeyboardButton(text=EDIT_ORDER_BTN), KeyboardButton(text=EDIT_SELLER_BTN)]
    ],
    resize_keyboard=True
)

def back_to_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_TO_MAIN_MENU_BTN)]],
        resize_keyboard=True
    )