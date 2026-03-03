"""
Assista V3.2 - 核心接口契约
定义所有模块间的数据结构和协议
"""

from typing import Protocol, Dict, Any, List, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from abc import ABC, abstractmethod


# ============================================================================
# 枚举定义
# ============================================================================

class TaskType(Enum):
    """任务类型枚举"""
    DIRECT_CHAT = "direct_chat"      # 纯对话，无需工具
    SINGLE_TOOL = "single_tool"      # 单工具调用
    MULTI_STEP = "multi_step"        # 多步骤任务
    COMPLEX = "complex"              # 需要规划的复杂任务
    CLARIFICATION = "clarification"  # 需要用户澄清


class ErrorCategory(Enum):
    """错误分类枚举"""
    LLM_ERROR = "llm_error"               # LLM 调用失败
    TOOL_ERROR = "tool_error"             # 工具执行失败
    PERMISSION_ERROR = "permission"       # 权限不足
    TIMEOUT_ERROR = "timeout"             # 超时
    VALIDATION_ERROR = "validation"       # 参数校验失败
    RATE_LIMIT_ERROR = "rate_limit"       # 限流
    UNKNOWN_ERROR = "unknown"             # 未知错误


class AgentStatus(Enum):
    """Agent 状态枚举"""
    IDLE = "idle"                       # 空闲
    THINKING = "thinking"               # 思考中
    EXECUTING = "executing"             # 执行工具
    WAITING_INPUT = "waiting_input"     # 等待用户输入
    ERROR = "error"                     # 错误状态


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class Message:
    """对话消息"""
    role: str                           # system / user / assistant / tool
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, str]:
        """转换为 LLM API 格式"""
        return {"role": self.role, "content": self.content}


@dataclass  
class ToolCall:
    """工具调用定义"""
    tool_name: str
    parameters: Dict[str, Any]
    call_id: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "parameters": self.parameters
        }


@dataclass
class ToolResult:
    """工具执行结果"""
    call_id: str
    tool_name: str
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    
    @classmethod
    def success_result(cls, call_id: str, tool_name: str, result: Any, execution_time_ms: int = 0):
        return cls(call_id=call_id, tool_name=tool_name, success=True, 
                   result=result, execution_time_ms=execution_time_ms)
    
    @classmethod
    def error_result(cls, call_id: str, tool_name: str, error_message: str):
        return cls(call_id=call_id, tool_name=tool_name, success=False, 
                   result=None, error_message=error_message)


@dataclass
class AgentInput:
    """Agent 输入数据"""
    message: str
    context: List[Message] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: datetime.now().isoformat())
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_llm_messages(self) -> List[Dict[str, str]]:
        """转换为 LLM 消息格式"""
        messages = [msg.to_dict() for msg in self.context]
        messages.append({"role": "user", "content": self.message})
        return messages


@dataclass
class AgentOutput:
    """Agent 输出数据"""
    response: str
    task_type: TaskType
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    latency_ms: int = 0
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """是否成功完成"""
        return self.error is None


@dataclass
class ReActStep:
    """ReAct 单步记录"""
    step_number: int
    thought: str                      # 思考过程
    action: Optional[ToolCall]        # 行动（工具调用）
    observation: Optional[str]        # 观察结果
    is_final: bool = False            # 是否最终回答


