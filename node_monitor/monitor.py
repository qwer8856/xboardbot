import requests
import json
import time
import logging
from datetime import datetime
import pytz
import os
import sys

# 添加父目录到Python路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# 设置工作目录为父目录
os.chdir(parent_dir)

from Config import config
import asyncio
from telegram import Bot

# 确保日志目录存在
log_dir = os.path.join(parent_dir, 'node_monitor', 'logs')
os.makedirs(log_dir, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'node_monitor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化Telegram机器人
bot = Bot(token=config.TELEGRAM.token)

async def send_telegram_message(message):
    """发送Telegram消息给管理员和群组"""
    try:
        # 发送给管理员
        await bot.send_message(
            chat_id=config.TELEGRAM.admin_telegram_id,
            text=message,
            parse_mode='HTML'
        )
        logger.info("已发送通知给管理员")
        
        # 发送给群组
        if hasattr(config.TELEGRAM, 'group_chat_id') and config.TELEGRAM.group_chat_id:
            await bot.send_message(
                chat_id=config.TELEGRAM.group_chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info("已发送通知给群组")
            
    except Exception as e:
        logger.error(f"发送Telegram消息失败: {str(e)}")

def _admin_auth():
    """获取管理员token"""
    try:
        URL = config.WEBSITE.url
        api = URL + '/api/v1/passport/auth/login'
        data = {
            'email': config.WEBSITE.email,
            'password': config.WEBSITE.password,
        }
        res = requests.post(api, data=data)
        
        try:
            json_data = res.json()
            if 'data' not in json_data or 'auth_data' not in json_data['data']:
                raise ValueError('返回数据缺少 auth_data')
            return json_data['data']['auth_data']
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"管理员登录失败: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"管理员登录失败: {str(e)}")
        return None

def check_nodes():
    """检查节点状态"""
    try:
        URL = config.WEBSITE.url
        SUFFIX = config.WEBSITE.suffix

        # 获取管理员token
        admin_token = _admin_auth()
        if not admin_token:
            return None
            
        # 使用正确的API路径
        api_path = f'/api/v2/{SUFFIX}/server/manage/getNodes'
        
        headers = {
            'Authorization': admin_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        api = URL.rstrip('/') + api_path
        res = requests.get(api, headers=headers)
        
        if res.status_code == 200:
            try:
                data = res.json()
                if data and isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                    offline_nodes = []
                    
                    # 检查每个节点状态
                    for item in data['data']:
                        if not isinstance(item, dict) or item.get('show', 1) == 0:
                            continue
                            
                        node_name = item.get('name', '未命名节点')
                        status = item.get('available_status', False)
                        
                        if not status:
                            offline_nodes.append(node_name)
                    
                    return offline_nodes
            except json.JSONDecodeError:
                logger.error("解析节点数据失败")
                return None
        else:
            logger.error(f"获取节点信息失败，HTTP状态码：{res.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"检查节点状态出错: {str(e)}")
        return None

async def monitor_nodes():
    """监控节点状态并发送通知"""
    while True:
        try:
            # 获取当前时间
            now = datetime.now(pytz.timezone('Asia/Shanghai'))
            current_time = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # 检查节点状态
            offline_nodes = check_nodes()
            
            if offline_nodes is not None and offline_nodes:
                # 构建通知消息
                message = f'''⚠️ <b>节点掉线通知</b>
————————————
<b>检测时间</b>: {current_time}
<b>掉线节点</b>:
{chr(10).join(f"• {node}" for node in offline_nodes)}
————————————'''
                
                # 发送通知
                await send_telegram_message(message)
                logger.info(f"发送掉线节点通知: {', '.join(offline_nodes)}")
            
            # 每30秒检查一次
            await asyncio.sleep(600)
            
        except Exception as e:
            logger.error(f"监控过程出错: {str(e)}")
            await asyncio.sleep(60)  # 出错后等待1分钟再继续

def main():
    """主函数"""
    logger.info("节点监控服务启动")
    
    # 创建事件循环
    loop = asyncio.get_event_loop()
    
    try:
        # 运行监控任务
        loop.run_until_complete(monitor_nodes())
    except KeyboardInterrupt:
        logger.info("节点监控服务停止")
    finally:
        loop.close()

if __name__ == '__main__':
    main() 