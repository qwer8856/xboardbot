import time
from datetime import datetime, timedelta
import logging

import requests
from peewee import *
import random
from Config import config
from Utils import getNodes
from models import V2User, BotUser, V2ServerVmess, V2Plan


def get_sky(cityName):
    url = 'https://ssch.api.moji.com/citymanage/json/h5/searchCity'
    data = {
        'keyWord': cityName
    }
    res = requests.post(url, data=data)
    try:
        cityId = res.json()['city_list'][0]['cityId']
    except:
        return 'cty_name error'
    url = 'https://h5ctywhr.api.moji.com/weatherDetail'
    data = {"cityId": cityId, "cityType": 0}
    res = requests.post(url, json=data)
    obj = res.json()
    temp = obj['condition']['temp']
    humidity = obj['condition']['humidity']
    weather = obj['condition']['weather']
    wind = obj['condition']['windDir'] + ' ' + str(obj['condition']['windLevel']) + '级'
    tips = obj['condition']['tips']
    city = f"{obj['provinceName']}-{obj['cityName']}"
    return f'''地区:{city}
温度:{temp} 湿度:{humidity}
天气:{weather} 风向:{wind}
提示:{tips}'''


def _addtime(day: int):
    v2_users = V2User.select().where(V2User.expired_at > 0).execute()
    second = day * 24 * 60 * 60
    for v2_user in v2_users:
        v2_user.expired_at += second
        v2_user.save()
    return f'{len(v2_users)}个有效用户添加成功{day}天时长成功'


def _wallet(telegram_id):
    v2_user = V2User.select().where(V2User.telegram_id == telegram_id).first()
    if not v2_user:
        return '未绑定,请先绑定'
        
    # 计算金额
    total = round((v2_user.balance + v2_user.commission_balance) / 100, 2)
    balance = round(v2_user.balance / 100, 2)
    commission = round(v2_user.commission_balance / 100, 2)
    
    text = f'''<b>💰 我的钱包</b>
━━━━━━━━━━━━━━━━
<b>💲 钱包总额</b>: <code>{total}</code> 元
<b>💵 账户余额</b>: <code>{balance}</code> 元
<b>💹 推广佣金</b>: <code>{commission}</code> 元
━━━━━━━━━━━━━━━━
<i>💡 温馨提示: 推广佣金可以用于购买套餐</i>
'''
    return text


def _bind(token, telegram_id):
    try:
        # 查询telegram_id是否绑定了其他账号
        botuser = BotUser.select().where(BotUser.telegram_id == telegram_id).first()
        if botuser and botuser.__data__.get('v2_user') != 0:
            return '❌ 该Telegram已经绑定了一个账号，请先解绑再绑定'
            
        v2_user = V2User.select().where(V2User.token == token).first()
        if not v2_user:
            return '❌ 用户不存在，请检查您的订阅链接是否正确'
            
        if v2_user.telegram_id:
            return '❌ 该账号已经绑定了Telegram账号，如需重新绑定请先解绑'
            
        if botuser:
            botuser.v2_user = v2_user
            v2_user.telegram_id = telegram_id
            v2_user.save()
            botuser.save()
        else:
            BotUser.create(telegram_id=telegram_id, v2_user=v2_user)
            v2_user.telegram_id = telegram_id
            v2_user.save()
            
        return f'''✅ 绑定成功！
————————————
📧 邮箱：{v2_user.email}
💰 余额：{round(v2_user.balance / 100, 2)} 元
🎁 佣金：{round(v2_user.commission_balance / 100, 2)} 元
'''
    except Exception as e:
        return f'❌ 绑定失败\n————————————\n错误信息：{str(e)}'


