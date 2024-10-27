from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(CommandStart())
async def start_message(message: types.Message, db_session, state: FSMContext) -> None:
    await state.set_state()
    await message.answer("Hello!")
