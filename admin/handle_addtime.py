import logging
import asyncio
import concurrent.futures
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from admin.utils import addtime, reducetime

# 添加一个函数来在线程池中运行同步函数
async def run_sync_function(func, *args, **kwargs):
    """在线程池中运行同步函数"""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(
            pool, 
            lambda: func(*args, **kwargs)
        )

async def handle_addtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理添加时长的命令"""
    try:
        # 获取要增加的天数
        days = int(update.message.text)
        if days <= 0:
            await update.message.reply_text("❌ 请输入大于0的整数")
            return
            
        # 调用异步的addtime函数，并传递天数
        await addtime(update, context, days)
        
    except ValueError:
        await update.message.reply_text("❌ 请输入有效的整数")
    except Exception as e:
        await update.message.reply_text(f"❌ 添加时长操作失败: {str(e)}")

async def handle_reducetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户输入的减少时长天数"""
    logging.info(f"收到减少时长输入: {update.message.text}")
    
    try:
        # 获取用户输入的天数
        user_input = update.message.text.strip()
        logging.info(f"处理减少时长输入: '{user_input}'")
        
        try:
            days = int(user_input)
            logging.info(f"转换后的天数: {days}")
            
            # 添加合理性检查
            if days <= 0:
                logging.warning(f"输入的天数不能为负数或零: {days}")
                await update.message.reply_text("❌ 请输入大于0的天数！")
                return 'v2board_settings'
            
            # 添加上限检查 (3650天 = 10年)
            if days > 3650:
                logging.warning(f"输入的天数超过上限: {days}")
                await update.message.reply_text("❌ 减少的天数不能超过3650天（10年）！")
                return 'v2board_settings'
                
        except ValueError:
            logging.warning(f"输入不是有效数字: '{user_input}'")
            await update.message.reply_text("❌ 请输入有效的数字！")
            return 'v2board_settings'
        
        # 调用异步的reducetime函数，并传递天数
        await reducetime(update, context, days)
        
        # 返回管理员主菜单
        return 'v2board_settings'
        
    except Exception as e:
        logging.error(f"处理减少时长时出错: {str(e)}", exc_info=True)
        await update.message.reply_text(f"❌ 减少时长出错: {str(e)}")
        return 'v2board_settings' 