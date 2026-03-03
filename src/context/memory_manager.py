"""
Assista V3.3 - Memory Manager
记忆管理系统
创建、更新、遗忘
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class MemoryEntry:
    """记忆条目"""
    timestamp: str
    category: str  # decision / insight / todo / conversation
    content: str
    importance: int  # 1-5，5 最重要
    tags: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        return cls(**data)


class MemoryManager:
    """
    记忆管理器
    
    管理三级记忆：
    - 工作记忆：当前会话（内存）
    - 短期记忆：每日文件（memory/YYYY-MM-DD.md）
    - 长期记忆：精选记忆（MEMORY.md）
    
    遗忘机制：
    - 遗忘对象：临时操作 + 闲聊（importance <= 2）
    - 触发条件：定时（30天）+ 容量上限（单文件100KB）
    - 防误删：重要性评分 + 关键词保护
    """
    
    # 遗忘配置
    FORGET_DAYS = 30              # 30天前的记忆可遗忘
    MAX_FILE_SIZE = 100 * 1024    # 单文件最大100KB
    MIN_IMPORTANCE = 3            # 重要性低于3的可遗忘
    
    # 保护关键词（包含这些的记忆不遗忘）
    PROTECTED_KEYWORDS = [
        "偏好", "喜欢", "目标", "决策", "决定",
        "重要", "关键", "约定", "规则", "记住"
    ]
    
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)
        self.memory_dir = self.workspace / "memory"
        self.memory_dir.mkdir(exist_ok=True)
        
        # 工作记忆（当前会话）
        self.working_memory: List[MemoryEntry] = []
    
    def should_forget_entry(self, entry: MemoryEntry) -> bool:
        """
        判断是否应该遗忘单条记忆
        
        遗忘规则：
        1. 重要性 <= 2
        2. 不包含保护关键词
        3. 超过30天
        """
        # 检查重要性
        if entry.importance >= self.MIN_IMPORTANCE:
            return False
        
        # 检查保护关键词
        content_lower = entry.content.lower()
        for keyword in self.PROTECTED_KEYWORDS:
            if keyword in content_lower:
                return False
        
        # 检查时间
        try:
            entry_date = datetime.fromisoformat(entry.timestamp)
            age = datetime.now() - entry_date
            if age.days < self.FORGET_DAYS:
                return False
        except:
            pass
        
        return True
    
    # ==================== 创建记忆 ====================
    
    def add(self, content: str, category: str = "insight", 
            importance: int = 3, tags: List[str] = None) -> MemoryEntry:
        """
        添加新记忆
        
        Args:
            content: 记忆内容
            category: 类型（decision/insight/todo/conversation）
            importance: 重要程度 1-5
            tags: 标签列表
        """
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            category=category,
            content=content,
            importance=importance,
            tags=tags or []
        )
        
        # 写入工作记忆
        self.working_memory.append(entry)
        
        # 自动写入今日记忆文件
        self._write_to_daily(entry)
        
        return entry
    
    def _write_to_daily(self, entry: MemoryEntry):
        """写入每日记忆文件"""
        today_file = self._get_today_file()
        
        # 读取现有内容
        if today_file.exists():
            content = today_file.read_text(encoding='utf-8')
        else:
            content = f"# {datetime.now().strftime('%Y-%m-%d')}.md - 今日记忆\n\n"
        
        # 追加新记忆
        timestamp = datetime.fromisoformat(entry.timestamp).strftime("%H:%M")
        new_entry = f"\n## {timestamp} [{entry.category.upper()}]\n\n{entry.content}\n"
        if entry.tags:
            new_entry += f"\n标签: {', '.join(entry.tags)}\n"
        
        content += new_entry
        
        # 写回文件
        today_file.write_text(content, encoding='utf-8')
    
    def _get_today_file(self) -> Path:
        """获取今日记忆文件路径"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.memory_dir / f"{date_str}.md"
    
    # ==================== 读取记忆 ====================
    
    def get_working_memory(self, limit: int = 10) -> List[MemoryEntry]:
        """获取工作记忆（当前会话）"""
        return self.working_memory[-limit:]
    
    def get_daily_memory(self, date: Optional[datetime] = None) -> str:
        """获取指定日期的记忆"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        memory_file = self.memory_dir / f"{date_str}.md"
        
        if memory_file.exists():
            return memory_file.read_text(encoding='utf-8')
        return ""
    
    def get_recent_memories(self, days: int = 7) -> List[str]:
        """获取最近 N 天的记忆"""
        memories = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            mem = self.get_daily_memory(date)
            if mem:
                memories.append(mem)
        
        return memories
    
    # ==================== 更新长期记忆 ====================
    
    def consolidate_to_longterm(self, entries: List[MemoryEntry]):
        """
        将重要记忆整理到长期记忆（MEMORY.md）
        
        通常由定期任务调用（如每天结束时）
        """
        memory_file = self.workspace / "MEMORY.md"
        
        # 筛选重要记忆（importance >= 4）
        important = [e for e in entries if e.importance >= 4]
        
        if not important:
            return
        
        # 读取现有长期记忆
        if memory_file.exists():
            content = memory_file.read_text(encoding='utf-8')
        else:
            content = "# MEMORY.md - 长期记忆\n\n"
        
        # 追加重要记忆
        content += f"\n## {datetime.now().strftime('%Y-%m-%d')} 整理\n\n"
        for entry in important:
            content += f"- [{entry.category}] {entry.content}\n"
        
        memory_file.write_text(content, encoding='utf-8')
        print(f"📝 已整理 {len(important)} 条记忆到长期记忆")
    
    # ==================== 遗忘机制 ====================
    
    def should_forget(self, entry: MemoryEntry, days_old: int = 30) -> bool:
        """
        判断是否应该遗忘
        
        遗忘规则：
        - 超过 30 天的低重要性记忆（importance <= 2）
        - 已完成的临时任务
        - 用户明确说"忘了"的内容
        """
        entry_date = datetime.fromisoformat(entry.timestamp)
        age = datetime.now() - entry_date
        
        # 低重要性且过期
        if entry.importance <= 2 and age.days > days_old:
            return True
        
        # 已完成的临时任务
        if entry.category == "todo" and entry.content.startswith("[已完成]"):
            return True
        
        return False
    
    def cleanup_old_memories(self, days: int = None):
        """
        智能清理过期记忆
        
        策略：
        1. 删除超过 FORGET_DAYS 天的低重要性记忆
        2. 保留包含保护关键词的记忆
        3. 大文件（>MAX_FILE_SIZE）时触发紧急清理
        """
        if days is None:
            days = self.FORGET_DAYS
        
        cutoff = datetime.now() - timedelta(days=days)
        deleted_files = 0
        cleaned_entries = 0
        
        for mem_file in self.memory_dir.glob("*.md"):
            try:
                # 解析文件日期
                date_str = mem_file.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # 读取内容
                content = mem_file.read_text(encoding='utf-8')
                
                # 检查文件大小
                file_size = mem_file.stat().st_size
                is_urgent = file_size > self.MAX_FILE_SIZE
                
                # 如果文件很新且不大，跳过
                if file_date >= cutoff and not is_urgent:
                    continue
                
                # 解析并过滤记忆条目
                lines = content.split('\n')
                kept_lines = []
                in_entry = False
                entry_buffer = []
                
                for line in lines:
                    # 检测记忆条目开始（## 时间戳 [类型]）
                    if re.match(r'^## \d{2}:\d{2} \[', line):
                        # 处理上一个条目
                        if entry_buffer:
                            if self._should_keep_entry(entry_buffer, cutoff, is_urgent):
                                kept_lines.extend(entry_buffer)
                            else:
                                cleaned_entries += 1
                        
                        in_entry = True
                        entry_buffer = [line]
                    elif in_entry:
                        entry_buffer.append(line)
                    else:
                        # 非条目内容（标题等）保留
                        kept_lines.append(line)
                
                # 处理最后一个条目
                if entry_buffer:
                    if self._should_keep_entry(entry_buffer, cutoff, is_urgent):
                        kept_lines.extend(entry_buffer)
                    else:
                        cleaned_entries += 1
                
                # 写回文件或删除空文件
                new_content = '\n'.join(kept_lines).strip()
                if new_content and len(new_content) > 50:  # 保留有意义的文件
                    mem_file.write_text(new_content, encoding='utf-8')
                else:
                    mem_file.unlink()
                    deleted_files += 1
                    
            except Exception as e:
                print(f"⚠️  清理 {mem_file} 时出错: {e}")
                continue
        
        # 输出结果
        if cleaned_entries > 0 or deleted_files > 0:
            print(f"🧹 遗忘完成：清理 {cleaned_entries} 条记忆，删除 {deleted_files} 个空文件")
    
    def _should_keep_entry(self, entry_lines: List[str], cutoff: datetime, is_urgent: bool) -> bool:
        """判断是否应该保留记忆条目"""
        entry_text = '\n'.join(entry_lines)
        
        # 提取时间戳
        time_match = re.search(r'## (\d{2}:\d{2})', entry_lines[0])
        if time_match:
            time_str = time_match.group(1)
            # 构建完整时间（假设是今天的，实际应该用文件日期+时间）
            # 简化处理：检查是否包含保护关键词
            pass
        
        # 检查保护关键词
        entry_lower = entry_text.lower()
        for keyword in self.PROTECTED_KEYWORDS:
            if keyword in entry_lower:
                return True
        
        # 检查重要性标记
        if '[INSIGHT]' in entry_text or '[DECISION]' in entry_text:
            return True
        
        # 紧急清理时更激进
        if is_urgent:
            # 只保留高重要性
            if '[ACTION]' in entry_text or '[CONVERSATION]' in entry_text:
                return False
        
        return True
    
    def forget_by_user_request(self, keyword: str) -> int:
        """
        用户主动要求遗忘
        
        Args:
            keyword: 要遗忘的内容关键词
        
        Returns:
            删除的记忆条数
        """
        deleted = 0
        
        for mem_file in self.memory_dir.glob("*.md"):
            try:
                content = mem_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                kept_lines = []
                entry_buffer = []
                
                for line in lines:
                    if re.match(r'^## \d{2}:\d{2} \[', line):
                        if entry_buffer:
                            entry_text = '\n'.join(entry_buffer)
                            if keyword.lower() not in entry_text.lower():
                                kept_lines.extend(entry_buffer)
                            else:
                                deleted += 1
                                print(f"🗑️  遗忘: {entry_buffer[0][:50]}...")
                        entry_buffer = [line]
                    elif entry_buffer:
                        entry_buffer.append(line)
                    else:
                        kept_lines.append(line)
                
                # 处理最后一个条目
                if entry_buffer:
                    entry_text = '\n'.join(entry_buffer)
                    if keyword.lower() not in entry_text.lower():
                        kept_lines.extend(entry_buffer)
                    else:
                        deleted += 1
                
                # 写回
                new_content = '\n'.join(kept_lines).strip()
                if new_content:
                    mem_file.write_text(new_content, encoding='utf-8')
                else:
                    mem_file.unlink()
                    
            except Exception as e:
                print(f"⚠️  处理 {mem_file} 时出错: {e}")
        
        if deleted > 0:
            print(f"✅ 已遗忘 {deleted} 条包含 '{keyword}' 的记忆")
        else:
            print(f"ℹ️  未找到包含 '{keyword}' 的记忆")
        
        return deleted
    
    # ==================== 搜索记忆 ====================
    
    def search(self, query: str, days: int = 30) -> List[MemoryEntry]:
        """
        简单关键词搜索记忆
        
        未来可升级为向量检索
        """
        results = []
        query_lower = query.lower()
        
        # 搜索工作记忆
        for entry in self.working_memory:
            if query_lower in entry.content.lower():
                results.append(entry)
        
        # 搜索近期每日记忆（简化实现）
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            mem_content = self.get_daily_memory(date)
            
            if query_lower in mem_content.lower():
                # 简化处理：找到包含关键词的行
                for line in mem_content.split('\n'):
                    if query_lower in line.lower():
                        entry = MemoryEntry(
                            timestamp=date.isoformat(),
                            category="search_result",
                            content=line.strip(),
                            importance=3,
                            tags=["search"]
                        )
                        results.append(entry)
        
        return results
