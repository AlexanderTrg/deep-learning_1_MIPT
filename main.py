from nst import *
import logging
import gc
import aiogram
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

from config import BOT_TOKEN
from io import BytesIO
from PIL import Image

logging.basicConfig(level=logging.INFO)
loop = asyncio.get_event_loop()
bot = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, loop=loop, storage=storage)

model_VGG = Stylo_on_VGG()


# автомат  https://docs.aiogram.dev/en/latest/examples/finite_state_machine_example.html
# https://mastergroosha.github.io/telegram-tutorial-2/fsm/

class process(StatesGroup):
    model = State()
    content = State()
    style = State()


@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer(text="Выберете модель, потом загрузите контент, "
                              "далее стиль, в котором хотите видеть контент, и усе)")


# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('хорошо исполняешь. гоу еще раз - введи /start', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await process.model.set()
    res = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    res.add(types.KeyboardButton(text='nst'))
    res.add(types.KeyboardButton(text="gan"))

    await message.reply('выбери модель', reply_markup=res)


@dp.message_handler(state=process.model)
async def model(message: types.Message, state: FSMContext):
    # await process.next()
    await state.update_data(requested_model=message.text)
    async with state.proxy() as data:
        if data['requested_model'] == "gan":
            await message.reply('это только за деньги), но есть бюджетный nst - введи /cancel')

        elif data['requested_model'] == 'nst':
            await process.content.set()
            await message.reply('гони контент')


@dp.message_handler(state=process.content, content_types=['photo'])
async def content(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    file_info = await bot.get_file(file_id)
    image_data = await bot.download_file(file_info.file_path)
    content_image = image_data
    await state.update_data(content_image=content_image)
    await process.style.set()
    await message.reply('Супер, теперь гони стайл')


@dp.message_handler(state=process.style, content_types=["photo"])
async def style(message: types.Message, state: FSMContext):
    file_id1 = message.photo[-1].file_id
    file_info1 = await bot.get_file(file_id1)
    image_data1 = await bot.download_file(file_info1.file_path)
    style_image = image_data1
    await state.update_data(style_image=style_image)
    await message.reply(text='ждемс...')
    async with state.proxy() as data:
        cont = model_VGG.image_loader(data['content_image'])
        styl = model_VGG.image_loader(data['style_image'])
        out = model_VGG.out(styl, cont)
        to_user = model_VGG.to_user(out)

    result = BytesIO()
    to_user.save(result, format="PNG")
    result.seek(0)
    await message.reply_photo(result)
    await process.model.set()
    await message.reply('хорошо исполняешь. гоу еще раз - введи /start')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
