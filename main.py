"""
Telegram Prompt Engineering Bot

This bot helps users optimize their prompts using 
different methodologies (CRAFT, LYRA) by interacting 
with LLMs (OpenAI or OpenRouter).

Main responsibilities:
- Handle Telegram bot commands and messages
- Manage user state and conversation flow
- Load and select prompt optimization system prompts
- Send user/system prompts to LLM and return responses
"""

import logging
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.error import (
    NetworkError, 
    TimedOut, 
    BadRequest, 
    ChatMigrated, 
    RetryAfter
)
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from state_manager import StateManager
from openrouter_client import OpenRouterClient
from openai_client import OpenAIClient
from conversation_manager import ConversationManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Maximum number of retries for sending messages
MAX_RETRIES = 3

async def safe_reply(update: Update, text: str, **kwargs) -> bool:
    """
    Safely send a reply message with error handling and retries.
    
    Args:
        update: The update object from the Telegram bot
        text: The message text to send
        **kwargs: Additional arguments to pass to reply_text
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    if not update or not update.message:
        logger.error("Invalid update or message object")
        return False
        
    for attempt in range(MAX_RETRIES):
        try:
            await update.message.reply_text(text, **kwargs)
            return True
            
        except RetryAfter as e:
            # Handle flood control limits
            wait_time = e.retry_after + 5  # Add some buffer time
            logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry...")
            await asyncio.sleep(wait_time)
            
        except TimedOut:
            logger.warning(f"Timeout while sending message (attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt == MAX_RETRIES - 1:
                logger.error("Max retries reached. Giving up.")
                return False
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
        except NetworkError as e:
            logger.error(f"Network error: {e}")
            if attempt == MAX_RETRIES - 1:
                return False
            await asyncio.sleep(2 ** attempt)
            
        except ChatMigrated as e:
            # Handle chat migration (supergroup migration)
            logger.warning(f"Chat migrated to {e.new_chat_id}")
            # You might want to update chat_id in your database here
            return False
            
        except BadRequest as e:
            logger.error(f"Bad request: {e}")
            return False
            
        except Exception as e:
            logger.exception(f"Unexpected error while sending message: {e}")
            if attempt == MAX_RETRIES - 1:
                return False
            await asyncio.sleep(1)
    
    return False

# Load environment variables
load_dotenv()

# Debug: Log environment variables
logger.info("Environment variables loaded. Checking required variables...")
required_vars = ['TELEGRAM_TOKEN', 'LLM_BACKEND']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
else:
    logger.info("All required environment variables are present.")
    logger.debug(f"LLM_BACKEND: {os.getenv('LLM_BACKEND')}")
    # Don't log tokens for security
    logger.debug("TELEGRAM_TOKEN present: Yes")

# --- PROMPT LOADING ---
def load_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')
CRAFT_PROMPT_PATH = os.path.join(PROMPTS_DIR, 'CRAFT_prompt.txt')
LYRA_PROMPT_PATH = os.path.join(PROMPTS_DIR, 'LYRA_prompt.txt')
GGL_PROMPT_PATH = os.path.join(PROMPTS_DIR, 'GGL_prompt.txt')

craft_prompt = load_prompt(CRAFT_PROMPT_PATH)
lyra_prompt = load_prompt(LYRA_PROMPT_PATH)
ggl_prompt = load_prompt(GGL_PROMPT_PATH)

CRAFT_BUTTON = 'CRAFT'
LYRA_BASIC_BUTTON = 'LYRA basic'
GGL_BUTTON = 'GGL Guide'
LYRA_DETAIL_BUTTON = 'LYRA detail'  # Kept for functionality but not shown in UI
SELECT_METHOD_KEYBOARD = ReplyKeyboardMarkup([
    [LYRA_BASIC_BUTTON, CRAFT_BUTTON, GGL_BUTTON]
], resize_keyboard=True)

state_manager = StateManager()
conversation_manager = ConversationManager()


# Select LLM backend
llm_backend = os.getenv('LLM_BACKEND', 'OPENROUTER').upper()
if llm_backend == 'OPENAI':
    llm_client = OpenAIClient(
        api_key=os.getenv('OPENAI_API_KEY'),
        model_name=os.getenv('MODEL_NAME', 'gpt-4o'),
        max_retries=5,  # Increased from default 3 to 5
        request_timeout=60.0,  # 60 seconds per request
        max_wait_time=300.0  # 5 minutes total including retries
    )
else:
    llm_client = OpenRouterClient(
        api_key=os.getenv('OPENROUTER_API_KEY'),
        model_name=os.getenv('MODEL_NAME', 'openai/gpt-4')
    )


NEW_PROMPT_BUTTON = 'Написать новый промпт'
keyboard = ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state_manager.set_waiting_for_prompt(user_id, True)
    state_manager.set_last_interaction(user_id, None)
    conversation_manager.reset(user_id)
    await safe_reply(
        update,
        'Введите промпт, который хотите улучшить.',
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    user_state = state_manager.get_user_state(user_id)

    # If waiting for prompt
    if user_state.waiting_for_prompt:
        conversation_manager.reset(user_id)
        conversation_manager.set_user_prompt(user_id, text)
        conversation_manager.append_message(user_id, "user", text)  # Store user prompt
        conversation_manager.set_waiting_for_method(user_id, True)
        user_state.waiting_for_prompt = False
        method_keyboard = list(SELECT_METHOD_KEYBOARD.keyboard)
        method_keyboard.append([NEW_PROMPT_BUTTON])
        await safe_reply(
            update,
            'Какой методикой оптимизурем промпт?',
            reply_markup=ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True)
        )
        return

    # If waiting for method selection
    if conversation_manager.is_waiting_for_method(user_id):
        transcript = conversation_manager.get_transcript(user_id)
        if text == CRAFT_BUTTON:
            # Insert system prompt at the start if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": craft_prompt})
            conversation_manager.set_waiting_for_method(user_id, False)
            try:
                response = await llm_client.send_prompt(transcript)
            except Exception as e:
                response = f"Ошибка: {e}"
            conversation_manager.append_message(user_id, "assistant", response)  # Store assistant response
            await safe_reply(
                update,
                response,
                reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
            )
            return
        elif text == LYRA_BASIC_BUTTON:
            # Insert LYRA system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": lyra_prompt})
            conversation_manager.append_message(user_id, "user", "BASIC using ChatGPT")
            conversation_manager.set_waiting_for_method(user_id, False)
            try:
                response = await llm_client.send_prompt(transcript)
            except Exception as e:
                response = f"Ошибка: {e}"
            conversation_manager.append_message(user_id, "assistant", response)
            await safe_reply(
                update,
                response,
                reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
            )
            return
        elif text == LYRA_DETAIL_BUTTON:
            # Insert LYRA system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": lyra_prompt})
            conversation_manager.append_message(user_id, "user", "DETAIL using ChatGPT")
            conversation_manager.set_waiting_for_method(user_id, False)
            try:
                response = await llm_client.send_prompt(transcript)
            except Exception as e:
                response = f"Ошибка: {e}"
            conversation_manager.append_message(user_id, "assistant", response)
            await safe_reply(
                update,
                response,
                reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
            )
            return
        elif text == GGL_BUTTON:
            # Insert GGL system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": ggl_prompt})
            conversation_manager.set_waiting_for_method(user_id, False)
            try:
                response = await llm_client.send_prompt(transcript)
            except Exception as e:
                response = f"Ошибка: {e}"
            conversation_manager.append_message(user_id, "assistant", response)
            await safe_reply(
                update,
                response,
                reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
            )
            return
        else:
            # Add NEW_PROMPT_BUTTON to the method selection keyboard
            method_keyboard = list(SELECT_METHOD_KEYBOARD.keyboard)
            method_keyboard.append([NEW_PROMPT_BUTTON])
            await safe_reply(
                update,
                'Пожалуйста, выберите методику: LYRA basic, CRAFT или GGL Guide.',
                reply_markup=ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True)
            )
            return

    # If user presses NEW_PROMPT_BUTTON
    if text == NEW_PROMPT_BUTTON:
        await start(update, context)
        return

    # Multi-turn: continue conversation with full transcript
    transcript = conversation_manager.get_transcript(user_id)
    conversation_manager.append_message(user_id, "user", text)
    try:
        response = await llm_client.send_prompt(transcript)
    except Exception as e:
        response = f"Ошибка: {e}"
    conversation_manager.append_message(user_id, "assistant", response)
    await safe_reply(
        update,
        response,
        reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
    )

async def main():
    """Start the bot."""
    # Get the token
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable is not set!")
        return

    logger.info("Starting bot with token: {}...".format(token[:5] + '...' + token[-5:]))
    
    try:
        # Create the Application with connection pool settings
        # Increased timeouts to handle slow LLM responses and poor connections
        application = (
            Application.builder()
            .token(token)
            .connect_timeout(60.0)      # Increased from 30s to 60s for initial connection
            .pool_timeout(60.0)         # Increased from 30s to 60s for connection pool
            .read_timeout(300.0)        # Increased from 30s to 300s (5 min) for LLM responses
            .write_timeout(120.0)       # Increased from 30s to 120s for sending data
            .get_updates_read_timeout(60.0)  # Specific timeout for getUpdates polling
            .pool_timeout(60.0)         # Timeout for getting a connection from the pool
            .build()
        )

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start the Bot with error handling
        logger.info("Starting polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Keep the application running
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("Shutting down...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        raise
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        logger.exception("Exception details:")
        raise

if __name__ == '__main__':
    import asyncio
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception("Exception details:")
        raise
