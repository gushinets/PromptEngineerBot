"""Tests for the messages module."""
import pytest

from src.messages import (
    get_processing_message, parse_llm_response, format_improved_prompt_response,
    _extract_tag_block, WELCOME_MESSAGE, BTN_CRAFT, BTN_LYRA, BTN_GGL
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
        response = "Some text <QUESTION>What do you want to achieve?</QUESTION> more text"
        
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


class TestFormatImprovedPromptResponse:
    """Test cases for format_improved_prompt_response function."""

    def test_format_improved_prompt_response_basic(self):
        """Test basic formatting of improved prompt response."""
        user_prompt = "Write a story"
        improved_prompt = "Write a compelling short story about adventure"
        method_name = "CRAFT"
        
        result = format_improved_prompt_response(user_prompt, improved_prompt, method_name)
        
        assert "CRAFT" in result
        assert "Write a story" in result
        assert "Write a compelling short story about adventure" in result
        assert "✅" in result

    def test_format_improved_prompt_response_markdown_escaping(self):
        """Test that markdown characters are escaped."""
        user_prompt = "Write a story with *emphasis* and `code`"
        improved_prompt = "Write a story with **bold** and _italic_"
        method_name = "LYRA"
        
        result = format_improved_prompt_response(user_prompt, improved_prompt, method_name)
        
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
        
        result = format_improved_prompt_response(user_prompt, improved_prompt, method_name)
        
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