def _unbind(telegram_id):
    # 先查找用户是否存在于 V2User 表中
    v2_user = V2User.select().where(V2User.telegram_id == telegram_id).first()
    if not v2_user:
        return '❌ 该用户未绑定任何账号'
        
    # 获取用户信息用于返回
    email = v2_user.email
    # 隐藏邮箱前5位
    hidden_email = '*****' + email[5:] if len(email) > 5 else email
    
    # 查找并更新 BotUser 表
    bot_user = BotUser.select().where(BotUser.telegram_id == telegram_id).first()
    if bot_user:
        bot_user.v2_user = 0
        bot_user.save()
    
    # 更新 V2User 表
    v2_user.telegram_id = None
    v2_user.save()
    
    return f'''✅ 解绑成功！
————————————
📧 已解绑账号：{hidden_email}
ℹ️ 您可以使用 /bind 命令重新绑定其他账号'''


def _checkin(telegram_id):
    botuser = BotUser.select().where(BotUser.telegram_id == telegram_id).first()
    if not botuser:
        return '❌ 未绑定账号，请先绑定'

    # 为了适应新版本
    if botuser.__data__.get('v2_user') == 0:
        return '❌ 未绑定账号，请先绑定'

    # 检查是否有购买套餐
    if not botuser.v2_user.plan_id:
        return '❌ 您还没有购买套餐，无法参与签到活动'

    # 检查套餐是否过期
    if botuser.v2_user.expired_at is None:
        # 不限时套餐
        pass
    else:
        # 对于有时间限制的套餐，检查是否过期
        now_time = int(time.time())
        if botuser.v2_user.expired_at == 0 or now_time > botuser.v2_user.expired_at:
            return '❌ 您的套餐已过期，请续费后再参与签到'

    # 检查今天是否签到过了 - 使用日期比较
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if botuser.sign_time and botuser.sign_time >= today_start:
        # 计算下次可以签到的时间
        next_checkin = today_start + timedelta(days=1)
        next_checkin_str = next_checkin.strftime('%Y-%m-%d') + ' 00:00'
        return f'⚠️ 您今天已经签到过了\n下次签到时间：{next_checkin_str}'

    if config.TELEGRAM.checkin.find('未配置') != -1:
        return '❌ 管理员未配置签到信息或未开启签到'
    if config.TELEGRAM.checkin == '关闭':
        return '❌ 签到功能已关闭，请联系管理员'
    try:
        statr, end = config.TELEGRAM.checkin.split('|')
        statr, end = int(statr), int(end)
    except:
        return '❌ 管理员签到信息配置错误或未开启签到'

    num = random.randint(statr, end)
    flow = num * 1024 * 1024
    botuser.v2_user.transfer_enable += flow
    botuser.sign_time = datetime.now()
    botuser.v2_user.save()
    botuser.save()

    return f'''✅ 签到成功！
————————————
🎁 获得流量：{round(num / 1024, 2)} GB'''


