"""
Assista V3.2 - LLM Adapter
支持多模型：Moonshot, OpenAI, Claude, Ollama
"""

import json
import asyncio
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, AsyncIterator
from abc import ABC, abstractmethod
from dataclasses import dataclass

from agent.core.interface import (
    LLMInterface, LLMError, ErrorCategory,
    AgentConfig
)


@dataclass
class LLMResponse:
    """LLM 响应标准化格式"""
    content: str
    tool_calls: List[Dict[str, Any]]
    usage: Dict[str, int]
    model: str
    raw_response: Dict[str, Any]


# ============================================================================
# Base Adapter
# ============================================================================

class BaseLLMAdapter(LLMInterface, ABC):
    """LLM 适配器基类"""
    
    def __init__(self, api_key: str, config: Optional[AgentConfig] = None):
        self.api_key = api_key
        self.config = config or AgentConfig()
    
    async def close(self):
        """关闭连接（同步适配器无需操作）"""
        pass
    
    @abstractmethod
    def _build_request_payload(self, messages: List[Dict], 
                               tools: Optional[List[Dict]],
                               temperature: float,
                               max_tokens: int) -> Dict[str, Any]:
        """构建请求体"""
        pass
    
    @abstractmethod
    def _parse_response(self, raw_response: Dict) -> LLMResponse:
        """解析响应"""
        pass
    
    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        pass
    
    async def chat(self, messages: List[Dict[str, str]], 
                   tools: Optional[List[Dict]] = None,
                   temperature: float = 0.7,
                   max_tokens: int = 2048) -> Dict[str, Any]:
        """调用 LLM 进行对话（使用线程池执行同步 HTTP）"""
        
        payload = self._build_request_payload(
            messages, tools, temperature, max_tokens
        )
        
        def _make_request():
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode('utf-8'),
                headers=self._get_headers(),
                method='POST'
            )
            
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    return json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                try:
                    error_data = json.loads(error_body)
                    error_msg = error_data.get("error", {}).get("message", error_body)
                except:
                    error_msg = error_body
                
                if e.code == 429:
                    raise LLMError(
                        f"Rate limit exceeded: {error_msg}",
                        category=ErrorCategory.RATE_LIMIT_ERROR,
                        retryable=True
                    )
                elif e.code == 401:
                    raise LLMError(
                        f"Authentication failed: {error_msg}",
                        category=ErrorCategory.LLM_ERROR,
                        retryable=False
                    )
                else:
                    raise LLMError(
                        f"API error ({e.code}): {error_msg}",
                        category=ErrorCategory.LLM_ERROR,
                        retryable=e.code >= 500
                    )
            except urllib.error.URLError as e:
                raise LLMError(
                    f"Network error: {str(e)}",
                    category=ErrorCategory.LLM_ERROR,
                    retryable=True
                )
        
        # 在线程池中执行同步 HTTP 请求
        loop = asyncio.get_event_loop()
        try:
            raw_data = await asyncio.wait_for(
                loop.run_in_executor(None, _make_request),
                timeout=60
            )
            result = self._parse_response(raw_data)
            return {
                "content": result.content,
                "tool_calls": result.tool_calls,
                "usage": result.usage,
                "model": result.model
            }
        except asyncio.TimeoutError:
            raise LLMError(
                "Request timeout",
                category=ErrorCategory.TIMEOUT_ERROR,
                retryable=True
            )
    
    async def stream_chat(self, messages: List[Dict[str, str]],
                          **kwargs) -> AsyncIterator[str]:
        """流式对话 - 子类可重写优化"""
        # 默认实现：先拿到完整响应再逐字yield
        result = await self.chat(messages, **kwargs)
        content = result.get("content", "")
        for char in content:
            yield char
            await asyncio.sleep(0.01)  # 模拟流式效果
    
    def get_model_name(self) -> str:
        return self.model


# ============================================================================
# Moonshot Adapter (Kimi)
# ============================================================================

class MoonshotAdapter(BaseLLMAdapter):
    """Moonshot Kimi 适配器"""
    
    def __init__(self, api_key: str, model: str = "kimi-k2.5", 
                 base_url: Optional[str] = None, config: Optional[AgentConfig] = None):
        super().__init__(api_key, config)
        self.model = model
        self.base_url = base_url or "https://api.moonshot.cn/v1/chat/completions"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_request_payload(self, messages: List[Dict], 
                               tools: Optional[List[Dict]],
                               temperature: float,
                               max_tokens: int) -> Dict[str, Any]:
        # Kimi k2.5 只支持 temperature=1
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 1,
            "max_tokens": max_tokens
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload
    
    def _parse_response(self, raw_response: Dict) -> LLMResponse:
        choice = raw_response["choices"][0]
        message = choice["message"]
        
        # 提取 tool_calls
        tool_calls = []
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                tool_calls.append({
                    "id": tc.get("id"),
                    "type": tc.get("type", "function"),
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                })
        
        return LLMResponse(
            content=message.get("content", ""),
            tool_calls=tool_calls,
            usage=raw_response.get("usage", {}),
            model=raw_response.get("model", self.model),
            raw_response=raw_response
        )


