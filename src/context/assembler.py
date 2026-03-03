"""
Assista V3.3 - Context Assembler
上下文组装器
将加载的上下文组装成 LLM 可用的格式
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .loader import ContextFile, ContextLoader


@dataclass
class AssembledContext:
    """组装好的上下文"""
    system_prompt: str      # 系统提示词（人格+能力定义）
    user_profile: str       # 用户信息
    recent_history: str     # 近期记忆
    longterm_memory: str    # 长期记忆（可选）
    tool_definitions: str   # 工具定义
    
    def to_messages(self) -> List[Dict[str, str]]:
        """
        转换为 LLM 消息格式
        
        返回：
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ]
        """
        # 组装系统提示词
        system_content = f"""{self.system_prompt}

=== 用户信息 ===
{self.user_profile}

=== 近期记忆 ===
{self.recent_history}
"""
        
        if self.longterm_memory:
            system_content += f"\n=== 长期记忆 ===\n{self.longterm_memory}\n"
        
        system_content += f"""
=== 可用工具 ===
{self.tool_definitions}

现在开始对话。"""
        
        return [
            {"role": "system", "content": system_content}
        ]


class ContextAssembler:
    """
    上下文组装器
    
    将 ContextLoader 加载的文件组装成结构化上下文
    """
    
    def __init__(self, loader: ContextLoader):
        self.loader = loader
    
    def assemble(self, is_main_session: bool = True) -> AssembledContext:
        """
        组装完整上下文
        
        Args:
            is_main_session: 是否主会话（决定是否加载长期记忆）
        
        Returns:
            组装好的上下文对象
        """
        files = self.loader.load_all(is_main_session)
        
        # 按类型分类
        soul_content = ""
        user_content = ""
        recent_content = ""
        longterm_content = ""
        tools_content = ""
        
        for f in files:
            if f.name == "SOUL.md":
                soul_content = f.content
            elif f.name == "USER.md":
                user_content = f.content
            elif f.name.startswith("memory/"):
                recent_content += f"\n{f.content}\n"
            elif f.name == "MEMORY.md":
                longterm_content = f.content
            elif f.name == "TOOLS.md":
                tools_content = f.content
        
        return AssembledContext(
            system_prompt=soul_content,
            user_profile=user_content,
            recent_history=recent_content,
            longterm_memory=longterm_content if is_main_session else "",
            tool_definitions=tools_content
        )
    
    def assemble_minimal(self) -> str:
        """
        组装最小上下文（仅核心信息）
        
        用于快速响应或资源受限场景
        """
        files = self.loader.load_all(is_main_session=False)
        
        # 只取 SOUL.md 和 USER.md
        parts = []
        for f in files:
            if f.name in ["SOUL.md", "USER.md"]:
                parts.append(f.content)
        
        return "\n\n".join(parts)
    
    def assemble_with_query(self, query: str, is_main_session: bool = True) -> AssembledContext:
        """
        根据查询组装相关上下文（未来支持 RAG）
        
        当前简化实现：加载全部，未来可基于 query 筛选相关记忆
        """
        return self.assemble(is_main_session)


# 便捷函数
def create_assembler(workspace_path: str) -> ContextAssembler:
    """创建组装器实例"""
    loader = ContextLoader(workspace_path)
    return ContextAssembler(loader)
