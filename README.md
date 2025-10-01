# Chirpy 🐦

An AI-powered Discord bot that uses the Groq API for intelligent conversations and responses. Chirpy uses Discord's slash commands (`bot.tree.command`) for a modern, user-friendly experience.

## Features

- 🤖 **AI-Powered Chat**: Engage in natural conversations using Groq's language models
- ⚡ **Slash Commands**: Modern Discord slash command interface
- 💬 **Conversation Memory**: Maintains conversation history per user
- 🛡️ **Error Handling**: Comprehensive error handling and logging
- 🎨 **Rich Embeds**: Beautiful Discord embeds for responses
- 🧹 **History Management**: Clear conversation history when needed

## Commands

- `/chat <message>` - Have a conversation with Chirpy
- `/clear` - Clear your conversation history
- `/info` - Get information about the bot
- `/ping` - Check bot responsiveness

## Setup

### Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- Groq API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/fishmeister1/Chirpy.git
   cd Chirpy
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your actual tokens:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   GROQ_API_KEY=your_groq_api_key_here
   BOT_PREFIX=!
   AI_MODEL=llama-3.1-70b-versatile
   ```

### Getting Your Tokens

#### Discord Bot Token

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Reset Token" and copy the token
5. Under "Privileged Gateway Intents", enable:
   - Message Content Intent (if you plan to read message content)

#### Groq API Key

1. Visit [Groq Console](https://console.groq.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key and copy it

### Bot Permissions

When inviting your bot to a server, make sure it has these permissions:

- `Send Messages`
- `Use Slash Commands`
- `Embed Links`
- `Read Message History`

**Invite Link Format:**
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=274877908992&scope=bot%20applications.commands
```

Replace `YOUR_BOT_CLIENT_ID` with your bot's client ID from the Discord Developer Portal.

## Running the Bot

```bash
python main.py
```

The bot will:
1. Load environment variables
2. Initialize the Groq client
3. Connect to Discord
4. Sync slash commands
5. Set its status and start responding to commands

## Configuration

### Available AI Models

You can change the AI model by updating the `AI_MODEL` environment variable. Some popular Groq models:

- `llama-3.1-70b-versatile` (default)
- `llama-3.1-8b-instant`
- `mixtral-8x7b-32768`
- `gemma-7b-it`

### Logging

The bot creates a `bot.log` file for debugging and monitoring. Log levels can be adjusted in the `main.py` file.

## File Structure

```
Chirpy/
├── main.py              # Main bot code
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Your actual environment variables (create this)
├── bot.log              # Log file (created when bot runs)
└── README.md           # This file
```

## Development

### Adding New Commands

To add a new slash command:

```python
@bot.tree.command(name="your_command", description="Command description")
@app_commands.describe(parameter="Parameter description")
async def your_command(interaction: discord.Interaction, parameter: str):
    await interaction.response.send_message(f"You said: {parameter}")
```

### Conversation History

The bot stores conversation history in memory. For production use, consider implementing:
- Database storage (PostgreSQL, MongoDB, etc.)
- Redis for caching
- Conversation history limits per user

## Troubleshooting

### Common Issues

1. **Bot doesn't respond to slash commands**
   - Ensure the bot has `applications.commands` scope
   - Check that slash commands are synced (check bot logs)

2. **Groq API errors**
   - Verify your API key is correct
   - Check your Groq account credits/limits
   - Ensure you're using a supported model

3. **Permission errors**
   - Verify bot has necessary permissions in the server
   - Check channel permissions

### Logs

Check `bot.log` for detailed error messages and debugging information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Feel free to use, modify, and distribute as needed.

## Support

If you encounter issues:
1. Check the troubleshooting section
2. Review the bot logs
3. Create an issue on GitHub with details

---

**Enjoy chatting with Chirpy!** 🐦✨