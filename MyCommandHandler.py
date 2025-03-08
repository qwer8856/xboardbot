from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ChatPermissions
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from Config import config
from keyboard import return_keyboard
from models import V2User
from v2board import _bind, _checkin, _traffic, _lucky, _unbind, _wallet
from Utils import START_ROUTES, END_ROUTES
from datetime import datetime


# 签到
async def command_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _checkin(update.effective_user.id)
    keyboard = [
        return_keyboard,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return START_ROUTES


# 绑定
async def command_bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        return_keyboard,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message.chat.type != 'private':
        text = '''❌ 绑定用户仅限私聊使用
————————————
请私聊机器人进行绑定操作'''
        await update.message.reply_text(text=text, reply_markup=reply_markup)
        return START_ROUTES
    else:
        if not context.args:
            text = '''📋 绑定账号说明
————————————
1️⃣ 在网站复制订阅链接
2️⃣ 发送: /bind 订阅链接

🔍 支持的订阅链接格式:
1. /bind https://xxx/s/xxxxxx
2. /bind http://xxx/api/v1/client/subscribe?token=xxxxxx

❗注意: 复制完整的订阅链接'''
            await update.message.reply_text(text=text, reply_markup=reply_markup)
            return START_ROUTES
        try:
            sub_url = context.args[0]
            # 处理两种不同格式的订阅链接
            if 'token=' in sub_url:
                # 处理token格式
                token = sub_url.split('token=')[-1]
            else:
                # 处理/s/格式
                token = sub_url.split('/s/')[-1]
                if '/' in token:  # 移除可能的额外路径
                    token = token.split('/')[0]
        except:
            text = '''❌ 参数错误
————————————
请发送完整的订阅链接，支持以下格式：
1. https://xxx/s/xxxxxx
2. http://xxx/api/v1/client/subscribe?token=xxxxxx'''
            await update.message.reply_text(text=text, reply_markup=reply_markup)
            return START_ROUTES
    text = _bind(token, update.effective_user.id)
    if text.startswith('✅ 绑定成功'):
        if 'chat_id' in context.user_data and 'user_id' in context.user_data and 'verify_type' in context.user_data:
            chat_id = context.user_data['chat_id']
            user_id = context.user_data['user_id']
            verify_type = context.user_data['verify_type']
            if verify_type == 'prohibition':
                permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                              can_send_other_messages=True)
                await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=permissions)
            elif verify_type == 'out':
                await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return START_ROUTES


