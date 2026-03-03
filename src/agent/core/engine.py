"""
Assista V3.3 - Core Engine
集成上下文工程的 ReAct Agent
"""

import json
import re
import asyncio
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from agent.core.interface import (
    AgentInterface, AgentInput, AgentOutput, AgentConfig,
    Message, ToolCall, ToolResult, SessionState,
    TaskType, AgentStatus, ErrorCategory,
    LLMError
)
from llm.adapter import LLMInterface, LLMFactory
from tools.registry import ToolRegistry, create_default_registry
from context import ContextAssembler, MemoryManager, create_assembler


class ReActEngine:
    """ReAct 引擎 - V3.3 集成上下文工程"""
    
    # 智能压缩阈值
    MAX_CONTEXT_MESSAGES = 10      # 保留最近 N 条完整对话
    SUMMARY_THRESHOLD = 20         # 超过此数量时触发压缩
    
    def __init__(self, llm: LLMInterface, tools: ToolRegistry, 
                 config: AgentConfig, workspace_path: str):
        self.llm = llm
        self.tools = tools
        self.config = config
        self.workspace_path = workspace_path
        
        # 上下文系统
        self.assembler = create_assembler(workspace_path)
        self.memory = MemoryManager(workspace_path)
        
        # 会话状态
        self.sessions: Dict[str, SessionState] = {}
    
    async def _compress_context(self, messages: List[Message]) -> List[Message]:
        """
        智能压缩上下文
        
        策略：
        1. 保留最近 MAX_CONTEXT_MESSAGES 条完整对话
        2. 更早的对话压缩成摘要
        3. 如果总长度仍超限，进一步精简
        """
        if len(messages) <= self.MAX_CONTEXT_MESSAGES:
            return messages
        
        # 分割：保留的 vs 需要压缩的
        keep_messages = messages[-self.MAX_CONTEXT_MESSAGES:]
        old_messages = messages[:-self.MAX_CONTEXT_MESSAGES]
        
        # 压缩早期对话
        summary = await self._generate_summary(old_messages)
        
        # 组装：摘要 + 保留的完整对话
        compressed = [
            Message(role="system", content=f"[早期对话摘要] {summary}")
        ] + keep_messages
        
        return compressed
    
    async def _generate_summary(self, messages: List[Message]) -> str:
        """生成对话摘要"""
        # 构建摘要提示
        dialog_text = "\n".join([
            f"{m.role}: {m.content[:200]}"  # 每条最多200字
            for m in messages
        ])
        
        summary_prompt = f"""请用2-3句话总结以下对话的核心内容，保留关键信息和用户意图：

{dialog_text}

摘要："""
        
        try:
            result = await self.llm.chat([
                {"role": "user", "content": summary_prompt}
            ])
            return result["content"].strip()
        except:
            # 如果摘要失败，返回简单统计
            return f"此前共 {len(messages)} 轮对话"
    
    def _get_or_create_session(self, session_id: str) -> SessionState:
        """获取或创建会话状态"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(
                session_id=session_id,
                status=AgentStatus.IDLE
            )
        return self.sessions[session_id]
    
    def _build_system_prompt(self) -> str:
        """使用上下文组装器构建系统提示词"""
        context = self.assembler.assemble(is_main_session=True)
        
        # 组装成系统提示词
        system_content = f"""{context.system_prompt}

=== 用户信息 ===
{context.user_profile}

=== 近期记忆 ===
{context.recent_history}
"""
        
        if context.longterm_memory:
            system_content += f"\n=== 长期记忆 ===\n{context.longterm_memory}\n"
        
        # 添加工具使用说明
        system_content += f"""
=== 工具使用说明 ===

可用工具：
{context.tool_definitions}

**何时使用工具：**
- 用户明确要求操作文件、执行命令
- 用户说"创建"、"列出"、"读取"、"运行"等动作词
- 需要获取系统信息或操作环境

**何时不使用工具：**
- 用户只是聊天、询问信息
- 用户说"记住"（这是记忆功能，不是工具）
- 纯对话、解释、建议

**工具调用格式（严格）：**
只有当你确定需要执行工具时，才输出：

<function_calls>
<invoke name="工具名称">
<parameter name="参数名">参数值</parameter>
</invoke>
</function_calls>