# ============================================================================
# OpenAI Adapter
# ============================================================================

class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI 适配器"""
    
    def __init__(self, api_key: str, model: str = "gpt-4",
                 base_url: Optional[str] = None, config: Optional[AgentConfig] = None):
        super().__init__(api_key, config)
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1/chat/completions"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_request_payload(self, messages: List[Dict], 
                               tools: Optional[List[Dict]],
                               temperature: float,
                               max_tokens: int) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload
    
    def _parse_response(self, raw_response: Dict) -> LLMResponse:
        choice = raw_response["choices"][0]
        message = choice["message"]
        
        tool_calls = []
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                tool_calls.append({
                    "id": tc.get("id"),
                    "type": tc.get("type", "function"),
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                })
        
        return LLMResponse(
            content=message.get("content", ""),
            tool_calls=tool_calls,
            usage=raw_response.get("usage", {}),
            model=raw_response.get("model", self.model),
            raw_response=raw_response
        )


# ============================================================================
# Ollama Adapter (本地模型)
# ============================================================================

class OllamaAdapter(BaseLLMAdapter):
    """Ollama 本地模型适配器"""
    
    def __init__(self, api_key: str = "", model: str = "llama2", 
                 base_url: Optional[str] = None, config: Optional[AgentConfig] = None):
        # Ollama 不需要 API key
        super().__init__("", config)
        self.model = model
        self.base_url = (base_url or "http://localhost:11434") + "/api/chat"
    
    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}
    
    def _build_request_payload(self, messages: List[Dict], 
                               tools: Optional[List[Dict]],
                               temperature: float,
                               max_tokens: int) -> Dict[str, Any]:
        # Ollama 格式略有不同
        return {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
    
    def _parse_response(self, raw_response: Dict) -> LLMResponse:
        message = raw_response.get("message", {})
        
        return LLMResponse(
            content=message.get("content", ""),
            tool_calls=[],  # Ollama 原生不支持 tool_calls
            usage={
                "prompt_tokens": raw_response.get("prompt_eval_count", 0),
                "completion_tokens": raw_response.get("eval_count", 0),
                "total_tokens": raw_response.get("prompt_eval_count", 0) + 
                               raw_response.get("eval_count", 0)
            },
            model=self.model,
            raw_response=raw_response
        )


# ============================================================================
# LLM Factory
# ============================================================================

class LLMFactory:
    """LLM 适配器工厂"""
    
    _adapters = {
        "moonshot": MoonshotAdapter,
        "openai": OpenAIAdapter,
        "ollama": OllamaAdapter,
    }
    
    @classmethod
    def create(cls, provider: str, **kwargs) -> LLMInterface:
        """
        创建 LLM 适配器
        
        Args:
            provider: 提供商名称 (moonshot, openai, ollama)
            **kwargs: 传递给适配器的参数
        
        Returns:
            LLMInterface 实例
        """
        if provider not in cls._adapters:
            raise ValueError(f"Unknown provider: {provider}. "
                           f"Available: {list(cls._adapters.keys())}")
        
        adapter_class = cls._adapters[provider]
        return adapter_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, adapter_class: type):
        """注册新的适配器"""
        cls._adapters[name] = adapter_class
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """列出所有支持的提供商"""
        return list(cls._adapters.keys())


# ============================================================================
# 配置加载
# ============================================================================

def load_llm_from_config(config_dict: Dict[str, Any]) -> LLMInterface:
    """
    从配置字典加载 LLM
    
    配置格式:
    {
        "provider": "moonshot",
        "api_key": "sk-...",
        "model": "kimi-k2.5",
        "base_url": "https://api.moonshot.cn/v1"  # 可选
    }
    """
    provider = config_dict.get("provider", "moonshot")
    
    kwargs = {
        "api_key": config_dict.get("api_key", ""),
        "model": config_dict.get("model"),
    }
    
    # 移除 None 值
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    if "base_url" in config_dict:
        kwargs["base_url"] = config_dict["base_url"]
    
    return LLMFactory.create(provider, **kwargs)
