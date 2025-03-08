import json
import logging
import asyncio
import concurrent.futures

from Config import config
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from admin.utils import addtime, reducetime, statDay, statMonth
from Utils import START_ROUTES

# 定义返回按钮布局
return_button = InlineKeyboardButton("⬅️返回", callback_data="v2board_settings")
return_keyboard = InlineKeyboardMarkup([[return_button]])

# 流量管理
add_time_keyboard = InlineKeyboardButton('⏱添加时长', callback_data='v2board_settings⏱添加时长')
reduce_time_keyboard = InlineKeyboardButton('🗑️减少时长', callback_data='v2board_settings🗑️减少时长')
unbind_keyboard = InlineKeyboardButton('🚮解绑用户', callback_data='v2board_settings🚮解绑用户')
set_title_keyboard = InlineKeyboardButton('📝标题设置', callback_data='v2board_settings📝标题设置')
yesterday_flow_keyboard = InlineKeyboardButton('🥇昨日排行', callback_data='v2board_settings🥇昨日排行')
month_flow_keyboard = InlineKeyboardButton('🏆本月排行', callback_data='v2board_settings🏆本月排行')
return_main_keyboard = InlineKeyboardButton('⬅️返回主菜单', callback_data='start_over')
keyboard = [
    [add_time_keyboard, reduce_time_keyboard],
    [unbind_keyboard, set_title_keyboard],
    [yesterday_flow_keyboard, month_flow_keyboard],
    [return_main_keyboard]
]
keyboard_admin = InlineKeyboardMarkup(keyboard)

# 添加一个函数来在线程池中运行同步函数
async def run_sync_function(func, *args, **kwargs):
    """在线程池中运行同步函数"""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(
            pool, 
            lambda: func(*args, **kwargs)
        )

async def select_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATUS = 'v2board_settings'
    query = update.callback_query
    await query.answer()
    
    # 获取回调数据，移除前缀
    callback = update.callback_query.data
    name = callback.replace('v2board_settings', '')
    logging.info(f"收到回调数据: {name}")
    
    try:
        if name == '⏱添加时长':
            text = '''⏱ 批量添加时长说明
————————————
请输入要增加的天数（正整数）
例如：30

⚠️ 注意事项：
- 数值必须为正整数
- 单位为天
- 此操作将为所有有效用户增加订阅时长
- 请谨慎操作'''
            await query.edit_message_text(text=text, reply_markup=return_keyboard)
            context.user_data['state'] = 'addtime'
            return 'addtime'
            
        elif name == '🗑️减少时长':
            text = '''🗑️ 批量减少时长说明
————————————
请输入要减少的天数（正整数）
例如：30

⚠️ 注意事项：
- 数值必须为正整数
- 单位为天
- 此操作将为所有有效用户减少订阅时长
- 请谨慎操作'''
            await query.edit_message_text(text=text, reply_markup=return_keyboard)
            context.user_data['state'] = 'reduce_time'
            return 'reduce_time'
            
        elif name == '🚮解绑用户':
            text = '''🚮 解绑用户说明
————————————
请使用以下命令解绑用户：
/unbind 用户邮箱

⚠️ 注意事项：
- 该命令仅限管理员使用
- 解绑后用户需要重新绑定
- 请谨慎操作'''
            await query.edit_message_text(text=text, reply_markup=return_keyboard)
            return STATUS
            
        elif name == '🥇昨日排行':
            try:
                logging.info("开始获取流量排行榜")
                try:
                    text = await run_sync_function(statDay)
                    if not text:
                        text = "❌ 未能获取流量排行数据，请联系管理员"
                    logging.info(f"获取流量排行榜结果: {text[:50]}...")
                except Exception as db_error:
                    logging.error(f"数据库查询错误: {str(db_error)}", exc_info=True)
                    text = f"❌ 数据库查询错误\n\n错误详情: {str(db_error)}\n\n请检查数据库连接和日志。"
            except Exception as e:
                error_msg = f"获取流量排行榜失败: {str(e)}"
                logging.error(error_msg, exc_info=True)
                text = f"❌ 获取流量排行榜失败\n\n错误详情: {str(e)}\n\n请检查日志了解更多信息。"
            
            await query.edit_message_text(text=text, reply_markup=return_keyboard)
            return STATUS
            
        elif name == '🏆本月排行':
            try:
                logging.info("开始获取流量排行榜")
                try:
                    text = await run_sync_function(statMonth)
                    if not text:
                        text = "❌ 未能获取流量排行数据，请联系管理员"
                    logging.info(f"获取流量排行榜结果: {text[:50]}...")
                except Exception as db_error:
                    logging.error(f"数据库查询错误: {str(db_error)}", exc_info=True)
                    text = f"❌ 数据库查询错误\n\n错误详情: {str(db_error)}\n\n请检查数据库连接和日志。"
            except Exception as e:
                error_msg = f"获取流量排行榜失败: {str(e)}"
                logging.error(error_msg, exc_info=True)
                text = f"❌ 获取流量排行榜失败\n\n错误详情: {str(e)}\n\n请检查日志了解更多信息。"
            
            await query.edit_message_text(text=text, reply_markup=return_keyboard)
            return STATUS
            
        elif name == '📝标题设置':
            text = '''📝 标题设置说明
————————————
请输入新的标题文本，例如：
"欢迎使用XXX机场"

⚠️ 注意事项：
- 标题文本不要太长
- 不支持HTML格式
- 可以使用emoji表情'''
            await query.edit_message_text(text=text, reply_markup=return_keyboard)
            context.user_data['state'] = 'title'
            return 'title'
            
        else:
            text = "❌ 未知的操作选项"
            await query.edit_message_text(text=text, reply_markup=return_keyboard)
            return STATUS
            
    except Exception as e:
        logging.error(f"处理管理员选项时出错: {str(e)}", exc_info=True)
        text = f"❌ 操作失败: {str(e)}"
        await query.edit_message_text(text=text, reply_markup=return_keyboard)
        return STATUS

async def set_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置机器人标题"""
    logging.info(f"收到设置标题输入: {update.message.text}")
    new_title = update.message.text
    
    try:
        # 更新配置
        config.TELEGRAM.title = new_title
        config.save()
        
        # 返回成功消息
        await update.message.reply_text(f"✅ 标题已更新为：\n\n{new_title}")
        
    except Exception as e:
        logging.error(f"设置标题时出错: {str(e)}", exc_info=True)
        await update.message.reply_text(f"❌ 设置标题失败: {str(e)}")
    
    return 'v2board_settings'

async def v2board_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 显示菜单
    text = '''⚙️ 管理员设置
————————————
请选择要执行的操作：'''
    
    await query.edit_message_text(text=text, reply_markup=keyboard_admin)
    return 'v2board_settings'
