"""
Bot response messages and text templates.

This module contains all the static messages and templates used by the Telegram bot
for consistent messaging and easier maintenance.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


# ===== Language Settings =====
# Set to 'ru' for Russian or 'en' for English
LANGUAGE = "ru"


def _(text_ru, text_en):
    """Helper function for translations"""
    return text_ru if LANGUAGE == "ru" else text_en


# ===== UI Elements =====
# Localized, emoji-enhanced button labels (single source of truth)
BTN_RESET = _("🔄 Сбросить диалог", "🔄 Reset Conversation")
BTN_LYRA = _("⚡ Быстро", "⚡ Quick")
BTN_CRAFT = _("🛠 По шагам", "🛠 Step-by-step")
BTN_GGL = _("🎯 Под результат", "🎯 Result-focused")
BTN_HELP = _("❓ Помощь", "❓ Help")

# Follow-up feature buttons
BTN_YES = _("✅ДА", "✅YES")
BTN_NO = _("❌НЕТ", "❌NO")
BTN_GENERATE_PROMPT = _("🤖Сгенерировать промпт", "🤖Generate Prompt")

# Callback data constants for inline buttons
CALLBACK_FOLLOWUP_YES = "followup_yes"
CALLBACK_FOLLOWUP_NO = "followup_no"

# Email delivery buttons
BTN_EMAIL_DELIVERY = _("📧 Отправить 3 промпта на email", "📧 Send 3 prompts to email")
BTN_POST_OPTIMIZATION_EMAIL = _("📧 Отправить промпт на e-mail", "📧 Send prompt to e-mail")

# Support button
BTN_SUPPORT = _("🆘 Техподдержка", "🆘 Support")

# Support URL
SUPPORT_BOT_URL = "https://t.me/prompthelpdesk_bot?start"

# Inline keyboard with support button
SUPPORT_KEYBOARD = InlineKeyboardMarkup([[InlineKeyboardButton(BTN_SUPPORT, url=SUPPORT_BOT_URL)]])

# ===== Data Processing Consent =====
# Consent message text
EMAIL_OTP_CONSENT_MESSAGE = _(
    "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
    "By entering the verification code, you consent to the processing of personal data",
)

# Agreement button text
BTN_DATA_AGREEMENT = _(
    "📄 Согласие на обработку персональных данных",
    "📄 Personal Data Processing Agreement",
)

# Agreement URL constant
DATA_AGREEMENT_URL = "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"

# Inline keyboard with agreement button
DATA_AGREEMENT_KEYBOARD = InlineKeyboardMarkup(
    [[InlineKeyboardButton(BTN_DATA_AGREEMENT, url=DATA_AGREEMENT_URL)]]
)

# ===== Welcome and Help Messages =====
# DEPRECATED: Use WELCOME_MESSAGE_1 and WELCOME_MESSAGE_2 instead.
# This constant is kept for backward compatibility and will be removed in a future version.
# The welcome flow now sends two separate messages: WELCOME_MESSAGE_1 (introduction)
# followed by WELCOME_MESSAGE_2 (instructions) with a support button.
WELCOME_MESSAGE = _(
    "🤖 Добро пожаловать в Prompt Engineering Bot!\n"
    "💡 Я превращаю ваши идеи в точные запросы для нейросетей — без лишних усилий.\n\n"
    "🎯 Методы оптимизации:\n"
    "⚡ Быстро — быстрый результат\n"
    "🛠 По шагам — структурированный подход\n"
    "🎯 Под результат — фокус на цели\n\n"
    "📌 Как это работает:\n"
    "1️⃣ Напишите свою задачу простыми словами\n"
    "2️⃣ Я подберу оптимальную структуру\n"
    "3️⃣ Выберите метод оптимизации\n"
    "4️⃣ Получите готовый запрос — понятный для нейросети 🚀\n\n"
    "✍️ Опишите свою задачу — я сделаю из неё промпт, который сработает сразу.",
    "🤖 Welcome to Prompt Engineering Bot!\n"
    "💡 I transform your ideas into precise queries for AI models — effortlessly.\n\n"
    "🎯 Optimization methods:\n"
    "⚡ Quick — quick results\n"
    "🛠 Step-by-step — structured approach\n"
    "🎯 Result-focused — goal-focused\n\n"
    "📌 How it works:\n"
    "1️⃣ Describe your task in simple words\n"
    "2️⃣ I'll find the optimal structure\n"
    "3️⃣ Choose an optimization method\n"
    "4️⃣ Get a ready query — clear for AI models 🚀\n\n"
    "✍️ Describe your task — I'll create a prompt that works right away.",
)

# New split welcome messages
WELCOME_MESSAGE_1 = _(
    "🤖 Привет. Я PromptEngineer.\n\n"
    "Я превращаю вашу задачу в готовый промпт для нейросети —\n"
    "такой, который можно сразу использовать, без правок и догадок.\n\n"
    "Не нужно знать, как «правильно» писать запросы.\n"
    "Просто опишите, что вам нужно сделать.\n\n"
    "✍️ Опишите свою задачу — я сделаю из неё промпт, который сработает сразу.",
    "🤖 Hi. I'm PromptEngineer.\n\n"
    "I transform your task into a ready-to-use prompt for AI —\n"
    "one you can use immediately, without edits or guesswork.\n\n"
    'You don\'t need to know how to write prompts "correctly."\n'
    "Just describe what you need to do.\n\n"
    "✍️ Describe your task — I'll create a prompt that works right away.",
)

WELCOME_MESSAGE_2 = _(
    "ℹ️ Как работать с PromptEngineer\n\n"
    "1️⃣ Опишите задачу своими словами\n"
    "Не нужно думать о формулировках — пишите как есть.\n\n"
    "2️⃣ Выберите подходящий вариант оптимизации:\n"
    "⚡ Быстро — короткий и рабочий запрос без лишних деталей\n"
    "🛠 По шагам — аккуратно разложенный и структурированный запрос\n"
    "🎯 Под результат — запрос под конкретный формат или итог\n\n"
    "3️⃣ Получите готовый промпт\n"
    "Его можно сразу использовать в нейросети без доработок.\n\n"
    "Если у вас возникнут вопросы по работе сервиса, "
    "воспользуйтесь кнопкой «Техподдержка» — мы поможем разобраться.",
    "ℹ️ How to work with PromptEngineer\n\n"
    "1️⃣ Describe your task in your own words\n"
    "No need to think about wording — just write as is.\n\n"
    "2️⃣ Choose the right optimization option:\n"
    "⚡ Quick — a short, working prompt without extra details\n"
    "🛠 Step-by-step — a neatly organized and structured prompt\n"
    "🎯 Result-focused — a prompt for a specific format or outcome\n\n"
    "3️⃣ Get your ready prompt\n"
    "You can use it immediately in AI without any modifications.\n\n"
    "If you have questions about the service, "
    "use the «Support» button — we'll help you figure it out.",
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

ERROR_VOICE_NOT_SUPPORTED = _(
    "⚠️ Текущая модель не поддерживает голосовые сообщения. Отправьте текст или выберите модель с поддержкой аудио.",
    "⚠️ The current model does not support voice messages. Send text or choose a model with audio support.",
)

ERROR_COUNTRY_REGION_TERRITORY_NOT_SUPPORTED = _(
    "❌ Выбранная страна, регион или территория не поддерживается вашей моделью.",
    "❌ The selected country, region, or territory is not supported by your model.",
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

ERROR_INTERNAL_SERVER = _(
    "❌ Внутренняя ошибка сервера. Пожалуйста, попробуйте позже.",
    "❌ Internal server error. Please try again later.",
)

ERROR_WRONG_API = (
    "❌ Неверный API ключ. Пожалуйста, проверьте настройки и попробуйте снова.",
    "❌ Invalid API key. Please check your settings and try again.",
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
    "📧 Код подтверждения отправлен на {email}.\n\n"
    "🔢 Введите 6-значный код из письма:\n\n"
    "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
    "📧 Verification code sent to {email}.\n\n"
    "🔢 Please enter the 6-digit code from the email:\n\n"
    "By entering the verification code, you consent to the processing of personal data",
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
    "✅ Готово! Я отправил Ваш промпт на e-mail.\n📋 Теперь можно сразу вставить его в ChatGPT, Gemini, Claude или любую другую — и получить ясный результат без лишних шагов.\n➡️ Есть новая задача? Просто напишите её — всё остальное я сделаю за вас.",
    "✅ Done! I sent your prompt to email.\n📋 Now you can directly paste it into ChatGPT, Gemini, Claude or any other — and get clear results without extra steps.\n➡️ Have a new task? Just write it — I'll handle everything else for you.",
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
    "✅ Ваш Email подтвержден",
    "✅ Your Email verified",
)

EMAIL_ALREADY_AUTHENTICATED = _(
    "✅ Вы уже авторизованы! Ваш email {email}",
    "✅ You're already authenticated! Your email {email}",
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

ERROR_POST_OPTIMIZATION_NO_RESULT = _(
    "❌ Нет доступного промпта для отправки на email.\n\n💡 Сначала оптимизируйте промпт одним из методов (CRAFT, LYRA, GGL), а затем используйте кнопку отправки на email.",
    "❌ No prompt available to send to email.\n\n💡 First optimize a prompt using one of the methods (CRAFT, LYRA, GGL), then use the email send button.",
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
    "🔄 Отправляем промпт на email",
    "🔄 Sending prompt to email",
)

INFO_ALL_METHODS_OPTIMIZATION = _(
    "🔄 Запускаем оптимизацию промпта всеми тремя методами...",
    "🔄 Starting prompt optimization with all three methods...",
)

# TEMPORARILY HIDDEN: Original message with email option commented out below
# SELECT_METHOD_MESSAGE_WITH_EMAIL = _(
#     "📝 **Ваш запрос получен!**\n\n"
#     "Теперь выберите один метод оптимизации:\n\n"
#     "⚡ Быстро — мгновенный результат\n"
#     "🛠 По шагам — структурированный подход\n"
#     "🎯 Под результат — фокус на цели, минимум вопросов\n\n"
#     'Или нажмите кнопку "Отправить на e-mail" и получите запрос, '
#     "оптимизированный всеми тремя методами сразу, на вашу почту.\n\n"
#     "👉 *Нажмите на кнопку ниже, чтобы начать*:",
#     "📝 **Your request has been received!**\n\n"
#     "Now choose one optimization method:\n\n"
#     "⚡ Quick — instant results\n"
#     "🛠 Step-by-step — structured approach\n"
#     "🎯 Result-focused — goal-focused, minimal questions\n\n"
#     'Or click the "Send to e-mail" button and receive your request '
#     "optimized with all three methods at once in your email.\n\n"
#     "👉 *Click the button below to start*:",
# )

SELECT_METHOD_MESSAGE = _(
    "📝 **Ваш запрос получен!**\n\n"
    "Теперь выберите один метод оптимизации:\n\n"
    "⚡ Быстро — мгновенный результат\n"
    "🛠 По шагам — структурированный подход\n"
    "🎯 Под результат — фокус на цели, минимум вопросов\n\n"
    "👉 *Нажмите на кнопку ниже, чтобы начать*:",
    "📝 **Your request has been received!**\n\n"
    "Now choose one optimization method:\n\n"
    "⚡ Quick — instant results\n"
    "🛠 Step-by-step — structured approach\n"
    "🎯 Result-focused — goal-focused, minimal questions\n\n"
    "👉 *Click the button below to start*:",
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
    return _(
        "🔄 Обрабатываю ваш промпт...\n\nЭто может занять несколько секунд.",
        "🔄 Processing your prompt...\n\nThis may take a few seconds.",
    )


GENERATING_RESPONSE = _(
    "✨ Генерирую оптимизированный промпт...", "✨ Generating optimized prompt..."
)

# ===== Success Messages =====
RESPONSE_READY = _("✅ Вот ваш оптимизированный промпт:", "✅ Here's your optimized prompt:")

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
    "✅ Готово! Я превратил вашу задачу в понятный запрос для нейросети.\n📋 Теперь можно сразу вставить его в ChatGPT, Gemini, Claude или любую другую — и получить ясный результат без лишних шагов.\n➡️ Есть новая задача? Просто напишите её — всё остальное я сделаю за вас.",
    "✅ Done! I've transformed your task into a clear query for AI.\n📋 Now you can directly paste it into ChatGPT, Gemini, Claude or any other — and get clear results without extra steps.\n➡️ Have a new task? Just write it — I'll handle everything else for you.",
)

FOLLOWUP_DECLINED_MESSAGE = _(
    "✅ Готово! Я превратил вашу задачу в понятный запрос для нейросети.\n📋 Теперь можно сразу вставить его в ChatGPT, Gemini, Claude или любую другую — и получить ясный результат без лишних шагов.\n➡️ Есть новая задача? Просто напишите её — всё остальное я сделаю за вас.",
    "✅ Done! I've transformed your task into a clear query for AI.\n📋 Now you can directly paste it into ChatGPT, Gemini, Claude or any other — and get clear results without extra steps.\n➡️ Have a new task? Just write it — I'll handle everything else for you.",
)

# Follow-up feature messages
FOLLOWUP_OFFER_MESSAGE = _(
    "✅Ваш промпт уже готов к использованию, но мы можем сделать его ещё лучше. Готовы ответить на несколько вопросов?",
    "✅Your prompt is ready to use, but we can make it even better. Ready to answer a few questions?",
)


# ===== Keyboard Layouts =====
# Method selection keyboard
# TEMPORARILY HIDDEN: Email button row commented out - to restore, uncomment the BTN_EMAIL_DELIVERY row
SELECT_METHOD_KEYBOARD = ReplyKeyboardMarkup(
    # [[BTN_EMAIL_DELIVERY], [BTN_LYRA, BTN_CRAFT, BTN_GGL]], resize_keyboard=True  # Original with email
    [[BTN_LYRA, BTN_CRAFT, BTN_GGL]],
    resize_keyboard=True,  # Without email button
)

# Follow-up feature keyboards
# DEPRECATED: Use FOLLOWUP_CHOICE_INLINE_KEYBOARD instead.
# This keyboard is kept for backward compatibility and will be removed in a future version.
# The follow-up choice flow now uses inline buttons attached to the message.
FOLLOWUP_CHOICE_KEYBOARD = ReplyKeyboardMarkup([[BTN_YES, BTN_NO]], resize_keyboard=True)

# Inline keyboard for follow-up choice (attached to message)
FOLLOWUP_CHOICE_INLINE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(BTN_YES, callback_data=CALLBACK_FOLLOWUP_YES),
            InlineKeyboardButton(BTN_NO, callback_data=CALLBACK_FOLLOWUP_NO),
        ]
    ]
)

# Regular keyboard with only Reset button (shown below inline buttons)
FOLLOWUP_CHOICE_RESET_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton(BTN_RESET)]], resize_keyboard=True
)

FOLLOWUP_CONVERSATION_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_GENERATE_PROMPT], [BTN_RESET]], resize_keyboard=True
)

# Post-optimization email keyboards
# TEMPORARILY HIDDEN: Email button row commented out - to restore, uncomment the BTN_POST_OPTIMIZATION_EMAIL row
POST_FOLLOWUP_COMPLETION_KEYBOARD = ReplyKeyboardMarkup(
    # [[BTN_POST_OPTIMIZATION_EMAIL], [BTN_RESET]], resize_keyboard=True  # Original with email
    [[BTN_RESET]],
    resize_keyboard=True,  # Without email button
)

# TEMPORARILY HIDDEN: Email button row commented out - to restore, uncomment the BTN_POST_OPTIMIZATION_EMAIL row
POST_FOLLOWUP_DECLINE_KEYBOARD = ReplyKeyboardMarkup(
    # [[BTN_POST_OPTIMIZATION_EMAIL], [BTN_RESET]], resize_keyboard=True  # Original with email
    [[BTN_RESET]],
    resize_keyboard=True,  # Without email button
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
    safe_user_prompt = user_prompt.replace("`", "\\`").replace("*", "\\*").replace("_", "\\_")
    safe_improved_prompt = (
        improved_prompt.strip().replace("`", "\\`").replace("*", "\\*").replace("_", "\\_")
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
            # Empty content, fall back to original response
            return response.strip(), False

        # No REFINED_PROMPT tag found, return original response
        return response.strip(), False

    except Exception as e:
        # Parsing error, return original response
        import logging

        logging.exception(f"Error parsing follow-up response: {e}")
        return response.strip(), False
