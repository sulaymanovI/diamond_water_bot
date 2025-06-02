from aiogram.fsm.state import State, StatesGroup

class ConsumptionStates(StatesGroup):
    SELECT_OWNER = State()
    ENTER_AMOUNT = State()
    ENTER_DESCRIPTION = State()
    ENTER_ID = State()
    VIEW_CONSUMPTION = State()
    SELECT_FIELD = State()

class EditConsumptionStates(StatesGroup):
    SELECT_FIELD = State()
    ENTER_NEW_VALUE = State()

class OrderStates(StatesGroup):
    CLIENT_PASSPORT = State()
    ITEM_COUNT = State()
    SUM_OF_ITEM = State()          
    MONTHLY_PAYMENT = State()      
    PREPAID_AMOUNT = State()
    SELLER_PASSPORT = State()
    CLIENT_FULLNAME = State()      
    CLIENT_PHONE = State()         
    CLIENT_ADDRESS = State()       

class ClientStates(StatesGroup):
    FULL_NAME = State()
    PHONE = State()
    ADDRESS = State()
    PASSPORT = State()             # Новое состояние для паспорта
    NOTES = State()
    CREATED_AT = State()           # Для ручного ввода даты создания (если нужно)
    LOCATION = State()

class SellerStates(StatesGroup):
    FULL_NAME = State()
    PHONE = State()
    PASSPORT = State()
    SALARY = State()               # Новое состояние для зарплаты
    START_DATE = State()

class EditOrderStates(StatesGroup):
    SELECT_ORDER = State()
    SELECT_FIELD = State()
    ENTER_NEW_VALUE = State()

class ViewOrderStates(StatesGroup):
    ENTER_ORDER_ID = State()         # Выбор заказа (по callback_data: edit_order:<id>)
    VIEW_ORDER = State() 
    SELECT_FIELD = State()        # Выбор поля для редактирования
    ENTER_NEW_VALUE = State()      # Ввод нового значени
    CHOOSE_STATUS= State()
    ADD_PAYMENT = State()

class EditSellerStates(StatesGroup):
    SELECT_SELLER = State()
    SELECT_FIELD = State()
    ENTER_NEW_VALUE = State()

class SearchSellerStates(StatesGroup):
    SELECT_SEARCH_METHOD = State()
    ENTER_SEARCH_QUERY = State()
    VIEW_SELLER = State()