from init import init
from admin import *
from games import *
from betting import *
import logging
import os
import traceback  # 添加traceback模块用于详细错误日志
import asyncio
from telegram import ChatMember, ChatMemberUpdated, Bot, ChatPermissions
from telegram.ext import (
    ChatMemberHandler,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler
)
from MenuHandle import *
from MyCommandHandler import command_checkin, command_bind, command_unbind, command_lucky, command_wallet, command_traffic, command_modify, command_getid
from Config import config
from games import gambling
from keyboard import start_keyboard, start_keyboard_admin
from v2board import _bind, _checkin, _traffic, _lucky, _addtime, is_bind
from models import Db, BotDb, BotUser
from Utils import START_ROUTES, END_ROUTES, get_next_first
from typing import Optional, Tuple
from admin.v2board_settings import set_title
from admin.utils import reducetime
from admin.settings import select_setting
from admin.setting_reload import setting_reload

# 加载不需要热加载的配置项
TOKEN = config.TELEGRAM.token
HTTP_PROXY = config.TELEGRAM.http_proxy
HTTPS_PROXY = config.TELEGRAM.https_proxy

if HTTP_PROXY.find('未配置') == -1:
    os.environ['HTTP_PROXY'] = HTTP_PROXY
if HTTPS_PROXY.find('未配置') == -1:
    os.environ['HTTPS_PROXY'] = HTTPS_PROXY

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_telegram_id = config.TELEGRAM.admin_telegram_id
    if type(admin_telegram_id) == str:
        config.TELEGRAM.admin_telegram_id = update.effective_user.id
        admin_telegram_id = config.TELEGRAM.admin_telegram_id
        config.save()
    if update.effective_user.id == admin_telegram_id and update.effective_message.chat.type == 'private':
        reply_markup = InlineKeyboardMarkup(start_keyboard_admin)
    else:
        reply_markup = InlineKeyboardMarkup(start_keyboard)
    # await context.bot.send_message(chat_id=update.effective_chat.id, text='my Bot', reply_markup=reply_markup)
    await update.message.reply_text(config.TELEGRAM.title, reply_markup=reply_markup, disable_web_page_preview=True)
    # await update.message.reply_photo(photo=open('1.jpeg', 'rb'), caption=config.TELEGRAM.title, reply_markup=reply_markup)
    return START_ROUTES


async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            # 使用辅助函数显示警告
            await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，你重新发起")
            return START_ROUTES
            
        await query.answer()
        admin_telegram_id = config.TELEGRAM.admin_telegram_id
        if update.effective_user.id == admin_telegram_id and update.effective_message.chat.type == 'private':
            reply_markup = InlineKeyboardMarkup(start_keyboard_admin)
        else:
            reply_markup = InlineKeyboardMarkup(start_keyboard)
        await query.edit_message_text(config.TELEGRAM.title, reply_markup=reply_markup, disable_web_page_preview=True)
    except Exception as e:
        print(f"Error in start_over: {str(e)}")
        traceback.print_exc()  # 打印详细错误堆栈
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return START_ROUTES


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


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if not is_private_chat:
            # 群聊中需要验证是否是原始消息的发送者
            if not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
                # 使用辅助函数显示警告
                await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，你重新发起")
                return ConversationHandler.END
            
        await query.answer()
        await query.edit_message_text(text="欢迎下次光临！")
    except Exception as e:
        print(f"Error in end: {str(e)}")
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")
    return ConversationHandler.END


# 获取电报id
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_user.id, text=update.effective_chat.id)


async def reboot_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """重启机器人"""
    # 检查是否是管理员
    if update.effective_user.id != config.TELEGRAM.admin_telegram_id:
        await update.message.reply_text("❌ 只有管理员才能使用此命令")
        return
        
    try:
        # 发送重启消息
        await update.message.reply_text("🔄 正在重启机器人...")
        
        # 关闭数据库连接
        Db.close()
        BotDb.close()
        
        # 使用subprocess执行重启命令
        import subprocess
        import sys
        
        # 获取当前脚本的完整路径
        current_script = os.path.abspath(sys.argv[0])
        
        # 构建杀死旧进程的命令
        kill_cmd = "pkill -f 'python3.9 Bot.py'"
        
        # 构建重启命令
        restart_cmd = f"nohup /root/v2boardbot/python-3.9.7/bin/python3.9 {current_script} &"
        
        # 先杀死旧进程
        subprocess.run(kill_cmd, shell=True, stderr=subprocess.DEVNULL)
        
        # 等待一小段时间确保进程被杀死
        await asyncio.sleep(2)
        
        # 执行重启命令
        subprocess.Popen(restart_cmd, shell=True)
        
        # 发送重启成功消息
        await update.message.reply_text("✅ 机器人重启成功！")
        
        # 等待一小段时间确保消息发送完成
        await asyncio.sleep(1)
        
        # 退出当前进程
        os._exit(0)
    except Exception as e:
        logging.error(f"重启机器人时出错: {str(e)}", exc_info=True)
        await update.message.reply_text(f"❌ 重启失败: {str(e)}")


