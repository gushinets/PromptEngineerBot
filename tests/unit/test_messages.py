"""Tests for the messages module."""

import pytest
from telegram import ForceReply

from telegram_bot.utils.messages import (
    BTN_CRAFT,
    BTN_GENERATE_PROMPT,
    BTN_GGL,
    BTN_LYRA,
    BTN_NO,
    BTN_YES,
    FOLLOWUP_CHOICE_KEYBOARD,
    FOLLOWUP_CONVERSATION_KEYBOARD,
    FOLLOWUP_OFFER_MESSAGE,
    LANGUAGE,
    WELCOME_MESSAGE,
    _,
    _extract_tag_block,
    format_improved_prompt_response,
    get_processing_message,
    parse_followup_response,
    parse_llm_response,
)


class TestGetProcessingMessage:
    """Test cases for get_processing_message function."""

    def test_get_processing_message_craft(self):
        """Test processing message for CRAFT method."""
        result = get_processing_message("craft")

        assert "CRAFT" in result
        assert "🔄" in result
        assert "Обрабатываю" in result or "Processing" in result

    def test_get_processing_message_lyra_basic(self):
        """Test processing message for LYRA basic method."""
        result = get_processing_message("lyra_basic")

        assert "LYRA BASIC" in result
        assert "🔄" in result

    def test_get_processing_message_ggl(self):
        """Test processing message for GGL method."""
        result = get_processing_message("ggl")

        assert "GGL" in result
        assert "🔄" in result

    def test_get_processing_message_case_handling(self):
        """Test processing message handles case conversion."""
        result = get_processing_message("test_method")

        assert "TEST METHOD" in result


class TestExtractTagBlock:
    """Test cases for _extract_tag_block function."""

    def test_extract_tag_block_simple(self):
        """Test extracting simple tag block."""
        text = "Some text <QUESTION>What is this?</QUESTION> more text"

        result, start_idx = _extract_tag_block(text, "QUESTION")

        assert result == "What is this?"
        assert start_idx == 10

    def test_extract_tag_block_no_closing(self):
        """Test extracting tag block without closing tag."""
        text = "Some text <QUESTION>What is this? No closing tag"

        result, start_idx = _extract_tag_block(text, "QUESTION")

        assert result == "What is this? No closing tag"
        assert start_idx == 10

    def test_extract_tag_block_not_found(self):
        """Test extracting tag block when tag not found."""
        text = "Some text without the tag"

        result, start_idx = _extract_tag_block(text, "QUESTION")

        assert result is None
        assert start_idx is None

    def test_extract_tag_block_case_insensitive(self):
        """Test extracting tag block is case insensitive."""
        text = "Some text <question>What is this?</QUESTION> more text"

        result, start_idx = _extract_tag_block(text, "QUESTION")

        assert result == "What is this?"

    def test_extract_tag_block_alternative_closing(self):
        """Test extracting tag block with alternative closing markers."""
        test_cases = [
            ("Text <QUESTION>Content<END QUESTION>", "Content"),
            ("Text <QUESTION>Content<END_QUESTION>", "Content"),
            ("Text <QUESTION>Content[END QUESTION]", "Content"),
            ("Text <QUESTION>Content[/QUESTION]", "Content"),
            ("Text <QUESTION>Content<QUESTION_END>", "Content"),
            ("Text <QUESTION>Content<END>", "Content"),
        ]

        for text, expected in test_cases:
            result, _ = _extract_tag_block(text, "QUESTION")
            assert result == expected

    def test_extract_tag_block_earliest_closing(self):
        """Test extracting tag block uses earliest closing marker."""
        text = "Text <QUESTION>Content<END>more<END QUESTION>"

        result, _ = _extract_tag_block(text, "QUESTION")

        assert result == "Content"


