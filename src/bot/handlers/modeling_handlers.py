from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message

from bot.keyboards import ModelMenuBtns, ModelMenuOption, get_model_kb, get_payment_kb
from config import Settings

router = Router()


@router.message(Command("model"))
async def model_message(message: Message):
    welcome_message = (
        "Добро пожаловать в мир возможностей! 🎭\n\n"
        "Меня зовут Валерий Стайсупов, я пластический хирург с 20-летним опытом в ринопластике. "
        "Понимаю, как сложно представить себя с новым носом, поэтому я создал этот сервис.\n\n"
        "<b>Что вы получите:</b>\n"
        "• Персональное моделирование вашего лица с новой формой носа\n"
        "• Реалистичное изображение, созданное с учетом анатомических особенностей\n"
        "• Профессиональную оценку возможностей коррекции именно вашего носа\n"
        "• Универсальное моделирование, которое поможет вам определиться с решением независимо от "
        "того, где вы планируете делать операцию\n\n"
        "<b>Как это работает:</b>\n"
        "Вы загружаете фото в профиль, я анализирую структуру носа и создаю один или два максимально "
        "реалистичных варианта возможной коррекции. Это не автоматическая обработка - каждое "
        "моделирование выполняется вручную с применением знаний пластической хирургии.\n\n"
        "<b>Важно понимать:</b>\n"
        "моделирование - это не гарантия результата операции, а возможность увидеть, "
        "как новая форма носа будет гармонировать с вашим лицом. "
        "Окончательный план операции всегда обсуждается на очной консультации.\n\n"
        "Готовы увидеть свое преображение?"
    )
    await message.answer(welcome_message, reply_markup=get_model_kb())


@router.callback_query(ModelMenuOption.filter())
async def model_menu_handler(callback: CallbackQuery, callback_data: ModelMenuOption):
    await callback.answer()
    match callback_data.action:
        case ModelMenuBtns.UPLOAD_PHOTO:
            ...
        case ModelMenuBtns.PHOTO_REQUIREMENTS:
            ...
        case ModelMenuBtns.DETAILS:
            modeling_message = (
                "<b>Стоимость и сроки</b>\n\n"
                "💰 Стоимость: 3000 рублей\n\n"
                "⏱️ Срок выполнения: 24 часа\n\n"
                "Моделирование выполняется персонально врачом-хирургом, а не автоматически. "
                "Доктор лично анализирует каждую фотографию, изучает "
                "анатомические особенности вашего лица и создает реалистичное моделирование с "
                "учетом принципов пластической хирургии.\n\n"
                "Именно поэтому требуется время - качественный анализ и моделирование не могут "
                "быть мгновенными.\n\n"
                "<b>Вы получите:</b>\n"
                "• Профессиональный анализ от хирурга с 20-летним опытом\n"
                "• Оптимальный вариант коррекции с учетом ваших особенностей и пожеланий "
                "(иногда возможны 2 варианта с небольшими отличиями)\n"
                "• Персональный подход к вашим анатомическим особенностям\n\n"
                "<b>Готовы заказать моделирование?</b> 📸"
            )
            await callback.message.answer(modeling_message, reply_markup=get_payment_kb())


@router.callback_query(F.data == "model_payment")
async def model_payment_handler(callback: CallbackQuery, settings: Settings):
    await callback.answer()
    description = "Стоимость: 3000 рублей."
    amount = 3000 * 100
    prices = [LabeledPrice(label="Оплатить", amount=amount)]
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Услуга моделирования.",
        description=description,
        payload="model",
        provider_token=settings.PAYMENT_PROVIDER_TOKEN.get_secret_value(),
        currency="RUB",
        prices=prices,
    )
