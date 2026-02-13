#!/bin/bash
#文件存放位置：/usr/local/bin 
#给执行权限 chmod +x gzh.sh

# ================= 配置区 =================
APP_NAME="main.py"               # 你的 Python 主程序名
LOG_FILE="bot.log"               # 日志文件名
PYTHON_CMD="python3 -u"          # Python 命令 (带 -u 保证实时输出)
WORK_DIR="/mnt/sda/wechat"       # 你的工作目录
# =========================================

# 颜色定义
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[36m'
PLAIN='\033[0m'

# 进入指定的工作目录
if [ ! -d "$WORK_DIR" ]; then
    echo -e "${RED}>>> 错误：找不到目录 $WORK_DIR${PLAIN}"
    exit 1
fi
cd "$WORK_DIR"

# 检查 PID
check_pid() {
    PID=$(ps -ef | grep "$APP_NAME" | grep -v grep | awk '{print $2}')
}

# 启动逻辑
start_bot() {
    check_pid
    if [ -n "$PID" ]; then
        echo -e "${YELLOW}>>> 程序正在运行中 (PID: $PID)，无需重复启动。${PLAIN}"
    else
        echo -e "${GREEN}>>> 正在启动机器人...${PLAIN}"
        # 再次确保在工作目录下运行
        cd "$WORK_DIR"
        nohup $PYTHON_CMD $APP_NAME > $LOG_FILE 2>&1 &
        sleep 2
        check_pid
        if [ -n "$PID" ]; then
            echo -e "${GREEN}>>> 启动成功！[PID: $PID]${PLAIN}"
            echo -e "${BLUE}>>> 日志正在写入 $LOG_FILE${PLAIN}"
        else
            echo -e "${RED}>>> 启动失败，请检查 Python 代码或环境。${PLAIN}"
        fi
    fi
}

# 停止逻辑 (已加入清理僵尸进程功能)
stop_bot() {
    check_pid
    if [ -n "$PID" ]; then
        echo -e "${YELLOW}>>> 正在停止 Python 主进程 (PID: $PID) ...${PLAIN}"
        kill -9 $PID
        sleep 1
        echo -e "${RED}>>> Python 主进程已停止。${PLAIN}"
    else
        echo -e "${RED}>>> Python 主进程未运行。${PLAIN}"
    fi
    
    # 核心新增：无差别清理残留的 Chrome/Chromium 进程，拯救内存
    echo -e "${YELLOW}>>> 正在清理后台残留的 Chromium/Chrome 浏览器进程...${PLAIN}"
    pkill -9 -f chromium >/dev/null 2>&1
    pkill -9 -f chrome >/dev/null 2>&1
    pkill -9 -f chromedriver >/dev/null 2>&1
    echo -e "${GREEN}>>> 战场清理完毕！Armbian 内存已完全释放。${PLAIN}"
}

# 查看日志
view_log() {
    echo -e "${BLUE}========================================${PLAIN}"
    echo -e "${BLUE}   正在实时读取日志 (按 Ctrl+C 退出查看)${PLAIN}"
    echo -e "${BLUE}========================================${PLAIN}"
    if [ -f "$LOG_FILE" ]; then
        tail -f $LOG_FILE
    else
        echo -e "${RED}>>> 日志文件 $LOG_FILE 不存在。${PLAIN}"
    fi
}

# 主菜单循环
while true; do
    clear
    check_pid
    
    echo -e "========================================"
    echo -e "    微信自动回复机器人 - 控制面板"
    echo -e "========================================"
    echo -e "工作目录: $WORK_DIR"
    
    if [ -n "$PID" ]; then
        echo -e "当前状态: ${GREEN}正在运行 (PID: $PID)${PLAIN}"
    else
        echo -e "当前状态: ${RED}已停止${PLAIN}"
    fi
    
    echo -e "----------------------------------------"
    echo -e "${GREEN} 1.${PLAIN} 启动机器人"
    echo -e "${RED} 2.${PLAIN} 停止并清理内存"
    echo -e "${YELLOW} 3.${PLAIN} 重启机器人 (断网/更新代码后推荐)"
    echo -e "${BLUE} 4.${PLAIN} 查看实时日志"
    echo -e " 0. 退出菜单"
    echo -e "----------------------------------------"
    
    read -p "请输入数字 [0-4]: " num
    
    case "$num" in
        1)
            start_bot
            ;;
        2)
            stop_bot
            ;;
        3)
            stop_bot
            start_bot
            ;;
        4)
            view_log
            ;;
        0)
            echo "退出管理脚本。"
            exit 0
            ;;
        *)
            echo -e "${RED}请输入正确的数字 [0-4]${PLAIN}"
            ;;
    esac
    
    if [ "$num" != "4" ] && [ "$num" != "0" ]; then
        echo -e "\n按回车键返回主菜单..."
        read
    fi
done
