from openai import OpenAI
import time

# vLLM服务配置（AutoDL公网端口映射）
BASE_URL = "  (待填写)公网访问地址，控制台->自定义服务->查看所租用服务器的公网IP "
BASE_URL += "/v1"
# 示例：BASE_URL = "https://u929078-9659-ea0648dd.bjb1.seetacloud.com:8443/v1"

#（本地回环地址）
# BASE_URL = "http://localhost:6006/v1"

API_KEY = "eda-dev-key-2026" # 前后端对接用，测试使用的是eda-dev-key-2026，可更换
MODEL_NAME = "qwen2.5-7b-eda"

# 初始化客户端
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def test_list_models():
    """测试1：查询加载的模型"""
    print("===== 1. 查询模型列表 =====")
    res = client.models.list()
    print(f"已加载模型：{res.data[0].id}\n")

def test_single_eda_qa():
    """测试2：单轮EDA专业知识问答"""
    print("===== 2. EDA知识问答测试 =====")
    prompt = "解释Verilog中always @*组合逻辑的使用场景，举例说明锁存器风险"
    start = time.time()
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800
    )
    cost = round(time.time() - start, 2)
    print(f"耗时：{cost}s")
    print(f"回答：\n{resp.choices[0].message.content}\n")

def test_verilog_code_gen():
    """测试3：Verilog代码生成（EDA核心场景）"""
    print("===== 3. Verilog代码生成测试 =====")
    prompt = "写一个同步8位计数器，带复位、使能端口，输出综合可综合代码"
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024
    )
    print(f"Verilog代码：\n{resp.choices[0].message.content}\n")

def test_stream_output():
    """测试4：流式输出（前端交互必备）"""
    print("===== 4. 流式输出测试（逐字打印） =====")
    prompt = "简述数字IC设计从RTL到GDSII的完整EDA流程"
    stream = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        max_tokens=600
    )
    full_text = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            txt = chunk.choices[0].delta.content
            full_text += txt
            print(txt, end="", flush=True)
    print("\n")

def test_multi_round_chat():
    """测试5：多轮上下文对话（学生连续提问场景）"""
    print("===== 5. 多轮对话上下文测试 =====")
    history = [
        {"role": "user", "content": "什么是建立时间？"},
        {"role": "assistant", "content": "建立时间是触发器输入数据需要提前稳定的最小时间，不满足会出现亚稳态"},
        {"role": "user", "content": "那如何修复建立时间违例？"}
    ]
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=history,
        temperature=0.4,
        max_tokens=600
    )
    print(f"多轮回答：\n{resp.choices[0].message.content}\n")

if __name__ == "__main__":
    # 依次执行全部接口验证用例
    test_list_models()
    test_single_eda_qa()
    test_verilog_code_gen()
    test_stream_output()
    test_multi_round_chat()
    print("===== 全部API接口测试完成，服务可用 =====")