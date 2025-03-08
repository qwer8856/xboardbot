from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from admin import game_dict
from keyboard import return_keyboard
from Config import config

edit_game_name = False


async def game_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    game_switch = '🔛赌博模式:开' if config.GAME.switch == True else '🚫赌博模式:关'
    buttons_per_row = 4
    keyboard = [
        [InlineKeyboardButton(j, callback_data=f'select_game{j}') for j in
         list(game_dict.keys())[i:i + buttons_per_row]]
        for i in range(0, len(game_dict), buttons_per_row)
    ]
    keyboard.insert(0, [InlineKeyboardButton(game_switch, callback_data='game_switch')])
    keyboard.append(return_keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=config.TELEGRAM.title, reply_markup=reply_markup
    )
    return 'game_settings'


async def game_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    callback = update.callback_query.data
    if callback == 'game_switch':
        if config.GAME.switch == True:
            config.GAME.switch = False
        else:
            config.GAME.switch = True
        config.save()
        await game_settings(update, context)
    else:
        game_name = callback.replace('game_switch', '')
        game_config = game_dict[game_name]
        if game_config.switch == True:
            game_config.switch = False
        else:
            game_config.switch = True
        config.save()
        await select_game(update, context, game_name)
    return 'game_settings'


async def game_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    global edit_game_name
    if query:
        await query.answer()
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        game_name = update.callback_query.data.replace('game_rate', '')
        game_config = game_dict[game_name]

        await query.edit_message_text(
            text=f'请发送{game_name}赔率\n当前倍率：{game_config.rate}', reply_markup=reply_markup
        )
        edit_game_name = game_name
    else:
        if edit_game_name == False:
            return 'game_settings'
        game_name = edit_game_name
        game_config = game_dict[game_name]
        try:
            rate = float(update.message.text)
            game_config.rate = rate
            config.save()
            text = f'编辑成功，当前{game_name}赔率为{rate}'
            edit_game_name = False
        except:
            text = '输入有误，请重新输入，请输入整数或者小数'
        await update.message.reply_text(text)
    return 'game_settings'


async def select_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_name=None):
    query = update.callback_query
    await query.answer()
    if not game_name:
        game_name = update.callback_query.data.replace('select_game', '')  # 点击的按钮
    game_config = game_dict[game_name]
    switch = '🔛开启' if game_config.switch == True else '🚫关闭'
    keyboard = [
        [
            InlineKeyboardButton(switch, callback_data=f'game_switch{game_name}'),
            InlineKeyboardButton(f'📈赔率:{game_config.rate}', callback_data=f'game_rate{game_name}'),
        ],
        return_keyboard,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f'{game_name}配置', reply_markup=reply_markup
    )
    return 'game_settings'
