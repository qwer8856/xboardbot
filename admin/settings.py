from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging
import asyncio

from admin import settings_dict
from keyboard import return_keyboard
from Config import config
from admin.utils import reducetime

# 全局变量
edit_setting_name = False


async def bot_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        is_admin = update.effective_user.id == config.TELEGRAM.admin_telegram_id
        
        # 私聊或管理员私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message:
            # 如果没有回复消息，说明是新的对话，记录当前用户ID
            context.user_data['original_user_id'] = update.effective_user.id
        elif query.message.reply_to_message.from_user.id != update.effective_user.id:
            # 测试另一种方式显示提示消息
            try:
                # 方法1：直接使用context.bot
                await context.bot.answer_callback_query(
                    callback_query_id=query.id,
                    text="❌ 该对话不属于你的对话，请重新发起",
                    show_alert=True
                )
            except Exception as alert_error:
                logging.error(f"显示弹窗失败(方法1): {str(alert_error)}")
                try:
                    # 方法2：使用query直接调用
                    await query.answer("❌ 该对话不属于你的对话，请重新发起", show_alert=True)
                except Exception as alert_error2:
                    logging.error(f"显示弹窗失败(方法2): {str(alert_error2)}")
                    try:
                        # 方法3：尝试发送一条新消息
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="❌ 该对话不属于你的对话，请重新发起"
                        )
                    except Exception as msg_error:
                        logging.error(f"发送消息失败: {str(msg_error)}")
            
            return 'bot_settings'
            
        await query.answer()
        buttons_per_row = 2
        keyboard = [
            [InlineKeyboardButton(j, callback_data=f'settings{j}') for j in
             list(settings_dict.keys())[i:i + buttons_per_row]]
            for i in range(0, len(settings_dict), buttons_per_row)
        ]
        keyboard.append(return_keyboard)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=config.TELEGRAM.title, reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"处理机器人设置时出错: {str(e)}", exc_info=True)
        try:
            # 尝试发送错误消息
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ 操作失败，请重试"
            )
        except:
            pass
    return 'bot_settings'


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global edit_setting_name
    try:
        if update.callback_query:
            query = update.callback_query
            # 检查聊天类型
            is_private_chat = update.effective_chat.type == 'private'
            
            # 私聊直接允许，不需要验证
            if is_private_chat:
                # 私聊中不需要验证发送者身份
                pass
            # 群聊中需要验证是否是原始消息的发送者
            elif not query.message.reply_to_message:
                # 如果没有回复消息，说明是新的对话，记录当前用户ID
                context.user_data['original_user_id'] = update.effective_user.id
            elif query.message.reply_to_message.from_user.id != update.effective_user.id:
                try:
                    # 显示提示消息
                    await context.bot.answer_callback_query(
                        callback_query_id=query.id,
                        text="❌ 该对话不属于你的对话，请重新发起",
                        show_alert=True
                    )
                except Exception as e:
                    logging.error(f"显示弹窗失败: {str(e)}")
                    try:
                        # 备用方法：发送消息
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="❌ 该对话不属于你的对话，请重新发起"
                        )
                    except:
                        pass
                return 'bot_settings'
                
            await query.answer()
            callback = update.callback_query.data
            name = callback.replace('settings', '')
            
            # 设置返回按钮
            keyboard = [
                [
                    InlineKeyboardButton("返回", callback_data='bot_settings'),
                ]
            ]
            
            # 根据不同的设置类型显示不同的提示文本
            if name == '🏷️标题设置':
                text = '请发送BOT的标题内容'
                state = 'title'
            elif name == '🗑️减少时长':
                text = '''🗑️ 减少订阅时长
————————————
请输入要减少的天数（正整数）
例如：1
        
⚠️ 此操作将减少所有有效订阅用户的订阅时长
⚠️ 请谨慎操作'''
                state = 'reduce_time'
            elif name == '📅签到设置':
                text = '''📅 签到设置
————————————
格式说明：最小值|最大值
单位：MB

示例：10|50
表示签到可获得10MB到50MB之间的随机流量

注意：
1. 使用|分隔最小值和最大值
2. 发送"关闭"可以关闭签到功能'''
                state = 'checkin'
            elif name == '✨抽奖设置':
                text = '''✨ 抽奖设置
————————————
格式说明：最小值|最大值
单位：MB

示例：-1024|1024
表示抽奖可获得-1024MB到1024MB之间的随机流量
负数表示扣除流量

注意：
1. 使用|分隔最小值和最大值
2. 发送"关闭"可以关闭抽奖功能'''
                state = 'lucky'
            else:
                text = "❌ 未知的设置选项"
                state = 'bot_settings'
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=text, reply_markup=reply_markup)
            context.user_data['state'] = state
            return state
            
        else:
            # 处理文本输入
            input_ = update.message.text
            state = context.user_data.get('state')
            set_name = edit_setting_name
            
            # 签到设置和抽奖设置
            if state in ['checkin', 'lucky']:
                if input_.strip().lower() == '关闭':
                    input_ = None
                    text = f'✅ {set_name}已关闭'
                else:
                    try:
                        min_val, max_val = map(int, input_.strip().split('|'))
                        if min_val > max_val:
                            min_val, max_val = max_val, min_val
                        input_ = f"{min_val}|{max_val}"
                        text = f'✅ {set_name}已设置为：{min_val}MB 到 {max_val}MB'
                    except:
                        text = '❌ 输入格式错误，请按照"最小值|最大值"的格式输入，例如：10|50'
                        await update.message.reply_text(text)
                        return 'bot_settings'
                setattr(config.TELEGRAM, settings_dict[set_name], input_)
                config.save()
                context.user_data['state'] = None
                edit_setting_name = False
                await update.message.reply_text(text)
                return 'bot_settings'
                
    except Exception as e:
        logging.error(f"处理设置时出错: {str(e)}", exc_info=True)
        try:
            if update.callback_query:
                # 发送错误消息
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ 操作失败，请重试"
                )
        except:
            pass
        return 'bot_settings'