class TestParseLLMResponse:
    """Test cases for parse_llm_response function."""

    def test_parse_llm_response_question(self):
        """Test parsing LLM response with QUESTION tag."""
        response = (
            "Some text <QUESTION>What do you want to achieve?</QUESTION> more text"
        )

        result, is_question, is_improved_prompt = parse_llm_response(response)

        assert result == "What do you want to achieve?"
        assert is_question is True
        assert is_improved_prompt is False

    def test_parse_llm_response_improved_prompt(self):
        """Test parsing LLM response with IMPROVED_PROMPT tag."""
        response = "Some text <IMPROVED_PROMPT>Here is your improved prompt</IMPROVED_PROMPT> more text"

        result, is_question, is_improved_prompt = parse_llm_response(response)

        assert result == "Here is your improved prompt"
        assert is_question is False
        assert is_improved_prompt is True

    def test_parse_llm_response_question_priority(self):
        """Test that QUESTION tag takes priority over IMPROVED_PROMPT."""
        response = """
        <QUESTION>What is your goal?</QUESTION>
        <IMPROVED_PROMPT>Improved prompt here</IMPROVED_PROMPT>
        """

        result, is_question, is_improved_prompt = parse_llm_response(response)

        assert result == "What is your goal?"
        assert is_question is True
        assert is_improved_prompt is False

    def test_parse_llm_response_no_tags(self):
        """Test parsing LLM response without special tags."""
        response = "This is a regular response without any special tags."

        result, is_question, is_improved_prompt = parse_llm_response(response)

        assert result == response
        assert is_question is False
        assert is_improved_prompt is False

    def test_parse_llm_response_empty(self):
        """Test parsing empty LLM response."""
        response = ""

        result, is_question, is_improved_prompt = parse_llm_response(response)

        assert result == ""
        assert is_question is False
        assert is_improved_prompt is False


class TestParseFollowupResponse:
    """Test cases for parse_followup_response function."""

    def test_parse_followup_response_with_refined_prompt_tag(self):
        """Test parsing response with REFINED_PROMPT tag."""
        response = "Some text <REFINED_PROMPT>Here is your refined prompt</REFINED_PROMPT> more text"

        result, is_refined_prompt = parse_followup_response(response)

        assert result == "Here is your refined prompt"
        assert is_refined_prompt is True

    def test_parse_followup_response_missing_closing_tag(self):
        """Test parsing response with missing closing tag."""
        response = (
            "Some text <REFINED_PROMPT>Here is your refined prompt without closing tag"
        )

        result, is_refined_prompt = parse_followup_response(response)

        assert result == "Here is your refined prompt without closing tag"
        assert is_refined_prompt is True

    def test_parse_followup_response_case_insensitive(self):
        """Test parsing response with case-insensitive tag matching."""
        response = "Some text <refined_prompt>Here is your refined prompt</refined_prompt> more text"

        result, is_refined_prompt = parse_followup_response(response)

        assert result == "Here is your refined prompt"
        assert is_refined_prompt is True

    def test_parse_followup_response_alternative_closing_tags(self):
        """Test parsing response with alternative closing tag formats."""
        test_cases = [
            ("Text <REFINED_PROMPT>Content</REFINED_PROMPT>", "Content"),
            ("Text <REFINED_PROMPT>Content<END REFINED_PROMPT>", "Content"),
            ("Text <REFINED_PROMPT>Content<END_REFINED_PROMPT>", "Content"),
            ("Text <REFINED_PROMPT>Content[END REFINED_PROMPT]", "Content"),
            ("Text <REFINED_PROMPT>Content[/REFINED_PROMPT]", "Content"),
            ("Text <REFINED_PROMPT>Content<REFINED_PROMPT_END>", "Content"),
            ("Text <REFINED_PROMPT>Content<END>", "Content"),
        ]

        for response, expected_content in test_cases:
            result, is_refined_prompt = parse_followup_response(response)
            assert result == expected_content
            assert is_refined_prompt is True

    def test_parse_followup_response_whitespace_handling(self):
        """Test proper whitespace handling in extracted content."""
        response = "Text <REFINED_PROMPT>  \n  Here is content with whitespace  \n  </REFINED_PROMPT>"

        result, is_refined_prompt = parse_followup_response(response)

        assert result == "Here is content with whitespace"
        assert is_refined_prompt is True

    def test_parse_followup_response_multiline_content(self):
        """Test parsing multiline refined prompt content."""
        response = """Some text <REFINED_PROMPT>
        Line 1 of refined prompt
        Line 2 of refined prompt
        Line 3 of refined prompt
        </REFINED_PROMPT> more text"""

        result, is_refined_prompt = parse_followup_response(response)

        expected = "Line 1 of refined prompt\n        Line 2 of refined prompt\n        Line 3 of refined prompt"
        assert result == expected
        assert is_refined_prompt is True

    def test_parse_followup_response_no_refined_prompt_tag(self):
        """Test parsing response without REFINED_PROMPT tag."""
        response = "This is a regular follow-up question without any special tags."

        result, is_refined_prompt = parse_followup_response(response)

        assert result == response
        assert is_refined_prompt is False

    def test_parse_followup_response_empty_string(self):
        """Test parsing empty response."""
        response = ""

        result, is_refined_prompt = parse_followup_response(response)

        assert result == ""
        assert is_refined_prompt is False

    def test_parse_followup_response_empty_tag_content(self):
        """Test parsing response with empty REFINED_PROMPT tag."""
        response = "Some text <REFINED_PROMPT></REFINED_PROMPT> more text"

        result, is_refined_prompt = parse_followup_response(response)

        # Empty tag content falls back to original response
        assert result == response
        assert is_refined_prompt is False

    def test_parse_followup_response_multiple_refined_prompt_tags(self):
        """Test parsing response with multiple REFINED_PROMPT tags (should use first one)."""
        response = "Text <REFINED_PROMPT>First prompt</REFINED_PROMPT> more <REFINED_PROMPT>Second prompt</REFINED_PROMPT>"

        result, is_refined_prompt = parse_followup_response(response)

        assert result == "First prompt"
        assert is_refined_prompt is True

    def test_parse_followup_response_malformed_tag_fallback(self):
        """Test fallback parsing for malformed responses."""
        # Test with unclosed tag
        response = "Text <REFINED_PROMPT>Content continues without proper closing"

        result, is_refined_prompt = parse_followup_response(response)

        assert result == "Content continues without proper closing"
        assert is_refined_prompt is True

    def test_parse_followup_response_tag_in_middle(self):
        """Test parsing when REFINED_PROMPT tag is in the middle of response."""
        response = "Here's some context. <REFINED_PROMPT>Your refined prompt is here</REFINED_PROMPT> And some conclusion."

        result, is_refined_prompt = parse_followup_response(response)

        assert result == "Your refined prompt is here"
        assert is_refined_prompt is True

    def test_parse_followup_response_special_characters(self):
        """Test parsing refined prompt with special characters."""
        response = '<REFINED_PROMPT>Prompt with "quotes", symbols: @#$%, and unicode: café</REFINED_PROMPT>'

        result, is_refined_prompt = parse_followup_response(response)

        assert result == 'Prompt with "quotes", symbols: @#$%, and unicode: café'
        assert is_refined_prompt is True

    def test_parse_followup_response_nested_tags(self):
        """Test parsing with nested or similar tags."""
        response = "Text <REFINED_PROMPT>Content with <OTHER_TAG>nested</OTHER_TAG> tags</REFINED_PROMPT>"

        result, is_refined_prompt = parse_followup_response(response)

        assert result == "Content with <OTHER_TAG>nested</OTHER_TAG> tags"
        assert is_refined_prompt is True


