"""
Bot response messages and text templates.

This module contains all the static messages and templates used by the Telegram bot
for consistent messaging and easier maintenance.
"""

from telegram import ReplyKeyboardMarkup

# ===== Language Settings =====
# Set to 'ru' for Russian or 'en' for English
LANGUAGE = "ru"


def _(text_ru, text_en):
    """Helper function for translations"""
    return text_ru if LANGUAGE == "ru" else text_en


# ===== UI Elements =====
# Localized, emoji-enhanced button labels (single source of truth)
BTN_RESET = _("🔄 Сбросить диалог", "🔄 Reset Conversation")
BTN_CRAFT = _("🛠 CRAFT", "🛠 CRAFT")
BTN_LYRA = _("⚡ LYRA", "⚡ LYRA")
BTN_LYRA_DETAIL = _("🧩 LYRA detail", "🧩 LYRA detail")
BTN_GGL = _("🔍 GGL", "🔍 GGL")
BTN_HELP = _("❓ Помощь", "❓ Help")

# ===== Welcome and Help Messages =====
WELCOME_MESSAGE = _(
    "🤖 Добро пожаловать в Prompt Engineering Bot!\n"
    "💡 Ваш помощник по созданию мощных и точных промптов для больших языковых моделей.\n\n"
    "🎯 Методы оптимизации:\n"
    "⚡ LYRA — мгновенный результат\n"
    "🛠 CRAFT — структурированный подход\n"
    "🔍 GGL — фокус на цели, минимум вопросов\n\n"
    "📌 Как это работает:\n"
    "1️⃣ Отправьте ваш промпт\n"
    "2️⃣ Выберите метод оптимизации\n"
    "3️⃣ Получите улучшенную версию\n"
    "4️⃣ Используйте её в нейросети 🚀\n\n"
    "✍️ Отправьте свой промпт прямо сейчас — и я превращу его в инструмент, который добьётся лучших результатов!",
    "🤖 Welcome to Prompt Engineering Bot!\n"
    "💡 Your assistant for creating powerful and precise prompts for large language models.\n\n"
    "🎯 Optimization methods:\n"
    "⚡ LYRA — instant results\n"
    "🛠 CRAFT — structured approach\n"
    "🔍 GGL — goal-focused, minimal questions\n\n"
    "📌 How it works:\n"
    "1️⃣ Send your prompt\n"
    "2️⃣ Choose an optimization method\n"
    "3️⃣ Get an improved version\n"
    "4️⃣ Use it in your AI model 🚀\n\n"
    "✍️ Send your prompt now — and I'll turn it into a tool that achieves better results!",
)

# ===== Error Messages =====
ERROR_GENERIC = _(
    "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз позже.",
    "❌ An error occurred. Please try again later.",
)

ERROR_EMPTY_MESSAGE = _(
    "❌ Пожалуйста, введите промпт для анализа.",
    "❌ Please provide a message or prompt to analyze.",
)

ERROR_MODEL_UNAVAILABLE = _(
    "❌ Выбранная модель в данный момент недоступна. Пожалуйста, попробуйте позже или выберите другую модель.",
    "❌ The selected model is currently unavailable. Please try again later or select a different model.",
)

ERROR_TOO_LONG = _(
    "❌ Ваше сообщение слишком длинное. Пожалуйста, попробуйте более короткий промпт.",
    "❌ Your message is too long. Please try a shorter prompt.",
)

ERROR_RATE_LIMIT = _(
    "⚠️ Слишком много запросов. Пожалуйста, подождите немного перед повторной попыткой.",
    "⚠️ Too many requests. Please wait a moment before trying again.",
)

ERROR_NETWORK = _(
    "🌐 Ошибка сети. Пожалуйста, проверьте подключение и попробуйте снова.",
    "🌐 Network error. Please check your connection and try again.",
)

# ===== Status Messages =====
RESET_CONFIRMATION = _(
    "🔄 Диалог сброшен. Вы можете начать новую оптимизацию промпта.",
    "🔄 Conversation has been reset. You can start a new prompt optimization.",
)

SELECT_METHOD_MESSAGE = _(
    "📝 **Ваш промпт получен!**\n\n"
    "Теперь выберите метод оптимизации:\n\n"
    "⚡ LYRA — мгновенный результат\n"
    "🛠 CRAFT — структурированный подход\n"
    "🔍 GGL — фокус на цели, минимум вопросов\n\n"
    "👉 *Нажмите на метод ниже, чтобы начать*:",
    "📝 **Your prompt has been received!**\n\n"
    "Now choose an optimization method:\n\n"
    "⚡ LYRA — instant results\n"
    "🛠 CRAFT — structured approach\n"
    "🔍 GGL — goal-focused, minimal questions\n\n"
    "👉 *Click on the method below to start*:",
)

ENTER_PROMPT_MESSAGE = _(
    "📝 Введите промпт, который вы хотите улучшить:",
    "📝 Please enter the prompt you'd like to improve:",
)


def get_processing_message(method: str) -> str:
    """Generate a processing message with the specified method.

    Args:
        method: The name of the method being used (craft, lyra, ggl, etc.)

    Returns:
        str: A formatted processing message in the user's language
    """
    # Clean method name for display (remove underscores, capitalize)
    display_method = method.replace("_", " ").upper()

    return _(
        f"🔄 Обрабатываю ваш промпт с помощью метода *{display_method}*...\n\nЭто может занять несколько секунд.",
        f"🔄 Processing your prompt using the *{display_method}* method...\n\nThis may take a few seconds.",
    )


GENERATING_RESPONSE = _(
    "✨ Генерирую оптимизированный промпт...", "✨ Generating optimized prompt..."
)

# ===== Success Messages =====
RESPONSE_READY = _(
    "✅ Вот ваш оптимизированный промпт:", "✅ Here's your optimized prompt:"
)

METHODOLOGY_SELECTED = _(
    "✅ Выбрана методика: {methodology}", "✅ Methodology selected: {methodology}"
)

PROMPT_READY_FOLLOW_UP = _(
    "✅Ваш промпт готов к использованию. 📋 Скопируйте и вставьте его в Ваш Искусственный интеллект: 🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek\n\nА мне отправьте новый промпт для дальнейшей оптимизации! 🚀",
    "✅Your prompt is ready to use. 📋 Copy and paste it into your AI: 🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek\n\nSend me a new prompt for further optimization! 🚀",
)

# ===== Keyboard Layouts =====
# Method selection keyboard
SELECT_METHOD_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_LYRA, BTN_CRAFT, BTN_GGL]], resize_keyboard=True
)

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
    """,
)


def format_improved_prompt_response(
    user_prompt: str, improved_prompt: str, method_name: str
) -> str:
    """
    Format the improved prompt response with the specified method name.

    NOTE: This function is kept for potential future use but is currently not used
    in the main flow. The bot now sends the optimized prompt immediately followed
    by a separate follow-up message.

    Args:
        user_prompt: The original prompt from the user
        improved_prompt: The optimized prompt from the LLM
        method_name: The name of the optimization method used (CRAFT, LYRA, GGL, etc.)

    Returns:
        str: Formatted response with the original and improved prompts
    """
    # Escape potential Markdown characters in user content
    safe_user_prompt = (
        user_prompt.replace("`", "\\`").replace("*", "\\*").replace("_", "\\_")
    )
    safe_improved_prompt = (
        improved_prompt.strip()
        .replace("`", "\\`")
        .replace("*", "\\*")
        .replace("_", "\\_")
    )

    return IMPROVED_PROMPT_RESPONSE.format(
        method_name=method_name,
        user_prompt=safe_user_prompt,
        improved_prompt=safe_improved_prompt,
    )


def _extract_tag_block(text: str, tag: str) -> tuple[str | None, int | None]:
    """Extract content between an opening tag and any acceptable closing marker.

    Closing markers supported (case-insensitive):
    - </TAG>
    - <END TAG>
    - <END_TAG>
    - [END TAG]
    - [ /TAG ] or [/TAG]
    - <TAG_END>
    - <END>

    Returns the extracted content and the index where the opening tag started.
    If opening tag not found, returns (None, None).
    """
    lowered = text.lower()
    normalized_tag = tag.lower()
    opening = f"<{normalized_tag}>"
    start = lowered.find(opening)
    if start == -1:
        return None, None

    content_start = start + len(opening)
    remainder = text[content_start:]
    remainder_lower = lowered[content_start:]

    # Build list of possible closing markers
    closing_candidates = [
        f"</{normalized_tag}>",
        f"<end {normalized_tag}>",
        f"<end_{normalized_tag}>",
        f"[{'end ' + normalized_tag}]",
        f"[/{normalized_tag}]",
        f"<{normalized_tag}_end>",
        "<end>",
    ]

    earliest_idx = None
    for marker in closing_candidates:
        idx = remainder_lower.find(marker)
        if idx != -1:
            if earliest_idx is None or idx < earliest_idx:
                earliest_idx = idx

    if earliest_idx is not None:
        extracted = remainder[:earliest_idx].strip()
    else:
        extracted = remainder.strip()

    return extracted, start


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

    # Prefer QUESTION if present
    extracted, _ = _extract_tag_block(response, "QUESTION")
    if extracted is not None:
        response = extracted
        is_question = True
    else:
        # Only check for IMPROVED_PROMPT if no QUESTION tag was found
        extracted, _ = _extract_tag_block(response, "IMPROVED_PROMPT")
        if extracted is not None:
            response = extracted
            is_improved_prompt = True

    return response, is_question, is_improved_prompt
