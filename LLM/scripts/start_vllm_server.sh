#!/bin/bash
# EDA教学大模型 vLLM推理服务启动脚本 AutoDL专用（适配公网端口映射）
# 环境路径配置
# CONDA_ENV="/root/autodl-tmp/teacheda"
# MODEL_PATH="/root/autodl-tmp/Qwen2-7B-Instruct-AWQ"
CONDA_ENV="(待填写)环境名"
MODEL_PATH="(待填写)模型下载路径"
HOST="0.0.0.0"  # 保持监听所有网卡
PORT=6006       # AutoDL支持的公网端口
GPU_UTIL=0.9
MAX_LEN=8192
API_KEY="eda-dev-key-2026" # 前后端对接用，测试使用的是eda-dev-key-2026，可更换

# 1. 激活虚拟环境
source /root/miniconda3/etc/profile.d/conda.sh
conda activate ${CONDA_ENV}

# 2. 检查模型文件是否存在
if [ ! -d ${MODEL_PATH} ]; then
    echo "错误：模型路径不存在 ${MODEL_PATH}，请先完成模型下载"
    exit 1
fi

# 3. tmux后台启动，vllm-eda是自定义会话名
SESSION_NAME="vllm-eda"
# 销毁已有同名会话
tmux kill-session -t ${SESSION_NAME} 2>/dev/null
# 创建新会话并启动vLLM服务
tmux new-session -d -s ${SESSION_NAME} \
python -m vllm.entrypoints.openai.api_server \
--model ${MODEL_PATH} \
--host ${HOST} \
--port ${PORT} \
--quantization awq \
--gpu-memory-utilization ${GPU_UTIL} \
--max-model-len ${MAX_LEN} \
--trust-remote-code \
--api-key ${API_KEY} \
--served-model-name qwen2.5-7b-eda

echo "====================================="
echo "vLLM推理服务已在tmux后台启动"
echo "容器内本地地址：http://localhost:${PORT}/v1"
# echo "公网访问地址：https://u929078-9659-ea0648dd.bjb1.seetacloud.com:8443/v1"
echo "(待填写)公网访问地址，控制台->自定义服务->查看所租用服务器的公网IP"
echo "API KEY：${API_KEY}"
echo "查看实时日志：tmux a -t ${SESSION_NAME}"
echo "关闭服务：tmux kill-session -t ${SESSION_NAME}"
echo "====================================="