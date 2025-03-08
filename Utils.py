import requests
import datetime
from Config import config
import pytz
import json

START_ROUTES, END_ROUTES = 0, 1

WAITING_INPUT = 2


def _admin_auth():  # 返回网站管理员auth_data
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
            return f'❌ 管理员登录失败\n————————————\n错误信息：{str(e)}'
            
    except Exception as e:
        return f'❌ 管理员登录失败\n————————————\n错误信息：{str(e)}'


def getNodes(user_id=None):
    try:
        URL = config.WEBSITE.url
        SUFFIX = config.WEBSITE.suffix

        # 获取管理员token
        admin_token = _admin_auth()
        if isinstance(admin_token, str) and admin_token.startswith('❌'):
            return admin_token
            
        # 使用正确的API路径
        api_path = f'/api/v2/{SUFFIX}/server/manage/getNodes'
        
        headers = {
            'Authorization': admin_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            api = URL.rstrip('/') + api_path
            res = requests.get(api, headers=headers)
            
            if res.status_code == 200:
                try:
                    data = res.json()
                    if data and isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                        # 统计在线和离线节点数量
                        online_nodes = 0
                        offline_nodes = 0
                        total_nodes = 0
                        
                        # 获取用户套餐信息
                        user_plan = None
                        if user_id:
                            try:
                                user_api = URL.rstrip('/') + f'/api/v2/{SUFFIX}/user/info'
                                user_res = requests.get(user_api, headers=headers)
                                if user_res.status_code == 200:
                                    user_data = user_res.json()
                                    if user_data and isinstance(user_data, dict) and 'data' in user_data:
                                        user_plan = user_data['data'].get('plan_id')
                            except:
                                pass
                        
                        # 先统计节点状态
                        for item in data['data']:
                            if not isinstance(item, dict) or item.get('show', 1) == 0:
                                continue
                                
                            # 检查节点是否属于用户套餐
                            if user_plan and item.get('plan_id') != user_plan:
                                continue
                                
                            total_nodes += 1
                            if item.get('available_status', False):
                                online_nodes += 1
                            else:
                                offline_nodes += 1
                        
                        # 构建标题和统计信息
                        text = f'''📡 <b>节点状态</b>
————————————
<b>总节点数</b>: {total_nodes}
<b>在线节点</b>: {online_nodes}
<b>离线节点</b>: {offline_nodes}
————————————\n'''
                        
                        # 添加节点详细信息
                        for item in data['data']:
                            if not isinstance(item, dict):
                                continue
                                
                            if item.get('show', 1) == 0:  # 默认显示
                                continue
                                
                            # 检查节点是否属于用户套餐
                            if user_plan and item.get('plan_id') != user_plan:
                                continue
                                
                            node_name = item.get('name', '未命名节点')
                            # 转义HTML特殊字符
                            node_name = node_name.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
                            
                            # 获取节点状态
                            status = item.get('available_status', False)
                            status_text = '🟢 在线' if status else '🔴 离线'
                            online = str(item.get('online', 0)) + '人'
                            
                            # 美化节点信息显示
                            line = f'''<b>节点名称</b>: {node_name}
<b>运行状态</b>: {status_text}
<b>在线人数</b>: {online}
————————————\n'''
                            text += line
                            
                        if text == '📡 <b>节点状态</b>\n————————————\n':
                            return '❌ 没有可用的节点信息'
                            
                        return text.rstrip()
                except json.JSONDecodeError:
                    return '❌ 解析节点数据失败\n————————————\n原因：服务器返回的数据格式不正确'
            else:
                return f'❌ 获取节点信息失败\n————————————\nHTTP状态码：{res.status_code}'
                
        except requests.exceptions.RequestException as e:
            return f'❌ 连接服务器失败\n————————————\n错误信息：{str(e)}'
            
    except Exception as e:
        return f'❌ 获取节点状态出错\n————————————\n错误信息：{str(e)}'


def get_next_first():
    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))
    for m in range(1, 6):
        open_minute = now + datetime.timedelta(minutes=m)
        if open_minute.minute % 5 == 0:
            open_date = open_minute.replace(second=0, microsecond=0)
            return open_date