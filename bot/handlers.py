from datetime import timedelta, timezone

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from pydantic import ValidationError

from app.database import SessionLocal
from app.exceptions import AppError
from app.models import AppealSource
from app.schemas import AppealCreate, normalize_phone
from app.services import appeals as appeal_service
from app.services import categories as category_service
from app.services import users as user_service
from bot.keyboards import (
    MY_APPEALS_BTN, NEW_APPEAL_BTN, appeals_kb, categories_kb, main_menu_kb, share_contact_kb,
)
from bot.states import NewAppeal


router = Router()


TASHKENT_TZ = timezone(timedelta(hours=5))  # Uzbekistan has no daylight saving time
STATUS_ICONS = {"NEW": "🆕", "IN_PROGRESS": "⏳", "REJECTED": "❌", "CLOSED": "✅"}
NOT_LINKED_TEXT = "Please send /start and share your phone number first."


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        user = await user_service.get_by_telegram_id(session, message.from_user.id)

    if user:
        await message.answer(f"Welcome back, {user.full_name or user.phone}!", reply_markup=main_menu_kb)
    else:
        await message.answer("Please share your phone number to continue.", reply_markup=share_contact_kb)


@router.message(F.contact)
async def contact_shared(message: Message):
    contact = message.contact
    # Accept only the user's own contact, otherwise anyone could link someone else's phone.
    if contact.user_id != message.from_user.id:
        await message.answer("Please share your own phone number using the button.", reply_markup=share_contact_kb)
        return

    # Telegram may send the number without "+".
    raw = contact.phone_number if contact.phone_number.startswith("+") else f"+{contact.phone_number}"
    try:
        phone = normalize_phone(raw)
    except ValueError:
        await message.answer("Only (+998) are supported.")
        return

    async with SessionLocal() as session:
        try:
            user = await user_service.link_telegram(
                session, phone, message.from_user.id, message.from_user.full_name[:100]  # users.full_name is 100 chars
            )
        except AppError as e:
            await message.answer(e.detail)
            return

    await message.answer(
        f"Your account {user.phone} is linked.\n"
        "To see your appeals on the website, register there with the same phone number.",
        reply_markup=main_menu_kb,
    )


# Menu buttons are registered before the FSM handlers, so pressing one always resets an unfinished appeal.
@router.message(F.text == NEW_APPEAL_BTN)
async def new_appeal(message: Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        user = await user_service.get_by_telegram_id(session, message.from_user.id)
        categories = await category_service.get_categories(session)

    if not user:
        await message.answer(NOT_LINKED_TEXT, reply_markup=share_contact_kb)
        return
    if not categories:
        await message.answer("No categories are available yet. Please try again later.")
        return

    await state.set_state(NewAppeal.category)
    await message.answer("Choose a category:", reply_markup=categories_kb(categories))


@router.message(F.text == MY_APPEALS_BTN)
async def my_appeals(message: Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        user = await user_service.get_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer(NOT_LINKED_TEXT, reply_markup=share_contact_kb)
            return
        appeals = await appeal_service.get_appeals_list(session, user, limit=10)

    if not appeals:
        await message.answer("You have no appeals yet.")
        return
    await message.answer("Your latest appeals:", reply_markup=appeals_kb(appeals))


@router.callback_query(NewAppeal.category, F.data.startswith("cat:"))
async def category_chosen(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(callback.data.split(":")[1]))
    await state.set_state(NewAppeal.description)
    await callback.message.edit_text("Describe your problem (10–2000 characters):")
    await callback.answer()


@router.message(NewAppeal.description, F.text)
async def description_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await user_service.get_by_telegram_id(session, message.from_user.id)
        if not user:
            await state.clear()
            await message.answer(NOT_LINKED_TEXT, reply_markup=share_contact_kb)
            return

        try:
            appeal_in = AppealCreate(phone=user.phone, description=message.text, category_id=data["category_id"])
        except ValidationError:
            await message.answer("The description must be 10–2000 characters. Please try again.")
            return

        try:
            appeal = await appeal_service.create_appeal(session, appeal_in, user, source=AppealSource.TELEGRAM)
        except AppError as e:
            await state.clear()
            await message.answer(e.detail, reply_markup=main_menu_kb)
            return

    await state.clear()
    await message.answer(
        f"✅ Appeal #{appeal.id} submitted.\n"
        f"Category: {appeal.category.name}\n"
        f"Status: {appeal.status.value}\n\n"
        "You will be notified here when its status changes.",
        reply_markup=main_menu_kb,
    )


@router.callback_query(F.data.startswith("appeal:"))
async def appeal_details(callback: CallbackQuery):
    appeal_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        user = await user_service.get_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer(NOT_LINKED_TEXT, show_alert=True)
            return
        try:
            appeal = await appeal_service.get_appeal(session, appeal_id, user)
        except AppError as e:
            await callback.answer(e.detail, show_alert=True)
            return

    lines = [
        f"Appeal #{appeal.id}",
        f"Category: {appeal.category.name}",
        f"Status: {STATUS_ICONS[appeal.status.value]} {appeal.status.value}",
        "",
        appeal.description,
        "",
        "History:",
    ]
    for h in appeal.history:
        line = f"• {h.created_at.astimezone(TASHKENT_TZ):%d.%m.%Y %H:%M} — {h.new_status.value}"
        if h.comment:
            line += f": {h.comment}"
        lines.append(line)

    await callback.message.answer("\n".join(lines))
    await callback.answer()
