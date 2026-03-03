"""
Assista V3.2 - Tool Registry
工具注册表和执行器
"""

import json
import asyncio
import subprocess
import shlex
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from agent.core.interface import (
    ToolInterface, ToolSchema, ToolResult, ToolCall,
    ToolError, ErrorCategory, ValidationError
)


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, ToolInterface] = {}
        self._schemas: Dict[str, ToolSchema] = {}
    
    def register(self, tool: ToolInterface) -> None:
        """注册工具"""
        schema = tool.schema
        self._tools[schema.name] = tool
        self._schemas[schema.name] = schema
    
    def unregister(self, tool_name: str) -> None:
        """注销工具"""
        self._tools.pop(tool_name, None)
        self._schemas.pop(tool_name, None)
    
    def get(self, tool_name: str) -> Optional[ToolInterface]:
        """获取工具"""
        return self._tools.get(tool_name)
    
    def get_schema(self, tool_name: str) -> Optional[ToolSchema]:
        """获取工具 Schema"""
        return self._schemas.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具 Schema（用于 LLM）"""
        return [schema.to_dict() for schema in self._schemas.values()]
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """执行工具调用"""
        tool = self.get(tool_call.tool_name)
        if not tool:
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                error_message=f"Tool not found: {tool_call.tool_name}"
            )
        
        # 验证参数
        valid, error_msg = tool.validate_params(tool_call.parameters)
        if not valid:
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                error_message=f"Parameter validation failed: {error_msg}"
            )
        
        # 执行工具
        try:
            import time
            start = time.time()
            result = await tool.execute(tool_call.parameters)
            execution_time = int((time.time() - start) * 1000)
            result.execution_time_ms = execution_time
            return result
        except Exception as e:
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                error_message=str(e)
            )


# ============================================================================
# 内置工具实现
# ============================================================================

class CreateFolderTool(ToolInterface):
    """创建文件夹工具"""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="create_folder",
            description="创建文件夹，支持多级目录",
            parameters={
                "type": "function",
                "function": {
                    "name": "create_folder",
                    "description": "创建文件夹，支持多级目录",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件夹路径，支持 ~ 表示 home 目录"
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        )
    
    def validate_params(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "path" not in parameters:
            return False, "Missing required parameter: path"
        if not isinstance(parameters["path"], str):
            return False, "Parameter 'path' must be a string"
        return True, None
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            path = Path(parameters["path"]).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            return ToolResult.success_result(
                call_id="",
                tool_name="create_folder",
                result=f"Created directory: {path}"
            )
        except Exception as e:
            raise ToolError(str(e), "create_folder")


class CreateFileTool(ToolInterface):
    """创建文件工具"""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="create_file",
            description="创建文件，自动创建父目录",
            parameters={
                "type": "function",
                "function": {
                    "name": "create_file",
                    "description": "创建文件，自动创建父目录",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径"
                            },
                            "content": {
                                "type": "string",
                                "description": "文件内容",
                                "default": ""
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        )
    
    def validate_params(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "path" not in parameters:
            return False, "Missing required parameter: path"
        return True, None
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            path = Path(parameters["path"]).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(parameters.get("content", ""), encoding='utf-8')
            return ToolResult.success_result(
                call_id="",
                tool_name="create_file",
                result=f"Created file: {path}"
            )
        except Exception as e:
            raise ToolError(str(e), "create_file")


class ListDirectoryTool(ToolInterface):
    """列出目录工具"""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="list_directory",
            description="列出目录内容",
            parameters={
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "列出目录内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "目录路径，默认为当前目录",
                                "default": "."
                            }
                        }
                    }
                }
            }
        )
    
    def validate_params(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        return True, None
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            path = Path(parameters.get("path", ".")).expanduser()
            if not path.exists():
                return ToolResult.error_result(
                    call_id="", tool_name="list_directory",
                    error_message=f"Directory not found: {path}"
                )
            
            items = []
            for i in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                icon = "📁" if i.is_dir() else "📄"
                items.append(f"{icon} {i.name}")
            
            return ToolResult.success_result(
                call_id="",
                tool_name="list_directory",
                result=f"Contents of {path}:\n" + "\n".join(items[:50])
            )
        except Exception as e:
            raise ToolError(str(e), "list_directory")


class ReadFileTool(ToolInterface):
    """读取文件工具"""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="read_file",
            description="读取文件内容",
            parameters={
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "最大读取行数",
                                "default": 100
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        )
    
    def validate_params(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "path" not in parameters:
            return False, "Missing required parameter: path"
        return True, None
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            path = Path(parameters["path"]).expanduser()
            if not path.exists():
                return ToolResult.error_result(
                    call_id="", tool_name="read_file",
                    error_message=f"File not found: {path}"
                )
            
            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')
            limit = parameters.get("limit", 100)
            
            if len(lines) > limit:
                content = '\n'.join(lines[:limit]) + f"\n\n... ({len(lines) - limit} more lines)"
            
            return ToolResult.success_result(
                call_id="",
                tool_name="read_file",
                result=content
            )
        except Exception as e:
            raise ToolError(str(e), "read_file")


class ExecuteCommandTool(ToolInterface):
    """执行命令工具（带白名单）"""
    
    # 危险命令黑名单
    BLACKLIST = [
        "rm -rf /", "rm -rf /*", "rm -rf ~", 
        "> /dev/sda", "dd if=/dev/zero",
        "mkfs", "format", "del /f /s /q"
    ]
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="execute_command",
            description="执行 shell 命令（安全白名单模式）",
            parameters={
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "执行 shell 命令（安全白名单模式）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的命令"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "超时时间（秒）",
                                "default": 30
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        )
    
    def validate_params(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "command" not in parameters:
            return False, "Missing required parameter: command"
        
        command = parameters["command"]
        
        # 检查黑名单
        for dangerous in self.BLACKLIST:
            if dangerous in command:
                return False, f"Dangerous command detected: {dangerous}"
        
        return True, None
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        command = parameters["command"]
        timeout = parameters.get("timeout", 30)
        
        try:
            # 使用 asyncio 创建子进程
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult.error_result(
                    call_id="", tool_name="execute_command",
                    error_message=f"Command timeout after {timeout}s"
                )
            
            output = stdout.decode('utf-8', errors='replace')
            if stderr:
                output += "\n[stderr]\n" + stderr.decode('utf-8', errors='replace')
            
            return ToolResult.success_result(
                call_id="",
                tool_name="execute_command",
                result=output[:2000]  # 限制输出长度
            )
        except Exception as e:
            raise ToolError(str(e), "execute_command")


# ============================================================================
# 工具工厂
# ============================================================================

def create_default_registry() -> ToolRegistry:
    """创建默认工具注册表（包含所有内置工具）"""
    registry = ToolRegistry()
    
    # 注册内置工具
    registry.register(CreateFolderTool())
    registry.register(CreateFileTool())
    registry.register(ListDirectoryTool())
    registry.register(ReadFileTool())
    registry.register(ExecuteCommandTool())
    
    return registry
