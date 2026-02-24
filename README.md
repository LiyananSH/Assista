# Assista - Operating System AI Assistant

Assista is an advanced operating system-level personal AI assistant that helps you manage your computer system through natural language conversations. Similar to Apple's Siri but for system administration, Assista can execute commands, monitor system health, and automate tasks - all through your favorite IM platform or web interface.

## 🚀 Features

- **AI-Powered Conversations**: Natural language interface powered by advanced LLM models
- **System Command Execution**: Safely execute system commands with intelligent risk assessment
- **Multi-Platform IM Support**: Integrate with Telegram, WeChat, Feishu, and generic webhooks
- **Real-Time System Monitoring**: Track CPU, memory, disk usage, and running processes
- **Task Management**: Track all operations with detailed history and status
- **Web Dashboard**: Modern, responsive UI for monitoring and control
- **Safety First**: Dangerous operations require confirmation before execution

## 📋 Prerequisites

- Node.js 24+
- pnpm (package manager)
- Linux-based operating system (tested on Ubuntu/Debian)

## 🛠️ Installation

1. **Clone and install dependencies**:
   ```bash
   pnpm install
   ```

2. **Start the development server**:
   ```bash
   coze dev
   ```

   The server will start on `http://localhost:5000`

## 🎯 Usage

### Web Interface

1. Open your browser and navigate to `http://localhost:5000`
2. Start chatting with Assista in the Chat tab
3. Monitor system health in the System tab
4. View task history in the Tasks tab

### IM Integration

Configure your IM platform's webhook to point to:
```
http://your-server:5000/api/webhook
```

**Telegram**:
```json
{
  "message": {
    "from": { "id": "123", "first_name": "John" },
    "text": "What's the system load?",
    "date": 1234567890
  }
}
```

**WeChat/Feishu**:
```json
{
  "event_type": "message",
  "event": {
    "sender": { "sender_id": { "user_id": "123" }, "sender_name": "John" },
    "content": { "text": "List running processes" },
    "create_time": 1234567890
  }
}
```

**Generic**:
```json
{
  "platform": "generic",
  "from": { "id": "123", "name": "John" },
  "text": "Check disk usage",
  "timestamp": 1234567890
}
```

## 💬 Example Conversations

**System Information**:
```
User: What's the current system status?
Assista: I'll check the system status for you.
Command completed. Result: CPU usage is low, memory at 65%, and disk at 53%.
```

**File Operations**:
```
User: Create a file called test.txt with "Hello World"
Assista: I'll execute: `echo 'Hello World' > test.txt` to create the file.
Command completed. Result: File created successfully.
```

**Process Management**:
```
User: Show me running processes
Assista: I'll execute: `ps aux | head -n 20` to show running processes.
Command completed. Result: [process list]
```

**Python Execution**:
```
User: Run a Python script to calculate fibonacci of 10
Assista: I'll create and execute a Python script for you.
Command completed. Result: 55
```

## 🔒 Safety Features

- **Command Whitelist**: Only pre-approved commands can be executed
- **Dangerous Operation Detection**: Automatically flags destructive operations
- **Confirmation Required**: Dangerous commands need user approval
- **Execution Timeout**: Commands are limited to 30 seconds
- **Error Handling**: Comprehensive error reporting

## 📊 API Endpoints

### Chat API
```
POST /api/chat
Content-Type: application/json

{
  "messages": [
    { "role": "user", "content": "Hello" }
  ]
}
```
Returns: Stream of AI responses

### System Operations API
```
POST /api/system/execute
Content-Type: application/json

{
  "action": "execute|systemInfo|processList|searchFiles|...",
  "params": { ... }
}
```

### Task Management API
```
GET /api/tasks?limit=20
POST /api/tasks
PUT /api/tasks
DELETE /api/tasks?taskId=xxx
```

### Conversation API
```
GET /api/conversations?userId=xxx
POST /api/conversations
DELETE /api/conversations?userId=xxx
```

### Webhook API
```
POST /api/webhook
GET /api/webhook?challenge=xxx
```

## 🎨 UI Features

- **Dark Theme**: Modern, eye-friendly dark interface
- **Real-time Updates**: Live task status and system monitoring
- **Responsive Design**: Works on desktop and mobile
- **Tab-based Navigation**: Easy switching between Chat, System, and Tasks
- **Status Badges**: Visual indicators for task completion

## 🔧 Configuration

### Environment Variables (Optional)
- `NEXT_PUBLIC_BASE_URL`: Base URL for API calls (default: `http://localhost:5000`)

### Safety Settings
- Command execution timeout: 30 seconds
- Conversation history retention: 20 messages per user
- Data retention: 7 days (auto-cleanup)

## 📈 Monitoring

- **Task Statistics**: Track total, completed, and failed tasks
- **Conversation Tracking**: Monitor user interactions
- **System Metrics**: Real-time CPU, memory, and disk usage
- **Process Monitoring**: View and manage running processes

## 🚧 Development

### Project Structure
```
src/
├── app/
│   ├── api/
│   │   ├── chat/          # AI chat endpoint
│   │   ├── system/        # System operations
│   │   ├── tasks/         # Task management
│   │   ├── conversations/ # Chat history
│   │   └── webhook/       # IM integration
│   └── page.tsx           # Main dashboard UI
├── components/ui/         # shadcn/ui components
└── lib/
    ├── system-command.ts  # Command execution logic
    └── task-manager.ts    # Task management logic
```

### Available Scripts
```bash
pnpm dev          # Start development server
pnpm build        # Build for production
pnpm start        # Start production server
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📝 License

This project is part of the Assista ecosystem.

## 🙏 Acknowledgments

- Built with Next.js 16 and React 19
- UI powered by shadcn/ui
- AI powered by Coze Coding SDK
- Inspired by Apple's Siri and system administration needs

## 📞 Support

For issues and questions, please check the documentation or create an issue.

---

**Assista - Your Personal AI System Administrator** 🤖💻
