"""
Unit tests for HTML email consent section.

This module tests that the OTP email HTML template includes the consent section
with the correct message text, link URL, and link text based on language setting.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.7
"""

from telegram_bot.utils.email_templates import EmailTemplates


class TestHtmlEmailConsentSection:
    """Test cases for HTML email consent section.

    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.7
    """

    def test_consent_section_appears_in_html_output(self):
        """Test that consent section appears in HTML output.

        Validates: Requirements 3.1
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        # Check that consent section div exists
        assert 'class="consent-section"' in html_body

    def test_consent_section_appears_before_greeting_in_html(self):
        """Test that consent section appears before greeting in HTML.

        Validates: Requirements 3.1
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        # Find positions of consent section and greeting
        consent_pos = html_body.find('class="consent-section"')
        greeting_pos = html_body.find("Hello!")

        assert consent_pos != -1, "Consent section not found in HTML"
        assert greeting_pos != -1, "Greeting not found in HTML"
        assert consent_pos < greeting_pos, "Consent section should appear before greeting"

    def test_consent_message_text_matches_english_language_setting(self):
        """Test consent message text matches English language setting.

        Validates: Requirements 3.2, 3.7
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        expected_consent_text = (
            "By entering the verification code, you consent to the processing of personal data"
        )
        assert expected_consent_text in html_body

    def test_consent_message_text_matches_russian_language_setting(self):
        """Test consent message text matches Russian language setting.

        Validates: Requirements 3.2, 3.7
        """
        templates = EmailTemplates("RU")
        html_body = templates.get_otp_html_body("123456")

        expected_consent_text = (
            "Вводя код подтверждения, вы даёте согласие на обработку персональных данных"
        )
        assert expected_consent_text in html_body

    def test_link_url_is_correct(self):
        """Test that link URL is correct.

        Validates: Requirements 3.4
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        expected_url = "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"
        assert f'href="{expected_url}"' in html_body

    def test_link_url_is_correct_russian(self):
        """Test that link URL is correct for Russian language.

        Validates: Requirements 3.4
        """
        templates = EmailTemplates("RU")
        html_body = templates.get_otp_html_body("123456")

        expected_url = "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"
        assert f'href="{expected_url}"' in html_body

    def test_link_text_matches_english_language_setting(self):
        """Test link text matches English language setting.

        Validates: Requirements 3.3, 3.7
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        expected_link_text = "📄 Personal Data Processing Agreement"
        assert expected_link_text in html_body

    def test_link_text_matches_russian_language_setting(self):
        """Test link text matches Russian language setting.

        Validates: Requirements 3.3, 3.7
        """
        templates = EmailTemplates("RU")
        html_body = templates.get_otp_html_body("123456")

        expected_link_text = "📄 Согласие на обработку персональных данных"
        assert expected_link_text in html_body

    def test_consent_section_has_agreement_button_class(self):
        """Test that consent section has agreement button with correct class.

        Validates: Requirements 3.3
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        assert 'class="agreement-button"' in html_body

    def test_consent_section_is_visually_highlighted(self):
        """Test that consent section has visual highlighting styles.

        Validates: Requirements 3.5 (implied by 3.1)
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        # Check for consent section styling
        assert ".consent-section" in html_body
        assert "background-color" in html_body
        assert "border" in html_body

    def test_consent_section_contains_legal_icon(self):
        """Test that consent section contains the legal/balance icon.

        Validates: Requirements 3.1
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        # Check for the legal icon (⚖️)
        assert "⚖️" in html_body

    def test_english_html_does_not_contain_russian_consent_text(self):
        """Test that English HTML does not contain Russian consent text.

        Validates: Requirements 3.7
        """
        templates = EmailTemplates("EN")
        html_body = templates.get_otp_html_body("123456")

        russian_consent_text = (
            "Вводя код подтверждения, вы даёте согласие на обработку персональных данных"
        )
        assert russian_consent_text not in html_body

    def test_russian_html_does_not_contain_english_consent_text(self):
        """Test that Russian HTML does not contain English consent text.

        Validates: Requirements 3.7
        """
        templates = EmailTemplates("RU")
        html_body = templates.get_otp_html_body("123456")

        english_consent_text = (
            "By entering the verification code, you consent to the processing of personal data"
        )
        assert english_consent_text not in html_body