class TestFormatImprovedPromptResponse:
    """Test cases for format_improved_prompt_response function."""

    def test_format_improved_prompt_response_basic(self):
        """Test basic formatting of improved prompt response."""
        user_prompt = "Write a story"
        improved_prompt = "Write a compelling short story about adventure"
        method_name = "CRAFT"

        result = format_improved_prompt_response(
            user_prompt, improved_prompt, method_name
        )

        assert "CRAFT" in result
        assert "Write a story" in result
        assert "Write a compelling short story about adventure" in result
        assert "✅" in result

    def test_format_improved_prompt_response_markdown_escaping(self):
        """Test that markdown characters are escaped."""
        user_prompt = "Write a story with *emphasis* and `code`"
        improved_prompt = "Write a story with **bold** and _italic_"
        method_name = "LYRA"

        result = format_improved_prompt_response(
            user_prompt, improved_prompt, method_name
        )

        # Check that markdown characters are escaped
        assert "\\*emphasis\\*" in result
        assert "\\`code\\`" in result
        assert "\\*\\*bold\\*\\*" in result
        assert "\\_italic\\_" in result

    def test_format_improved_prompt_response_whitespace_handling(self):
        """Test that improved prompt whitespace is stripped."""
        user_prompt = "Test prompt"
        improved_prompt = "  \n  Improved prompt with whitespace  \n  "
        method_name = "GGL"

        result = format_improved_prompt_response(
            user_prompt, improved_prompt, method_name
        )

        assert "Improved prompt with whitespace" in result
        # Should not contain extra whitespace
        assert "  \n  Improved prompt with whitespace  \n  " not in result


