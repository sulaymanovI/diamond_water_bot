from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from .types import (
    ADD_ORDER_BTN,
    ADD_SELLER_BTN,
    ADD_LIST_OF_ORDERS_BTN,
    ADD_LIST_OF_SELLERS_BTN,
    VIEW_ORDER_BTN,
    VIEW_SELLER_BTN,
    BACK_TO_MAIN_MENU_BTN ,
    ADD_CONSUMPTION_BTN,
    ADD_LIST_OF_CONSUMPTION_BTN,
    VIEW_CONSUMPTION_BTN,
    VIEW_STATISTICS_CONSUMPTION_BTN
)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=ADD_ORDER_BTN), KeyboardButton(text=ADD_LIST_OF_ORDERS_BTN)],[KeyboardButton(text=VIEW_ORDER_BTN)],
        [KeyboardButton(text=ADD_SELLER_BTN), KeyboardButton(text=ADD_LIST_OF_SELLERS_BTN)],[KeyboardButton(text=VIEW_SELLER_BTN)],
        [KeyboardButton(text=ADD_CONSUMPTION_BTN), KeyboardButton(text=ADD_LIST_OF_CONSUMPTION_BTN)],
        [KeyboardButton(text=VIEW_CONSUMPTION_BTN), KeyboardButton(text=VIEW_STATISTICS_CONSUMPTION_BTN)],
    ],
    resize_keyboard=True
)

def back_to_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_TO_MAIN_MENU_BTN)]],
        resize_keyboard=True
    )

def get_employees_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Maxmudho'ja"), KeyboardButton(text="Abdulbosit")],
            [KeyboardButton(text="Bekzod"), KeyboardButton(text="Og'abek")],
            [KeyboardButton(text="Hodimlar"), KeyboardButton(text= BACK_TO_MAIN_MENU_BTN)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )