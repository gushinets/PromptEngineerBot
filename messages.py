"""
Bot response messages and text templates.

This module contains all the static messages and templates used by the Telegram bot
for consistent messaging and easier maintenance.
"""

from telegram import ReplyKeyboardMarkup

# ===== Language Settings =====
# Set to 'ru' for Russian or 'en' for English
LANGUAGE = 'ru'

def _(text_ru, text_en):
    """Helper function for translations"""
    return text_ru if LANGUAGE == 'ru' else text_en

# ===== UI Elements =====
# Button labels
NEW_PROMPT_BUTTON = _('Начать с начала', 'Start over')
CRAFT_BUTTON = _('CRAFT', 'CRAFT')
LYRA_BASIC_BUTTON = _('LYRA basic', 'LYRA basic')
LYRA_DETAIL_BUTTON = _('LYRA detail', 'LYRA detail')
GGL_BUTTON = _('GGL Guide', 'GGL Guide')

# ===== Welcome and Help Messages =====
WELCOME_MESSAGE = _(
    "🤖 **Добро пожаловать в Prompt Engineering Bot!**\n\n"
    "Я помогу вам создать эффективные промпты для больших языковых моделей.\n\n"
    "**Доступные методы оптимизации:**\n"
    "• **CRAFT** - Структурированный подход с контекстом, ролью, действиями, форматом и целевой аудиторией\n"
    "• **LYRA** - Оптимизация языка, результатов, ролей и действий\n"
    "• **GGL** - Фокус на цели, руководящие принципы и язык\n\n"
    "**Как использовать:**\n"
    "1. Отправьте ваш промпт\n"
    "2. Выберите метод оптимизации\n"
    "3. Получите улучшенную версию промпта\n"
    "4. Скопируйте и отправьте в нейросеть\n\n"
    "Отправьте ваш промпт, и я помогу его оптимизировать! 🚀",
    
    "🤖 **Welcome to Prompt Engineering Bot!**\n\n"
    "I can help you create effective prompts for large language models.\n\n"
    "**Available optimization methods:**\n"
    "• **CRAFT** - Structured approach with context, role, actions, format, and target audience\n"
    "• **LYRA** - Language, yield, roles, and actions optimization\n"
    "• **GGL** - Focus on goals, guidelines, and language\n\n"
    "**How to use:**\n"
    "1. Send your prompt\n"
    "2. Choose an optimization method\n"
    "3. Get an improved version of your prompt\n"
    "4. Copy and send it to the AI model\n\n"
    "Send me your prompt, and I'll help you optimize it! 🚀"
)

HELP_MESSAGE = _(
    "ℹ️ *Доступные команды*\n\n"
    "*Методики*\n"
    "/craft* - Методика CRAFT для оптимизации промптов\n"
    "/lyra* - Методика LYRA для оптимизации промптов\n"
    "/ggl* - Методика GGL для оптимизации промптов\n\n"
    "*Общие команды*\n"
    "/start* - Показать приветственное сообщение\n"
    "/help* - Показать это сообщение\n"
    "/reset* - Сбросить текущий диалог",
    
    "ℹ️ *Available Commands*\n\n"
    "*Methodologies*\n"
    "/craft* - CRAFT methodology for prompt optimization\n"
    "/lyra* - LYRA methodology for prompt optimization\n"
    "/ggl* - GGL methodology for prompt optimization\n\n"
    "*General*\n"
    "/start* - Show welcome message\n"
    "/help* - Show this help message\n"
    "/reset* - Reset the current conversation"
)

# ===== Error Messages =====
ERROR_GENERIC = _(
    "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз позже.",
    "❌ An error occurred. Please try again later."
)

ERROR_EMPTY_MESSAGE = _(
    "❌ Пожалуйста, введите промпт для анализа.",
    "❌ Please provide a message or prompt to analyze."
)

ERROR_MODEL_UNAVAILABLE = _(
    "❌ Выбранная модель в данный момент недоступна. Пожалуйста, попробуйте позже или выберите другую модель.",
    "❌ The selected model is currently unavailable. Please try again later or select a different model."
)

