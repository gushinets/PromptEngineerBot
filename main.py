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
from messages import (
    WELCOME_MESSAGE, SELECT_METHOD_MESSAGE, 
    NEW_PROMPT_BUTTON, CRAFT_BUTTON, LYRA_BASIC_BUTTON, GGL_BUTTON, LYRA_DETAIL_BUTTON,
    SELECT_METHOD_KEYBOARD, ENTER_PROMPT_MESSAGE, get_processing_message,
    ERROR_EMPTY_MESSAGE, ERROR_GENERIC, ERROR_NETWORK, ERROR_RATE_LIMIT, ERROR_TOO_LONG,
    parse_llm_response, format_improved_prompt_response
)
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
    if not text or text.strip() == '':
        logger.warning("Attempted to send empty message")
        await update.message.reply_text(ERROR_EMPTY_MESSAGE)
        return False
    
    # Check message length (Telegram's limit is 4096 characters)
    if len(text) > 4000:  # Leave some room for potential formatting
        logger.warning(f"Message too long: {len(text)} characters")
        await update.message.reply_text(ERROR_TOO_LONG)
        return False
        
    for attempt in range(MAX_RETRIES):
        try:
            await update.message.reply_text(text, **kwargs)
            return True
            
        except RetryAfter as e:
            # Handle flood control limits
            wait_time = e.retry_after + 5  # Add some buffer time
            logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry...")
            await update.message.reply_text(ERROR_RATE_LIMIT)
            await asyncio.sleep(wait_time)
            
        except TimedOut as e:
            logger.warning(f"Timeout while sending message (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt == MAX_RETRIES - 1:
                logger.error("Max retries reached. Giving up.")
                await update.message.reply_text(ERROR_NETWORK)
                return False
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
        except NetworkError as e:
            logger.error(f"Network error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt == MAX_RETRIES - 1:
                await update.message.reply_text(ERROR_NETWORK)
                return False
            await asyncio.sleep(2 ** attempt)
            
        except ChatMigrated as e:
            # Handle chat migration (supergroup migration)
            logger.warning(f"Chat migrated to {e.new_chat_id}")
            # You might want to update chat_id in your database here
            return False
            
        except BadRequest as e:
            logger.error(f"Bad request: {e}")
            if "message is too long" in str(e).lower():
                await update.message.reply_text(ERROR_TOO_LONG)
            else:
                await update.message.reply_text(ERROR_GENERIC)
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            if attempt == MAX_RETRIES - 1:
                await update.message.reply_text(ERROR_GENERIC)
                return False
            await asyncio.sleep(2 ** attempt)
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


# Keyboard is now defined in messages.py

def reset_user_state(user_id: int):
    """
    Reset the user's state and conversation history.
    
    Args:
        user_id: The ID of the user whose state should be reset
    """
    state_manager.set_waiting_for_prompt(user_id, True)
    state_manager.set_last_interaction(user_id, None)
    conversation_manager.reset(user_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command or New Prompt button."""
    user_id = update.effective_user.id
    reset_user_state(user_id)
    
    # Send welcome message
    await safe_reply(
        update,
        WELCOME_MESSAGE,
        parse_mode='Markdown'
    )
    

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    user_state = state_manager.get_user_state(user_id)

    # If user presses NEW_PROMPT_BUTTON, always reset the conversation
    if text == NEW_PROMPT_BUTTON:
        await start(update, context)
        return

    # If waiting for prompt
    if user_state.waiting_for_prompt:
        conversation_manager.reset(user_id)
        conversation_manager.set_user_prompt(user_id, text)
        conversation_manager.append_message(user_id, "user", text)  # Store user prompt
        conversation_manager.set_waiting_for_method(user_id, True)
        user_state.waiting_for_prompt = False
        
        # Add NEW_PROMPT_BUTTON to the method selection keyboard
        method_keyboard = list(SELECT_METHOD_KEYBOARD.keyboard)
        method_keyboard.append([NEW_PROMPT_BUTTON])
        await safe_reply(
            update,
            SELECT_METHOD_MESSAGE,
            reply_markup=ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True)
        )
        return

    # If waiting for method selection
    if conversation_manager.is_waiting_for_method(user_id):
        transcript = conversation_manager.get_transcript(user_id)
        if text == CRAFT_BUTTON or text == '/craft':
            # Insert system prompt at the start if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": craft_prompt})
            conversation_manager.set_waiting_for_method(user_id, False)
            conversation_manager.set_current_method(user_id, "CRAFT")
            # Send processing message with method name
            await update.message.reply_text(
                get_processing_message("craft"),
                parse_mode='Markdown'
            )
            try:
                raw_response = await llm_client.send_prompt(transcript)
                response, is_question, is_improved_prompt = parse_llm_response(raw_response)
                conversation_manager.append_message(user_id, "assistant", raw_response)
                
                if is_improved_prompt:
                    # Format the improved prompt response
                    user_prompt = conversation_manager.get_user_prompt(user_id)
                    method_name = "CRAFT" if text == CRAFT_BUTTON or text == '/craft' else "LYRA" if text in [LYRA_BASIC_BUTTON, LYRA_DETAIL_BUTTON, '/lyra'] else "GGL"
                    response = format_improved_prompt_response(user_prompt, response, method_name)
                    # Reset conversation after sending improved prompt
                    conversation_manager.reset(user_id)
                    # Reset the user state using the state manager
                    state_manager.set_waiting_for_prompt(user_id, True)
                
                await safe_reply(
                    update,
                    response,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
                )
            except Exception as e:
                logger.error(f"Error in CRAFT processing: {e}", exc_info=True)
                await safe_reply(
                    update,
                    f"{ERROR_GENERIC}\n\n{str(e)}",
                    reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
                )
            return
        elif text == LYRA_BASIC_BUTTON or text == '/lyra':
            # Insert LYRA system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": lyra_prompt})
            conversation_manager.append_message(user_id, "user", "BASIC using ChatGPT")
            conversation_manager.set_waiting_for_method(user_id, False)
            conversation_manager.set_current_method(user_id, "LYRA Basic")
            # Send processing message with method name
            await update.message.reply_text(
                get_processing_message("lyra"),
                parse_mode='Markdown'
            )
            try:
                raw_response = await llm_client.send_prompt(transcript)
                response, is_question, is_improved_prompt = parse_llm_response(raw_response)
                conversation_manager.append_message(user_id, "assistant", raw_response)
                
                if is_improved_prompt:
                    # Format the improved prompt response
                    user_prompt = conversation_manager.get_user_prompt(user_id)
                    method_name = "CRAFT" if text == CRAFT_BUTTON or text == '/craft' else "LYRA" if text in [LYRA_BASIC_BUTTON, LYRA_DETAIL_BUTTON, '/lyra'] else "GGL"
                    response = format_improved_prompt_response(user_prompt, response, method_name)
                    # Reset conversation after sending improved prompt
                    conversation_manager.reset(user_id)
                    # Reset the user state using the state manager
                    state_manager.set_waiting_for_prompt(user_id, True)
                
                await safe_reply(
                    update,
                    response,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
                )
            except Exception as e:
                error_msg = f"Ошибка: {e}"
                conversation_manager.append_message(user_id, "assistant", error_msg)
                await safe_reply(
                    update,
                    error_msg,
                    reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
                )
            return
        elif text == LYRA_DETAIL_BUTTON:
            # Insert LYRA system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": lyra_prompt})
            conversation_manager.append_message(user_id, "user", "DETAILED using ChatGPT")
            conversation_manager.set_waiting_for_method(user_id, False)
            conversation_manager.set_current_method(user_id, "LYRA Detail")
            # Send processing message with method name
            await update.message.reply_text(
                get_processing_message("lyra_detail"),
                parse_mode='Markdown'
            )
            try:
                raw_response = await llm_client.send_prompt(transcript)
                response, is_question, is_improved_prompt = parse_llm_response(raw_response)
                conversation_manager.append_message(user_id, "assistant", raw_response)
                
                if is_improved_prompt:
                    # Format the improved prompt response
                    user_prompt = conversation_manager.get_user_prompt(user_id)
                    method_name = "CRAFT" if text == CRAFT_BUTTON or text == '/craft' else "LYRA" if text in [LYRA_BASIC_BUTTON, LYRA_DETAIL_BUTTON, '/lyra'] else "GGL"
                    response = format_improved_prompt_response(user_prompt, response, method_name)
                    # Reset conversation after sending improved prompt
                    conversation_manager.reset(user_id)
                    # Reset the user state using the state manager
                    state_manager.set_waiting_for_prompt(user_id, True)
                
                await safe_reply(
                    update,
                    response,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
                )
            except Exception as e:
                error_msg = f"Ошибка: {e}"
                conversation_manager.append_message(user_id, "assistant", error_msg)
                await safe_reply(
                    update,
                    error_msg,
                    reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
                )
            return
        elif text == GGL_BUTTON or text == '/ggl':
            # Insert GGL system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": ggl_prompt})
            conversation_manager.set_waiting_for_method(user_id, False)
            # Send processing message with method name
            await update.message.reply_text(
                get_processing_message("ggl"),
                parse_mode='Markdown'
            )
            try:
                raw_response = await llm_client.send_prompt(transcript)
                response, is_question, is_improved_prompt = parse_llm_response(raw_response)
                conversation_manager.append_message(user_id, "assistant", raw_response)
                
                if is_improved_prompt:
                    # Format the improved prompt response
                    user_prompt = conversation_manager.get_user_prompt(user_id)
                    method_name = "CRAFT" if text == CRAFT_BUTTON or text == '/craft' else "LYRA" if text in [LYRA_BASIC_BUTTON, LYRA_DETAIL_BUTTON, '/lyra'] else "GGL"
                    response = format_improved_prompt_response(user_prompt, response, method_name)
                    # Reset conversation after sending improved prompt
                    conversation_manager.reset(user_id)
                    # Reset the user state using the state manager
                    state_manager.set_waiting_for_prompt(user_id, True)
                
                await safe_reply(
                    update,
                    response,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
                )
            except Exception as e:
                error_msg = f"Ошибка: {e}"
                conversation_manager.append_message(user_id, "assistant", error_msg)
                await safe_reply(
                    update,
                    error_msg,
                    reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
                )
            return
        else:
            # Add NEW_PROMPT_BUTTON to the method selection keyboard
            method_keyboard = list(SELECT_METHOD_KEYBOARD.keyboard)
            method_keyboard.append([NEW_PROMPT_BUTTON])
            await safe_reply(
                update,
                SELECT_METHOD_MESSAGE,
                reply_markup=ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True)
            )
            return

    # This check is now at the beginning of the function

    # Multi-turn: continue conversation with full transcript
    transcript = conversation_manager.get_transcript(user_id)
    conversation_manager.append_message(user_id, "user", text)
    try:
        raw_response = await llm_client.send_prompt(transcript)
        response, is_question, is_improved_prompt = parse_llm_response(raw_response)
        conversation_manager.append_message(user_id, "assistant", raw_response)
        
        if is_improved_prompt:
            # Format the improved prompt response
            user_prompt = conversation_manager.get_user_prompt(user_id)
            method_name = conversation_manager.get_current_method(user_id)
            response = format_improved_prompt_response(user_prompt, response, method_name)
            # Reset user state after sending improved prompt
            reset_user_state(user_id)
        
        await safe_reply(
            update,
            response,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True)
        )
    except Exception as e:
        error_msg = f"Ошибка: {e}"
        conversation_manager.append_message(user_id, "assistant", error_msg)
        await safe_reply(
            update,
            error_msg,
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