class TestConstants:
    """Test cases for message constants."""

    def test_button_constants_exist(self):
        """Test that button constants are defined."""
        assert BTN_CRAFT is not None
        assert BTN_LYRA is not None
        assert BTN_GGL is not None

        # Should contain emoji and text
        assert "🛠" in BTN_CRAFT
        assert "CRAFT" in BTN_CRAFT
        assert "⚡" in BTN_LYRA
        assert "LYRA" in BTN_LYRA
        assert "🔍" in BTN_GGL
        assert "GGL" in BTN_GGL

    def test_welcome_message_exists(self):
        """Test that welcome message is defined and not empty."""
        assert WELCOME_MESSAGE is not None
        assert len(WELCOME_MESSAGE) > 0
        assert "🤖" in WELCOME_MESSAGE


class TestFollowUpFeatureMessages:
    """Test cases for follow-up feature messages and UI elements."""

    def test_followup_offer_message_exists(self):
        """Test that follow-up offer message is defined and not empty."""
        assert FOLLOWUP_OFFER_MESSAGE is not None
        assert len(FOLLOWUP_OFFER_MESSAGE) > 0

        # Should contain key phrases based on current language
        if LANGUAGE == "ru":
            assert "готов к использованию" in FOLLOWUP_OFFER_MESSAGE
            assert "ещё лучше" in FOLLOWUP_OFFER_MESSAGE
            assert "вопросов" in FOLLOWUP_OFFER_MESSAGE
        else:
            assert "ready to use" in FOLLOWUP_OFFER_MESSAGE
            assert "even better" in FOLLOWUP_OFFER_MESSAGE
            assert "questions" in FOLLOWUP_OFFER_MESSAGE

    def test_followup_button_constants_exist(self):
        """Test that follow-up button constants are defined."""
        assert BTN_YES is not None
        assert BTN_NO is not None
        assert BTN_GENERATE_PROMPT is not None

        # Check content based on current language
        if LANGUAGE == "ru":
            assert "ДА" in BTN_YES
            assert "НЕТ" in BTN_NO
            assert "Сгенерировать промпт" in BTN_GENERATE_PROMPT
        else:
            assert "YES" in BTN_YES
            assert "NO" in BTN_NO
            assert "Generate Prompt" in BTN_GENERATE_PROMPT

    def test_followup_choice_keyboard_structure(self):
        """Test that follow-up choice keyboard has correct structure."""
        keyboard = FOLLOWUP_CHOICE_KEYBOARD

        # Should have one row with two buttons
        assert len(keyboard.keyboard) == 1
        assert len(keyboard.keyboard[0]) == 2

        # Should contain YES and NO buttons
        buttons = [btn.text for btn in keyboard.keyboard[0]]
        assert BTN_YES in buttons
        assert BTN_NO in buttons

        # Should be resizable
        assert keyboard.resize_keyboard is True

    def test_followup_conversation_keyboard_structure(self):
        """Test that follow-up conversation keyboard has correct structure."""
        keyboard = FOLLOWUP_CONVERSATION_KEYBOARD

        # Should have two rows
        assert len(keyboard.keyboard) == 2

        # First row should have generate button
        assert len(keyboard.keyboard[0]) == 1
        assert keyboard.keyboard[0][0].text == BTN_GENERATE_PROMPT

        # Second row should have reset button
        assert len(keyboard.keyboard[1]) == 1
        # Import BTN_RESET to check
        from telegram_bot.utils.messages import BTN_RESET

        assert keyboard.keyboard[1][0].text == BTN_RESET

        # Should be resizable
        assert keyboard.resize_keyboard is True

    def test_localization_helper_function(self):
        """Test that the localization helper function works correctly."""
        # Test with Russian language
        if LANGUAGE == "ru":
            result = _("Русский", "English")
            assert result == "Русский"
        else:
            result = _("Русский", "English")
            assert result == "English"

    def test_followup_messages_localization_consistency(self):
        """Test that follow-up messages follow localization pattern."""
        # All follow-up messages should be properly localized
        messages_to_test = [
            FOLLOWUP_OFFER_MESSAGE,
            BTN_YES,
            BTN_NO,
            BTN_GENERATE_PROMPT,
        ]

        for message in messages_to_test:
            # Messages should not be empty
            assert message is not None
            assert len(message.strip()) > 0

            # Messages should contain appropriate language content
            # This is a basic check - more specific checks are in individual tests


