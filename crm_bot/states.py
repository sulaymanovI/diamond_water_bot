from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    CLIENT_PASSPORT = State()
    ITEM_COUNT = State()
    SUM_OF_ITEM = State()          # Новое состояние для общей суммы
    MONTHLY_PAYMENT = State()      # Новое состояние для ежемесячного платежа
    PREPAID_AMOUNT = State()
    SELLER_PASSPORT = State()
    CLIENT_FULLNAME = State()      # Для новых клиентов
    CLIENT_PHONE = State()         # Для новых клиентов
    CLIENT_ADDRESS = State()       # Для новых клиентов
    RETURN_STATUS = State()        # Новое состояние для статуса возврата

class ClientStates(StatesGroup):
    FULL_NAME = State()
    PHONE = State()
    ADDRESS = State()
    PASSPORT = State()             # Новое состояние для паспорта
    NOTES = State()
    CREATED_AT = State()           # Для ручного ввода даты создания (если нужно)

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

class EditSellerStates(StatesGroup):
    SELECT_SELLER = State()
    SELECT_FIELD = State()
    ENTER_NEW_VALUE = State()