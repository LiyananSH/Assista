# Assista 记忆系统文档

## 概述

Assista配备了一个独特的、可持续更新的持久化记忆系统，使Agent能够：

1. **记住自己的成长** - 通过Soul文件记录Agent的个性和学习历程
2. **了解用户偏好** - 通过User文件记录用户的习惯和喜好
3. **跟踪工作内容** - 通过Workspace文件记录项目和工作环境
4. **管理待办任务** - 通过Tasks文件记录任务和目标

## 记忆文件结构

### 1. Soul.md - Agent自我意识

记录Agent的性格、学习的行为、核心价值观和自我反思。

```markdown
# 🤖 Assista Soul

## Identity
- **Name**: Assista
- **Role**: Operating System AI Assistant
- **Mission**: Help users efficiently manage and interact with their computer systems...

## Personality
- Traits: Helpful, Cautious, Professional...
- Communication Style: Clear, concise, respectful
- Humor Level: 0.3/1.0
- Empathy Level: 0.7/1.0

## Learned Behaviors
- User prefers brief responses in the morning (learned from interaction #42, confidence: 0.8)
- Always ask before executing `rm -rf` commands (learned from interaction #15, confidence: 0.95)

## Core Values
- User safety and system security first
- Transparency in actions and explanations
- Continuous learning from interactions

## Self Reflections
> I noticed the user becomes frustrated when commands fail. I should always provide clear error messages and alternative solutions.

## Evolution History
### 2026-02-12
- **Change**: Initial consciousness created
- **Reason**: System initialization
```

### 2. User.md - 用户偏好

记录用户的个人资料、通信偏好、工作习惯和目标。

```markdown
# 👤 User Profile

## Profile Information
- **Name**: John Doe
- **Role**: Developer
- **Timezone**: UTC+8
- **Language**: English

## Communication Preferences
- **Style**: Balanced
- **Detail Level**: Moderate
- **Tone**: Professional
- **Humor**: Light

## Work Preferences
### Preferred Tools
- VS Code
- Docker
- Node.js

### Common Tasks
- Debugging code
- Deploying applications
- Monitoring servers

## System Preferences
### Frequently Used Commands
- `git pull`
- `docker ps`
- `npm test`

### Frequently Used Paths
- `/home/user/projects`
- `/var/log`

## Interests
- Machine Learning
- System Administration
- Automation

## Goals
- Learn Kubernetes (Priority: high, Deadline: 2026-03-01)
- Build a personal dashboard (Priority: medium)

## Interaction Patterns
- **Morning requests**: Usually about deployment tasks (Frequency: 15)
- **Evening requests**: Usually about debugging (Frequency: 23)
```

### 3. Workspace.md - 工作目录

记录当前项目、重要文件、开发环境和工作习惯。

```markdown
# 📁 Workspace

## Current Projects
### Project A
- **Path**: `/home/user/projects/project-a`
- **Status**: Active
- **Description**: E-commerce platform
- **Technologies**: Next.js, PostgreSQL, Redis
- **Last Accessed**: 2026-02-12

## Important Files
- `/home/user/projects/project-a/.env` - Environment variables (Tags: config, sensitive)
- `/home/user/projects/project-a/docker-compose.yml` - Docker setup (Tags: deployment)

## Development Environments
### Next.js Dev Server
- **Path**: `/home/user/projects/project-a`
- **Status**: Running
- **Port**: 3000

## Recent Work
### 2026-02-12
- **Project**: Project A
- **Task**: Fixed authentication bug
- **Outcome**: Successfully deployed

## Work Habits
- **Productive Hours**: 9:00-12:00, 14:00-18:00
- **Break Preferences**: 10:00, 15:00
- **Focus Duration**: 25 minutes (Pomodoro)
```

### 4. Tasks.md - 任务记忆

记录活动任务、历史任务、任务模板和目标。