# 解绑
async def command_unbind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id  # 当前发送命令的用户ID
    keyboard = [
        return_keyboard,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 检查是否是管理员
    is_admin = telegram_id == config.TELEGRAM.admin_telegram_id
    
    # 管理员在群组中回复消息解绑
    if is_admin and update.message.reply_to_message:
        try:
            # 获取被回复消息的信息
            reply_msg = update.message.reply_to_message
            
            # 调试信息
            print("回复消息对象:", reply_msg)
            print("回复消息类型:", type(reply_msg))
            print("回复消息ID:", reply_msg.message_id)
            print("回复消息文本:", reply_msg.text)
            
            # 获取被回复用户的信息
            replied_user = reply_msg.from_user
            print("被回复用户对象:", replied_user)
            print("被回复用户类型:", type(replied_user))
            
            if not replied_user:
                text = '''❌ 无法获取被回复用户信息
————————————
请确保回复了正确的用户消息'''
                await update.message.reply_text(text=text, reply_markup=reply_markup)
                return START_ROUTES
            
            # 获取被回复用户的详细信息
            replied_user_id = replied_user.id
            replied_username = replied_user.username or '未设置用户名'
            replied_first_name = replied_user.first_name or '未设置名字'
            
            # 更多调试信息
            print("当前用户ID:", telegram_id)
            print("被回复用户ID:", replied_user_id)
            print("被回复用户名:", replied_username)
            print("被回复用户姓名:", replied_first_name)
            
            # 检查是否是自己的消息
            if replied_user_id == telegram_id:
                text = '''❌ 不能解绑自己的账号
————————————
请回复其他用户的消息'''
                await update.message.reply_text(text=text, reply_markup=reply_markup)
                return START_ROUTES
                
            # 检查被回复的用户是否已绑定账号
            v2_user = V2User.select().where(V2User.telegram_id == replied_user_id).first()
            if not v2_user:
                text = f'''❌ 操作失败
————————————
该用户未绑定任何账号
👤 用户名：@{replied_username}
👤 名字：{replied_first_name}
🆔 用户ID：{replied_user_id}'''
                await update.message.reply_text(text=text, reply_markup=reply_markup)
                return START_ROUTES
                
            # 执行解绑操作
            text = _unbind(replied_user_id)  # 使用被回复用户的ID进行解绑
            if text.startswith('✅ 解绑成功'):
                # 隐藏邮箱前5位
                hidden_email = '*****' + v2_user.email[5:] if len(v2_user.email) > 5 else v2_user.email
                text = f'''✅ 解绑成功！
————————————
📧 已解绑账号：{hidden_email}
👤 用户名：@{replied_username}
👤 名字：{replied_first_name}
🆔 用户ID：{replied_user_id}
⚠️ 管理员操作提示：该操作由管理员执行'''
            
            await update.message.reply_text(text=text, reply_markup=reply_markup)
            return START_ROUTES
            
        except Exception as e:
            print(f"解绑操作出错: {str(e)}")
            print(f"错误类型: {type(e)}")
            print(f"错误详情: {e.__dict__}")
            text = '''❌ 解绑操作出错
————————————
请确保回复了正确的用户消息'''
            await update.message.reply_text(text=text, reply_markup=reply_markup)
            return START_ROUTES
    
    # 管理员通过邮箱解绑
    if is_admin and len(context.args) >= 1:
        email = context.args[0]
        v2_user = V2User.select().where(V2User.email == email).first()
        if not v2_user:
            text = '''❌ 用户不存在
————————————
请检查邮箱是否正确'''
            await update.message.reply_text(text=text, reply_markup=reply_markup)
            return START_ROUTES
            
        if not v2_user.telegram_id:
            text = '''❌ 操作失败
————————————
该用户未绑定TG账号'''
            await update.message.reply_text(text=text, reply_markup=reply_markup)
            return START_ROUTES
            
        # 执行解绑操作
        target_telegram_id = v2_user.telegram_id
        text = _unbind(target_telegram_id)
        if text.startswith('✅ 解绑成功'):
            # 隐藏邮箱前5位
            hidden_email = '*****' + email[5:] if len(email) > 5 else email
            text = f'''✅ 解绑成功！
————————————
📧 已解绑账号：{hidden_email}
🆔 用户ID：{target_telegram_id}
⚠️ 管理员操作提示：该操作由管理员执行'''
            
        await update.message.reply_text(text=text, reply_markup=reply_markup)
        return START_ROUTES
    
    # 管理员查看绑定用户列表
    if is_admin and not context.args and not update.message.reply_to_message:
        bound_users = V2User.select().where(V2User.telegram_id.is_null(False))
        if not bound_users:
            text = '''📝 绑定用户列表
————————————
暂无用户绑定TG账号'''
        else:
            user_list = []
            for user in bound_users:
                # 隐藏邮箱前5位
                hidden_email = '*****' + user.email[5:] if len(user.email) > 5 else user.email
                user_list.append(f"📧 {hidden_email} | 🆔 {user.telegram_id}")
            text = '''📝 绑定用户列表
————————————
{}

📌 管理员解绑方式：
1. 回复用户消息 + /unbind
2. /unbind 用户邮箱（完整邮箱）
'''.format('\n'.join(user_list))
        await update.message.reply_text(text=text, reply_markup=reply_markup)
        return START_ROUTES
    
    # 普通用户解绑自己的账号
    text = _unbind(telegram_id)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return START_ROUTES

# 抽奖
async def command_lucky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = _lucky(telegram_id)
    keyboard = [
        return_keyboard,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return START_ROUTES

# 查看钱包
async def command_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = _wallet(telegram_id)
    keyboard = [
        return_keyboard,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return START_ROUTES

# 流量查询
async def command_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = _traffic(telegram_id)
    keyboard = [
        return_keyboard,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return START_ROUTES

# 获取用户ID
async def command_getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        return_keyboard,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 如果是回复消息
    if update.message.reply_to_message:
        # 获取被回复消息的用户信息
        replied_user = update.message.reply_to_message.from_user
        replied_user_id = replied_user.id
        replied_username = replied_user.username or '未设置用户名'
        replied_first_name = replied_user.first_name or '未设置名字'
        
        text = f'''👤 被回复用户信息
————————————
🆔 用户ID：{replied_user_id}
📝 用户名：@{replied_username}
👤 名字：{replied_first_name}'''
    else:
        text = '''❌ 请回复一个用户的消息来获取其ID'''
    
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return START_ROUTES

async def command_modify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    管理员回复用户消息修改流量或时长
    格式：/modify [流量|时长] [数值]
    例如：
    /modify 流量 10 (增加10GB流量)
    /modify 流量 -10 (减少10GB流量)
    /modify 时长 30 (增加30天)
    /modify 时长 -30 (减少30天)
    """
    # 检查是否是管理员
    if update.effective_user.id != config.TELEGRAM.admin_telegram_id:
        await update.message.reply_text('❌ 该命令仅限管理员使用')
        return START_ROUTES

    # 检查是否回复了消息
    if not update.message.reply_to_message:
        text = '''❌ 请回复要修改的用户消息
————————————
使用方法：
回复用户消息并发送以下命令：
/modify 流量 10 (增加10GB流量)
/modify 流量 -10 (减少10GB流量)
/modify 时长 30 (增加30天)
/modify 时长 -30 (减少30天)'''
        await update.message.reply_text(text)
        return START_ROUTES

    # 获取被回复用户的telegram_id
    target_user_id = update.message.reply_to_message.from_user.id
    
    # 检查参数
    if len(context.args) != 2:
        text = '''❌ 参数错误
————————————
使用方法：
/modify 流量 10 (增加10GB流量)
/modify 流量 -10 (减少10GB流量)
/modify 时长 30 (增加30天)
/modify 时长 -30 (减少30天)'''
        await update.message.reply_text(text)
        return START_ROUTES

    modify_type = context.args[0]
    try:
        value = float(context.args[1])
    except ValueError:
        await update.message.reply_text('❌ 数值格式错误，请输入数字')
        return START_ROUTES

    # 查找用户
    v2_user = V2User.select().where(V2User.telegram_id == target_user_id).first()
    if not v2_user:
        await update.message.reply_text('❌ 该用户未绑定账号')
        return START_ROUTES

    try:
        if modify_type == '流量':
            # 转换GB到字节
            bytes_value = int(value * 1024 * 1024 * 1024)
            v2_user.transfer_enable += bytes_value
            if v2_user.transfer_enable < 0:
                v2_user.transfer_enable = 0
            v2_user.save()
            
            # 计算当前总流量和已用流量
            total_gb = round(v2_user.transfer_enable / 1024 / 1024 / 1024, 2)
            used_gb = round((v2_user.u + v2_user.d) / 1024 / 1024 / 1024, 2)
            remaining_gb = round(total_gb - used_gb, 2)
            
            # 隐藏邮箱前5位
            hidden_email = '*****' + v2_user.email[5:] if len(v2_user.email) > 5 else v2_user.email
            
            text = f'''✅ 流量修改成功
————————————
👤 用户：{hidden_email}
{'➕ 增加' if value > 0 else '➖ 减少'}：{abs(value)}GB

📊 流量详情
├─ 总流量：{total_gb}GB
├─ 已使用：{used_gb}GB
└─ 剩余：{remaining_gb}GB

⚠️ 管理员操作提示：该操作由管理员执行'''
            
        elif modify_type == '时长':
            # 检查是否是不限时用户
            if v2_user.expired_at is None:
                await update.message.reply_text('❌ 该用户为不限时套餐，无法修改时长')
                return START_ROUTES
                
            if v2_user.expired_at == 0:
                await update.message.reply_text('❌ 该用户为无限期账户，无法修改时长')
                return START_ROUTES
                
            # 转换天数到秒数
            seconds = int(value * 24 * 60 * 60)
            v2_user.expired_at += seconds
            v2_user.save()
            
            # 格式化到期时间
            expired_time = datetime.fromtimestamp(v2_user.expired_at)
            expired_str = expired_time.strftime('%Y-%m-%d %H:%M:%S')
            # 隐藏邮箱前5位
            hidden_email = '*****' + v2_user.email[5:] if len(v2_user.email) > 5 else v2_user.email
            
            text = f'''✅ 时长修改成功
————————————
👤 用户：{hidden_email}
{'➕ 增加' if value > 0 else '➖ 减少'}：{abs(value)}天
📅 到期时间：{expired_str}'''
            
        else:
            text = '''❌ 参数错误
————————————
修改类型只能是"流量"或"时长"'''
            
        await update.message.reply_text(text)
        return START_ROUTES
        
    except Exception as e:
        await update.message.reply_text(f'❌ 操作失败\n————————————\n错误信息：{str(e)}')
        return START_ROUTES