class TestFollowupResponseErrorHandling:
    """Test cases for enhanced follow-up response parsing with error handling."""

    def test_parse_followup_response_empty_content_fallback(self):
        """Test parsing follow-up response with empty refined prompt content falls back."""
        response = "<REFINED_PROMPT></REFINED_PROMPT>"

        parsed, is_refined = parse_followup_response(response)

        # Should fall back to original response when content is empty
        assert parsed == response.strip()
        assert is_refined is False

    def test_parse_followup_response_whitespace_only_content_fallback(self):
        """Test parsing follow-up response with whitespace-only refined prompt content falls back."""
        response = "<REFINED_PROMPT>   \n\t   </REFINED_PROMPT>"

        parsed, is_refined = parse_followup_response(response)

        # Should fall back to original response when content is only whitespace
        assert parsed == response.strip()
        assert is_refined is False

    def test_parse_followup_response_parsing_exception_fallback(self):
        """Test parsing follow-up response when parsing raises exception."""
        response = "<REFINED_PROMPT>Valid content</REFINED_PROMPT>"

        # Mock _extract_tag_block to raise an exception
        from unittest.mock import patch

        with patch("telegram_bot.utils.messages._extract_tag_block") as mock_extract:
            mock_extract.side_effect = Exception("Parsing error")

            parsed, is_refined = parse_followup_response(response)

            # Should fall back to original response
            assert parsed == response.strip()
            assert is_refined is False

    def test_parse_followup_response_malformed_tag_handling(self):
        """Test parsing follow-up response with malformed tag structure."""
        response = "<REFINED_PROMPT>Content here<WRONG_CLOSING>"

        parsed, is_refined = parse_followup_response(response)

        # Should still extract content even with malformed closing
        assert parsed == "Content here<WRONG_CLOSING>"
        assert is_refined is True

    def test_parse_followup_response_multiple_tags_first_priority(self):
        """Test parsing follow-up response with multiple refined prompt tags uses first."""
        response = "<REFINED_PROMPT>First content</REFINED_PROMPT> Some text <REFINED_PROMPT>Second content</REFINED_PROMPT>"

        parsed, is_refined = parse_followup_response(response)

        # Should extract the first occurrence
        assert parsed == "First content"
        assert is_refined is True

    def test_parse_followup_response_nested_content_preservation(self):
        """Test parsing follow-up response preserves nested content that looks like tags."""
        response = "<REFINED_PROMPT>Content with <nested> tags inside</REFINED_PROMPT>"

        parsed, is_refined = parse_followup_response(response)

        assert parsed == "Content with <nested> tags inside"
        assert is_refined is True

    def test_parse_followup_response_robust_whitespace_handling(self):
        """Test robust whitespace handling in various scenarios."""
        test_cases = [
            ("<REFINED_PROMPT>\n\nContent\n\n</REFINED_PROMPT>", "Content"),
            ("<REFINED_PROMPT>  Content  </REFINED_PROMPT>", "Content"),
            ("<REFINED_PROMPT>\tContent\t</REFINED_PROMPT>", "Content"),
            ("<REFINED_PROMPT> \n \t Content \t \n </REFINED_PROMPT>", "Content"),
        ]

        for response, expected_content in test_cases:
            parsed, is_refined = parse_followup_response(response)
            assert parsed == expected_content
            assert is_refined is True

    def test_parse_followup_response_special_characters_preservation(self):
        """Test that special characters are preserved during parsing."""
        special_chars = (
            'Content with "quotes", symbols: @#$%^&*(), and unicode: café 🚀'
        )
        response = f"<REFINED_PROMPT>{special_chars}</REFINED_PROMPT>"

        parsed, is_refined = parse_followup_response(response)

        assert parsed == special_chars
        assert is_refined is True

    def test_parse_followup_response_large_content_handling(self):
        """Test parsing large refined prompt content."""
        large_content = "This is a very long refined prompt. " * 100
        response = f"<REFINED_PROMPT>{large_content}</REFINED_PROMPT>"

        parsed, is_refined = parse_followup_response(response)

        # Content should be stripped, so compare with stripped version
        assert parsed == large_content.strip()
        assert is_refined is True

    def test_parse_followup_response_edge_case_empty_string(self):
        """Test parsing completely empty response string."""
        response = ""

        parsed, is_refined = parse_followup_response(response)

        assert parsed == ""
        assert is_refined is False

    def test_parse_followup_response_edge_case_only_whitespace(self):
        """Test parsing response that is only whitespace."""
        response = "   \n\t   "

        parsed, is_refined = parse_followup_response(response)

        assert parsed == ""  # Should be stripped
        assert is_refined is False



