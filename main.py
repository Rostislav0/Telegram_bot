# import libraries
import asyncio
from telebot import types
from transfer_style import Style_Transfer
from telebot.async_telebot import AsyncTeleBot
import os

os.mkdir("pictures")

bot = AsyncTeleBot('2110529010:AAH0tkIHL74pQbphax1XPt-D7avkEc2knL0')

path = 'pictures/'

# reaction to 'start' command
@bot.message_handler(commands=['start'])
async def start(message):
    mess_of_start = f"""Hi <b>{message.from_user.first_name}</b>
I'm bot and I was created to transfer style your photos.
You can send me /help to get more details"""
    # make button
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    help_button = types.KeyboardButton('/help')
    markup.add(help_button)
    # send message with button
    await bot.send_message(message.chat.id, mess_of_start, parse_mode='html', reply_markup=markup)


# reaction to 'help' command
@bot.message_handler(commands=['help'])
async def help(message):
    # message
    mess_of_help = f"""I can:
info - to find out about the project
style - to transfer style from a photo to another"""
    # make buttons
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    style_button = types.KeyboardButton('style')
    info_button = types.KeyboardButton('info')
    markup.add(style_button, info_button)
    # send message with buttons
    await bot.send_message(message.chat.id, mess_of_help, parse_mode='html', reply_markup=markup)


# reaction to 'info' message
@bot.message_handler(commands=['info'])
async def info(message):
    # message
    mess_of_info = f"""I was created by Rostislav Misiukevich for project's MFTI. Creator's contacts:
        426913702 - Stepic
        @__r.o.s.t.i.k_ - Instagram
        @Rostislav000 - Telegram"""
    # make button
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    style_button = types.KeyboardButton('style')
    markup.add(style_button)
    # send message with button
    await bot.send_message(message.chat.id, mess_of_info, parse_mode='html', reply_markup=markup)


# reaction to any text from user
@bot.message_handler(content_types=['text'])
async def get_user_text(message):
    if message.text.lower() == 'hi' or message.text.lower() == 'hello':
        # make buttons
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        style_button = types.KeyboardButton('style')
        info_button = types.KeyboardButton('info')
        markup.add(style_button, info_button)
        # send message with buttons
        await bot.send_message(message.chat.id, f"Hello <b>{message.from_user.first_name}</b>", parse_mode='html',
                         reply_markup=markup)

    elif message.text.isnumeric() is True:

        if len(os.listdir(path)) == 2 and 0 < int(message.text) < 11:
            result = Style_Transfer(path_style_image='pictures/style.jpg', path_content_image='pictures/cont.jpg',
                                    num_steps_from_user=int(message.text)).sdf()

            await bot.send_photo(message.chat.id, result)

        elif len(os.listdir(path)) == 2:
            await bot.send_message(message.chat.id, 'Send me a number from 1 to 10', parse_mode='html')

        else:
            # message
            mess_of_sm = "I don't understand you, use /help"
            # make button
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            help_button = types.KeyboardButton('/help')
            markup.add(help_button)
            # send message with button
            await bot.send_message(message.chat.id, mess_of_sm, parse_mode='html', reply_markup=markup)

    elif message.text.lower() == 'style':
        # send message
        await bot.send_message(message.chat.id, f"Send me a picture from which you want take style", parse_mode='html')
        os.remove(path+'cont.jpg')
        os.remove(path+'style.jpg')

    elif message.text.lower() == 'info':
        # message
        mess_of_info = f"""I was created by Rostislav Misiukevich for project's MFTI. Creator's contacts:
426913702 - Stepic
@__r.o.s.t.i.k_ - Instagram
@Rostislav000 - Telegram"""
        # make buttons
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        style_button = types.KeyboardButton('style')
        markup.add(style_button)
        # send message with buttons
        await bot.send_message(message.chat.id, mess_of_info, parse_mode='html', reply_markup=markup)
    else:
        # message
        mess_of_sm = "I don't understand you, use /help"
        # make button
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        help_button = types.KeyboardButton('/help')
        markup.add(help_button)
        # send message with button
        await bot.send_message(message.chat.id, mess_of_sm, parse_mode='html', reply_markup=markup)

# save photo from user, apply function 'transform' and send result to user
@bot.message_handler(content_types=['photo'])
async def get_style_photo(message):
    num_of_pictures = len(os.listdir(path))
    if num_of_pictures == 2:
        os.remove(path+'cont.jpg')
        os.remove(path+'style.jpg')
        num_of_pictures = len(os.listdir(path))
    if num_of_pictures == 0:
        await bot.send_message(message.chat.id, 'Saving style...')
        file_info = await bot.get_file(message.photo[-1].file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        with open('pictures/style.jpg', 'wb') as new_file:
            new_file.write(downloaded_file)
        await bot.send_message(message.chat.id, 'Send me another photo on which you apply the style')

    elif num_of_pictures == 1:
        await bot.send_message(message.chat.id, 'Saving content...')
        file_info = await bot.get_file(message.photo[-1].file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        with open('pictures/cont.jpg', 'wb') as new_file:
            new_file.write(downloaded_file)

        await bot.send_message(message.chat.id, 'Send me a number from 1 to 10 - degree of transfer')

# continuous working of bot
asyncio.run(bot.polling(none_stop=True, request_timeout=100000000000000000000000))
