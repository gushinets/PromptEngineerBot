"""
Bot response messages and text templates.

This module contains all the static messages and templates used by the Telegram bot
for consistent messaging and easier maintenance.
"""

from telegram import ForceReply, ReplyKeyboardMarkup

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

# Follow-up feature buttons
BTN_YES = _("✅ДА", "✅YES")
BTN_NO = _("❌НЕТ", "❌NO")
BTN_GENERATE_PROMPT = _("🤖Сгенерировать промпт", "🤖Generate Prompt")

# Email delivery button
BTN_EMAIL_DELIVERY = _("📧 Отправить 3 промпта на email", "📧 Send 3 prompts to email")

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

# Email service error messages
ERROR_EMAIL_INPUT_FAILED = _(
    "❌ Ошибка ввода email. Попробуйте позже.",
    "❌ Email input error. Please try again later.",
)

ERROR_EMAIL_SERVICE_UNAVAILABLE = _(
    "❌ Сервис email недоступен. Попробуйте позже.",
    "❌ Email service not available. Please try again later.",
)

ERROR_OTP_VERIFICATION_FAILED = _(
    "❌ Ошибка проверки OTP. Попробуйте позже.",
    "❌ OTP verification error. Please try again later.",
)

ERROR_EMAIL_SERVICE_ERROR = _(
    "❌ Ошибка сервиса email. Попробуйте позже.",
    "❌ Email service error. Please try again later.",
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

# Follow-up specific error messages
ERROR_FOLLOWUP_TIMEOUT = _(
    "⏱️ Время ожидания истекло во время уточняющих вопросов. Используем исходный улучшенный промпт.",
    "⏱️ Timeout occurred during follow-up questions. Using the original improved prompt.",
)

# Follow-up timeout and fallback messages
FOLLOWUP_TIMEOUT_FALLBACK = _(
    "Время ожидания истекло. Используем исходный улучшенный промпт:",
    "Timeout occurred. Using the original improved prompt:",
)

FOLLOWUP_TIMEOUT_RESTART = _(
    "Время ожидания истекло. Попробуйте начать с нового промпта.",
    "Timeout occurred. Please try starting with a new prompt.",
)

FOLLOWUP_NETWORK_FALLBACK = _(
    "Проблемы с сетью. Используем исходный улучшенный промпт:",
    "Network issues. Using the original improved prompt:",
)

FOLLOWUP_NETWORK_RESTART = _(
    "Проблемы с сетью. Попробуйте начать с нового промпта.",
    "Network issues. Please try starting with a new prompt.",
)

FOLLOWUP_RATE_LIMIT_FALLBACK = _(
    "Превышен лимит запросов. Используем исходный улучшенный промпт:",
    "Rate limit exceeded. Using the original improved prompt:",
)

FOLLOWUP_RATE_LIMIT_RESTART = _(
    "Превышен лимит запросов. Попробуйте позже.",
    "Rate limit exceeded. Please try again later.",
)

FOLLOWUP_API_ERROR_FALLBACK = _(
    "Ошибка API. Используем исходный улучшенный промпт:",
    "API error. Using the original improved prompt:",
)

FOLLOWUP_API_ERROR_RESTART = _(
    "Ошибка API. Попробуйте начать с нового промпта.",
    "API error. Please try starting with a new prompt.",
)

FOLLOWUP_GENERIC_ERROR_RESTART = _(
    "Произошла ошибка. Попробуйте начать с нового промпта.",
    "An error occurred. Please try starting with a new prompt.",
)

ERROR_FOLLOWUP_NETWORK = _(
    "🌐 Проблемы с сетью во время уточняющих вопросов. Используем исходный улучшенный промпт.",
    "🌐 Network issues during follow-up questions. Using the original improved prompt.",
)

ERROR_FOLLOWUP_GENERIC = _(
    "❌ Произошла ошибка во время уточняющих вопросов. Используем исходный улучшенный промпт.",
    "❌ An error occurred during follow-up questions. Using the original improved prompt.",
)

ERROR_FOLLOWUP_STATE_CORRUPTED = _(
    "⚠️ Состояние диалога повреждено. Восстанавливаем с исходного улучшенного промпта.",
    "⚠️ Conversation state corrupted. Recovering with the original improved prompt.",
)

ERROR_FOLLOWUP_PARSING = _(
    "⚠️ Не удалось обработать ответ. Используем исходный улучшенный промпт.",
    "⚠️ Failed to process response. Using the original improved prompt.",
)

# State recovery error messages
ERROR_PROMPT_RETRIEVAL_FALLBACK = _(
    "Не удалось получить улучшенный промпт. Используем исходный:",
    "Failed to retrieve improved prompt. Using the original:",
)

ERROR_PROMPT_GENERATION_FAILED = _(
    "Не удалось сгенерировать улучшенный промпт. Попробуйте начать заново.",
    "Failed to generate improved prompt. Please try starting over.",
)

ERROR_STATE_RECOVERY_SUCCESS = _(
    "Восстанавливаем состояние диалога. Используем ваш улучшенный промпт:",
    "Recovering conversation state. Using your improved prompt:",
)

ERROR_STATE_CORRUPTED_RESTART = _(
    "Состояние диалога повреждено. Начните с нового промпта.",
    "Conversation state corrupted. Start with a new prompt.",
)

ERROR_STATE_RECOVERY_FAILED = _(
    "Не удалось восстановить состояние. Начните с нового промпта.",
    "Failed to recover state. Start with a new prompt.",
)

# Email authentication messages
EMAIL_INPUT_MESSAGE = _(
    "📧 Введите ваш email адрес для получения оптимизированных промптов:",
    "📧 Please enter your email address to receive optimized prompts:",
)

ERROR_EMAIL_INVALID = _(
    "❌ Неверный формат email адреса. Пожалуйста, введите корректный email (например: user@example.com):",
    "❌ Invalid email format. Please enter a valid email address (e.g., user@example.com):",
)

EMAIL_OTP_SENT = _(
    "📧 Код подтверждения отправлен на {email}.\n\n🔢 Введите 6-значный код из письма:",
    "📧 Verification code sent to {email}.\n\n"
    "🔢 Please enter the 6-digit code from the email:",
)

ERROR_EMAIL_RATE_LIMITED = _(
    "⚠️ Слишком много попыток отправки кода. Попробуйте позже.",
    "⚠️ Too many code sending attempts. Please try again later.",
)

ERROR_EMAIL_SEND_FAILED = _(
    "❌ Не удалось отправить код подтверждения. Попробуйте позже или проверьте email адрес.",
    "❌ Failed to send verification code. Please try again later or check your email address.",
)

EMAIL_OPTIMIZATION_SUCCESS = _(
    "✅ Оптимизированные промпты отправлены на {email}!",
    "✅ Optimized prompts sent to {email}!",
)

ERROR_EMAIL_OPTIMIZATION_FAILED = _(
    "❌ Не удалось отправить оптимизированные промпты на email. Попробуйте позже.",
    "❌ Failed to send optimized prompts to email. Please try again later.",
)

ERROR_OTP_INVALID = _(
    "❌ Неверный код. Попробуйте еще раз (осталось попыток: {attempts}):",
    "❌ Invalid code. Please try again (attempts remaining: {attempts}):",
)

ERROR_OTP_EXPIRED = _(
    "❌ Код истек. Пожалуйста, запросите новый код.",
    "❌ Code has expired. Please request a new code.",
)

ERROR_OTP_ATTEMPTS_EXCEEDED = _(
    "❌ Превышено количество попыток ввода кода. Пожалуйста, запросите новый код.",
    "❌ Too many attempts. Please request a new code.",
)

OTP_VERIFICATION_SUCCESS = _(
    "✅ Email подтвержден! Переходим к улучшению промпта...",
    "✅ Email verified! Proceeding to prompt improvement...",
)

EMAIL_ALREADY_AUTHENTICATED = _(
    "✅ Вы уже авторизованы! Отправляем промпты на ваш email {email}...",
    "✅ You're already authenticated! Sending prompts to your email {email}...",
)

ERROR_REDIS_UNAVAILABLE = _(
    "⚠️ Сервис временно недоступен. Пожалуйста, попробуйте позже.",
    "⚠️ Service temporarily unavailable. Please try again later.",
)

ERROR_SMTP_UNAVAILABLE = _(
    "⚠️ Не удается отправить email. Показываем результаты в чате:",
    "⚠️ Unable to send email. Showing results in chat:",
)

# Email flow specific error messages
ERROR_ORIGINAL_PROMPT_NOT_FOUND = _(
    "❌ Не удалось найти исходный промпт. Пожалуйста, начните заново.",
    "❌ Failed to find original prompt. Please start over.",
)

ERROR_EMAIL_FLOW_START_FAILED = _(
    "❌ Произошла ошибка при запуске email-потока. Попробуйте позже.",
    "❌ An error occurred while starting email flow. Please try again later.",
)

ERROR_EMAIL_PROCESSING_FAILED = _(
    "❌ Произошла ошибка при обработке email. Попробуйте позже.",
    "❌ An error occurred while processing email. Please try again later.",
)

ERROR_OTP_CODE_VALIDATION = _(
    "❌ Код должен состоять из 6 цифр. Попробуйте еще раз:",
    "❌ Code must consist of 6 digits. Please try again:",
)

ERROR_OTP_VERIFICATION_PROCESSING = _(
    "❌ Произошла ошибка при проверке кода. Попробуйте позже.",
    "❌ An error occurred while verifying the code. Please try again later.",
)

ERROR_FLOW_DATA_NOT_FOUND = _(
    "❌ Не удалось найти данные потока. Попробуйте начать заново.",
    "❌ Failed to find flow data. Please start over.",
)

ERROR_FLOW_PROMPT_NOT_FOUND = _(
    "❌ Не удалось найти исходный промпт. Попробуйте начать заново.",
    "❌ Failed to find original prompt. Please start over.",
)

ERROR_OPTIMIZATION_TRANSITION_FAILED = _(
    "❌ Произошла ошибка при переходе к оптимизации промпта. Попробуйте позже.",
    "❌ An error occurred while transitioning to prompt optimization. Please try again later.",
)

ERROR_PROMPT_OPTIMIZATION_FAILED = _(
    "❌ Не удалось оптимизировать промпт. Попробуйте позже.",
    "❌ Failed to optimize prompt. Please try again later.",
)

ERROR_EMAIL_ADDRESS_NOT_FOUND = _(
    "❌ Не удалось найти email адрес. Попробуйте начать заново.",
    "❌ Failed to find email address. Please start over.",
)

ERROR_EMAIL_OPTIMIZATION_PROCESSING = _(
    "❌ Произошла ошибка при оптимизации и отправке email. Попробуйте позже.",
    "❌ An error occurred during optimization and email sending. Please try again later.",
)

ERROR_OPTIMIZATION_EXECUTION_FAILED = _(
    "❌ Не удалось выполнить оптимизацию промпта. Попробуйте позже.",
    "❌ Failed to execute prompt optimization. Please try again later.",
)

# ===== Status Messages =====
RESET_CONFIRMATION = _(
    "🔄 Диалог сброшен. Вы можете начать новую оптимизацию промпта.",
    "🔄 Conversation has been reset. You can start a new prompt optimization.",
)

# Processing status messages
INFO_EMAIL_OPTIMIZATION_PROCESSING = _(
    "🔄 Оптимизируем ваш промпт тремя методами и отправляем на email...",
    "🔄 Optimizing your prompt with three methods and sending to email...",
)

INFO_ALL_METHODS_OPTIMIZATION = _(
    "🔄 Запускаем оптимизацию промпта всеми тремя методами...",
    "🔄 Starting prompt optimization with all three methods...",
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

SUCCESS_ALL_PROMPTS_SENT_TO_CHAT = _(
    "✅ Все оптимизированные промпты отправлены в чат!",
    "✅ All optimized prompts sent to chat!",
)

# ===== Template Messages =====
# Optimization method result template
OPTIMIZATION_METHOD_RESULT_TEMPLATE = _(
    "🔹 **{method_name} оптимизированный промпт:**\n\n{prompt}",
    "🔹 **{method_name} optimized prompt:**\n\n{prompt}",
)

# Optimization error template
OPTIMIZATION_ERROR_TEMPLATE = _(
    "Ошибка оптимизации методом {method_name}",
    "Optimization error with {method_name} method",
)

# No follow-up instruction for system prompts
NO_FOLLOWUP_INSTRUCTION = _(
    "\n\n### ВАЖНО\n"
    "Ни в коем случае не задавай ни одного уточняющего вопроса. "
    "Твоя задача улучшить промпт пользователя по имеющимся данным. "
    "Твой ответ должен содержать только улучшенный промпт и ничего больше",
    "\n\n### IMPORTANT\n"
    "Under no circumstances ask any clarifying questions. "
    "Your task is to improve the user's prompt based on available data. "
    "Your response should contain only the improved prompt and nothing else",
)

# System validation strings (internal use, not user-facing)
SYSTEM_FOLLOWUP_PROMPT_INDICATOR = _(
    "промпт-инжинирингу",
    "prompt-engineering",
)

# Optimization error prefix for result validation
OPTIMIZATION_ERROR_PREFIX = _(
    "Ошибка оптимизации методом",
    "Optimization error with method",
)

# Method result message template
METHOD_RESULT_MESSAGE_TEMPLATE = _(
    "🔹 **{method_name} оптимизированный промпт:**\n\n{prompt}",
    "🔹 **{method_name} optimized prompt:**\n\n{prompt}",
)

METHODOLOGY_SELECTED = _(
    "✅ Выбрана методика: {methodology}", "✅ Methodology selected: {methodology}"
)

PROMPT_READY_FOLLOW_UP = _(
    "✅Ваш промпт готов к использованию. 📋 Скопируйте и вставьте его в Ваш Искусственный интеллект: 🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek\n\nА мне отправьте новый промпт для дальнейшей оптимизации! 🚀",
    "✅Your prompt is ready to use. 📋 Copy and paste it into your AI: 🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek\n\nSend me a new prompt for further optimization! 🚀",
)

# Follow-up feature messages
FOLLOWUP_OFFER_MESSAGE = _(
    "✅Ваш промпт уже готов к использованию, но мы можем сделать его ещё лучше. Готовы ответить на несколько вопросов?",
    "✅Your prompt is ready to use, but we can make it even better. Ready to answer a few questions?",
)

FOLLOWUP_PROMPT_INPUT_MESSAGE = _(
    "Поменяйте или добавьте любые детали промпта. Если всё верно, просто скопируйте и отправьте этот промпт мне:",
    "Modify or add any details to the prompt. If everything is correct, just copy and send this prompt to me:",
)

# ===== Keyboard Layouts =====
# Method selection keyboard
SELECT_METHOD_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_EMAIL_DELIVERY], [BTN_LYRA, BTN_CRAFT, BTN_GGL]], resize_keyboard=True
)