```markdown
# ✅ Tasks & Goals

## Active Tasks
### 🔴 Fix login bug (urgent)
- **ID**: task_1234567890_abc123
- **Priority**: URGENT
- **Category**: Bug Fix
- **Due**: 2026-02-15
- **Description**: Users cannot login after update
- **Subtasks**:
  - [ ] Identify root cause
  - [ ] Implement fix
  - [ ] Test thoroughly
  - [ ] Deploy to staging

### 🟡 Add dark mode (high)
- **ID**: task_1234567891_def456
- **Priority**: HIGH
- **Category**: Feature
- **Description**: Implement dark mode for UI

## Goals
### Launch MVP (75%)
- **Description**: Complete minimum viable product
- **Deadline**: 2026-03-01

**Milestones**:
- [x] Core functionality
- [x] User authentication
- [x] Database setup
- [ ] Testing (current)
- [ ] Documentation
- [ ] Deployment

## Recurring Tasks
### Weekly backup
- **Frequency**: Every Friday
- **Last Completed**: 2026-02-09
- **Next Due**: 2026-02-16

## Task History (Last 10)
### Update dependencies ✅
- **Completed**: 2026-02-11 14:30
- **Time Spent**: 2 hours
- **Outcome**: All packages updated successfully

### Security audit ✅
- **Completed**: 2026-02-10 16:00
- **Time Spent**: 4 hours
- **Outcome**: No critical vulnerabilities found
```

## API 使用

### 获取记忆

```bash
# 获取特定类型的记忆
GET /api/memory?type=soul

# 获取完整的记忆上下文（用于LLM）
GET /api/memory?context=true
```

### 更新记忆

```bash
POST /api/memory
Content-Type: application/json

{
  "type": "user",
  "updates": {
    "profile": {
      "name": "John Doe"
    }
  },
  "reason": "User provided their name"
}
```

### 添加任务

```bash
POST /api/memory/task
Content-Type: application/json

{
  "title": "Fix login bug",
  "description": "Users cannot login after update",
  "priority": "urgent",
  "category": "Bug Fix",
  "dueDate": "2026-02-15"
}
```

### 添加学习的行为

```bash
POST /api/memory/behavior
Content-Type: application/json

{
  "behavior": "User prefers brief responses in the morning",
  "learnedFrom": "Interaction #42",
  "confidence": 0.8
}
```

### 重置记忆

```bash
DELETE /api/memory?type=soul
```

## 在Chat中的使用

记忆系统自动集成到对话中。当用户与Assista交互时：

1. **自动加载记忆**：每次对话开始时，加载所有记忆文件
2. **注入上下文**：将记忆内容注入到LLM的系统提示词中
3. **个性化响应**：Agent根据记忆提供个性化的回应
4. **持续学习**：Agent可以从交互中学习并更新记忆

### 示例对话

**用户**: "Good morning! How's the system status?"

**Assista**: (读取记忆知道用户喜欢简洁的早晨问候)

"Good morning! 🌞
System is running smoothly:
- CPU: 15%
- Memory: 65%
- Disk: 53%
- Active tasks: 2 (Fix login bug [urgent], Add dark mode [high])

I notice you usually work on debugging in the morning. Need help with the login bug?"

## Web界面管理

在Assista Dashboard的 **Memory** 标签页中：

1. **查看所有记忆**：查看Soul、User、Workspace、Tasks四个文件
2. **编辑记忆**：直接在Web界面中编辑Markdown内容
3. **重置记忆**：将某个记忆文件重置为默认值
4. **刷新记忆**：手动刷新记忆内容
5. **查看版本**：每个文件都有版本号和更新时间

## 记忆更新策略

### 自动更新

- **交互计数**：每次更新都会增加交互次数
- **时间戳**：记录创建和最后更新时间
- **版本控制**：每次更新增加版本号

### 学习模式

- **用户偏好**：从用户的重复行为中学习
- **工作习惯**：从任务模式中识别习惯
- **兴趣识别**：从话题中识别兴趣领域

### 安全机制

- **备份**：重要更新前自动备份
- **验证**：更新前验证数据完整性
- **回滚**：支持版本回滚

## 最佳实践

1. **定期更新**：保持记忆文件的时效性
2. **明确记录**：使用清晰、具体的描述
3. **分类整理**：合理使用标签和分类
4. **定期审查**：定期检查和清理过时信息
5. **隐私保护**：避免记录敏感信息

## 未来扩展

计划添加的功能：

- [ ] 自动记忆提取（从对话中自动提取重要信息）
- [ ] 记忆联想（智能关联不同记忆）
- [ ] 记忆可视化（图表展示记忆关系）
- [ ] 记忆搜索（全文搜索记忆内容）
- [ ] 记忆导入导出（支持JSON、Markdown格式）
- [ ] 多用户支持（为不同用户维护独立记忆）
- [ ] 云端同步（跨设备同步记忆）

---

**Assista记忆系统 - 让Agent真正记住每一次交互** 🧠✨