def _sub(telegram_id):
    try:
        # 获取用户信息
        v2_user = V2User.select().where(V2User.telegram_id == telegram_id).first()
        if not v2_user:
            return '未绑定,请先绑定'
            
        # 处理到期时间
        if v2_user.expired_at == None:
            expired_at = '∞'
            expired_time = '不限时套餐'
        elif v2_user.expired_at == 0:
            expired_at = '-∞'
            expired_time = '未订阅'
        else:
            now_time = datetime.now()
            expired_at = (datetime.fromtimestamp(v2_user.expired_at) - now_time).days
            expired_time = datetime.fromtimestamp(v2_user.expired_at).strftime('%Y-%m-%d')
            
        if expired_time == '未订阅':
            return '❌ 未订阅任何套餐，请先订阅'
            
        try:
            # 获取用户当前的套餐信息
            plan = V2Plan.get_by_id(v2_user.plan_id)
            
            # 使用用户实际的流量限制而不是套餐的流量限制
            user_traffic = round(v2_user.transfer_enable / (1024 * 1024 * 1024), 2)
            
            # 计算进度条 - 时间进度条
            if expired_at != '∞':
                # 假设套餐有30天有效期
                plan_days = 30
                days_used = plan_days - expired_at
                days_percent = min(100, max(0, (days_used / plan_days) * 100))
                days_progress_length = 10
                days_filled_length = int(days_progress_length * days_percent / 100)
                days_progress_bar = '█' * days_filled_length + '░' * (days_progress_length - days_filled_length)
                days_bar = f"<code>{days_progress_bar}</code> {round(days_percent, 1)}%"
            else:
                days_bar = "<code>♾️ 永久</code>"
            
            text = f'''<b>📊 我的订阅信息</b>
━━━━━━━━━━━━━━━━
<b>📦 套餐名称</b>: <code>{plan.name}</code>
<b>💫 套餐流量</b>: <code>{user_traffic}</code> GB
<b>⏳ 剩余天数</b>: <code>{expired_at}</code> 天
<b>📅 到期时间</b>: <code>{expired_time}</code>
<b>⌛ 时间进度</b>: {days_bar}
━━━━━━━━━━━━━━━━
<i>💡 请及时续费以确保服务不中断</i>
'''
        except V2Plan.DoesNotExist:
            print(f"找不到套餐ID: {v2_user.plan_id}")
            # 使用用户自身的流量信息
            user_traffic = round(v2_user.transfer_enable / (1024 * 1024 * 1024), 2)
            text = f'''<b>📊 我的订阅信息</b>
━━━━━━━━━━━━━━━━
<b>📦 套餐名称</b>: <code>未知套餐</code>
<b>💫 套餐流量</b>: <code>{user_traffic}</code> GB
<b>⏳ 剩余天数</b>: <code>{expired_at}</code> 天
<b>📅 到期时间</b>: <code>{expired_time}</code>
━━━━━━━━━━━━━━━━
<i>💡 请及时续费以确保服务不中断</i>
'''
        except Exception as e:
            print(f"获取套餐信息时出错: {str(e)}")
            print(f"错误类型: {type(e)}")
            # 使用用户自身的流量信息
            user_traffic = round(v2_user.transfer_enable / (1024 * 1024 * 1024), 2)
            text = f'''<b>📊 我的订阅信息</b>
━━━━━━━━━━━━━━━━
<b>📦 套餐名称</b>: <code>获取失败</code>
<b>💫 套餐流量</b>: <code>{user_traffic}</code> GB
<b>⏳ 剩余天数</b>: <code>{expired_at}</code> 天
<b>📅 到期时间</b>: <code>{expired_time}</code>
━━━━━━━━━━━━━━━━
<i>💡 请及时续费以确保服务不中断</i>
'''
        return text
            
    except Exception as e:
        print(f"获取订阅信息时出错: {str(e)}")
        print(f"错误类型: {type(e)}")
        return f'❌ 获取订阅信息失败: {str(e)}'


def _mysub(telegram_id):
    v2_user = V2User.select().where(V2User.telegram_id == telegram_id).first()
    if not v2_user:
        return '未绑定,请先绑定'
    
    # 获取面板地址并确保没有尾部斜杠
    suburl = config.WEBSITE.suburl if hasattr(config.WEBSITE, 'suburl') else config.WEBSITE.url
    suburl = suburl.rstrip('/')
    
    # 使用新版xboard格式
    sub_link = f'{suburl}/s/{v2_user.token}'
    
    # 获取已用流量和总流量，计算流量使用进度
    total_traffic = v2_user.transfer_enable / 1024 ** 3  # 总流量 GB
    used_traffic = (v2_user.u + v2_user.d) / 1024 ** 3  # 已用流量 GB
    traffic_percent = min(100, max(0, (used_traffic / total_traffic) * 100 if total_traffic > 0 else 0))
    
    # 计算流量进度条
    progress_length = 10
    filled_length = int(progress_length * traffic_percent / 100)
    traffic_bar = '█' * filled_length + '░' * (progress_length - filled_length)
    
    # 获取当前日期和到期日期，计算剩余天数
    now = datetime.now()
    if v2_user.expired_at is None:
        expired_days = "永久"
        expired_date = "永不过期"
    elif v2_user.expired_at == 0:
        expired_days = "已过期"
        expired_date = "已过期"
    else:
        expired_date = datetime.fromtimestamp(v2_user.expired_at).strftime('%Y-%m-%d')
        remaining_days = (datetime.fromtimestamp(v2_user.expired_at) - now).days
        expired_days = f"{remaining_days}天"
    
    # 构建美观的QR码图片链接
    qr_link = f'{suburl}/api/v1/client/subscribe?token={v2_user.token}&flag=shadowrocket'
    
    # 构建点击复制的订阅链接文本
    text = f'''<b>🔗 我的订阅链接</b>
━━━━━━━━━━━━━━━━
<b>📱 通用订阅</b>: <code>{sub_link}</code>

<b>📊 流量使用情况</b>
<b>📈 使用进度</b>: <code>{traffic_bar}</code> {round(traffic_percent, 1)}%
<b>📉 已用流量</b>: <code>{round(used_traffic, 2)}</code> GB
<b>📊 总流量</b>: <code>{round(total_traffic, 2)}</code> GB

<b>⏱️ 有效期信息</b>
<b>⏳ 剩余时间</b>: <code>{expired_days}</code>
<b>📅 到期日期</b>: <code>{expired_date}</code>
━━━━━━━━━━━━━━━━
<i>💡 小贴士: 长按以上链接可复制使用</i>
'''
    return text