ERROR_TOO_LONG = _(
    "❌ Ваше сообщение слишком длинное. Пожалуйста, попробуйте более короткий промпт.",
    "❌ Your message is too long. Please try a shorter prompt."
)

ERROR_RATE_LIMIT = _(
    "⚠️ Слишком много запросов. Пожалуйста, подождите немного перед повторной попыткой.",
    "⚠️ Too many requests. Please wait a moment before trying again."
)

ERROR_NETWORK = _(
    "🌐 Ошибка сети. Пожалуйста, проверьте подключение и попробуйте снова.",
    "🌐 Network error. Please check your connection and try again."
)

# ===== Status Messages =====
RESET_CONFIRMATION = _(
    "🔄 Диалог сброшен. Вы можете начать новую оптимизацию промпта.",
    "🔄 Conversation has been reset. You can start a new prompt optimization."
)

SELECT_METHOD_MESSAGE = _(
    "📝 **Ваш промпт получен!**\n\n"
    "Теперь выберите метод оптимизации:\n\n"
    "**CRAFT** - Детальный структурированный подход\n"
    "**LYRA** - Оптимизация языка и результатов  \n"
    "**GGL** - Фокус на цели и руководящие принципы\n\n"
    "Выберите метод:",
    "📝 **Your prompt has been received!**\n\n"
    "Now choose an optimization method:\n\n"
    "**CRAFT** - Detailed structured approach\n"
    "**LYRA** - Language and results optimization\n"
    "**GGL** - Focus on goals and guidelines\n\n"
    "Choose a method:"
)

ENTER_PROMPT_MESSAGE = _(
    "📝 Введите промпт, который вы хотите улучшить:",
    "📝 Please enter the prompt you'd like to improve:"
)

def get_processing_message(method: str) -> str:
    """Generate a processing message with the specified method.
    
    Args:
        method: The name of the method being used (craft, lyra, ggl, etc.)
        
    Returns:
        str: A formatted processing message in the user's language
    """
    return _(
        f"🔄 Обрабатываю ваш промпт с помощью метода **{method.upper()}**...\n\nЭто может занять несколько секунд.",
        f"🔄 Processing your prompt using the **{method.upper()}** method...\n\nThis may take a few seconds."
    )

GENERATING_RESPONSE = _(
    "✨ Генерирую оптимизированный промпт...",
    "✨ Generating optimized prompt..."
)

# ===== Success Messages =====
RESPONSE_READY = _(
    "✅ Вот ваш оптимизированный промпт:",
    "✅ Here's your optimized prompt:"
)

METHODOLOGY_SELECTED = _(
    "✅ Выбрана методика: {methodology}",
    "✅ Methodology selected: {methodology}"
)

# ===== Keyboard Layouts =====
# Method selection keyboard
SELECT_METHOD_KEYBOARD = ReplyKeyboardMarkup(
    [
        [LYRA_BASIC_BUTTON, CRAFT_BUTTON],
        [GGL_BUTTON, LYRA_DETAIL_BUTTON]
    ],
    resize_keyboard=True
)

# Main keyboard with all options
MAIN_KEYBOARD = [
    [CRAFT_BUTTON, LYRA_BASIC_BUTTON, GGL_BUTTON],
    [NEW_PROMPT_BUTTON]
]

# ===== Prompt Templates =====
PROMPT_TEMPLATE = _(
    "**Ваш оригинальный промпт:**\n{user_prompt}\n\n"
    "**Оптимизированный промпт:**\n{optimized_prompt}\n\n"
    "**Объяснение:**\n{explanation}",
    
    "**Your original prompt:**\n{user_prompt}\n\n"
    "**Optimized prompt:**\n{optimized_prompt}\n\n"
    "**Explanation:**\n{explanation}"
)



# Button labels
BTN_RESET = "🔄 Reset Conversation"
BTN_CRAFT = "🛠 CRAFT"
BTN_LYRA = "🎯 LYRA"
BTN_GGL = "🔍 GGL"
BTN_HELP = "❓ Help"

# Keyboard layouts
MAIN_KEYBOARD = [[BTN_CRAFT, BTN_LYRA, BTN_GGL], [BTN_HELP, BTN_RESET]]

