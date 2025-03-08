from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)
import logging

from Config import config
from keyboard import return_keyboard
from models import V2User
from v2board import _bind, _checkin, _traffic, _lucky, _sub, _node, _wallet, _mysub
from Utils import START_ROUTES, END_ROUTES, WAITING_INPUT


async def show_telegram_alert(context, query, message):
    """多种方式尝试显示Telegram警告弹窗"""
    success = False
    error_details = []
    
    # 方法1: 使用bot.answer_callback_query
    try:
        await context.bot.answer_callback_query(
            callback_query_id=query.id,
            text=message,
            show_alert=True
        )
        success = True
        return success
    except Exception as e:
        error_details.append(f"方法1失败: {str(e)}")
        
    # 方法2: 使用query.answer
    if not success:
        try:
            await query.answer(message, show_alert=True)
            success = True
            return success
        except Exception as e:
            error_details.append(f"方法2失败: {str(e)}")
    
    # 方法3: 发送新消息
    if not success:
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message
            )
            success = True
            return success
        except Exception as e:
            error_details.append(f"方法3失败: {str(e)}")
    
    # 记录所有错误
    if not success:
        error_msg = "显示警告弹窗失败: " + "; ".join(error_details)
        print(error_msg)
        logging.error(error_msg)
    
    return success


# 赌博模式
async def menu_gambling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 显示提示消息
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，请重新发起")
            return START_ROUTES
            
        await query.answer()
        
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        v2_user = V2User.select().where(V2User.telegram_id == update.effective_user.id).first()
        if not v2_user:
            await query.edit_message_text(
                text=f'未绑定,请先绑定',
                reply_markup=reply_markup
            )
            return START_ROUTES
            # 总开关
        if config.GAME.switch != True:
            await query.message.reply_text(text='当前赌博模式关闭，请联系管理员！')
            return ConversationHandler.END
        await query.edit_message_text(
            text=f'请发送🎰或🎲表情，可以连续发送\n当前赔率:🎰1赔{config.TIGER.rate} 🎲1赔{config.DICE.rate}\n发送"不玩了"退出赌博模式',
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error in menu_gambling: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return WAITING_INPUT


# 钱包
async def menu_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 显示提示消息
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，请重新发起")
            return START_ROUTES
            
        await query.answer()
        
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        v2_user = V2User.select().where(V2User.telegram_id == update.effective_user.id).first()
        if not v2_user:
            await query.edit_message_text(
                text=f'未绑定,请先绑定',
                reply_markup=reply_markup
            )
            return START_ROUTES
        text = _wallet(update.effective_user.id)
        await query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Error in menu_wallet: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return START_ROUTES


# 菜单签到
async def menu_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 显示提示消息
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，请重新发起")
            return START_ROUTES
            
        await query.answer()
        
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        v2_user = V2User.select().where(V2User.telegram_id == update.effective_user.id).first()
        if not v2_user:
            await query.edit_message_text(
                text=f'未绑定,请先绑定',
                reply_markup=reply_markup
            )
            return START_ROUTES
        text = _checkin(update.effective_user.id)
        await query.edit_message_text(
            text=text, reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error in menu_checkin: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return START_ROUTES


async def menu_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 显示提示消息
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，请重新发起")
            return START_ROUTES
            
        await query.answer()
        
        v2_user = V2User.select().where(V2User.telegram_id == update.effective_user.id).first()
        if not v2_user:
            keyboard = [
                return_keyboard,
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f'未绑定,请先绑定',
                reply_markup=reply_markup
            )
            return START_ROUTES
            
        text = _sub(update.effective_user.id)
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Error in menu_sub: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return START_ROUTES


async def menu_mysub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 显示提示消息
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，请重新发起")
            return START_ROUTES
            
        await query.answer()
        
        v2_user = V2User.select().where(V2User.telegram_id == update.effective_user.id).first()
        if not v2_user:
            keyboard = [
                return_keyboard,
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f'未绑定,请先绑定',
                reply_markup=reply_markup
            )
            return START_ROUTES
            
        text = _mysub(update.effective_user.id)
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Error in menu_mysub: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return START_ROUTES


# 流量查询
async def menu_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 显示提示消息
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，请重新发起")
            return START_ROUTES
            
        await query.answer()
        
        v2_user = V2User.select().where(V2User.telegram_id == update.effective_user.id).first()
        if not v2_user:
            keyboard = [
                return_keyboard,
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f'未绑定,请先绑定',
                reply_markup=reply_markup
            )
            return START_ROUTES
            
        text = _traffic(update.effective_user.id)
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Error in menu_traffic: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return START_ROUTES


# 幸运抽奖
async def menu_lucky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 显示提示消息
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，请重新发起")
            return START_ROUTES
            
        await query.answer()
        
        v2_user = V2User.select().where(V2User.telegram_id == update.effective_user.id).first()
        if not v2_user:
            keyboard = [
                return_keyboard,
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f'未绑定,请先绑定',
                reply_markup=reply_markup
            )
            return START_ROUTES
            
        text = _lucky(update.effective_user.id)
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=text, reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error in menu_lucky: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return START_ROUTES


# 节点状态
async def menu_node(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 显示提示消息
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，请重新发起")
            return START_ROUTES
            
        await query.answer()
        
        v2_user = V2User.select().where(V2User.telegram_id == update.effective_user.id).first()
        if not v2_user:
            keyboard = [
                return_keyboard,
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f'未绑定,请先绑定',
                reply_markup=reply_markup
            )
            return START_ROUTES
            
        text = _node(update.effective_user.id)
        keyboard = [
            return_keyboard,
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Error in menu_node: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return START_ROUTES
