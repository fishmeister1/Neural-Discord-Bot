import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from groq import Groq
from dotenv import load_dotenv
import asyncio
import random
from supabase import create_client, Client

# Load local environment variables as fallback
load_dotenv()

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SupabaseConfig:
    """Handle environment variables from Supabase with local fallback"""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.storage_mode = os.getenv('ENV_STORAGE_MODE', 'local')
        self.supabase: Client = None
        self._env_cache = {}
        
        if self.storage_mode == 'supabase' and self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                logger.info("Falling back to local environment variables")
                self.storage_mode = 'local'
    
    async def get_env_var(self, key: str, default: str = None) -> str:
        """Get environment variable from Supabase or local fallback"""
        
        # Check cache first
        if key in self._env_cache:
            return self._env_cache[key]
        
        if self.storage_mode == 'supabase' and self.supabase:
            try:
                # Try to get from Supabase environment_variables table
                response = self.supabase.table('environment_variables').select('value').eq('key', key).execute()
                
                if response.data and len(response.data) > 0:
                    value = response.data[0]['value']
                    self._env_cache[key] = value
                    return value
                else:
                    logger.warning(f"Environment variable '{key}' not found in Supabase, using local fallback")
            except Exception as e:
                logger.error(f"Error fetching {key} from Supabase: {e}")
        
        # Fallback to local environment variables
        value = os.getenv(key, default)
        if value:
            self._env_cache[key] = value
        return value
    
    def get_env_var_sync(self, key: str, default: str = None) -> str:
        """Synchronous version for initialization - only uses local env vars"""
        return os.getenv(key, default)
    
    async def set_env_var(self, key: str, value: str) -> bool:
        """Set environment variable in Supabase (if available)"""
        if self.storage_mode == 'supabase' and self.supabase:
            try:
                # Upsert the environment variable
                response = self.supabase.table('environment_variables').upsert({
                    'key': key,
                    'value': value
                }).execute()
                
                # Update cache
                self._env_cache[key] = value
                logger.info(f"Successfully updated environment variable '{key}' in Supabase")
                return True
            except Exception as e:
                logger.error(f"Failed to set {key} in Supabase: {e}")
        
        logger.warning(f"Cannot set environment variable '{key}' - Supabase not available")
        return False
    
    def clear_cache(self):
        """Clear the environment variable cache"""
        self._env_cache.clear()
    
    async def get_user_conversation(self, user_id: int) -> list:
        """Get user's conversation history from Supabase"""
        if self.storage_mode != 'supabase' or not self.supabase:
            return []
        
        try:
            response = self.supabase.table('user_conversations')\
                .select('messages')\
                .eq('user_id', str(user_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                messages = response.data[0]['messages']
                logger.info(f"Retrieved {len(messages)} messages for user {user_id}")
                return messages
            else:
                logger.info(f"No conversation history found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving conversation for user {user_id}: {e}")
            return []
    
    async def save_user_conversation(self, user_id: int, messages: list) -> bool:
        """Save user's conversation history to Supabase"""
        if self.storage_mode != 'supabase' or not self.supabase:
            return False
        
        try:
            # Upsert the conversation
            response = self.supabase.table('user_conversations').upsert({
                'user_id': str(user_id),
                'messages': messages,
                'updated_at': 'now()'
            }).execute()
            
            logger.info(f"Successfully saved conversation for user {user_id} ({len(messages)} messages)")
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation for user {user_id}: {e}")
            return False
    
    async def clear_user_conversation(self, user_id: int) -> bool:
        """Clear user's conversation history from Supabase"""
        if self.storage_mode != 'supabase' or not self.supabase:
            return False
        
        try:
            response = self.supabase.table('user_conversations')\
                .delete()\
                .eq('user_id', str(user_id))\
                .execute()
            
            logger.info(f"Successfully cleared conversation for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing conversation for user {user_id}: {e}")
            return False

# Initialize configuration
config = SupabaseConfig()

class NeuralBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix=config.get_env_var_sync('BOT_PREFIX', '!'),
            intents=intents,
            help_command=None
        )
        
        # Initialize with local env vars for now, will be updated in setup_hook
        self.groq_client = None
        self.ai_model = None
        self.config_loaded = False
        
        # Store conversation history (local cache + Supabase)
        self.conversations = {}  # Local cache for performance
        
        # AI response embed colors
        self.embed_colors = [
            0x87CEEB,  # Light blue
            0xDDA0DD,  # Light purple (plum)
            0x9370DB,  # Purple (medium slate blue)
            0x40E0D0   # Light turquoise
        ]
    
    def get_random_embed_color(self):
        """Get a random color for AI response embeds"""
        return random.choice(self.embed_colors)
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            # Load configuration from Supabase
            await self.load_configuration()
            
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def load_configuration(self):
        """Load configuration from Supabase with fallback to local env"""
        try:
            logger.info("Loading configuration...")
            
            # Get Groq API key
            groq_api_key = await config.get_env_var('GROQ_API_KEY')
            if not groq_api_key:
                raise ValueError("GROQ_API_KEY not found in configuration")
            
            # Initialize Groq client
            self.groq_client = Groq(api_key=groq_api_key)
            
            # Get AI model
            self.ai_model = await config.get_env_var('AI_MODEL', 'llama-3.1-70b-versatile')
            
            self.config_loaded = True
            logger.info(f"Configuration loaded successfully. Using AI model: {self.ai_model}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.info("Falling back to local environment variables...")
            
            # Fallback to local env vars
            groq_api_key = os.getenv('GROQ_API_KEY')
            if groq_api_key:
                self.groq_client = Groq(api_key=groq_api_key)
                self.ai_model = os.getenv('AI_MODEL', 'llama-3.1-70b-versatile')
                self.config_loaded = True
                logger.info("Fallback configuration loaded successfully")
            else:
                logger.error("No GROQ_API_KEY found in local environment either!")
                raise
    
    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        logger.info(f'{self.user} has landed!')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/chat"
            )
        )
    
    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        
        logger.error(f"Command error: {error}")
        
        if ctx.interaction:
            await ctx.interaction.response.send_message(
                "❌ An error occurred while processing your command.",
                ephemeral=True
            )
    
    async def get_ai_response(self, user_id: int, message: str) -> str:
        """Get AI response from Groq API with Supabase conversation storage"""
        try:
            # Get or load conversation history for user
            if user_id not in self.conversations:
                # Try to load from Supabase first
                saved_conversation = await config.get_user_conversation(user_id)
                
                if saved_conversation:
                    self.conversations[user_id] = saved_conversation
                    logger.info(f"Loaded conversation history for user {user_id} from Supabase")
                else:
                    # Create new conversation with system message
                    self.conversations[user_id] = [
                        {
                            "role": "system",
                            "content": (
                                "You are Neural, an intelligent and helpful Discord bot. "
                                "You're enthusiastic and always try to be helpful. "
                                "Keep responses concise but informative. "
                                "If someone asks about your capabilities, mention that you can chat, "
                                "help with questions, and provide information on various topics."
                            )
                        }
                    ]
            
            # Add user message to conversation
            self.conversations[user_id].append({
                "role": "user",
                "content": message
            })
            
            # Keep conversation history manageable (last 20 messages + system message)
            if len(self.conversations[user_id]) > 21:  # 1 system + 20 messages
                self.conversations[user_id] = (
                    [self.conversations[user_id][0]] +  # Keep system message
                    self.conversations[user_id][-20:]   # Keep last 20 messages
                )
            
            # Get response from Groq
            chat_completion = self.groq_client.chat.completions.create(
                messages=self.conversations[user_id],
                model=self.ai_model,
                max_tokens=1000,
                temperature=0.7
            )
            
            ai_response = chat_completion.choices[0].message.content
            
            # Add AI response to conversation history
            self.conversations[user_id].append({
                "role": "assistant",
                "content": ai_response
            })
            
            # Save updated conversation to Supabase (async, don't wait)
            asyncio.create_task(config.save_user_conversation(user_id, self.conversations[user_id]))
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return "🤔 Sorry, I'm having trouble thinking right now. Please try again in a moment!"

