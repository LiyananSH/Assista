# Quick Start Guide

## 5 Minutes to Get Started with Assista

### Step 1: Start the Server

The development server is already running! Access it at:
```
http://localhost:5000
```

### Step 2: Try the Chat Interface

1. Open the web interface in your browser
2. In the Chat tab, type: "What's the current system status?"
3. Press Enter or click Send
4. Watch Assista analyze and respond

### Step 3: Explore System Monitoring

1. Click the "System" tab
2. View real-time CPU, memory, and disk usage
3. Click "Refresh System Stats" to update

### Step 4: Check Task History

1. Click the "Tasks" tab
2. See all operations Assista has performed
3. View task status and outputs

### Step 5: Set Up IM Integration (Optional)

For Telegram:
1. Create a Telegram bot via @BotFather
2. Get your bot token
3. Set webhook: `https://api.telegram.org/bot<token>/setWebhook?url=http://your-server:5000/api/webhook`

For Generic Webhooks:
1. Send POST request to `http://localhost:5000/api/webhook`
2. Format: `{"platform":"generic","from":{"id":"user123"},"text":"Hello","timestamp":1234567890}`

## Example Commands to Try

- "Show me the current directory"
- "List all running processes"
- "Check disk usage"
- "Create a file called test.txt"
- "What's the CPU model?"
- "How much memory is available?"

## Safety Tips

✅ Assista will ask for confirmation before dangerous operations
✅ Commands are limited to 30 seconds execution time
✅ Destructive commands like `rm -rf` require approval
✅ All actions are logged in the Tasks tab

## Getting Help

- Check the full README.md for detailed documentation
- All APIs are RESTful and return JSON
- Check browser console for frontend errors
- Check server logs for backend issues

## Next Steps

- Customize the system prompt in `src/app/api/chat/route.ts`
- Add more commands to `src/lib/system-command.ts`
- Integrate with your favorite IM platform
- Deploy to your own server

**That's it! You're ready to use Assista! 🎉**
