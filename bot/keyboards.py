from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

NEW_APPEAL_BTN = "📝 New appeal"
MY_APPEALS_BTN = "📋 My appeals"

share_contact_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Share phone number", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=NEW_APPEAL_BTN)], [KeyboardButton(text=MY_APPEALS_BTN)]],
    resize_keyboard=True,
)


def categories_kb(categories) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category.name, callback_data=f"cat:{category.id}")] for category in categories
    ])


def appeals_kb(appeals) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"#{appeal.id} · {appeal.status.value} · {appeal.category.name}", callback_data=f"appeal:{appeal.id}")]
        for appeal in appeals
    ])
