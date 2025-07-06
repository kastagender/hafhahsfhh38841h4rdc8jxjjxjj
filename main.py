from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from sheets import get_analytics, get_motivation
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import os
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton

from sheets import append_order, get_orders, update_order_status, add_promo_code, get_all_promos, use_promo_code, get_used_promos

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())


# === FSM ===
class OrderForm(StatesGroup):
    name = State()
    item = State()
    price = State()
    prepay = State()
    comment = State()

class PromoAdd(StatesGroup):
    code = State()

class PromoUse(StatesGroup):
    username = State()
    price = State()

# === Handlers ===
@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer("✅ Бот запущен. Используй /neworder чтобы создать заказ.")

@dp.message(F.text == "/menu")
async def menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить промо", callback_data="addpromo")],
        [InlineKeyboardButton(text="🎟 Все промо", callback_data="ade3")],
        [InlineKeyboardButton(text="👤 Использовали промо", callback_data="usedpromos")],
        [InlineKeyboardButton(text="📦 Заказы", callback_data="orders")]
    ])
    await message.answer("📋 Главное меню:", reply_markup=kb)
@dp.message(F.text == "/adminhere")
async def adminhere(message: Message):
    done, not_done = get_analytics()
    motivation = get_motivation()
    text = (
        f"📊 <b>Аналитика по заказам:</b>\n"
        f"✅ Выполнено: <b>{done}</b>\n"
        f"🚧 В процессе: <b>{not_done}</b>\n\n"
        f"🔗 <a href='https://t.me/c/2359630578/4'>Посмотреть детали</a>\n\n"
        f"💡 <i>{motivation}</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить промо", callback_data="addpromo")],
        [InlineKeyboardButton(text="📦 Заказы", callback_data="orders")]
    ])
    await message.answer(text, reply_markup=kb)
@dp.message(F.text == "/neworder")
async def new_order(message: Message, state: FSMContext):
    await state.set_state(OrderForm.name)
    await message.answer("👤 Введи имя клиента или @username:")

@dp.message(OrderForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.item)
    await message.answer("🎽 Что заказал клиент?")

@dp.message(OrderForm.item)
async def process_item(message: Message, state: FSMContext):
    await state.update_data(item=message.text)
    await state.set_state(OrderForm.price)
    await message.answer("💸 Цена товара (грн):")

@dp.message(OrderForm.price)
async def process_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(OrderForm.prepay)
    await message.answer("💰 Предоплата (грн):")

@dp.message(OrderForm.prepay)
async def process_prepay(message: Message, state: FSMContext):
    await state.update_data(prepay=message.text)
    await state.set_state(OrderForm.comment)
    await message.answer("🗒 Комментарий (если есть):")

@dp.message(OrderForm.comment)
async def process_comment(message: Message, state: FSMContext):
    data = await state.update_data(comment=message.text)
    await state.clear()

    order = data.copy()
    order["manager"] = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    append_order(order)

    await message.answer("✅ Заказ сохранён в таблицу!")


# === PROMO ===
@dp.message(F.text == "/addpromo")
async def addpromo(message: Message, state: FSMContext):
    await state.set_state(PromoAdd.code)
    await message.answer("🎟 Введи промокод:")

@dp.message(PromoAdd.code)
async def promo_input(message: Message, state: FSMContext):
    add_promo_code(message.text)
    await state.clear()
    await message.answer("✅ Промокод добавлен!")
@dp.callback_query(F.data == "addpromo")
async def cb_addpromo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoAdd.code)
    await callback.message.answer("🎟 Введи промокод:")
    await callback.answer()

@dp.callback_query(F.data == "ade3")
async def cb_ade3(callback: CallbackQuery):
    codes = get_all_promos()
    await callback.message.answer("🎟 Все промокоды:\n" + "\n".join(codes))
    await callback.answer()

@dp.callback_query(F.data == "usedpromos")
async def cb_used(callback: CallbackQuery):
    users = get_used_promos()
    await callback.message.answer("👤 Использовали промо:\n" + "\n".join(users))
    await callback.answer()

@dp.callback_query(F.data == "orders")
async def cb_orders(callback: CallbackQuery):
    await orders(callback.message)
    await callback.answer()
@dp.message(F.text == "/ade3")
async def promo_list(message: Message):
    codes = get_all_promos()
    await message.answer("🎟 Все промокоды:\n" + "\n".join(codes))

@dp.message(F.text == "/promo")
async def promo_use(message: Message, state: FSMContext):
    await state.set_state(PromoUse.username)
    await message.answer("👤 Введи username покупателя:")

@dp.message(PromoUse.username)
async def promo_user(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await state.set_state(PromoUse.price)
    await message.answer("💵 Введи цену заказа (грн):")

@dp.message(PromoUse.price)
async def promo_price(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    price = float(message.text)
    payout = round(price * 0.85, 2)
    use_promo_code(username, price, payout)
    await state.clear()
    await message.answer(f"✅ Сохранено! Клиент должен оплатить: {payout} грн (-15%)")

@dp.message(F.text == "/usedpromos")
async def used_list(message: Message):
    users = get_used_promos()
    await message.answer("👤 Использовали промо:\n" + "\n".join(users))


# === ORDERS ===
@dp.message(F.text == "/orders")
async def orders(message: Message):
    orders = get_orders()
    for idx, order in orders:
        builder = InlineKeyboardBuilder()
        for status in ["Оформлен", "Идёт доставка", "Получено"]:
            builder.button(text=status, callback_data=f"status:{idx}:{status}")
        kb = builder.as_markup()
        await message.answer(f"📦 Заказ {idx}: {order}", reply_markup=kb)

@dp.callback_query(F.data.startswith("status:"))
async def status_change(callback: CallbackQuery):
    _, idx, status = callback.data.split(":")
    update_order_status(int(idx), status)
    await callback.answer("✅ Статус обновлён")
    await callback.message.edit_reply_markup(reply_markup=None)


# === Запуск ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())