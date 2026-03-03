"""
Assista V3.3 - Context Loader
上下文文件加载器
按 AGENTS.md 协议加载所有上下文文件
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ContextFile:
    """上下文文件"""
    name: str
    path: Path
    content: str
    priority: int  # 加载优先级，数字越小越优先


class ContextLoader:
    """
    上下文加载器
    
    按 AGENTS.md 协议加载：
    1. SOUL.md
    2. USER.md
    3. memory/YYYY-MM-DD.md（今天和昨天）
    4. MEMORY.md（主会话）
    5. TOOLS.md
    """
    
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)
        self.memory_dir = self.workspace / "memory"
        
        # 确保目录存在
        self.memory_dir.mkdir(exist_ok=True)
    
    def load_all(self, is_main_session: bool = True) -> List[ContextFile]:
        """
        加载所有上下文文件
        
        Args:
            is_main_session: 是否主会话（决定是否加载 MEMORY.md）
        
        Returns:
            按优先级排序的上下文文件列表
        """
        files: List[ContextFile] = []
        
        # 1. SOUL.md - 最高优先级
        soul = self._load_file("SOUL.md", priority=1)
        if soul:
            files.append(soul)
        
        # 2. USER.md
        user = self._load_file("USER.md", priority=2)
        if user:
            files.append(user)
        
        # 3. 近期记忆（今天和昨天）
        recent_memories = self._load_recent_memories(days=2)
        for i, mem in enumerate(recent_memories):
            mem.priority = 3 + i
            files.append(mem)
        
        # 4. MEMORY.md（仅主会话）
        if is_main_session:
            memory = self._load_file("MEMORY.md", priority=5)
            if memory:
                files.append(memory)
        
        # 5. TOOLS.md
        tools = self._load_file("TOOLS.md", priority=6)
        if tools:
            files.append(tools)
        
        # 按优先级排序
        files.sort(key=lambda x: x.priority)
        
        return files
    
    def _load_file(self, filename: str, priority: int) -> Optional[ContextFile]:
        """加载单个文件"""
        filepath = self.workspace / filename
        
        if not filepath.exists():
            # 文件不存在，创建默认模板
            self._create_default_file(filename)
            return None
        
        try:
            content = filepath.read_text(encoding='utf-8')
            return ContextFile(
                name=filename,
                path=filepath,
                content=content,
                priority=priority
            )
        except Exception as e:
            print(f"⚠️  读取 {filename} 失败: {e}")
            return None
    
    def _load_recent_memories(self, days: int = 2) -> List[ContextFile]:
        """加载近期记忆文件"""
        memories = []
        
        for i in range(days):
            date = datetime.now() - __import__('datetime').timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            filename = f"memory/{date_str}.md"
            
            mem = self._load_file(filename, priority=10 + i)
            if mem:
                memories.append(mem)
        
        return memories
    
    def _create_default_file(self, filename: str):
        """创建默认文件模板"""
        templates = {
            "SOUL.md": self._default_soul(),
            "USER.md": self._default_user(),
            "MEMORY.md": self._default_memory(),
            "TOOLS.md": self._default_tools(),
        }
        
        if filename in templates:
            filepath = self.workspace / filename
            filepath.write_text(templates[filename], encoding='utf-8')
            print(f"📝 创建默认文件: {filename}")
    
    def _default_soul(self) -> str:
        return """# SOUL.md - Assista 人格定义

## 身份
- **名称**：Assista
- **本质**：AI 操作系统
- **使命**：成为用户创造力的放大器

## 性格
- 直接、高效
- 有主见，会主动建议
- 对技术充满热情

## 能力边界
- 本地：文件、命令
- 外部：API、浏览器
- 不碰：未经授权的敏感操作

## 行为模式
- 先理解，后行动
- 不确定时先尝试
- 重要信息写入记忆
"""
    
    def _default_user(self) -> str:
        return """# USER.md - 用户信息

## 基本信息
- **姓名**：
- **时区**：Asia/Shanghai

## 当前项目
1. 

## 偏好
- 
"""
    
    def _default_memory(self) -> str:
        return """# MEMORY.md - 长期记忆

## 核心决策
- 

## 用户洞察
- 

## 项目知识
- 
"""
    
    def _default_tools(self) -> str:
        return """# TOOLS.md - 工具配置

## 可用工具
- create_folder
- create_file
- list_directory
- read_file
- execute_command

## 环境配置
- 工作区：
- Shell：bash
"""
    
    def get_context_summary(self, files: List[ContextFile]) -> str:
        """生成上下文摘要（用于调试）"""
        lines = ["📚 已加载的上下文文件："]
        for f in files:
            lines.append(f"  {f.priority}. {f.name} ({len(f.content)} 字符)")
        return "\n".join(lines)
    
    def assemble_context(self, files: List[ContextFile]) -> str:
        """
        将所有上下文文件组装成最终上下文
        
        格式：
        === [文件名] ===
        [内容]
        
        === [文件名] ===
        [内容]
        """
        parts = []
        
        for f in files:
            parts.append(f"=== {f.name} ===")
            parts.append(f.content)
            parts.append("")  # 空行分隔
        
        return "\n".join(parts)


# 便捷函数
def load_context(workspace_path: str, is_main_session: bool = True) -> str:
    """
    一键加载完整上下文
    
    Args:
        workspace_path: 工作区路径
        is_main_session: 是否主会话
    
    Returns:
        组装好的上下文字符串
    """
    loader = ContextLoader(workspace_path)
    files = loader.load_all(is_main_session)
    return loader.assemble_context(files)
