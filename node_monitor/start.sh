#!/bin/bash

# 进入父目录
cd "$(dirname "$0")/.."

# 检查必要的文件是否存在
if [ ! -f "Config.py" ]; then
    echo "错误：找不到Config.py文件"
    exit 1
fi

if [ ! -f "config.yaml" ]; then
    echo "错误：找不到config.yaml文件"
    exit 1
fi

# 进入node_monitor目录
cd node_monitor

# 确保日志目录存在
mkdir -p logs

# 启动监控程序
nohup /root/xboardbot/python-3.9.7/bin/python3.9 monitor.py > logs/monitor.out 2>&1 &

# 保存进程ID
echo $! > monitor.pid

echo "节点监控服务已启动，进程ID: $(cat monitor.pid)"
echo "日志文件位置: $(pwd)/logs/monitor.out" 
