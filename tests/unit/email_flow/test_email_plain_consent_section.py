"""
Unit tests for plain text email consent section.

This module tests that the OTP email plain text template includes the consent section
with the correct message text and URL based on language setting.

Validates: Requirements 3.6, 3.7
"""

from telegram_bot.utils.email_templates import EmailTemplates


class TestPlainTextEmailConsentSection:
    """Test cases for plain text email consent section.

    Validates: Requirements 3.6, 3.7
    """

    def test_consent_section_appears_in_plain_text_output(self):
        """Test that consent section appears in plain text output.

        Validates: Requirements 3.6
        """
        templates = EmailTemplates("EN")
        plain_body = templates.get_otp_plain_body("123456")

        # Check that consent message exists in plain text
        expected_consent_text = "By entering the verification code in the bot, you consent to the processing of personal data"
        assert expected_consent_text in plain_body

    def test_consent_section_appears_before_greeting_in_plain_text(self):
        """Test that consent section appears before greeting in plain text.

        Validates: Requirements 3.6
        """
        templates = EmailTemplates("EN")
        plain_body = templates.get_otp_plain_body("123456")

        # Find positions of consent message and greeting
        consent_pos = plain_body.find(
            "By entering the verification code in the bot, you consent to the processing of personal data"
        )
        greeting_pos = plain_body.find("Hello!")

        assert consent_pos != -1, "Consent section not found in plain text"
        assert greeting_pos != -1, "Greeting not found in plain text"
        assert consent_pos < greeting_pos, "Consent section should appear before greeting"

    def test_consent_message_text_matches_english_language_setting(self):
        """Test consent message text matches English language setting.

        Validates: Requirements 3.7
        """
        templates = EmailTemplates("EN")
        plain_body = templates.get_otp_plain_body("123456")

        expected_consent_text = "By entering the verification code in the bot, you consent to the processing of personal data"
        assert expected_consent_text in plain_body

    def test_consent_message_text_matches_russian_language_setting(self):
        """Test consent message text matches Russian language setting.

        Validates: Requirements 3.7
        """
        templates = EmailTemplates("RU")
        plain_body = templates.get_otp_plain_body("123456")

        expected_consent_text = (
            "Вводя код подтверждения в бота, вы даёте согласие на обработку персональных данных"
        )
        assert expected_consent_text in plain_body

    def test_url_is_included_in_plain_text(self):
        """Test that agreement URL is included in plain text.

        Validates: Requirements 3.6
        """
        templates = EmailTemplates("EN")
        plain_body = templates.get_otp_plain_body("123456")

        expected_url = "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"
        assert expected_url in plain_body

    def test_url_is_included_in_russian_plain_text(self):
        """Test that agreement URL is included in Russian plain text.

        Validates: Requirements 3.6
        """
        templates = EmailTemplates("RU")
        plain_body = templates.get_otp_plain_body("123456")

        expected_url = "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"
        assert expected_url in plain_body

    def test_link_text_matches_english_language_setting(self):
        """Test link text matches English language setting.

        Validates: Requirements 3.7
        """
        templates = EmailTemplates("EN")
        plain_body = templates.get_otp_plain_body("123456")

        expected_link_text = "📄 Personal Data Processing Agreement"
        assert expected_link_text in plain_body

    def test_link_text_matches_russian_language_setting(self):
        """Test link text matches Russian language setting.

        Validates: Requirements 3.7
        """
        templates = EmailTemplates("RU")
        plain_body = templates.get_otp_plain_body("123456")

        expected_link_text = "📄 Согласие на обработку персональных данных"
        assert expected_link_text in plain_body

    def test_consent_section_contains_legal_icon(self):
        """Test that consent section contains the legal/balance icon.

        Validates: Requirements 3.6
        """
        templates = EmailTemplates("EN")
        plain_body = templates.get_otp_plain_body("123456")

        # Check for the legal icon (⚖️)
        assert "⚖️" in plain_body

    def test_english_plain_text_does_not_contain_russian_consent_text(self):
        """Test that English plain text does not contain Russian consent text.

        Validates: Requirements 3.7
        """
        templates = EmailTemplates("EN")
        plain_body = templates.get_otp_plain_body("123456")

        russian_consent_text = (
            "Вводя код подтверждения в бота, вы даёте согласие на обработку персональных данных"
        )
        assert russian_consent_text not in plain_body

    def test_russian_plain_text_does_not_contain_english_consent_text(self):
        """Test that Russian plain text does not contain English consent text.

        Validates: Requirements 3.7
        """
        templates = EmailTemplates("RU")
        plain_body = templates.get_otp_plain_body("123456")

        english_consent_text = "By entering the verification code in the bot, you consent to the processing of personal data"
        assert english_consent_text not in plain_body