def _lucky(telegram_id):
    """用户抽奖功能
    
    Args:
        telegram_id: 用户的 Telegram ID
        
    Returns:
        抽奖结果文本
    """
    try:
        # 先检查该用户是否存在
        botuser = BotUser.select().where(BotUser.telegram_id == telegram_id).first()
        
        # 用户不存在
        if not botuser:
            logging.warning(f"用户 {telegram_id} 未找到")
            return '❌ 未绑定账号，请先绑定'
            
        # 为了适应新版本
        if botuser.__data__.get('v2_user') == 0:
            logging.warning(f"用户 {telegram_id} 未关联v2用户")
            return '❌ 未绑定账号，请先绑定'

        # 检查是否有购买套餐
        if not botuser.v2_user.plan_id:
            logging.warning(f"用户 {telegram_id} 未购买套餐")
            return '❌ 您还没有购买套餐，无法参与抽奖活动'

        # 检查套餐是否过期
        if botuser.v2_user.expired_at is None:
            # 不限时套餐，限制抽奖流量在5MB-10MB之间
            min_mb, max_mb = 5, 10
        else:
            # 对于有时间限制的套餐，检查是否过期
            now_time = int(time.time())
            if botuser.v2_user.expired_at < now_time:
                logging.warning(f"用户 {telegram_id} 套餐已过期")
                return '❌ 您的套餐已过期，无法参与抽奖活动'
                
            # 获取抽奖配置
            if config.TELEGRAM.lucky.find('未配置') != -1:
                return '❌ 管理员未配置抽奖信息或未开启抽奖'
            if config.TELEGRAM.lucky == '关闭':
                return '❌ 抽奖功能已关闭，请联系管理员'
                
            try:
                min_mb, max_mb = config.TELEGRAM.lucky.split('|')
                min_mb, max_mb = int(min_mb), int(max_mb)
            except:
                return '❌ 管理员抽奖信息配置错误或未开启抽奖'
                
        # 检查是否可以抽奖（4小时间隔）
        now = datetime.now()
        if botuser.lucky_time:
            time_diff = now - botuser.lucky_time
            if time_diff.total_seconds() < 4 * 3600:  # 4小时 = 4 * 3600秒
                next_lucky_time = botuser.lucky_time + timedelta(hours=4)
                next_lucky_str = next_lucky_time.strftime('%Y-%m-%d %H:%M')
                return f'⏰ 抽奖冷却中\n下次抽奖时间：{next_lucky_str}'
        
        # 进行抽奖计算（单位：MB）
        traffic_mb = random.randint(min_mb, max_mb)
        # 转换为字节
        traffic_bytes = traffic_mb * 1024 * 1024
        
        # 更新用户流量
        v2_user = botuser.v2_user
        v2_user.transfer_enable += traffic_bytes
        v2_user.save()
        
        # 更新抽奖时间
        botuser.lucky_time = now
        botuser.save()
        
        # 返回抽奖结果
        traffic_gb = round(traffic_mb / 1024, 2)  # 转换为GB显示
        total_gb = round(v2_user.transfer_enable / (1024 * 1024 * 1024), 2)  # 总流量（GB）
        next_lucky_time = now + timedelta(hours=4)
        next_lucky_str = next_lucky_time.strftime('%Y-%m-%d %H:%M')
        
        result = f'''🎉 恭喜您抽到了 {traffic_gb} GB 流量！
————————————
📊 当前总流量：{total_gb} GB
⏰ 下次抽奖时间：{next_lucky_str}'''
        logging.info(f"用户 {telegram_id} 抽奖获得 {traffic_gb} GB 流量")
        return result
        
    except Exception as e:
        error_msg = f"抽奖出错: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return f"❌ 抽奖失败: {str(e)}"


