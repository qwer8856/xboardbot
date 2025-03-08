# XBoard 节点监控程序

这是一个用于监控 XBoard 面板节点状态的程序，可以自动检测节点是否掉线，并通过 Telegram 发送通知给管理员和群组。

## 功能特点

- 每600秒自动检查一次所有节点状态
- 发现掉线节点立即通过 Telegram 发送通知给管理员和群组
- 支持多节点同时监控
- 自动记录运行日志
- 支持后台持续运行

## 系统要求

- Python 3.9+
- Linux 系统（推荐 Ubuntu/Debian）

## 安装步骤

1. 安装必要的 Python 包：
```bash
/root/xboardbot/python-3.9.7/bin/pip3.9 install python-telegram-bot requests pytz
```

2. 确保配置文件正确：
   - 检查 `Config.py` 中的配置是否正确
   - 确保 `config.yaml` 文件存在并配置正确
   - 确保 Telegram Bot Token 和管理员 ID 配置正确
   - 在 `config.yaml` 中配置群组 ID（可选）：
     ```yaml
     TELEGRAM:
       token: "YOUR_BOT_TOKEN"
       admin_telegram_id: "YOUR_ADMIN_ID"
       group_chat_id: "YOUR_GROUP_ID"  # 添加群组ID配置
     ```

## 获取群组ID的方法

1. 将机器人添加到目标群组
2. 在群组中发送一条消息
3. 访问以下URL（替换为您的bot token）：
   ```
   https://api.telegram.org/bot<YourBOTToken>/getUpdates
   ```
4. 在返回的JSON中找到 `chat` 对象中的 `id` 字段
5. 将获取到的群组ID填入 `config.yaml` 中的 `group_chat_id` 字段

## 使用方法

### 使用 Screen 运行（推荐）

1. 安装 screen（如果未安装）：
```bash
apt-get install screen
```

2. 启动监控程序：
```bash
cd /root/xboardbot/node_monitor
screen -S xboard_monitor
python3.9 monitor.py
```

3. 分离 screen 会话（让程序在后台运行）：
   - 按 `Ctrl + A` 然后按 `D`

### 使用 Nohup 运行（备选方案）

```bash
cd /root/xboardbot/node_monitor
nohup python3.9 monitor.py > monitor.out 2>&1 &
```

## 常用命令

### Screen 相关命令

- 查看所有 screen 会话：
```bash
screen -ls
```

- 重新连接到监控会话：
```bash
screen -r xboard_monitor
```

- 停止程序：
  1. 重新连接到会话：`screen -r xboard_monitor`
  2. 按 `Ctrl + C` 停止程序
  3. 输入 `exit` 退出 screen 会话

- 强制关闭会话：
```bash
screen -X -S xboard_monitor quit
```

### 进程管理命令

- 查看运行中的监控程序：
```bash
ps aux | grep "monitor.py" | grep -v grep
```

- 停止所有监控程序：
```bash
pkill -f "monitor.py"
```

## 日志查看

- 查看程序运行日志：
```bash
tail -f /root/xboardbot/node_monitor/logs/node_monitor.log
```

- 查看程序输出（如果使用 nohup）：
```bash
tail -f /root/xboardbot/node_monitor/monitor.out
```

## 故障排除

1. 如果程序无法启动，检查：
   - Python 包是否安装完整
   - 配置文件是否正确
   - 日志文件权限是否正确

2. 如果没有收到通知，检查：
   - Telegram Bot Token 是否正确
   - 管理员 ID 是否正确
   - 群组 ID 是否正确（如果配置了群组通知）
   - 网络连接是否正常

3. 如果程序异常退出，检查：
   - 日志文件中的错误信息
   - 系统资源使用情况
   - 网络连接状态

## 注意事项

1. 确保服务器时间正确，建议使用 NTP 同步时间
2. 定期检查日志文件大小，必要时进行清理
3. 建议使用 screen 运行程序，方便管理和监控
4. 如果使用 nohup，注意检查 monitor.out 文件大小
5. 确保机器人有权限在群组中发送消息

## 更新日志

### v1.0.1
- 添加群组通知功能
- 优化通知发送逻辑

### v1.0.0
- 初始版本发布
- 支持基本的节点监控功能
- 支持 Telegram 通知
- 支持后台运行 
