#!/bin/bash

# 进入脚本所在目录
cd "$(dirname "$0")"

# 检查PID文件是否存在
if [ -f monitor.pid ]; then
    # 读取进程ID
    pid=$(cat monitor.pid)
    
    # 检查进程是否存在
    if ps -p $pid > /dev/null; then
        # 终止进程
        kill $pid
        echo "节点监控服务已停止，进程ID: $pid"
    else
        echo "进程 $pid 不存在"
    fi
    
    # 删除PID文件
    rm monitor.pid
else
    echo "未找到PID文件，服务可能未运行"
fi 