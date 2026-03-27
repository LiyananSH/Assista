# 导入核心库
import streamlit as st
import requests
import sqlite3
import re
import subprocess
import shlex
import os
import time

# ---------------------- 1. 本地记忆+上下文模块（彻底修复拆包问题） ----------------------
def init_db():
    conn = sqlite3.connect("xixiang_memory.db")
    c = conn.cursor()
    # 记忆表
    c.execute('''CREATE TABLE IF NOT EXISTS user_memory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, value TEXT)''')
    # 上下文表
    c.execute('''CREATE TABLE IF NOT EXISTS chat_context
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, response TEXT, create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_memory(user_input):
    # 修复核心：统一的patterns格式 (正则表达式, 关键词分组索引, 值分组索引)
    patterns = [
        # 匹配 "把A改成B" / "将A重命名为B" / "将A改为B"
        (r"把(.*?)改成(.*)", 1, 2),
        (r"将(.*?)重命名为(.*)", 1, 2),
        (r"将(.*?)改为(.*)", 1, 2),
        # 匹配 "我的XX是XX" / "XX叫XX"
        (r"(我的|)?(.*?)是(.*)", 2, 3),
        (r"(我的|)?(.*?)叫(.*)", 2, 3),
        # 匹配 "新建XX文件名为XX"
        (r"新建(.*?)文件名为(.*)", 1, 2)
    ]
    
    # 遍历所有匹配模式，避免拆包错误
    for pattern, key_group, val_group in patterns:
        match = re.search(pattern, user_input, re.DOTALL)
        if match:
            try:
                # 提取关键词和值，过滤空内容
                key = match.group(key_group).strip() if match.group(key_group) else ""
                value = match.group(val_group).strip() if match.group(val_group) else ""
                
                # 只有关键词和值都不为空时才存储
                if key and value:
                    conn = sqlite3.connect("xixiang_memory.db")
                    c = conn.cursor()
                    c.execute("INSERT OR REPLACE INTO user_memory (key, value) VALUES (?, ?)", (key, value))
                    conn.commit()
                    conn.close()
                    return f"已记住：你的{key}是{value}～"
            except IndexError:
                # 匹配到但分组索引不对时，跳过当前模式
                continue
    return None

def get_memory(key):
    # 查询记忆的通用函数
    conn = sqlite3.connect("xixiang_memory.db")
    c = conn.cursor()
    c.execute("SELECT value FROM user_memory WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_context(query, response):
    # 保存对话上下文，最多保留5轮
    conn = sqlite3.connect("xixiang_memory.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_context (query, response) VALUES (?, ?)", (query, response))
    # 只保留最近5轮上下文
    c.execute("DELETE FROM chat_context WHERE id NOT IN (SELECT id FROM chat_context ORDER BY create_time DESC LIMIT 5)")
    conn.commit()
    conn.close()

def get_context():
    # 获取最近5轮上下文，用于Kimi生成命令
    conn = sqlite3.connect("xixiang_memory.db")
    c = conn.cursor()
    c.execute("SELECT query, response FROM chat_context ORDER BY create_time DESC LIMIT 5")
    contexts = c.fetchall()
    conn.close()
    # 反转成时间正序
    contexts.reverse()
    context_str = ""
    for q, r in contexts:
        context_str += f"用户：{q}\n助理：{r}\n"
    return context_str

# ---------------------- 2. 安全校验+命令参数检查 ----------------------
def is_safe_command(cmd):
    # 危险命令列表，严格过滤
    dangerous_commands = ["rm -rf", "sudo", "format", "mkfs", "dd", "rmdir", "shutdown", "rm ", "kill", "chmod 777"]
    if any(danger.lower() in cmd.lower() for danger in dangerous_commands):
        return False, f"禁止执行危险命令：{[d for d in dangerous_commands if d in cmd]}"
    
    # 仅允许操作桌面目录
    desktop_path = os.path.expanduser("~/Desktop")
    cmd_abs = os.path.expanduser(cmd)
    if not (desktop_path in cmd_abs or "~/Desktop" in cmd or "/Desktop" in cmd):
        return False, "仅允许操作桌面目录，请确认命令包含~/Desktop！"
    
    # 允许的安全操作
    allowed_ops = ["mv", "cp", "touch", "ls", "open", "zip", "unzip", "find"]
    if not any(cmd.strip().startswith(op) for op in allowed_ops):
        return False, f"仅允许执行：{', '.join(allowed_ops)} 命令！"
    
    return True, "命令安全"

def pre_check_command_params(cmd, user需求):
    # 预检查命令参数是否完整
    if "mv" in cmd and (cmd.count("~/Desktop/") < 2 or len(cmd.strip().split()) < 2):
        return False, "重命名命令参数不全，请告诉我原文件名和新文件名（比如“把test.txt改成test2.txt”）"
    if "touch" in cmd and len(cmd.strip().split()) < 2:
        return False, "新建文件命令缺少文件名，请告诉我要新建的文件名（比如“新建笔记.txt”）"
    return True, "参数完整"

# ---------------------- 3. Kimi API调用（核心） ----------------------
def generate_terminal_command(user需求, memory_info, context_info):
    # 替换为你的Kimi API密钥
    KIMI_API_KEY = "sk-x8HNE5D1Ik9DdoByia5PZbGjYN4abEtfNmzGoD8atgKLhtq8"  # ← 必须替换！
    KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
    
    # 精准Prompt，确保Kimi生成正确的Mac终端命令
    prompt = f"""
    你是专业的Mac终端命令生成专家，严格遵守以下规则：
    1. 仅生成能直接在Mac终端执行的单行命令，无任何解释、注释、换行；
    2. 所有文件操作必须针对Mac桌面目录（~/Desktop/），命令中必须包含~/Desktop/；
    3. 允许生成的命令：mv(重命名)、cp(复制)、touch(新建)、ls(查看)、open(打开)、zip(压缩)、unzip(解压)、find(查找)；
    4. 禁止生成任何危险命令（rm、sudo、格式化、删除、提权等）；
    5. 结合用户记忆和上下文，自动补全命令参数，参数不全时生成最合理的默认命令；
    6. 命令必须符合Mac终端语法，文件名包含空格时用引号包裹，避免中文乱码。

    对话上下文：
    {context_info}

    用户记忆信息：{memory_info}

    用户需求：{user需求}

    生成Mac终端命令：
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {KIMI_API_KEY}",
            "Content-Type": "application/json"
        }
        # Kimi API参数
        data = {
            "model": "moonshot-v1-8k",  # Kimi基础模型，免费额度足够
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,  # 低随机性，保证命令精准
            "stream": False
        }
        # 超时重试机制，提升稳定性
        for _ in range(2):
            try:
                response = requests.post(KIMI_API_URL, json=data, headers=headers, timeout=10)
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                time.sleep(1)
                continue
        else:
            return "生成命令超时，请重试！"
        
        # 提取并清理命令
        cmd = response.json()["choices"][0]["message"]["content"].strip()
        cmd = cmd.replace("`", "").replace("bash", "").replace("\n", "").strip()
        return cmd
    except Exception as e:
        return f"生成命令失败：{str(e)}"

# ---------------------- 4. 命令执行+自动纠错 ----------------------
def run_terminal_command(cmd):
    # 安全执行终端命令，捕获输出和错误
    try:
        cmd_list = shlex.split(cmd)
        result = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10  # 超时保护
        )
        if result.returncode == 0:
            return True, f"执行成功！\n输出：{result.stdout}"
        else:
            return False, f"执行失败！\n错误信息：{result.stderr}"
    except Exception as e:
        return False, f"执行异常：{str(e)}"

def fix_command(cmd, error_msg, user需求):
    # 调用Kimi自动修正错误命令
    KIMI_API_KEY = "sk-x8HNE5D1Ik9DdoByia5PZbGjYN4abEtfNmzGoD8atgKLhtq8"  # ← 和上面保持一致
    KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
    
    prompt = f"""
    你是Mac终端命令纠错专家，根据错误信息修正命令：
    1. 原命令：{cmd}
    2. 执行错误：{error_msg}
    3. 用户需求：{user需求}
    4. 修正规则：仅生成单行正确命令，包含~/Desktop/，禁止危险命令，符合Mac语法。
    修正后的命令：
    """
    
    try:
        headers = {"Authorization": f"Bearer {KIMI_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "moonshot-v1-8k",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        response = requests.post(KIMI_API_URL, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        fix_cmd = response.json()["choices"][0]["message"]["content"].strip()
        fix_cmd = fix_cmd.replace("`", "").replace("bash", "").strip()
        return fix_cmd
    except Exception as e:
        return f"修正命令失败：{str(e)}"

# ---------------------- 5. 主交互界面（优化版） ----------------------
init_db()
st.title("xixiang - Kimi驱动的Mac智能助理（最终稳定版）")

# 会话状态管理，提升交互体验
if "cmd_status" not in st.session_state:
    st.session_state.cmd_status = None
if "last_cmd" not in st.session_state:
    st.session_state.last_cmd = None
if "error_msg" not in st.session_state:
    st.session_state.error_msg = None

# 多行输入框，支持复杂需求
user_input = st.text_area(
    "请告诉xixiang你想操作什么：",
    placeholder="示例：\n1. 把桌面test.txt改成new_test.txt\n2. 打开桌面的周报.txt\n3. 压缩桌面的照片文件夹为photo.zip\n4. 查找桌面所有txt文件",
    height=120
)

# 按钮布局
col1, col2 = st.columns(2)
with col1:
    submit_btn = st.button("处理需求", type="primary", use_container_width=True)
with col2:
    clear_btn = st.button("清空记忆/上下文", use_container_width=True)

# 清空记忆和上下文
if clear_btn:
    conn = sqlite3.connect("xixiang_memory.db")
    c = conn.cursor()
    c.execute("DELETE FROM user_memory")
    c.execute("DELETE FROM chat_context")
    conn.commit()
    conn.close()
    st.success("✅ 已清空所有记忆和对话上下文！")
    st.rerun()

# 核心处理逻辑
if submit_btn and user_input:
    # 步骤1：存储用户记忆
    memory_msg = save_memory(user_input)
    if memory_msg:
        st.success(memory_msg)
        save_context(user_input, memory_msg)
    else:
        # 步骤2：提取记忆和上下文
        memory_keys = ["文件名", "新名字", "文件类型", "目录", "原文件名", "压缩文件名"]
        memory_info = {k: get_memory(k) for k in memory_keys if get_memory(k)}
        memory_str = str(memory_info) if memory_info else "无"
        context_str = get_context()
        
        # 步骤3：调用Kimi生成终端命令
        with st.spinner("🤖 正在调用Kimi生成终端命令..."):
            cmd = generate_terminal_command(user_input, memory_str, context_str)
        st.session_state.last_cmd = cmd
        
        # 显示生成的命令
        st.subheader("生成的终端命令")
        st.code(cmd, language="bash")
        
        # 步骤4：参数预校验
        param_ok, param_msg = pre_check_command_params(cmd, user_input)
        if not param_ok:
            st.warning(f"⚠️ {param_msg}")
            save_context(user_input, param_msg)
        else:
            # 步骤5：安全校验
            safe_ok, safe_msg = is_safe_command(cmd)
            if not safe_ok:
                st.error(f"🚫 命令不安全：{safe_msg}")
                save_context(user_input, f"命令不安全：{safe_msg}")
            else:
                st.success("✅ 命令校验通过！")
                # 步骤6：确认执行命令
                if st.button("📝 确认执行该命令"):
                    with st.spinner("⚙️ 正在执行命令..."):
                        success, result = run_terminal_command(cmd)
                    st.session_state.cmd_status = success
                    st.session_state.error_msg = result if not success else None
                    
                    if success:
                        st.success(f"✅ {result}")
                        save_context(user_input, f"执行成功：{cmd}\n{result}")
                    else:
                        st.error(f"❌ {result}")
                        save_context(user_input, f"执行失败：{cmd}\n{result}")
                        
                        # 步骤7：自动修正命令
                        with st.spinner("🤖 正在调用Kimi自动修正命令..."):
                            fix_cmd = fix_command(cmd, result, user_input)
                        st.subheader("修正后的命令")
                        st.code(fix_cmd, language="bash", caption="Kimi自动修正的命令")
                        
                        # 执行修正后的命令
                        if st.button("📝 执行修正后的命令"):
                            if is_safe_command(fix_cmd)[0]:
                                with st.spinner("⚙️ 正在执行修正后的命令..."):
                                    fix_success, fix_result = run_terminal_command(fix_cmd)
                                if fix_success:
                                    st.success(f"✅ 修正后执行成功！\n{fix_result}")
                                    save_context(user_input, f"修正后执行成功：{fix_cmd}\n{fix_result}")
                                else:
                                    st.error(f"❌ 修正后仍执行失败：{fix_result}")
                            else:
                                st.error("🚫 修正后的命令不安全，禁止执行！")

# 侧边栏：数据面板
with st.sidebar:
    st.title("📝 数据面板")
    
    # 显示本地记忆
    st.subheader("本地记忆")
    conn = sqlite3.connect("xixiang_memory.db")
    c = conn.cursor()
    memories = c.execute("SELECT key, value FROM user_memory").fetchall()
    if memories:
        for k, v in memories:
            st.write(f"• {k}：{v}")
    else:
        st.write("暂无记忆，可输入“把test.txt改成new.txt”添加")
    
    st.divider()
    
    # 显示最近上下文
    st.subheader("最近对话上下文")
    contexts = c.execute("SELECT query, response FROM chat_context ORDER BY create_time DESC LIMIT 3").fetchall()
    if contexts:
        for q, r in contexts:
            st.write(f"🔹 用户：{q[:25]}..." if len(q) > 25 else f"🔹 用户：{q}")
            st.write(f"🔹 助理：{r[:30]}..." if len(r) > 30 else f"🔹 助理：{r}")
            st.divider()
    else:
        st.write("暂无对话上下文")
    conn.close()
