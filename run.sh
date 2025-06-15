#!/bin/bash
# 保存当前工作目录
current_dir=$(pwd)
# 切换到脚本所在目录
cd "$(dirname "$0")"
# 设置环境变量
export ALL_PROXY=''
export all_proxy=''
# 执行 Python 脚本
python main.py
# 切换回原工作目录
cd "$current_dir"