def _traffic(telegram_id):
    v2_user = V2User.select().where(V2User.telegram_id == telegram_id).first()
    if not v2_user:
        return '未绑定,请先绑定'
    if v2_user.expired_at == 0:
        return '未订阅任何套餐，请先订阅'
        
    # 计算流量数据
    traffic = v2_user.transfer_enable / 1024 ** 3  # 总量
    upload = v2_user.u / 1024 ** 3  # 已用上行
    download = v2_user.d / 1024 ** 3  # 已用下行
    residual = traffic - upload - download  # 剩余流量
    used = upload + download  # 已用总流量
    
    # 计算使用百分比
    usage_percent = (used / traffic) * 100 if traffic > 0 else 0
    usage_percent = min(100, max(0, usage_percent))  # 确保在0-100之间
    
    # 生成进度条
    progress_length = 10
    filled_length = int(progress_length * usage_percent / 100)
    progress_bar = '█' * filled_length + '░' * (progress_length - filled_length)
    
    # 格式化数字，保留两位小数
    traffic_formatted = f"{round(traffic, 2):.2f}"
    upload_formatted = f"{round(upload, 2):.2f}"
    download_formatted = f"{round(download, 2):.2f}"
    residual_formatted = f"{round(residual, 2):.2f}"
    used_formatted = f"{round(used, 2):.2f}"
    
    text = f'''<b>🚥 流量使用统计</b>
━━━━━━━━━━━━━━━━
<b>📊 总流量</b>: <code>{traffic_formatted}</code> GB
<b>📈 使用情况</b>: <code>{progress_bar}</code> {round(usage_percent, 1)}%

<b>📤 上传</b>: <code>{upload_formatted}</code> GB
<b>📥 下载</b>: <code>{download_formatted}</code> GB
<b>📉 已用</b>: <code>{used_formatted}</code> GB
<b>📌 剩余</b>: <code>{residual_formatted}</code> GB
━━━━━━━━━━━━━━━━
<i>💡 及时关注您的流量使用情况</i>
'''
    return text


def _node(telegram_id):
    v2_user = V2User.select().where(V2User.telegram_id == telegram_id).first()
    if not v2_user:
        return '未绑定,请先绑定'
    return getNodes(telegram_id)

def is_bind(telegram_id):
    v2_user = V2User.select().where(V2User.telegram_id == telegram_id).first()
    if v2_user:
        return True
    else:
        return False

# b9bc3bee61de39f04047dbf8dca12e97
if __name__ == '__main__':
    print(_bind('896776c848efb99a1b8b324225c33277', '1111', sub_domain='172.16.1.14'))
    # print(_bind('3a23da6ebb70a66e2c00b8250df03c62', '1111', sub_domain='172.16.1.14'))
    # print(_bind('bc1d3d0d99bb8348f803665821d145f1', '1111', sub_domain='172.16.1.14'))
