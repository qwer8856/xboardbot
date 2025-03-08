import json
import logging

from Config import config
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from Utils import START_ROUTES


async def setting_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        config.reload()
        logging.info("配置重载成功")
        await query.message.reply_text(text='✅ 配置重载成功')
    except Exception as e:
        logging.error(f"配置重载失败: {str(e)}")
        await query.message.reply_text(text=f'❌ 配置重载失败: {str(e)}')
    return START_ROUTES
