"""Property-based tests for OTP consent agreement feature.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the OTP consent
agreement feature.

**Feature: otp-consent-agreement**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

import telegram_bot.utils.messages as messages_module


class TestOTPMessageContainsConsentText:
    """
    **Feature: otp-consent-agreement, Property 1: OTP Message Contains Consent Text**
    **Validates: Requirements 1.1, 1.2, 1.3**

    Property 1: OTP Message Contains Consent Text
    *For any* language setting (Russian or English), the EMAIL_OTP_SENT message
    SHALL contain the corresponding consent message text.
    """

    @given(email=st.emails())
    @settings(max_examples=100, deadline=None)
    def test_otp_message_contains_consent_text_russian(self, email: str):
        """
        **Feature: otp-consent-agreement, Property 1: OTP Message Contains Consent Text**
        **Validates: Requirements 1.1, 1.2, 1.3**

        For any email address, when language is Russian, the EMAIL_OTP_SENT message
        formatted with that email SHALL contain the Russian consent message text.
        """
        # Import with Russian language setting

        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set Russian language
            messages_module.LANGUAGE = "ru"

            # Re-evaluate the message with Russian language
            email_otp_sent_ru = messages_module._(
                "📧 Код подтверждения отправлен на {email}.\n\n"
                "🔢 Введите 6-значный код из письма:\n\n"
                "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
                "📧 Verification code sent to {email}.\n\n"
                "🔢 Please enter the 6-digit code from the email:\n\n"
                "By entering the verification code, you consent to the processing of personal data",
            )

            # Format the message with the generated email
            formatted_message = email_otp_sent_ru.format(email=email)

            # Russian consent text that must be present
            russian_consent_text = (
                "Вводя код подтверждения, вы даёте согласие на обработку персональных данных"
            )

            # Property assertion: message must contain Russian consent text
            assert russian_consent_text in formatted_message, (
                f"EMAIL_OTP_SENT (Russian) must contain consent text.\n"
                f"Expected: '{russian_consent_text}'\n"
                f"Got message: '{formatted_message}'"
            )

            # Additional assertion: message should contain the email
            assert email in formatted_message, (
                f"EMAIL_OTP_SENT must contain the email address.\n"
                f"Expected email: '{email}'\n"
                f"Got message: '{formatted_message}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language

    @given(email=st.emails())
    @settings(max_examples=100, deadline=None)
    def test_otp_message_contains_consent_text_english(self, email: str):
        """
        **Feature: otp-consent-agreement, Property 1: OTP Message Contains Consent Text**
        **Validates: Requirements 1.1, 1.2, 1.3**

        For any email address, when language is English, the EMAIL_OTP_SENT message
        formatted with that email SHALL contain the English consent message text.
        """
        # Import with English language setting

        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set English language
            messages_module.LANGUAGE = "en"

            # Re-evaluate the message with English language
            email_otp_sent_en = messages_module._(
                "📧 Код подтверждения отправлен на {email}.\n\n"
                "🔢 Введите 6-значный код из письма:\n\n"
                "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
                "📧 Verification code sent to {email}.\n\n"
                "🔢 Please enter the 6-digit code from the email:\n\n"
                "By entering the verification code, you consent to the processing of personal data",
            )

            # Format the message with the generated email
            formatted_message = email_otp_sent_en.format(email=email)

            # English consent text that must be present
            english_consent_text = (
                "By entering the verification code, you consent to the processing of personal data"
            )

            # Property assertion: message must contain English consent text
            assert english_consent_text in formatted_message, (
                f"EMAIL_OTP_SENT (English) must contain consent text.\n"
                f"Expected: '{english_consent_text}'\n"
                f"Got message: '{formatted_message}'"
            )

            # Additional assertion: message should contain the email
            assert email in formatted_message, (
                f"EMAIL_OTP_SENT must contain the email address.\n"
                f"Expected email: '{email}'\n"
                f"Got message: '{formatted_message}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language

    @given(language=st.sampled_from(["ru", "en"]), email=st.emails())
    @settings(max_examples=100, deadline=None)
    def test_otp_message_consent_text_matches_language(self, language: str, email: str):
        """
        **Feature: otp-consent-agreement, Property 1: OTP Message Contains Consent Text**
        **Validates: Requirements 1.1, 1.2, 1.3**

        For any language setting and any email address, the EMAIL_OTP_SENT message
        SHALL contain the consent text in the corresponding language.
        """

        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set the language
            messages_module.LANGUAGE = language

            # Re-evaluate the message with the current language setting
            email_otp_sent = messages_module._(
                "📧 Код подтверждения отправлен на {email}.\n\n"
                "🔢 Введите 6-значный код из письма:\n\n"
                "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
                "📧 Verification code sent to {email}.\n\n"
                "🔢 Please enter the 6-digit code from the email:\n\n"
                "By entering the verification code, you consent to the processing of personal data",
            )

            # Format the message with the generated email
            formatted_message = email_otp_sent.format(email=email)

            # Define expected consent text based on language
            consent_texts = {
                "ru": (
                    "Вводя код подтверждения, вы даёте согласие на обработку персональных данных"
                ),
                "en": (
                    "By entering the verification code, you consent "
                    "to the processing of personal data"
                ),
            }

            expected_consent = consent_texts[language]

            # Property assertion: message must contain consent text for the language
            assert expected_consent in formatted_message, (
                f"EMAIL_OTP_SENT ({language}) must contain consent text.\n"
                f"Expected: '{expected_consent}'\n"
                f"Got message: '{formatted_message}'"
            )

            # Property assertion: message must contain the email
            assert email in formatted_message, (
                f"EMAIL_OTP_SENT must contain the email address.\n"
                f"Expected email: '{email}'\n"
                f"Got message: '{formatted_message}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language


class TestAgreementButtonHasCorrectURL:
    """
    **Feature: otp-consent-agreement, Property 2: Agreement Button Has Correct URL**
    **Validates: Requirements 2.1, 2.4**

    Property 2: Agreement Button Has Correct URL
    *For any* InlineKeyboardButton created for the data agreement, the button's
    URL property SHALL equal the Agreement_URL constant.
    """

    @given(language=st.sampled_from(["ru", "en"]))
    @settings(max_examples=100, deadline=None)
    def test_agreement_button_url_matches_constant(self, language: str):
        """
        **Feature: otp-consent-agreement, Property 2: Agreement Button Has Correct URL**
        **Validates: Requirements 2.1, 2.4**

        For any language setting, the DATA_AGREEMENT_KEYBOARD inline button's URL
        SHALL equal the DATA_AGREEMENT_URL constant.
        """
        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set the language
            messages_module.LANGUAGE = language

            # Get the expected URL constant
            expected_url = messages_module.DATA_AGREEMENT_URL

            # Get the keyboard and extract the button URL
            keyboard = messages_module.DATA_AGREEMENT_KEYBOARD
            button = keyboard.inline_keyboard[0][0]
            actual_url = button.url

            # Property assertion: button URL must equal the constant
            assert actual_url == expected_url, (
                f"DATA_AGREEMENT_KEYBOARD button URL must equal DATA_AGREEMENT_URL.\n"
                f"Expected: '{expected_url}'\n"
                f"Got: '{actual_url}'"
            )

            # Property assertion: URL must be the specific agreement URL
            assert actual_url == "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q", (
                f"Agreement URL must be the Yandex Disk link.\n"
                f"Expected: 'https://disk.yandex.ru/i/zGiuY7mtIfOA-Q'\n"
                f"Got: '{actual_url}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=100, deadline=None)
    def test_agreement_keyboard_structure_is_valid(self, _iteration: int):
        """
        **Feature: otp-consent-agreement, Property 2: Agreement Button Has Correct URL**
        **Validates: Requirements 2.1, 2.4**

        The DATA_AGREEMENT_KEYBOARD SHALL have exactly one row with one button,
        and that button SHALL have a valid URL.
        """
        keyboard = messages_module.DATA_AGREEMENT_KEYBOARD

        # Property assertion: keyboard must have exactly one row
        assert len(keyboard.inline_keyboard) == 1, (
            f"DATA_AGREEMENT_KEYBOARD must have exactly 1 row.\n"
            f"Got: {len(keyboard.inline_keyboard)} rows"
        )

        # Property assertion: row must have exactly one button
        assert len(keyboard.inline_keyboard[0]) == 1, (
            f"DATA_AGREEMENT_KEYBOARD row must have exactly 1 button.\n"
            f"Got: {len(keyboard.inline_keyboard[0])} buttons"
        )

        # Property assertion: button must have a URL (not None)
        button = keyboard.inline_keyboard[0][0]
        assert button.url is not None, "DATA_AGREEMENT_KEYBOARD button must have a URL"

        # Property assertion: URL must start with https://
        assert button.url.startswith("https://"), (
            f"Agreement button URL must use HTTPS.\nGot: '{button.url}'"
        )

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=100, deadline=None)
    def test_agreement_button_has_valid_text(self, _iteration: int):
        """
        **Feature: otp-consent-agreement, Property 2: Agreement Button Has Correct URL**
        **Validates: Requirements 2.1, 2.4**

        The DATA_AGREEMENT_KEYBOARD button SHALL have non-empty text
        containing the document emoji and be one of the valid translations.
        """
        # Get the keyboard and extract the button
        keyboard = messages_module.DATA_AGREEMENT_KEYBOARD
        button = keyboard.inline_keyboard[0][0]

        # Property assertion: button must have non-empty text
        assert button.text, "DATA_AGREEMENT_KEYBOARD button must have text"

        # Property assertion: button text must contain the document emoji
        assert "📄" in button.text, (
            f"Agreement button text must contain document emoji.\nGot: '{button.text}'"
        )

        # Property assertion: button text must be one of the valid translations
        valid_texts = [
            "📄 Согласие на обработку персональных данных",
            "📄 Personal Data Processing Agreement",
        ]
        assert button.text in valid_texts, (
            f"Agreement button text must be a valid translation.\n"
            f"Expected one of: {valid_texts}\n"
            f"Got: '{button.text}'"
        )


class TestEmailConsentSectionContainsRequiredElements:
    """
    **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6, 3.7**

    Property 3: Email Consent Section Contains Required Elements
    *For any* OTP email generated by the Email_Service, the email body SHALL contain:
    - The consent message text matching the current language setting
    - A clickable link/button with text matching the current language setting
    - The link href pointing to the Agreement_URL
    """

    @given(
        language=st.sampled_from(["EN", "RU"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_html_email_contains_consent_message_for_language(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
        **Validates: Requirements 3.1, 3.2, 3.7**

        For any language setting and any valid OTP, the HTML email body SHALL contain
        the consent message text in the corresponding language.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates(language)
        html_body = templates.get_otp_html_body(otp)

        # Define expected consent text based on language
        consent_texts = {
            "RU": "Вводя код подтверждения в бота, вы даёте согласие на обработку персональных данных",
            "EN": "By entering the verification code in the bot, you consent to the processing of personal data",
        }

        expected_consent = consent_texts[language]

        # Property assertion: HTML email must contain consent message for the language
        assert expected_consent in html_body, (
            f"HTML email ({language}) must contain consent message.\n"
            f"Expected: '{expected_consent}'\n"
            f"OTP: '{otp}'"
        )

    @given(
        language=st.sampled_from(["EN", "RU"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_html_email_contains_agreement_link_text_for_language(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
        **Validates: Requirements 3.3, 3.7**

        For any language setting and any valid OTP, the HTML email body SHALL contain
        the agreement link/button text in the corresponding language.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates(language)
        html_body = templates.get_otp_html_body(otp)

        # Define expected link text based on language
        link_texts = {
            "RU": "📄 Согласие на обработку персональных данных",
            "EN": "📄 Personal Data Processing Agreement",
        }

        expected_link_text = link_texts[language]

        # Property assertion: HTML email must contain link text for the language
        assert expected_link_text in html_body, (
            f"HTML email ({language}) must contain agreement link text.\n"
            f"Expected: '{expected_link_text}'\n"
            f"OTP: '{otp}'"
        )

    @given(
        language=st.sampled_from(["EN", "RU"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_html_email_contains_correct_agreement_url(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
        **Validates: Requirements 3.4**

        For any language setting and any valid OTP, the HTML email body SHALL contain
        the correct agreement URL.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates(language)
        html_body = templates.get_otp_html_body(otp)

        expected_url = "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"

        # Property assertion: HTML email must contain the agreement URL
        assert expected_url in html_body, (
            f"HTML email ({language}) must contain agreement URL.\n"
            f"Expected: '{expected_url}'\n"
            f"OTP: '{otp}'"
        )

        # Property assertion: URL must be in an href attribute
        assert f'href="{expected_url}"' in html_body, (
            f"HTML email ({language}) must have agreement URL in href attribute.\n"
            f"Expected: 'href=\"{expected_url}\"'\n"
            f"OTP: '{otp}'"
        )

    @given(
        language=st.sampled_from(["EN", "RU"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_plain_email_contains_consent_message_for_language(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
        **Validates: Requirements 3.6, 3.7**

        For any language setting and any valid OTP, the plain text email body SHALL contain
        the consent message text in the corresponding language.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates(language)
        plain_body = templates.get_otp_plain_body(otp)

        # Define expected consent text based on language
        consent_texts = {
            "RU": "Вводя код подтверждения в бота, вы даёте согласие на обработку персональных данных",
            "EN": "By entering the verification code in the bot, you consent to the processing of personal data",
        }

        expected_consent = consent_texts[language]

        # Property assertion: plain text email must contain consent message for the language
        assert expected_consent in plain_body, (
            f"Plain text email ({language}) must contain consent message.\n"
            f"Expected: '{expected_consent}'\n"
            f"OTP: '{otp}'"
        )

    @given(
        language=st.sampled_from(["EN", "RU"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_plain_email_contains_agreement_link_text_for_language(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
        **Validates: Requirements 3.6, 3.7**

        For any language setting and any valid OTP, the plain text email body SHALL contain
        the agreement link text in the corresponding language.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates(language)
        plain_body = templates.get_otp_plain_body(otp)

        # Define expected link text based on language
        link_texts = {
            "RU": "📄 Согласие на обработку персональных данных",
            "EN": "📄 Personal Data Processing Agreement",
        }

        expected_link_text = link_texts[language]

        # Property assertion: plain text email must contain link text for the language
        assert expected_link_text in plain_body, (
            f"Plain text email ({language}) must contain agreement link text.\n"
            f"Expected: '{expected_link_text}'\n"
            f"OTP: '{otp}'"
        )

    @given(
        language=st.sampled_from(["EN", "RU"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_plain_email_contains_correct_agreement_url(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
        **Validates: Requirements 3.6**

        For any language setting and any valid OTP, the plain text email body SHALL contain
        the correct agreement URL.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates(language)
        plain_body = templates.get_otp_plain_body(otp)

        expected_url = "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"

        # Property assertion: plain text email must contain the agreement URL
        assert expected_url in plain_body, (
            f"Plain text email ({language}) must contain agreement URL.\n"
            f"Expected: '{expected_url}'\n"
            f"OTP: '{otp}'"
        )

    @given(
        language=st.sampled_from(["EN", "RU"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_html_email_consent_section_appears_before_greeting(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
        **Validates: Requirements 3.1**

        For any language setting and any valid OTP, the HTML email consent section
        SHALL appear before the greeting.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates(language)
        html_body = templates.get_otp_html_body(otp)

        # Define greeting based on language
        greetings = {
            "RU": "Здравствуйте!",
            "EN": "Hello!",
        }

        greeting = greetings[language]
        consent_section_marker = 'class="consent-section"'

        consent_pos = html_body.find(consent_section_marker)
        greeting_pos = html_body.find(greeting)

        # Property assertion: consent section must exist
        assert consent_pos != -1, (
            f"HTML email ({language}) must contain consent section.\nOTP: '{otp}'"
        )

        # Property assertion: greeting must exist
        assert greeting_pos != -1, (
            f"HTML email ({language}) must contain greeting.\nExpected: '{greeting}'\nOTP: '{otp}'"
        )

        # Property assertion: consent section must appear before greeting
        assert consent_pos < greeting_pos, (
            f"HTML email ({language}) consent section must appear before greeting.\n"
            f"Consent position: {consent_pos}, Greeting position: {greeting_pos}\n"
            f"OTP: '{otp}'"
        )

    @given(
        language=st.sampled_from(["EN", "RU"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_plain_email_consent_section_appears_before_greeting(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 3: Email Consent Section Contains Required Elements**
        **Validates: Requirements 3.6**

        For any language setting and any valid OTP, the plain text email consent section
        SHALL appear before the greeting.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates(language)
        plain_body = templates.get_otp_plain_body(otp)

        # Define consent text and greeting based on language
        consent_texts = {
            "RU": "Вводя код подтверждения в бота, вы даёте согласие на обработку персональных данных",
            "EN": "By entering the verification code in the bot, you consent to the processing of personal data",
        }
        greetings = {
            "RU": "Здравствуйте!",
            "EN": "Hello!",
        }

        consent_text = consent_texts[language]
        greeting = greetings[language]

        consent_pos = plain_body.find(consent_text)
        greeting_pos = plain_body.find(greeting)

        # Property assertion: consent text must exist
        assert consent_pos != -1, (
            f"Plain text email ({language}) must contain consent text.\nOTP: '{otp}'"
        )

        # Property assertion: greeting must exist
        assert greeting_pos != -1, (
            f"Plain text email ({language}) must contain greeting.\n"
            f"Expected: '{greeting}'\n"
            f"OTP: '{otp}'"
        )

        # Property assertion: consent text must appear before greeting
        assert consent_pos < greeting_pos, (
            f"Plain text email ({language}) consent section must appear before greeting.\n"
            f"Consent position: {consent_pos}, Greeting position: {greeting_pos}\n"
            f"OTP: '{otp}'"
        )


class TestLanguageConsistency:
    """
    **Feature: otp-consent-agreement, Property 4: Language Consistency**
    **Validates: Requirements 1.2, 1.3, 2.2, 2.3, 3.7**

    Property 4: Language Consistency
    *For any* language setting, the consent message text in Telegram and email SHALL use
    the same language, and the button/link text SHALL use the same language.

    Note: Email templates use slightly different consent text ("в бота"/"in the bot")
    than Telegram messages, but both must be in the same language.
    """

    @given(otp=st.text(alphabet="0123456789", min_size=6, max_size=6))
    @settings(max_examples=100, deadline=None)
    def test_russian_consent_message_consistency(self, otp: str):
        """
        **Feature: otp-consent-agreement, Property 4: Language Consistency**
        **Validates: Requirements 1.2, 2.2, 3.7**

        For Russian language setting, the consent message text in Telegram messages
        and email templates SHALL both be in Russian.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set Russian language for Telegram messages
            messages_module.LANGUAGE = "ru"

            # Get Telegram consent message (Russian)
            telegram_consent = messages_module._(
                "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
                "By entering the verification code, you consent to the processing of personal data",
            )

            # Get email consent message (Russian)
            templates = EmailTemplates("RU")
            html_body = templates.get_otp_html_body(otp)
            plain_body = templates.get_otp_plain_body(otp)

            # Expected Russian consent text for Telegram
            expected_telegram_ru_consent = (
                "Вводя код подтверждения, вы даёте согласие на обработку персональных данных"
            )

            # Expected Russian consent text for Email (includes "в бота")
            expected_email_ru_consent = (
                "Вводя код подтверждения в бота, вы даёте согласие на обработку персональных данных"
            )

            # Property assertion: Telegram consent must match expected Russian text
            assert telegram_consent == expected_telegram_ru_consent, (
                f"Telegram consent message must be in Russian.\n"
                f"Expected: '{expected_telegram_ru_consent}'\n"
                f"Got: '{telegram_consent}'"
            )

            # Property assertion: HTML email must contain Russian consent text
            assert expected_email_ru_consent in html_body, (
                f"HTML email consent must be in Russian.\nExpected: '{expected_email_ru_consent}'"
            )

            # Property assertion: Plain text email must contain Russian consent
            assert expected_email_ru_consent in plain_body, (
                f"Plain text email consent must be in Russian.\n"
                f"Expected: '{expected_email_ru_consent}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language

    @given(otp=st.text(alphabet="0123456789", min_size=6, max_size=6))
    @settings(max_examples=100, deadline=None)
    def test_english_consent_message_consistency(self, otp: str):
        """
        **Feature: otp-consent-agreement, Property 4: Language Consistency**
        **Validates: Requirements 1.3, 2.3, 3.7**

        For English language setting, the consent message text in Telegram messages
        and email templates SHALL both be in English.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set English language for Telegram messages
            messages_module.LANGUAGE = "en"

            # Get Telegram consent message (English)
            telegram_consent = messages_module._(
                "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
                "By entering the verification code, you consent to the processing of personal data",
            )

            # Get email consent message (English)
            templates = EmailTemplates("EN")
            html_body = templates.get_otp_html_body(otp)
            plain_body = templates.get_otp_plain_body(otp)

            # Expected English consent text for Telegram
            expected_telegram_en_consent = (
                "By entering the verification code, you consent to the processing of personal data"
            )

            # Expected English consent text for Email (includes "in the bot")
            expected_email_en_consent = "By entering the verification code in the bot, you consent to the processing of personal data"

            # Property assertion: Telegram consent must match expected English text
            assert telegram_consent == expected_telegram_en_consent, (
                f"Telegram consent message must be in English.\n"
                f"Expected: '{expected_telegram_en_consent}'\n"
                f"Got: '{telegram_consent}'"
            )

            # Property assertion: HTML email must contain English consent text
            assert expected_email_en_consent in html_body, (
                f"HTML email consent must be in English.\nExpected: '{expected_email_en_consent}'"
            )

            # Property assertion: Plain text email must contain English consent
            assert expected_email_en_consent in plain_body, (
                f"Plain text email consent must be in English.\n"
                f"Expected: '{expected_email_en_consent}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language

    @given(otp=st.text(alphabet="0123456789", min_size=6, max_size=6))
    @settings(max_examples=100, deadline=None)
    def test_russian_button_text_consistency(self, otp: str):
        """
        **Feature: otp-consent-agreement, Property 4: Language Consistency**
        **Validates: Requirements 2.2, 3.7**

        For Russian language setting, the agreement button/link text in Telegram
        and email templates SHALL be identical.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set Russian language for Telegram messages
            messages_module.LANGUAGE = "ru"

            # Get Telegram button text (Russian)
            telegram_button_text = messages_module._(
                "📄 Согласие на обработку персональных данных",
                "📄 Personal Data Processing Agreement",
            )

            # Get email button/link text (Russian)
            templates = EmailTemplates("RU")
            html_body = templates.get_otp_html_body(otp)
            plain_body = templates.get_otp_plain_body(otp)

            # Expected Russian button text
            expected_ru_button = "📄 Согласие на обработку персональных данных"

            # Property assertion: Telegram button text must match expected Russian text
            assert telegram_button_text == expected_ru_button, (
                f"Telegram button text must be in Russian.\n"
                f"Expected: '{expected_ru_button}'\n"
                f"Got: '{telegram_button_text}'"
            )

            # Property assertion: HTML email must contain the same Russian button text
            assert expected_ru_button in html_body, (
                f"HTML email button text must match Telegram button (Russian).\n"
                f"Expected: '{expected_ru_button}'"
            )

            # Property assertion: Plain text email must contain the same Russian button
            assert expected_ru_button in plain_body, (
                f"Plain text email link text must match Telegram button (Russian).\n"
                f"Expected: '{expected_ru_button}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language

    @given(otp=st.text(alphabet="0123456789", min_size=6, max_size=6))
    @settings(max_examples=100, deadline=None)
    def test_english_button_text_consistency(self, otp: str):
        """
        **Feature: otp-consent-agreement, Property 4: Language Consistency**
        **Validates: Requirements 2.3, 3.7**

        For English language setting, the agreement button/link text in Telegram
        and email templates SHALL be identical.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set English language for Telegram messages
            messages_module.LANGUAGE = "en"

            # Get Telegram button text (English)
            telegram_button_text = messages_module._(
                "📄 Согласие на обработку персональных данных",
                "📄 Personal Data Processing Agreement",
            )

            # Get email button/link text (English)
            templates = EmailTemplates("EN")
            html_body = templates.get_otp_html_body(otp)
            plain_body = templates.get_otp_plain_body(otp)

            # Expected English button text
            expected_en_button = "📄 Personal Data Processing Agreement"

            # Property assertion: Telegram button text must match expected English text
            assert telegram_button_text == expected_en_button, (
                f"Telegram button text must be in English.\n"
                f"Expected: '{expected_en_button}'\n"
                f"Got: '{telegram_button_text}'"
            )

            # Property assertion: HTML email must contain the same English button text
            assert expected_en_button in html_body, (
                f"HTML email button text must match Telegram button (English).\n"
                f"Expected: '{expected_en_button}'"
            )

            # Property assertion: Plain text email must contain the same English button
            assert expected_en_button in plain_body, (
                f"Plain text email link text must match Telegram button (English).\n"
                f"Expected: '{expected_en_button}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language

    @given(
        language=st.sampled_from(["ru", "en"]),
        otp=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_language_consistency_across_all_components(self, language: str, otp: str):
        """
        **Feature: otp-consent-agreement, Property 4: Language Consistency**
        **Validates: Requirements 1.2, 1.3, 2.2, 2.3, 3.7**

        For any language setting, the consent message and button text in Telegram
        messages and email templates SHALL use the same language consistently.

        Note: Email templates use slightly different consent text ("в бота"/"in the bot")
        than Telegram messages, but both must be in the same language.
        """
        from telegram_bot.utils.email_templates import EmailTemplates

        # Store original language
        original_language = messages_module.LANGUAGE

        try:
            # Set the language for Telegram messages
            messages_module.LANGUAGE = language

            # Map language codes for email templates (email uses uppercase)
            email_language = language.upper()

            # Define expected texts based on language for Telegram
            expected_telegram_consent = {
                "ru": "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
                "en": "By entering the verification code, you consent to the "
                "processing of personal data",
            }

            # Define expected texts based on language for Email (includes "в бота"/"in the bot")
            expected_email_consent = {
                "ru": "Вводя код подтверждения в бота, вы даёте согласие на обработку персональных данных",
                "en": "By entering the verification code in the bot, you consent to the "
                "processing of personal data",
            }

            expected_button = {
                "ru": "📄 Согласие на обработку персональных данных",
                "en": "📄 Personal Data Processing Agreement",
            }

            # Get Telegram messages
            telegram_consent = messages_module._(
                "Вводя код подтверждения, вы даёте согласие на обработку персональных данных",
                "By entering the verification code, you consent to the processing of personal data",
            )
            telegram_button = messages_module._(
                "📄 Согласие на обработку персональных данных",
                "📄 Personal Data Processing Agreement",
            )

            # Get email templates
            templates = EmailTemplates(email_language)
            html_body = templates.get_otp_html_body(otp)
            plain_body = templates.get_otp_plain_body(otp)

            # Property assertion: Telegram consent matches expected language
            assert telegram_consent == expected_telegram_consent[language], (
                f"Telegram consent must be in {language}.\n"
                f"Expected: '{expected_telegram_consent[language]}'\n"
                f"Got: '{telegram_consent}'"
            )

            # Property assertion: Telegram button matches expected language
            assert telegram_button == expected_button[language], (
                f"Telegram button must be in {language}.\n"
                f"Expected: '{expected_button[language]}'\n"
                f"Got: '{telegram_button}'"
            )

            # Property assertion: HTML email consent is in correct language
            assert expected_email_consent[language] in html_body, (
                f"HTML email consent must be in {language}.\n"
                f"Expected: '{expected_email_consent[language]}'"
            )

            # Property assertion: HTML email button matches Telegram button
            assert expected_button[language] in html_body, (
                f"HTML email button must match Telegram ({language}).\n"
                f"Expected: '{expected_button[language]}'"
            )

            # Property assertion: Plain text email consent is in correct language
            assert expected_email_consent[language] in plain_body, (
                f"Plain text email consent must be in {language}.\n"
                f"Expected: '{expected_email_consent[language]}'"
            )

            # Property assertion: Plain text email button matches Telegram button
            assert expected_button[language] in plain_body, (
                f"Plain text email button must match Telegram ({language}).\n"
                f"Expected: '{expected_button[language]}'"
            )

        finally:
            # Restore original language
            messages_module.LANGUAGE = original_language
