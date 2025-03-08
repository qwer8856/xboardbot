# admin/__init__.py
import logging
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

# 导入工具函数
from admin.utils import (
    game_dict, 
    settings_dict, 
    v2board_dict, 
    addtime, 
    reducetime,
    statDay,
    statMonth
)

# 导入处理函数
from admin.settings import settings, select_setting
from admin.game_settings import game_settings, select_game, game_switch, game_rate
from admin.setting_reload import setting_reload
from admin.handle_addtime import handle_addtime, handle_reducetime

# 最后导入v2board相关函数
from admin.v2board_settings import v2board_settings, select_setting as v2board_select_setting, set_title

# 导出外部可用的功能
__all__ = [
    'settings', 
    'select_setting', 
    'v2board_settings', 
    'v2board_select_setting', 
    'set_title',
    'game_settings', 
    'select_game', 
    'game_switch', 
    'game_rate',
    'handle_addtime',
    'handle_reducetime',
    'setting_reload',
    'bot_settings',
    'traffic_manage',
    'time_manage'
]

async def bot_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATUS = 'bot_settings'
    query = update.callback_query
    await query.answer()
    
    # 将按钮两个一行排列
    keyboard = []
    settings_items = list(settings_dict.items())
    
    # 过滤掉"减少时长"按钮
    settings_items = [(key, value) for key, value in settings_items if '减少时长' not in key]
    
    # 每两个按钮一组
    for i in range(0, len(settings_items), 2):
        row = []
        # 添加当前按钮
        row.append(InlineKeyboardButton(settings_items[i][0], callback_data=f'settings{settings_items[i][0]}'))
        # 如果还有下一个按钮，也添加到当前行
        if i + 1 < len(settings_items):
            row.append(InlineKeyboardButton(settings_items[i+1][0], callback_data=f'settings{settings_items[i+1][0]}'))
        keyboard.append(row)
    
    # 只添加返回按钮
    keyboard.append([InlineKeyboardButton('⬅️返回', callback_data='start_over')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text='👑 管理员设置', reply_markup=reply_markup)
    return STATUS

async def traffic_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """流量管理菜单"""
    query = update.callback_query
    await query.answer()
    keyboard = []
    
    # 定义流量菜单按钮
    keyboard.append([
        InlineKeyboardButton('🥇昨日排行', callback_data='v2board_settings🥇昨日排行'),
        InlineKeyboardButton('🏆本月排行', callback_data='v2board_settings🏆本月排行')
    ])
    keyboard.append([InlineKeyboardButton('⬅️返回管理员设置', callback_data='bot_settings')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text='📊 流量管理\n\n您可以查看用户流量使用情况及排名',
        reply_markup=reply_markup
    )
    return 'v2board_settings'

async def time_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """时长管理菜单"""
    query = update.callback_query
    await query.answer()
    keyboard = []
    
    # 定义时长菜单按钮
    keyboard.append([
        InlineKeyboardButton('⏱添加时长', callback_data='v2board_settings⏱添加时长'),
        InlineKeyboardButton('🗑️减少时长', callback_data='v2board_settings🗑️减少时长')
    ])
    keyboard.append([
        InlineKeyboardButton('🚮解绑用户', callback_data='v2board_settings🚮解绑用户'),
        InlineKeyboardButton('📝标题设置', callback_data='v2board_settings📝标题设置')
    ])
    keyboard.append([InlineKeyboardButton('⬅️返回管理员设置', callback_data='bot_settings')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text='⏱️ 时长管理\n\n您可以批量增加或减少用户订阅时长',
        reply_markup=reply_markup
    )
    return 'v2board_settings'