# Methodologies
def get_methodology_description(method: str) -> str:
    """Get a description of the selected methodology."""
    descriptions = {
        "craft": (
            "🛠 *CRAFT Methodology*\n\n"
            "CRAFT helps you create clear, specific, and effective prompts by:\n"
            "• Clarifying the task\n"
            "• Providing context and examples\n"
            "• Specifying the desired output format\n"
            "• Adding constraints and requirements"
        ),
        "lyra": (
            "🎯 *LYRA Methodology*\n\n"
            "LYRA focuses on creating prompts that are:\n"
            "• Logical and structured\n"
            "• Yield specific results\n"
            "• Relevant to the task\n"
            "• Actionable for the AI"
        ),
        "ggl": (
            "🔍 *GGL Methodology*\n\n"
            "GGL (Google's Generative Language) approach emphasizes:\n"
            "• Clear goal definition\n"
            "• Guiding principles for the AI\n"
            "• Layered instructions for complex tasks"
        )
    }
    return descriptions.get(method.lower(), "Select a methodology to get started.")

def get_typing_delay(text: str) -> float:
    """Calculate typing delay based on message length."""
    # 10 seconds for first 100 chars, then 1 second per 100 chars
    return min(5.0, 10.0 + (len(text) / 100))

# ===== Improved Prompt Response =====
IMPROVED_PROMPT_RESPONSE = _(
    """
✅ **Промпт оптимизирован с помощью {method_name}!**

**Ваш исходный промпт:**
```
{user_prompt}
```

**Улучшенный промпт:**
```
{improved_prompt}
```
Ваш промпт готов к использованию. 
📋 Скопируйте и вставьте его в Ваш Искусственный интеллект: 🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek

А мне отправьте новый промпт для дальнейшей оптимизации! 🚀
""",
    """
✅ **Prompt optimized with {method_name}!**

**Your original prompt:**
```
{user_prompt}
```

**Improved prompt:**
```
{improved_prompt}
```
Your prompt is ready to use.
📋 Copy and paste it into your AI: 🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek

Send me a new prompt for further optimization! 🚀
"""
)

def format_improved_prompt_response(user_prompt: str, improved_prompt: str, method_name: str) -> str:
    """
    Format the improved prompt response with the specified method name.
    
    Args:
        user_prompt: The original prompt from the user
        improved_prompt: The optimized prompt from the LLM
        method_name: The name of the optimization method used (CRAFT, LYRA, GGL, etc.)
        
    Returns:
        str: Formatted response with the original and improved prompts
    """
    return IMPROVED_PROMPT_RESPONSE.format(
        method_name=method_name,
        user_prompt=user_prompt,
        improved_prompt=improved_prompt.strip()
    )

def parse_llm_response(response: str) -> tuple[str, bool, bool]:
    """
    Parse LLM response to extract content and determine if it's a question or improved prompt.
    Handles cases where closing tags might be missing by extracting everything after the opening tag.
    
    Args:
        response: The raw response from the LLM
        
    Returns:
        tuple: (parsed_response, is_question, is_improved_prompt)
    """
    is_question = False
    is_improved_prompt = False
    
    # Check for QUESTION tags
    question_start = response.find('<QUESTION>')
    
    if question_start != -1:
        # If we find the opening tag, extract everything after it
        response = response[question_start + 10:].strip()
        # Try to find the closing tag, but if not found, keep everything
        question_end = response.find('</QUESTION>')
        if question_end != -1:
            response = response[:question_end].strip()
        is_question = True
    else:
        # Only check for IMPROVED_PROMPT if no QUESTION tag was found
        prompt_start = response.find('<IMPROVED_PROMPT>')
        if prompt_start != -1:
            # If we find the opening tag, extract everything after it
            response = response[prompt_start + 17:].strip()
            # Try to find the closing tag, but if not found, keep everything
            prompt_end = response.find('</IMPROVED_PROMPT>')
            if prompt_end != -1:
                response = response[:prompt_end].strip()
            is_improved_prompt = True
    
    return response, is_question, is_improved_prompt