**重要：**
- 必须包含完整的 <function_calls>...</function_calls> 包裹
- 解释工具用法时，不要输出完整格式，用自然语言描述
- 如果不确定是否需要工具，先询问用户
"""
        
        return system_content
    
    def _extract_memory_content(self, user_msg: str, assistant_reply: str) -> str:
        """
        智能提取需要记忆的核心信息
        
        规则：
        1. 用户说"记住" - 提取记住的内容
        2. 用户表达偏好（喜欢/不喜欢/习惯）- 提取偏好
        3. 重要决策或约定 - 提取决策
        4. 其他日常对话 - 返回空（不记录）
        """
        import re
        
        # 规则 1: 用户说"记住"
        if "记住" in user_msg or "记得" in user_msg:
            # 提取"记住"后面的完整内容
            content = re.sub(r'.*记住[：:]?\s*', '', user_msg)
            content = re.sub(r'.*记得[：:]?\s*', '', content)
            
            # 检查提取的内容是否包含偏好
            if any(kw in content for kw in ["喜欢", "爱", "偏好", "习惯", "讨厌", "不喜欢"]):
                return f"用户偏好: {content}"
            return f"用户要求记住: {content}"
        
        # 规则 2: 用户表达偏好（直接说，没有"记住"）
        preference_patterns = [
            r'我(喜欢|爱|偏好|倾向于|习惯用|常用)\s*(.+)',
            r'我(不喜欢|讨厌|反感)\s*(.+)',
            r'我(是|做)\s*(.+?)(的|工作|开发)',
        ]
        for pattern in preference_patterns:
            match = re.search(pattern, user_msg)
            if match:
                return f"用户偏好: {match.group(0)}"
        
        # 规则 3: 重要信息（项目、目标、约束）
        important_patterns = [
            r'我正在做(.+)',
            r'我的目标是(.+)',
            r'项目叫(.+)',
            r' deadline[是:]?(.+)',
        ]
        for pattern in important_patterns:
            match = re.search(pattern, user_msg)
            if match:
                return f"重要信息: {match.group(0)}"
        
        # 日常对话不记录（返回空）
        return ""
    
    def _parse_tool_call(self, response: str) -> Optional[ToolCall]:
        """
        从响应中解析工具调用
        
        严格检测：必须包含 <function_calls> 包裹的 <invoke> 才认为是真正的工具调用
        避免将解释性内容误解析为工具调用
        """
        # 首先检查是否有 function_calls 标记
        if '<function_calls>' not in response:
            return None
        
        # 提取 function_calls 块内的内容
        import re
        func_match = re.search(r'<function_calls>(.*?)</function_calls>', response, re.DOTALL)
        if not func_match:
            return None
        
        # 在 function_calls 块内解析 invoke
        inner_content = func_match.group(1)
        xml_pattern = r'<invoke\s+name="([^"]+)">\s*<parameter\s+name="([^"]+)">([^<]+)</parameter>\s*</invoke>'
        xml_match = re.search(xml_pattern, inner_content, re.DOTALL)
        
        if xml_match:
            tool_name = xml_match.group(1).strip()
            param_name = xml_match.group(2).strip()
            param_value = xml_match.group(3).strip()
            
            # 验证工具名称是否合法
            if tool_name in self.tools.list_tools():
                return ToolCall(
                    tool_name=tool_name,
                    parameters={param_name: param_value}
                )
        
        return None
    
    async def run(self, input_data: AgentInput) -> AgentOutput:
        """执行主循环"""
        start_time = time.time()
        session = self._get_or_create_session(input_data.session_id)
        session.status = AgentStatus.THINKING
        
        try:
            # 构建系统提示词（从上下文文件）
            system_prompt = self._build_system_prompt()
            
            # 智能压缩上下文（如果对话历史过长）
            compressed_context = await self._compress_context(input_data.context)
            
            # 构建消息：系统提示 + 压缩后的上下文 + 当前用户消息
            messages = [
                {"role": "system", "content": system_prompt},
                *[m.to_dict() for m in compressed_context],
                {"role": "user", "content": input_data.message}
            ]
            
            # 调用 LLM
            result = await self.llm.chat(messages)
            content = result["content"]
            
            # 尝试解析工具调用
            tool_call = self._parse_tool_call(content)
            
            if tool_call:
                # 执行工具
                session.status = AgentStatus.EXECUTING
                tool_result = await self.tools.execute(tool_call)
                
                # 构建结果消息
                if tool_result.success:
                    response = f"✅ 已完成！\n\n{tool_result.result}"
                else:
                    response = f"❌ 执行失败：{tool_result.error_message}"
                
                # 记录工具执行到记忆（仅记录重要操作）
                if tool_call.tool_name in ['create_folder', 'create_file', 'execute_command']:
                    self.memory.add(
                        content=f"执行: {tool_call.tool_name} {tool_call.parameters}",
                        category="action",
                        importance=2,
                        tags=["file_operation"]
                    )
                
                return AgentOutput(
                    response=response,
                    task_type=TaskType.SINGLE_TOOL,
                    tool_calls=[tool_call],
                    tool_results=[tool_result],
                    latency_ms=int((time.time() - start_time) * 1000),
                    token_usage=result.get("usage", {})
                )
            
            # 处理特殊命令：遗忘
            if input_data.message.startswith("遗忘") or input_data.message.startswith("忘记"):
                keyword = input_data.message.replace("遗忘", "").replace("忘记", "").strip()
                if keyword:
                    deleted = self.memory.forget_by_user_request(keyword)
                    return AgentOutput(
                        response=f"已遗忘 {deleted} 条相关记忆" if deleted > 0 else "未找到相关记忆",
                        task_type=TaskType.DIRECT_CHAT,
                        latency_ms=int((time.time() - start_time) * 1000)
                    )
            
            # 处理特殊命令：清理记忆
            if input_data.message.strip() == "清理记忆":
                self.memory.cleanup_old_memories()
                return AgentOutput(
                    response="记忆清理完成",
                    task_type=TaskType.DIRECT_CHAT,
                    latency_ms=int((time.time() - start_time) * 1000)
                )
            
            # 纯对话回复 - 智能提取核心信息记录到记忆
            memory_content = self._extract_memory_content(input_data.message, content)
            if memory_content:
                importance = 2 if "偏好" in memory_content or "喜欢" in memory_content else 1
                self.memory.add(
                    content=memory_content,
                    category="insight" if importance > 1 else "conversation",
                    importance=importance,
                    tags=["user_preference"] if importance > 1 else []
                )
            
            session.status = AgentStatus.IDLE
            return AgentOutput(
                response=content,
                task_type=TaskType.DIRECT_CHAT,
                latency_ms=int((time.time() - start_time) * 1000),
                token_usage=result.get("usage", {})
            )
            
        except LLMError as e:
            session.status = AgentStatus.ERROR
            return AgentOutput(
                response=f"LLM 调用失败: {str(e)}",
                task_type=TaskType.DIRECT_CHAT,
                error=str(e),
                error_category=e.category,
                latency_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            session.status = AgentStatus.ERROR
            return AgentOutput(
                response=f"执行出错: {str(e)}",
                task_type=TaskType.DIRECT_CHAT,
                error=str(e),
                error_category=ErrorCategory.UNKNOWN_ERROR,
                latency_ms=int((time.time() - start_time) * 1000)
            )


class AssistaAgent(AgentInterface):
    """Assista V3.3 主 Agent - 集成上下文工程"""
    
    def __init__(self, config: Optional[AgentConfig] = None, 
                 workspace_path: str = "./workspace"):
        self.config = config or AgentConfig()
        self.workspace_path = workspace_path
        self.llm: Optional[LLMInterface] = None
        self.tools: Optional[ToolRegistry] = None
        self.engine: Optional[ReActEngine] = None
        self._initialized = False
    
    async def initialize(self, llm_config: Dict[str, Any]):
        """初始化 Agent"""
        # 创建 LLM
        self.llm = LLMFactory.create(**llm_config)
        
        # 创建工具注册表
        self.tools = create_default_registry()
        
        # 创建引擎（集成上下文）
        self.engine = ReActEngine(
            self.llm, self.tools, self.config, self.workspace_path
        )
        
        self._initialized = True
        print(f"✅ Agent 初始化完成（工作区: {self.workspace_path}）")
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """处理用户输入"""
        if not self._initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        return await self.engine.run(input_data)
    
    async def classify_intent(self, message: str, 
                              context: List[Message]) -> TaskType:
        """意图分类"""
        keywords = ["创建", "新建", "列出", "读取", "运行", "执行"]
        for kw in keywords:
            if kw in message:
                return TaskType.SINGLE_TOOL
        return TaskType.DIRECT_CHAT
    
    async def plan(self, task_type: TaskType, message: str,
                   context: List[Message]) -> List[Dict[str, Any]]:
        """任务规划"""
        return [{"step": 1, "action": "process", "description": message}]
    
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """获取会话状态"""
        if not self.engine:
            return None
        return self.engine.sessions.get(session_id)
    
    async def close(self):
        """关闭资源"""
        if self.llm:
            await self.llm.close()