# Follow-up feature keyboards
FOLLOWUP_CHOICE_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_YES, BTN_NO]], resize_keyboard=True
)

FOLLOWUP_CONVERSATION_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_GENERATE_PROMPT], [BTN_RESET]], resize_keyboard=True
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


def create_prompt_input_reply(improved_prompt: str) -> ForceReply:
    """Create ForceReply with improved prompt as placeholder text.

    This function creates a ForceReply object that displays the improved prompt
    in the Telegram input field as placeholder text, allowing users to modify
    or confirm the prompt before starting follow-up questions.

    Args:
        improved_prompt: The improved prompt to show as placeholder text

    Returns:
        ForceReply: Telegram ForceReply object with the prompt as placeholder
    """
    return ForceReply(input_field_placeholder=improved_prompt, selective=False)


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


def parse_followup_response(response: str) -> tuple[str, bool]:
    """
    Parse follow-up LLM response to extract refined prompts.

    This function specifically handles REFINED_PROMPT tags from follow-up conversations.
    It supports various tag formats including missing closing tags and provides
    fallback parsing for malformed responses.

    Args:
        response: The raw response from the follow-up LLM

    Returns:
        tuple: (parsed_content, is_refined_prompt)
            - parsed_content: The extracted refined prompt content or original response
            - is_refined_prompt: True if a REFINED_PROMPT tag was found and parsed
    """
    try:
        # Check for REFINED_PROMPT tag
        extracted, _ = _extract_tag_block(response, "REFINED_PROMPT")
        if extracted is not None:
            # Validate extracted content
            if extracted.strip():
                return extracted, True
            else:
                # Empty content, fall back to original response
                return response.strip(), False

        # No REFINED_PROMPT tag found, return original response
        return response.strip(), False

    except Exception as e:
        # Parsing error, return original response
        import logging

        logging.error(f"Error parsing follow-up response: {e}")
        return response.strip(), False