async def handle_input_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    try:
        text = _addtime(int(user_input))
    except:
        text = '输入有误，请输入整数'
    await update.message.reply_text(text)
    return ConversationHandler.END


async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.deleteMessage(chat_id=context.job.chat_id, message_id=context.job.user_id, pool_timeout=30)
    except Exception as e:
        logging.warning(f"删除消息失败: chat_id={context.job.chat_id}, message_id={context.job.user_id}, 错误: {str(e)}")
        # 不向管理员发送太多错误通知，避免消息过多
        pass


async def set_commands(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.set_my_commands(commands=[
        ("start", "展开管理面板"),
        ("bind", "绑定账号(仅限私聊)"),
        ("unbind", "解除绑定"),
        ("checkin", "每日签到"),
        ("lucky", "幸运抽奖"),
        ("wallet", "查看钱包"),
        ("traffic", "查看流量"),
        ("modify", "修改用户流量/时长(仅限管理员)"),
        ("getid", "获取用户ID"),
        # reboot命令不显示在命令列表中，只有管理员知道
    ])


async def keyword_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理关键词回复"""
    try:
        # 1. 获取消息内容
        if not update.message or not update.message.text:
            return None
            
        content = update.message.text.strip()
        if not content:
            return None
            
        # 记录消息来源
        chat_type = update.message.chat.type
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id
        logging.info(f"收到消息 - 类型: {chat_type}, 群组ID: {chat_id}, 用户ID: {user_id}, 内容: {content}")
            
        # 2. 获取关键词配置
        keyword_config = config.TELEGRAM.keyword_reply
        if not isinstance(keyword_config, dict) or not keyword_config:
            logging.info("关键词配置为空或格式错误")
            return None
            
        # 3. 遍历关键词进行匹配
        for key, value in keyword_config.items():
            if not key or not value:
                continue
                
            # 使用更灵活的匹配方式
            if str(key).lower() in str(content).lower():
                logging.info(f"匹配到关键词: {key} -> {value}")
                # 根据消息类型决定是否回复
                if chat_type in ['private', 'group', 'supergroup']:
                    await update.message.reply_text(str(value))
                    return True
                
        # 4. 如果没有匹配到关键词，返回None让其他处理器处理
        logging.info("未匹配到任何关键词")
        return None
                
    except Exception as e:
        logging.error(f"关键词回复出错: {str(e)}", exc_info=True)
        return None


def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


async def greet_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greets new users in chats and announces when someone leaves"""

    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    user_id = update.chat_member.from_user.id
    chat_id = update.chat_member.chat.id
    cause_name = update.chat_member.from_user.mention_html()
    member_name = update.chat_member.new_chat_member.user.mention_html()

    if not was_member and is_member:
        context.user_data['user_id'] = user_id
        context.user_data['chat_id'] = chat_id
        if not is_bind(user_id):
            if config.TELEGRAM.new_members == 'prohibition':
                context.user_data['verify_type'] = 'prohibition'
                permissions = ChatPermissions(can_send_messages=False, can_send_media_messages=False,
                                              can_send_other_messages=False)
                await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=permissions)
                keyboard = [[
                    InlineKeyboardButton("🔗前往绑定", url=f'{context.bot.link}?bind=bind'),
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_chat.send_message(
                    f"{member_name} 绑定账号后解除禁言！",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
            elif config.TELEGRAM.new_members == 'out':
                context.user_data['verify_type'] = 'out'
                await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id, until_date=60)
            elif config.TELEGRAM.new_members == 'verify':
                permissions = ChatPermissions(can_send_messages=False, can_send_media_messages=False,
                                              can_send_other_messages=False)
                await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=permissions)
                verify_dict = {
                    '苹果': '🍎',
                    '香蕉': '🍌',
                    '葡萄': '🍇',
                    '草莓': '🍓',
                    '橙子': '🍊',
                    '樱桃': '🍒',
                    '椰子': '🥥',
                    '菠萝': '🍍',
                    '桃子': '🍑',
                    '芒果': '🥭',
                }
                import random
                verify_value = random.choice(list(verify_dict.keys()))
                buttons_per_row = 4
                keyboard = [
                    [InlineKeyboardButton(j, callback_data=f'verify{j}') for j in
                     list(verify_dict.keys())[i:i + buttons_per_row]]
                    for i in range(0, len(verify_dict), buttons_per_row)
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_chat.send_message(
                    f"{member_name} 欢迎你加入本群！\n请点击下方的 {verify_value} 解除禁言",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                context.user_data['verify_value'] = verify_value


async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data == {}:
        return
    query = update.callback_query
    try:
        # 检查聊天类型
        is_private_chat = update.effective_chat.type == 'private'
        
        # 私聊直接允许，不需要验证
        if not is_private_chat:
            # 群聊中需要验证是否是原始消息的发送者
            if not query.message.reply_to_message or query.message.reply_to_message.from_user.id != update.effective_user.id:
                # 使用辅助函数显示警告
                await show_telegram_alert(context, query, "❌ 该对话不属于你的对话，你重新发起")
                return
            
        await query.answer()
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        verify_value = query.data.replace('verify', '')
        
        # 检查verify_value键是否存在
        if 'verify_value' not in context.user_data:
            logging.warning(f"用户 {user_id} 验证时缺少verify_value键")
            return
            
        if context.user_data['user_id'] == user_id and context.user_data['verify_value'] == verify_value:
            permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                          can_send_other_messages=True)
            await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=permissions)
            message_id = update.effective_message.id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logging.info(f"用户 {user_id} 验证成功，已解除限制")
        else:
            logging.warning(f"用户 {user_id} 验证失败，输入:{verify_value}, 预期:{context.user_data.get('verify_value', 'None')}")
    except Exception as e:
        print(f"Error in verify: {str(e)}")
        traceback.print_exc()  # 打印详细错误堆栈
        try:
            await show_telegram_alert(context, query, "❌ 操作失败，请重试")
        except Exception as e2:
            print(f"Error showing alert: {str(e2)}")


class Mybot(Bot):
    async def add_message_dict(self, botmessage, dice=False):
        when = config.TELEGRAM.delete_message
        if type(when) == str:
            return
        if botmessage.reply_to_message:
            chat_id = botmessage.chat.id
            if dice:
                job_queue.run_once(delete_message, when, chat_id=chat_id, user_id=botmessage.id)
            else:
                job_queue.run_once(delete_message, when, chat_id=chat_id,
                                   user_id=botmessage.id)
                job_queue.run_once(delete_message, when, chat_id=chat_id,
                                   user_id=botmessage.reply_to_message.message_id)

    async def send_message(self, **kwargs):
        botmessage = await super().send_message(**kwargs)
        await self.add_message_dict(botmessage)
        return botmessage

    async def send_dice(self, **kwargs):
        botmessage = await super().send_dice(**kwargs)
        await self.add_message_dict(botmessage, dice=True)
        return botmessage


def main():
    # 面板数据库连接
    Db.connect()
    if os.path.exists('bot.db'):
        res = BotDb.connect()
    else:
        res = BotDb.connect()
        BotDb.create_tables([BotUser])
    bot = Mybot(token=TOKEN)
    application = Application.builder().token(TOKEN).build()
    job_queue = application.job_queue
    first = get_next_first()
    job_queue.run_once(set_commands, 1)
    job_queue.run_repeating(open_number, interval=300, first=first)

    # 命令处理器列表
    command_handlers = [
        CommandHandler("start", start),
        CommandHandler("myid", myid),
        CommandHandler("checkin", command_checkin),
        CommandHandler('bind', command_bind),
        CommandHandler('unbind', command_unbind),
        CommandHandler('lucky', command_lucky),
        CommandHandler('wallet', command_wallet),
        CommandHandler('traffic', command_traffic),
        CommandHandler('modify', command_modify),
        CommandHandler('getid', command_getid),
        CommandHandler('reboot', reboot_bot),  # 添加重启命令
    ]

    # 创建状态处理对话处理器
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            CallbackQueryHandler(select_setting, pattern="^settings.*"),
            CallbackQueryHandler(v2board_settings, pattern="^v2board_settings$"),
            CallbackQueryHandler(v2board_select_setting, pattern="^v2board_settings.*"),
        ],
        states={
            START_ROUTES: [
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
                CallbackQueryHandler(start_over, pattern="^start_over$"),
                CallbackQueryHandler(end, pattern="^end$"),
            ],
            'bot_settings': [
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
                CallbackQueryHandler(select_setting, pattern="^settings.*"),
                CallbackQueryHandler(start_over, pattern="^start_over$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings),
            ],
            'v2board_settings': [
                CallbackQueryHandler(v2board_select_setting, pattern="^v2board_settings.*"),
                CallbackQueryHandler(start_over, pattern="^start_over$"),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
            'title': [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_title),
                CallbackQueryHandler(v2board_settings, pattern="^v2board_settings$"),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
            'bot_reduce_time': [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
            'reduce_time': [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reducetime),
                CallbackQueryHandler(v2board_settings, pattern="^v2board_settings$"),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
            'addtime': [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_addtime),
                CallbackQueryHandler(v2board_settings, pattern="^v2board_settings$"),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
            'checkin': [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
            'lucky': [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
            'keyword_reply': [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
            'new_members': [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings),
                CallbackQueryHandler(bot_settings, pattern="^bot_settings$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(end, pattern="^end$"),
        ],
        allow_reentry=True,
        name="bot_settings_conversation",
    )

    # 按钮回调处理器
    callback_handlers = [
        CallbackQueryHandler(betting_slots, pattern="^betting_slots"),
        CallbackQueryHandler(start_over, pattern="^start_over$"),
        CallbackQueryHandler(verify, pattern="^verify"),
        CallbackQueryHandler(game_settings, pattern="^game_settings"),
        CallbackQueryHandler(start_game, pattern="^start_game"),
        CallbackQueryHandler(select_flow, pattern="^[1-9]|10GB|xGB$"),
        CallbackQueryHandler(v2board_settings, pattern="^v2board_settings$"),
        CallbackQueryHandler(select_setting, pattern="^v2board_settings.+"),
        CallbackQueryHandler(menu_wallet, pattern="^wallet"),
        CallbackQueryHandler(menu_checkin, pattern="^checkin$"),
        CallbackQueryHandler(menu_sub, pattern="^sub$"),
        CallbackQueryHandler(menu_mysub, pattern="^mysub"),
        CallbackQueryHandler(menu_traffic, pattern="^traffic$"),
        CallbackQueryHandler(menu_lucky, pattern="^lucky"),
        CallbackQueryHandler(menu_node, pattern="^node"),
        CallbackQueryHandler(traffic_manage, pattern="^traffic_manage"),
        CallbackQueryHandler(time_manage, pattern="^time_manage"),
        CallbackQueryHandler(game_switch, pattern="^game_switch"),
        CallbackQueryHandler(select_game, pattern="^select_game"),
        CallbackQueryHandler(game_rate, pattern="^game_rate"),
        CallbackQueryHandler(setting_reload, pattern="^setting_reload$"),
    ]

    # 其他消息处理器
    message_handlers = [
        MessageHandler(filters.Text(['不玩了', '退出', 'quit']), quit_game),
        MessageHandler(filters.Text(['设置为开奖群']), set_open_group),
        MessageHandler(filters.Dice(), gambling),
    ]

    # 添加处理器的顺序很重要
    # 1. 添加命令处理器
    for handler in command_handlers:
        application.add_handler(handler)

    # 2. 添加对话处理器
    application.add_handler(conv_handler)

    # 3. 添加回调处理器
    for handler in callback_handlers:
        application.add_handler(handler)

    # 4. 添加关键词回复处理器（放在最后，确保最高优先级）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, keyword_reply))

    # 5. 添加其他消息处理器
    for handler in message_handlers:
        application.add_handler(handler)

    # 添加成员处理器
    application.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))

    # 异步运行
    application.run_polling()

    # 关闭数据库
    Db.close()
    BotDb.close()


if __name__ == '__main__':
    main()