@dataclass
class SessionState:
    """会话状态"""
    session_id: str
    status: AgentStatus
    current_task: Optional[str] = None
    react_history: List[ReActStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 工具相关定义
# ============================================================================

@dataclass
class ToolSchema:
    """工具 schema 定义"""
    name: str
    description: str
    parameters: Dict[str, Any]        # JSON Schema
    required: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        # 返回 OpenAI function calling 格式
        return self.parameters


# ============================================================================
# 协议定义 (Interfaces)
# ============================================================================

class LLMInterface(Protocol):
    """LLM 适配器接口"""
    
    async def chat(self, messages: List[Dict[str, str]], 
                   tools: Optional[List[Dict]] = None,
                   temperature: float = 0.7,
                   max_tokens: int = 2048) -> Dict[str, Any]:
        """
        调用 LLM 进行对话
        
        Returns:
            {
                "content": str,           # 回复内容
                "tool_calls": List[Dict], # 工具调用请求
                "usage": Dict,            # token 使用情况
                "model": str              # 实际使用的模型
            }
        """
        ...
    
    async def stream_chat(self, messages: List[Dict[str, str]],
                          **kwargs) -> AsyncIterator[str]:
        """流式对话"""
        ...
    
    def get_model_name(self) -> str:
        """获取当前模型名称"""
        ...


class ToolInterface(Protocol):
    """工具接口"""
    
    @property
    def schema(self) -> ToolSchema:
        """获取工具 schema"""
        ...
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """执行工具"""
        ...
    
    def validate_params(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """验证参数，返回 (是否有效, 错误信息)"""
        ...


class MemoryInterface(Protocol):
    """记忆系统接口"""
    
    async def add(self, session_id: str, message: Message) -> None:
        """添加消息到记忆"""
        ...
    
    async def get_context(self, session_id: str, 
                          limit: int = 10) -> List[Message]:
        """获取会话上下文"""
        ...
    
    async def search(self, query: str, session_id: Optional[str] = None,
                     limit: int = 5) -> List[Message]:
        """语义搜索记忆"""
        ...
    
    async def clear(self, session_id: str) -> None:
        """清空会话记忆"""
        ...


class AgentInterface(ABC):
    """Agent 抽象基类"""
    
    @abstractmethod
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """处理用户输入，返回结果"""
        pass
    
    @abstractmethod
    async def classify_intent(self, message: str, 
                              context: List[Message]) -> TaskType:
        """意图分类"""
        pass
    
    @abstractmethod
    async def plan(self, task_type: TaskType, message: str,
                   context: List[Message]) -> List[Dict[str, Any]]:
        """任务规划，生成执行步骤"""
        pass
    
    @abstractmethod
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """获取会话状态"""
        pass


# ============================================================================
# 异常定义
# ============================================================================

class AssistaError(Exception):
    """基础异常类"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
                 details: Optional[Dict] = None):
        super().__init__(message)
        self.category = category
        self.details = details or {}


class LLMError(AssistaError):
    """LLM 调用异常"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.LLM_ERROR,
                 retryable: bool = True, details: Optional[Dict] = None):
        super().__init__(message, category, details)
        self.retryable = retryable


class ToolError(AssistaError):
    """工具执行异常"""
    def __init__(self, message: str, tool_name: str,
                 category: ErrorCategory = ErrorCategory.TOOL_ERROR,
                 details: Optional[Dict] = None):
        super().__init__(message, category, details)
        self.tool_name = tool_name


class ValidationError(AssistaError):
    """参数校验异常"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, ErrorCategory.VALIDATION_ERROR)
        self.field = field


# ============================================================================
# 配置类
# ============================================================================

@dataclass
class AgentConfig:
    """Agent 配置"""
    # LLM 配置
    llm_provider: str = "moonshot"
    llm_model: str = "kimi-k2.5"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    
    # 行为配置
    max_react_steps: int = 10           # ReAct 最大步数
    max_context_messages: int = 20      # 最大上下文消息数
    enable_streaming: bool = False      # 是否启用流式输出
    
    # 错误处理
    max_retries: int = 3                # 最大重试次数
    retry_delay_ms: int = 1000          # 重试延迟
    
    # 工具配置
    allowed_tools: List[str] = field(default_factory=list)  # 空列表表示允许所有
    blocked_tools: List[str] = field(default_factory=list)
    
    # 安全配置
    enable_sandbox: bool = True         # 启用沙箱
    max_execution_time_ms: int = 30000  # 最大执行时间


@dataclass
class MetricsSnapshot:
    """性能指标快照"""
    timestamp: datetime
    request_count: int
    avg_latency_ms: float
    error_rate: float
    active_sessions: int
    token_usage_total: int