# Initialize bot
bot = NeuralBot()

@bot.tree.command(name="ask", description="Ask Neural anything!")
@app_commands.describe(message="What would you like to talk about?")
async def chat(interaction: discord.Interaction, message: str):
    """Main chat command using Groq AI"""
    await interaction.response.defer()
    
    try:
        # Get AI response
        ai_response = await bot.get_ai_response(interaction.user.id, message)
        
        # Create embed for response
        embed = discord.Embed(
            description=ai_response,
            color=bot.get_random_embed_color()
        )
        embed.set_footer(text=f"✦ Neural Response")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Chat command error: {e}")
        await interaction.followup.send(
            "❌ Something went wrong while processing your message. Please try again!",
            ephemeral=True
        )

@bot.tree.command(name="clear", description="Clear your conversation history with Neural")
async def clear_history(interaction: discord.Interaction):
    """Clear user's conversation history from both local cache and Supabase"""
    user_id = interaction.user.id
    
    # Clear from local cache
    local_cleared = user_id in bot.conversations
    if local_cleared:
        del bot.conversations[user_id]
    
    # Clear from Supabase
    supabase_cleared = await config.clear_user_conversation(user_id)
    
    if local_cleared or supabase_cleared:
        embed = discord.Embed(
            title="✅ History Cleared",
            description="Your conversation history has been cleared! 🧹",
            color=0x00ff88
        )
        
        details = []
        if local_cleared:
            details.append("• Local cache cleared")
        if supabase_cleared:
            details.append("• Supabase records cleared")
        
        if details:
            embed.add_field(
                name="Cleared from:",
                value="\n".join(details),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(
            "🤷 You don't have any conversation history to clear!",
            ephemeral=True
        )

@bot.tree.command(name="help", description="Get information about Neural")
async def bot_info(interaction: discord.Interaction):
    """Display bot information"""
    embed = discord.Embed(
        title="About Neural",
        description="I'm an AI-powered Discord bot ready to chat and help!",
        color=0x00ff88
    )
    
    embed.add_field(
        name="🤖 AI Model",
        value=f"`{bot.ai_model}`",
        inline=True
    )
    
    embed.add_field(
        name="📊 Servers",
        value=f"`{len(bot.guilds)}`",
        inline=True
    )
    
    embed.add_field(
        name="👥 Users",
        value=f"`{len(bot.users)}`",
        inline=True
    )
    
    embed.add_field(
        name="💬 Commands",
        value=(
            "`/chat` - Have a conversation with me\n"
            "`/clear` - Clear your chat history\n"
            "`/info` - Show this information\n"
            "`/ping` - Check if I'm responsive"
        ),
        inline=False
    )
    
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check if Neural is responsive")
async def ping(interaction: discord.Interaction):
    """Simple ping command"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: `{latency}ms`",
        color=0x00ff88
    )
    
    await interaction.response.send_message(embed=embed)

# Error handler for app commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors"""
    logger.error(f"Slash command error: {error}")
    
    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ An error occurred while processing your command.",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            "❌ An error occurred while processing your command.",
            ephemeral=True
        )

async def main():
    """Main function to run the bot"""
    try:
        # Get Discord token (try Supabase first, then local env)
        discord_token = await config.get_env_var('DISCORD_TOKEN')
        
        if not discord_token:
            logger.error("DISCORD_TOKEN not found in configuration!")
            return
        
        logger.info("Starting Neural bot with Supabase configuration...")
        await bot.start(discord_token)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        
        # Fallback to local environment
        logger.info("Trying fallback with local environment variables...")
        token = os.getenv('DISCORD_TOKEN')
        
        if not token:
            logger.error("DISCORD_TOKEN not found in local environment either!")
            return
        
        try:
            await bot.start(token)
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")

if __name__ == "__main__":
    asyncio.run(main())