async def select_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global edit_setting_name
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if is_private_chat:
            # 私聊中不需要验证发送者身份
            pass
        # 群聊中需要验证是否是原始消息的发送者
        elif not query.message.reply_to_message:
            # 如果没有回复消息，说明是新的对话，记录当前用户ID
            context.user_data['original_user_id'] = update.effective_user.id
        elif query.message.reply_to_message.from_user.id != update.effective_user.id:
            try:
                # 显示提示消息
                await context.bot.answer_callback_query(
                    callback_query_id=query.id,
                    text="❌ 该对话不属于你的对话，请重新发起",
                    show_alert=True
                )
            except Exception as e:
                logging.error(f"显示弹窗失败: {str(e)}")
                try:
                    # 备用方法：发送消息
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ 该对话不属于你的对话，请重新发起"
                    )
                except:
                    pass
            return 'bot_settings'
            
        await query.answer()
        callback = update.callback_query.data
        name = callback.replace('settings', '')
        
        # 设置返回按钮
        keyboard = [
            [
                InlineKeyboardButton("返回", callback_data='bot_settings'),
            ]
        ]
        
        # 根据不同的设置类型显示不同的提示文本
        if name == '🏷️标题设置':
            text = '请发送BOT的标题内容'
            state = 'title'
        elif name == '🗑️减少时长':
            text = '''🗑️ 减少订阅时长
————————————
请输入要减少的天数（正整数）
例如：1
        
⚠️ 此操作将减少所有有效订阅用户的订阅时长
⚠️ 请谨慎操作'''
            state = 'reduce_time'
        elif name == '📅签到设置':
            text = '''📅 签到设置
————————————
格式说明：最小值|最大值
单位：MB

示例：10|50
表示签到可获得10MB到50MB之间的随机流量

注意：
1. 使用|分隔最小值和最大值
2. 发送"关闭"可以关闭签到功能'''
            state = 'checkin'
        elif name == '✨抽奖设置':
            text = '''✨ 抽奖设置
————————————
格式说明：最小值|最大值
单位：MB

示例：-1024|1024
表示抽奖可获得-1024MB到1024MB之间的随机流量
负数表示扣除流量

注意：
1. 使用|分隔最小值和最大值
2. 发送"关闭"可以关闭抽奖功能'''
            state = 'lucky'
        else:
            text = "❌ 未知的设置选项"
            state = 'bot_settings'
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
        context.user_data['state'] = state
        edit_setting_name = name
        return state
        
    except Exception as e:
        logging.error(f"处理设置选择时出错: {str(e)}", exc_info=True)
        try:
            # 发送错误消息
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ 操作失败，请重试"
            )
        except:
            pass
        return 'bot_settings'
