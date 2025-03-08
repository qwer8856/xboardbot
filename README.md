# V2Board Telegram Bot

一个功能丰富的 Telegram 机器人，专为 V2Board 面板用户设计，提供用户账户管理、订阅信息查询、流量统计等功能。通过美观直观的界面，为用户提供极佳的使用体验。

## ✨ 功能特点

### 🔑 用户管理
- 账户绑定/解绑
- 流量查询（美观的进度条展示）
- 钱包余额查询
- 订阅信息查看
- 订阅链接获取

### 🎁 用户福利
- 每日签到获取流量
- 幸运抽奖获取随机流量

### 📊 数据展示
- 节点状态实时查询
- 美观的流量统计图表
- 详细的订阅信息展示

### 👑 管理功能
- 管理员专属设置面板
- 一键调整系统参数
- 套餐有效期批量管理
- 签到/抽奖参数配置

## 🛠️ 安装步骤

### 前提条件
- Python 3.9+
- V2Board 面板
- Telegram Bot Token

### 安装过程
1. 克隆仓库
```bash
git clone https://github.com/qwer8856/xboardbot.git
cd v2boardbot
```

2. 一键安装
```bash
cd xboardbot
sh install.sh
```

4. 启动机器人
```bash
/root/xboardbot/python-3.9.7/bin/python3.9 Bot.py  #后台运行
nohup /root/v2boardbot/python-3.9.7/bin/python3.9 Bot.py &  #静默运行
```

## 🖼️ 界面展示

### 💰 钱包信息
```
💰 我的钱包
━━━━━━━━━━━━━━━━
💲 钱包总额: 100.00 元
💵 账户余额: 80.00 元
💹 推广佣金: 20.00 元
━━━━━━━━━━━━━━━━
💡 温馨提示: 推广佣金可以用于购买套餐
```

### 🚥 流量统计
```
🚥 流量使用统计
━━━━━━━━━━━━━━━━
📊 总流量: 100.00 GB
📈 使用情况: ████░░░░░░ 40.5%

📤 上传: 15.00 GB
📥 下载: 25.50 GB
📉 已用: 40.50 GB
📌 剩余: 59.50 GB
━━━━━━━━━━━━━━━━
💡 及时关注您的流量使用情况
```

### 📡 节点状态
```
📡 节点状态概览
━━━━━━━━━━━━━━━━
✅ 总节点数: 15 个
🟢 在线节点: 12 个
🔴 离线节点: 3 个
━━━━━━━━━━━━━━━━
🏣 香港节点 01
┣ 状态: 🟢 在线
┗ 在线: 125 人
...
```

## 🔧 配置选项

### 管理员设置
- `🏷️标题设置`: 设置机器人显示的标题
- `🗑️减少时长`: 批量调整所有用户的订阅时长
- `📅签到设置`: 配置每日签到可获得的流量范围 (格式: 最小值|最大值)
- `✨抽奖设置`: 配置抽奖可获得的流量范围 (格式: 最小值|最大值)

