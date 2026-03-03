#!/usr/bin/env python3
"""
Assista V3.3 - 主程序入口
集成上下文工程系统
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.core.interface import AgentInput, Message, AgentConfig
from agent.core.engine import AssistaAgent


# 默认配置
DEFAULT_CONFIG = {
    "provider": "moonshot",
    "api_key": "sk-OLxkWFTucs16C0OTkKBfJOhdiyUWJPgzTibPiOampXVzpW80",
    "model": "kimi-k2.5"
}

# 工作区路径
WORKSPACE_PATH = str(Path(__file__).parent / "workspace")


async def main():
    print("🚀 Assista V3.3 开发版")
    print("=" * 40)
    print()
    
    # 初始化 Agent（集成上下文工程）
    agent = AssistaAgent(
        AgentConfig(max_react_steps=5),
        workspace_path=WORKSPACE_PATH
    )
    await agent.initialize(DEFAULT_CONFIG)
    
    print()
    print("💬 输入 'exit' 退出")
    print("-" * 40)
    print()
    
    # 对话历史
    context: list[Message] = []
    
    while True:
        try:
            # 获取用户输入
            user_input = input("👤 你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "退出"]:
                print("\n👋 再见！")
                break
            
            # 构建输入
            agent_input = AgentInput(
                message=user_input,
                context=context
            )
            
            # 处理
            print("🤖 Assista: ", end="", flush=True)
            result = await agent.process(agent_input)
            
            # 输出结果
            print(result.response)
            
            # 显示工具调用信息
            if result.tool_calls:
                print(f"   [使用了 {len(result.tool_calls)} 个工具]")
            
            print()
            
            # 更新上下文
            context.append(Message(role="user", content=user_input))
            context.append(Message(role="assistant", content=result.response))
            
            # 限制上下文长度
            if len(context) > 20:
                context = context[-20:]
                
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
            print()
    
    # 清理资源
    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
