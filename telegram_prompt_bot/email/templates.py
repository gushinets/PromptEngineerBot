"""
Email templates with multilingual support for the Telegram bot.

This module provides email template functionality with Russian/English support
using the same translation pattern as the main messages module.
"""

import html
import re
from typing import Optional


def _(text_ru: str, text_en: str, language: str = "EN") -> str:
    """Helper function for translations in email templates."""
    return text_ru if language.upper() == "RU" else text_en


class EmailTemplates:
    """
    Email template manager with multilingual support.

    Provides HTML and plain text email templates for:
    - OTP verification emails
    - Optimized prompts delivery emails
    """

    def __init__(self, language: str = "EN"):
        """
        Initialize email templates with specified language.

        Args:
            language: Language code ("EN" or "RU")
        """
        self.language = language.upper()

    def _escape_html(self, text: str) -> str:
        """Escape HTML characters in text content and sanitize dangerous protocols."""
        if not text:
            return ""

        # First escape HTML
        escaped = html.escape(text, quote=True)

        # Remove dangerous protocols
        dangerous_protocols = [
            "javascript:",
            "data:",
            "vbscript:",
            "file:",
            "about:",
        ]

        for protocol in dangerous_protocols:
            escaped = re.sub(re.escape(protocol), "", escaped, flags=re.IGNORECASE)

        # Remove dangerous event handlers and attributes (after HTML escaping)
        dangerous_attributes = [
            r"onerror\s*=",
            r"onload\s*=",
            r"onclick\s*=",
            r"onmouseover\s*=",
            r"onfocus\s*=",
            r"onblur\s*=",
            r"onchange\s*=",
            r"onsubmit\s*=",
        ]

        for attr_pattern in dangerous_attributes:
            escaped = re.sub(attr_pattern, "", escaped, flags=re.IGNORECASE)

        # Remove script tags and other dangerous elements
        dangerous_tags = [
            r"<script[^>]*>.*?</script>",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
        ]

        for tag_pattern in dangerous_tags:
            escaped = re.sub(tag_pattern, "", escaped, flags=re.IGNORECASE | re.DOTALL)

        return escaped

    def _format_code_block(self, text: str) -> str:
        """Format text as HTML code block with proper escaping."""
        escaped_text = self._escape_html(text)
        return f"<pre><code>{escaped_text}</code></pre>"

    def _format_plain_code_block(self, text: str) -> str:
        """Format text as plain text code block."""
        return f"```\n{text}\n```"

    def get_otp_subject(self) -> str:
        """Get OTP email subject line."""
        return _(
            "Код подтверждения для Prompt Engineering Bot",
            "Verification Code for Prompt Engineering Bot",
            self.language,
        )

    def get_otp_html_body(self, otp: str) -> str:
        """
        Get OTP email HTML body.

        Args:
            otp: One-time password to include in email

        Returns:
            HTML formatted email body
        """
        title = _("Код подтверждения", "Verification Code", self.language)

        greeting = _("Здравствуйте!", "Hello!", self.language)

        message = _(
            "Ваш код подтверждения для доступа к функции отправки промптов на email:",
            "Your verification code for accessing the email prompt delivery feature:",
            self.language,
        )

        code_label = _("Код подтверждения:", "Verification Code:", self.language)

        expiry_note = _(
            "Код действителен в течение 5 минут.",
            "This code is valid for 5 minutes.",
            self.language,
        )

        security_note = _(
            "Если вы не запрашивали этот код, просто проигнорируйте это письмо.",
            "If you didn't request this code, please ignore this email.",
            self.language,
        )

        signature = _(
            "С уважением,<br>Prompt Engineering Bot",
            "Best regards,<br>Prompt Engineering Bot",
            self.language,
        )

        return f"""
<!DOCTYPE html>
<html lang="{self.language.lower()}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .otp-code {{
            background-color: #f8f9fa;
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }}
        .otp-number {{
            font-size: 32px;
            font-weight: bold;
            color: #007bff;
            letter-spacing: 4px;
            font-family: 'Courier New', monospace;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 14px;
        }}
        .security-note {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            color: #856404;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 {title}</h1>
        </div>
        
        <p>{greeting}</p>
        
        <p>{message}</p>
        
        <div class="otp-code">
            <div style="margin-bottom: 10px;"><strong>{code_label}</strong></div>
            <div class="otp-number">{self._escape_html(otp)}</div>
        </div>
        
        <p><strong>⏰ {expiry_note}</strong></p>
        
        <div class="security-note">
            <strong>🔒 {security_note}</strong>
        </div>
        
        <div class="footer">
            <p>{signature}</p>
        </div>
    </div>
</body>
</html>
"""

    def get_otp_plain_body(self, otp: str) -> str:
        """
        Get OTP email plain text body.

        Args:
            otp: One-time password to include in email

        Returns:
            Plain text formatted email body
        """
        title = _(
            "Код подтверждения для Prompt Engineering Bot",
            "Verification Code for Prompt Engineering Bot",
            self.language,
        )

        greeting = _("Здравствуйте!", "Hello!", self.language)

        message = _(
            "Ваш код подтверждения для доступа к функции отправки промптов на email:",
            "Your verification code for accessing the email prompt delivery feature:",
            self.language,
        )

        expiry_note = _(
            "Код действителен в течение 5 минут.",
            "This code is valid for 5 minutes.",
            self.language,
        )

        security_note = _(
            "Если вы не запрашивали этот код, просто проигнорируйте это письмо.",
            "If you didn't request this code, please ignore this email.",
            self.language,
        )

        signature = _(
            "С уважением,\nPrompt Engineering Bot",
            "Best regards,\nPrompt Engineering Bot",
            self.language,
        )

        return f"""
{title}

{greeting}

{message}

Код подтверждения: {otp}

⏰ {expiry_note}

🔒 {security_note}

{signature}
"""

    def get_optimization_subject(self) -> str:
        """Get optimized prompts email subject line."""
        return _(
            "Ваши 3 оптимизированных промпта готовы",
            "Your 3 Optimized Prompts Are Ready",
            self.language,
        )

    def get_optimization_html_body(
        self,
        original_prompt: str,
        craft_result: str,
        lyra_result: str,
        ggl_result: str,
        improved_prompt: str = None,
    ) -> str:
        """
        Get optimized prompts email HTML body.

        Args:
            original_prompt: User's original prompt
            craft_result: CRAFT optimization result
            lyra_result: LYRA optimization result
            ggl_result: GGL optimization result
            improved_prompt: Improved prompt from follow-up questions (optional)

        Returns:
            HTML formatted email body
        """
        title = _(
            "Ваши оптимизированные промпты", "Your Optimized Prompts", self.language
        )

        greeting = _(
            "Отлично! Ваши промпты готовы.",
            "Great! Your prompts are ready.",
            self.language,
        )

        intro = _(
            "Мы проанализировали ваш запрос и создали три оптимизированные версии с помощью разных методов. Каждый метод имеет свои преимущества:",
            "We analyzed your request and created three optimized versions using different methods. Each method has its own advantages:",
            self.language,
        )

        original_label = _(
            "Ваш исходный промпт:", "Your Original Prompt:", self.language
        )

        improved_label = _(
            "Улучшенный промпт (после уточняющих вопросов):",
            "Improved Prompt (after follow-up questions):",
            self.language,
        )

        craft_label = _(
            "🛠 CRAFT - Структурированный подход:",
            "🛠 CRAFT - Structured Approach:",
            self.language,
        )

        lyra_label = _(
            "⚡ LYRA - Быстрая оптимизация:",
            "⚡ LYRA - Quick Optimization:",
            self.language,
        )

        ggl_label = _(
            "🔍 GGL - Фокус на цели:", "🔍 GGL - Goal-Focused:", self.language
        )

        usage_note = _(
            "Выберите тот промпт, который лучше всего подходит для ваших задач, и используйте его в любом ИИ-помощнике:",
            "Choose the prompt that best fits your needs and use it with any AI assistant:",
            self.language,
        )

        ai_list = _(
            "🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek",
            "🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek",
            self.language,
        )

        signature = _(
            "Удачи в работе с ИИ!<br><br>С уважением,<br>Prompt Engineering Bot",
            "Good luck with your AI work!<br><br>Best regards,<br>Prompt Engineering Bot",
            self.language,
        )

        return f"""
<!DOCTYPE html>
<html lang="{self.language.lower()}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #007bff;
        }}
        .prompt-section {{
            margin: 25px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .original-prompt {{
            background-color: #f8f9fa;
            border-left-color: #6c757d;
        }}
        .improved-prompt {{
            background-color: #e7f3ff;
            border-left-color: #007bff;
        }}
        .craft-prompt {{
            background-color: #fff8e1;
            border-left-color: #ff9800;
        }}
        .lyra-prompt {{
            background-color: #f3e5f5;
            border-left-color: #9c27b0;
        }}
        .ggl-prompt {{
            background-color: #e8f5e8;
            border-left-color: #4caf50;
        }}
        .prompt-label {{
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
        }}
        .prompt-content {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.4;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
        }}
        .usage-section {{
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 20px;
            margin: 30px 0;
        }}
        .ai-list {{
            font-size: 18px;
            text-align: center;
            margin: 15px 0;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 {title}</h1>
            <p>{greeting}</p>
        </div>
        
        <p>{intro}</p>
        
        <div class="prompt-section original-prompt">
            <div class="prompt-label">{original_label}</div>
            <div class="prompt-content">{self._escape_html(original_prompt)}</div>
        </div>
        
        {
            f'''<div class="prompt-section improved-prompt">
            <div class="prompt-label">{improved_label}</div>
            <div class="prompt-content">{self._escape_html(improved_prompt)}</div>
        </div>'''
            if improved_prompt
            else ""
        }
        
        <div class="prompt-section craft-prompt">
            <div class="prompt-label">{craft_label}</div>
            <div class="prompt-content">{self._escape_html(craft_result)}</div>
        </div>
        
        <div class="prompt-section lyra-prompt">
            <div class="prompt-label">{lyra_label}</div>
            <div class="prompt-content">{self._escape_html(lyra_result)}</div>
        </div>
        
        <div class="prompt-section ggl-prompt">
            <div class="prompt-label">{ggl_label}</div>
            <div class="prompt-content">{self._escape_html(ggl_result)}</div>
        </div>
        
        <div class="usage-section">
            <p><strong>💡 {usage_note}</strong></p>
            <div class="ai-list">{ai_list}</div>
        </div>
        
        <div class="footer">
            <p>{signature}</p>
        </div>
    </div>
</body>
</html>
"""

    def get_optimization_plain_body(
        self,
        original_prompt: str,
        craft_result: str,
        lyra_result: str,
        ggl_result: str,
        improved_prompt: str = None,
    ) -> str:
        """
        Get optimized prompts email plain text body.

        Args:
            original_prompt: User's original prompt
            craft_result: CRAFT optimization result
            lyra_result: LYRA optimization result
            ggl_result: GGL optimization result
            improved_prompt: Improved prompt from follow-up questions (optional)

        Returns:
            Plain text formatted email body
        """
        title = _(
            "Ваши оптимизированные промпты", "Your Optimized Prompts", self.language
        )

        greeting = _(
            "Отлично! Ваши промпты готовы.",
            "Great! Your prompts are ready.",
            self.language,
        )

        intro = _(
            "Мы проанализировали ваш запрос и создали три оптимизированные версии с помощью разных методов.",
            "We analyzed your request and created three optimized versions using different methods.",
            self.language,
        )

        original_label = _(
            "ВАШ ИСХОДНЫЙ ПРОМПТ:", "YOUR ORIGINAL PROMPT:", self.language
        )

        improved_label = _(
            "УЛУЧШЕННЫЙ ПРОМПТ (после уточняющих вопросов):",
            "IMPROVED PROMPT (after follow-up questions):",
            self.language,
        )

        craft_label = _(
            "🛠 CRAFT - СТРУКТУРИРОВАННЫЙ ПОДХОД:",
            "🛠 CRAFT - STRUCTURED APPROACH:",
            self.language,
        )

        lyra_label = _(
            "⚡ LYRA - БЫСТРАЯ ОПТИМИЗАЦИЯ:",
            "⚡ LYRA - QUICK OPTIMIZATION:",
            self.language,
        )

        ggl_label = _(
            "🔍 GGL - ФОКУС НА ЦЕЛИ:", "🔍 GGL - GOAL-FOCUSED:", self.language
        )

        usage_note = _(
            "Выберите тот промпт, который лучше всего подходит для ваших задач, и используйте его в любом ИИ-помощнике:",
            "Choose the prompt that best fits your needs and use it with any AI assistant:",
            self.language,
        )

        ai_list = _(
            "🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek",
            "🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek",
            self.language,
        )

        signature = _(
            "Удачи в работе с ИИ!\n\nС уважением,\nPrompt Engineering Bot",
            "Good luck with your AI work!\n\nBest regards,\nPrompt Engineering Bot",
            self.language,
        )

        return f"""
{title}

{greeting}

{intro}

{"=" * 50}
{original_label}
{"=" * 50}
{self._format_plain_code_block(original_prompt)}

{
            f'''{"=" * 50}
{improved_label}
{"=" * 50}
{self._format_plain_code_block(improved_prompt)}

'''
            if improved_prompt
            else ""
        }

{"=" * 50}
{craft_label}
{"=" * 50}
{self._format_plain_code_block(craft_result)}

{"=" * 50}
{lyra_label}
{"=" * 50}
{self._format_plain_code_block(lyra_result)}

{"=" * 50}
{ggl_label}
{"=" * 50}
{self._format_plain_code_block(ggl_result)}

💡 {usage_note}

{ai_list}

{signature}
"""

    def compose_optimization_email(
        self,
        original_prompt: str,
        craft_result: str,
        lyra_result: str,
        ggl_result: str,
        improved_prompt: str = None,
    ) -> tuple[str, str, str]:
        """
        Compose comprehensive optimization email with all three methods.

        Args:
            original_prompt: User's original prompt
            craft_result: CRAFT optimization result
            lyra_result: LYRA optimization result
            ggl_result: GGL optimization result
            improved_prompt: Improved prompt from follow-up questions (optional)

        Returns:
            Tuple of (subject, html_body, plain_body)
        """
        subject = self.get_optimization_subject()
        html_body = self.get_optimization_html_body(
            original_prompt, craft_result, lyra_result, ggl_result, improved_prompt
        )
        plain_body = self.get_optimization_plain_body(
            original_prompt, craft_result, lyra_result, ggl_result, improved_prompt
        )

        return subject, html_body, plain_body

    def get_single_result_subject(self) -> str:
        """Get single optimization result email subject line."""
        return _(
            "Ваш оптимизированный промпт готов",
            "Your Optimized Prompt Is Ready",
            self.language,
        )

    def get_single_result_html_body(
        self,
        original_prompt: str,
        method_name: str,
        optimized_result: str,
    ) -> str:
        """
        Get single optimization result email HTML body.

        Args:
            original_prompt: User's original prompt
            method_name: Name of the optimization method used
            optimized_result: The optimization result

        Returns:
            HTML formatted email body
        """
        title = _(
            "Ваш оптимизированный промпт", "Your Optimized Prompt", self.language
        )

        greeting = _(
            "Отлично! Ваш промпт готов.",
            "Great! Your prompt is ready.",
            self.language,
        )

        intro = _(
            f"Мы оптимизировали ваш запрос с помощью метода {method_name}:",
            f"We optimized your request using the {method_name} method:",
            self.language,
        )

        original_label = _(
            "Ваш исходный промпт:", "Your Original Prompt:", self.language
        )

        optimized_label = _(
            f"Оптимизированный промпт ({method_name}):",
            f"Optimized Prompt ({method_name}):",
            self.language,
        )

        usage_note = _(
            "Теперь вы можете использовать этот оптимизированный промпт в любом ИИ-помощнике:",
            "Now you can use this optimized prompt with any AI assistant:",
            self.language,
        )

        ai_list = _(
            "🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek",
            "🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek",
            self.language,
        )

        signature = _(
            "Удачи в работе с ИИ!<br><br>С уважением,<br>Prompt Engineering Bot",
            "Good luck with your AI work!<br><br>Best regards,<br>Prompt Engineering Bot",
            self.language,
        )

        return f"""
<!DOCTYPE html>
<html lang="{self.language.lower()}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #007bff;
        }}
        .prompt-section {{
            margin: 25px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .original-prompt {{
            background-color: #f8f9fa;
            border-left-color: #6c757d;
        }}
        .optimized-prompt {{
            background-color: #e7f3ff;
            border-left-color: #007bff;
        }}
        .prompt-label {{
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
        }}
        .prompt-content {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.4;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
        }}
        .usage-section {{
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 20px;
            margin: 30px 0;
        }}
        .ai-list {{
            font-size: 18px;
            text-align: center;
            margin: 15px 0;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 {title}</h1>
            <p>{greeting}</p>
        </div>
        
        <p>{intro}</p>
        
        <div class="prompt-section original-prompt">
            <div class="prompt-label">{original_label}</div>
            <div class="prompt-content">{self._escape_html(original_prompt)}</div>
        </div>
        
        <div class="prompt-section optimized-prompt">
            <div class="prompt-label">{optimized_label}</div>
            <div class="prompt-content">{self._escape_html(optimized_result)}</div>
        </div>
        
        <div class="usage-section">
            <p><strong>💡 {usage_note}</strong></p>
            <div class="ai-list">{ai_list}</div>
        </div>
        
        <div class="footer">
            <p>{signature}</p>
        </div>
    </div>
</body>
</html>
"""

    def get_single_result_plain_body(
        self,
        original_prompt: str,
        method_name: str,
        optimized_result: str,
    ) -> str:
        """
        Get single optimization result email plain text body.

        Args:
            original_prompt: User's original prompt
            method_name: Name of the optimization method used
            optimized_result: The optimization result

        Returns:
            Plain text formatted email body
        """
        title = _(
            "Ваш оптимизированный промпт", "Your Optimized Prompt", self.language
        )

        greeting = _(
            "Отлично! Ваш промпт готов.",
            "Great! Your prompt is ready.",
            self.language,
        )

        intro = _(
            f"Мы оптимизировали ваш запрос с помощью метода {method_name}:",
            f"We optimized your request using the {method_name} method:",
            self.language,
        )

        original_label = _(
            "ВАШ ИСХОДНЫЙ ПРОМПТ:", "YOUR ORIGINAL PROMPT:", self.language
        )

        optimized_label = _(
            f"ОПТИМИЗИРОВАННЫЙ ПРОМПТ ({method_name}):",
            f"OPTIMIZED PROMPT ({method_name}):",
            self.language,
        )

        usage_note = _(
            "Теперь вы можете использовать этот оптимизированный промпт в любом ИИ-помощнике:",
            "Now you can use this optimized prompt with any AI assistant:",
            self.language,
        )

        ai_list = _(
            "🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek",
            "🧠 ChatGPT | 🤖 Gemini | 🦾 Claude | 🧬 GROK | 🐳 DeepSeek",
            self.language,
        )

        signature = _(
            "Удачи в работе с ИИ!\n\nС уважением,\nPrompt Engineering Bot",
            "Good luck with your AI work!\n\nBest regards,\nPrompt Engineering Bot",
            self.language,
        )

        return f"""
{title}

{greeting}

{intro}

{"=" * 50}
{original_label}
{"=" * 50}
{self._format_plain_code_block(original_prompt)}

{"=" * 50}
{optimized_label}
{"=" * 50}
{self._format_plain_code_block(optimized_result)}

💡 {usage_note}

{ai_list}

{signature}
"""

    def compose_single_result_email(
        self,
        original_prompt: str,
        method_name: str,
        optimized_result: str,
    ) -> tuple[str, str, str]:
        """
        Compose single optimization result email.

        Args:
            original_prompt: User's original prompt
            method_name: Name of the optimization method used
            optimized_result: The optimization result

        Returns:
            Tuple of (subject, html_body, plain_body)
        """
        subject = self.get_single_result_subject()
        html_body = self.get_single_result_html_body(
            original_prompt, method_name, optimized_result
        )
        plain_body = self.get_single_result_plain_body(
            original_prompt, method_name, optimized_result
        )

        return subject, html_body, plain_body
