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
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
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

# Load environment variables
load_dotenv()

# --- PROMPT LOADING ---
def load_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')
CRAFT_PROMPT_PATH = os.path.join(PROMPTS_DIR, 'CRAFT_prompt.txt')
LYRA_PROMPT_PATH = os.path.join(PROMPTS_DIR, 'LYRA_prompt.txt')

craft_prompt = load_prompt(CRAFT_PROMPT_PATH)
lyra_prompt = load_prompt(LYRA_PROMPT_PATH)

CRAFT_BUTTON = 'CRAFT'
LYRA_BASIC_BUTTON = 'LYRA basic'
LYRA_DETAIL_BUTTON = 'LYRA detail'
SELECT_METHOD_KEYBOARD = ReplyKeyboardMarkup([[LYRA_BASIC_BUTTON, LYRA_DETAIL_BUTTON, CRAFT_BUTTON]], resize_keyboard=True)

state_manager = StateManager()
conversation_manager = ConversationManager()


# Select LLM backend
llm_backend = os.getenv('LLM_BACKEND', 'OPENROUTER').upper()
if llm_backend == 'OPENAI':
    llm_client = OpenAIClient(
        api_key=os.getenv('OPENAI_API_KEY'),
        model_name=os.getenv('MODEL_NAME', 'gpt-4o')
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
    await update.message.reply_text(
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
        await update.message.reply_text(
            'Какой методикой оптимизурем промпт?',
            reply_markup=SELECT_METHOD_KEYBOARD
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
            await update.message.reply_text(response, reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True))
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
            await update.message.reply_text(response, reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True))
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
            await update.message.reply_text(response, reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True))
            return
        else:
            await update.message.reply_text('Пожалуйста, выберите методику: LYRA basic, LYRA detail или CRAFT.', reply_markup=SELECT_METHOD_KEYBOARD)
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
    await update.message.reply_text(response, reply_markup=ReplyKeyboardMarkup([[NEW_PROMPT_BUTTON]], resize_keyboard=True))

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
