# Implementation Plan

## ✅ FEATURE COMPLETE

All tasks for the follow-up questions feature have been successfully implemented and tested. The feature is fully functional and integrated into the bot.

**Status**: All requirements from the requirements document have been implemented and are working correctly. The codebase analysis confirms that all functionality is in place and properly tested.

**Recent Fix**: Task 22 was identified as incomplete during the review and has been properly implemented. The implementation was simplified based on user feedback to send only 2 messages instead of 3 when the user clicks YES:
1. Instruction message (FOLLOWUP_PROMPT_INPUT_MESSAGE)
2. Improved prompt wrapped in code blocks (```) combined with ForceReply for better UX

This provides a cleaner user experience while still allowing easy copying of the improved prompt and modification through the ForceReply input area. All tests are now passing and the feature is fully functional.

### Completed Implementation

- [x] 1. Extend StateManager with follow-up conversation states
  - Add new fields to UserState dataclass for follow-up conversation tracking
  - Implement methods for managing follow-up choice waiting state
  - Implement methods for managing follow-up conversation active state
  - Add improved prompt caching functionality to store prompts between conversations
  - Write unit tests for new state management methods
  - _Requirements: 1.1, 2.1, 3.1, 4.1_

- [x] 2. Add localized messages and UI elements for follow-up feature
  - Add FOLLOWUP_OFFER_MESSAGE constant with Russian and English versions
  - Add BTN_YES and BTN_NO button constants with localization
  - Add BTN_GENERATE_PROMPT button constant with localization
  - Create FOLLOWUP_CHOICE_KEYBOARD layout for ДА/НЕТ buttons
  - Create FOLLOWUP_CONVERSATION_KEYBOARD layout with generate button and reset
  - Write unit tests to verify message localization
  - _Requirements: 1.3, 2.1, 4.2, 6.1, 6.2, 6.3_

- [x] 3. Implement refined prompt parsing functionality
  - Create parse_followup_response function to detect and extract REFINED_PROMPT tags
  - Handle various tag formats including missing closing tags
  - Implement tag content extraction with proper whitespace handling
  - Add fallback parsing for malformed responses
  - Write comprehensive unit tests for all parsing scenarios
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 4. Extend ConversationManager for follow-up conversations
  - Add start_followup_conversation method to initialize follow-up context
  - Implement is_in_followup_conversation state checking method
  - Add reset_to_followup_ready method for conversation state management
  - Modify existing reset method to handle follow-up state cleanup
  - Write unit tests for new conversation management methods
  - _Requirements: 3.2, 3.3, 4.1, 4.5_

- [x] 5. Implement follow-up choice handling in BotHandler
  - Create _handle_followup_choice method to process ДА/НЕТ button clicks
  - Handle НЕТ choice by sending RESET_CONFIRMATION and returning to prompt input
  - Handle ДА choice by starting follow-up conversation flow
  - Add proper state transitions and conversation reset logic
  - Write unit tests for choice handling logic
  - _Requirements: 2.1, 2.2, 2.3, 3.1_

- [x] 6. Implement follow-up conversation management in BotHandler
  - Create _handle_followup_conversation method for question-answer phase
  - Add conversation history management for follow-up messages
  - Implement proper role assignment for follow-up conversation messages
  - Handle user responses and LLM question flow
  - Write unit tests for conversation flow management
  - _Requirements: 3.4, 3.5, 4.1, 4.5_

- [x] 7. Implement generate prompt button functionality
  - Create _process_followup_generation method to handle generate button clicks
  - Send "<GENERATE_PROMPT>" signal to LLM when button is pressed
  - Process LLM response and extract refined prompt
  - Handle both button-triggered and natural conversation completion
  - Write unit tests for generate button functionality
  - _Requirements: 4.2, 4.3, 4.4, 5.2_

- [x] 8. Modify existing _process_with_llm method for follow-up integration
  - Add follow-up offer logic after improved prompt detection
  - Cache improved prompt before offering follow-up questions
  - Send follow-up offer message with ДА/НЕТ buttons
  - Set appropriate state for follow-up choice waiting
  - Preserve existing functionality for non-follow-up flows
  - Write integration tests for modified LLM processing
  - _Requirements: 1.1, 1.2, 1.3, 5.5_

- [x] 9. Update main message routing in handle_message method
  - Add routing logic for follow-up choice waiting state
  - Add routing logic for follow-up conversation state
  - Ensure proper state checking order and precedence
  - Maintain existing message routing for other states
  - Write integration tests for message routing logic
  - _Requirements: 1.3, 2.1, 3.1, 4.1_

- [x] 10. Implement follow-up conversation completion flow
  - Handle refined prompt extraction and parsing in follow-up context
  - Send parsed refined prompt to user
  - Send PROMPT_READY_FOLLOW_UP message after refined prompt
  - Reset conversation state to prompt input ready
  - Clear cached improved prompt data
  - Write end-to-end tests for complete follow-up flow
  - _Requirements: 5.4, 5.5, 5.6, 5.7_

- [x] 11. Add comprehensive error handling for follow-up feature
  - Handle LLM timeout/failure during follow-up conversations
  - Implement fallback to original improved prompt on errors
  - Add state recovery mechanisms for corrupted follow-up states
  - Handle malformed refined prompt responses gracefully
  - Write error handling tests for various failure scenarios
  - _Requirements: 3.3, 4.4, 5.1, 5.2, 5.3_

- [x] 12. Create integration tests for complete follow-up workflow
  - Test complete ДА flow from offer to refined prompt delivery
  - Test complete НЕТ flow from offer to prompt input reset
  - Test generate button functionality during question-answer phase
  - Test conversation state management throughout entire flow
  - Test proper cleanup and reset after follow-up completion
  - Verify integration with existing prompt optimization methods
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

### Implementation Summary

The follow-up questions feature has been fully implemented with:

- **Complete state management** for follow-up conversation flows
- **Localized UI elements** with Russian and English support
- **Robust parsing** for refined prompt extraction with fallback handling
- **Comprehensive error handling** with graceful fallbacks
- **Full integration** with existing prompt optimization methods
- **Extensive test coverage** including unit and integration tests

The feature is production-ready and provides users with an interactive way to refine their prompts through guided questions after receiving an initial improved prompt.

## 🔧 ForceReply Input Enhancement Required

Based on the new requirement to show improved prompts in the Telegram input area, the following tasks need to be implemented:

- [x] 19. Add ForceReply functionality to messages module





  - Import ForceReply from telegram library
  - Add FOLLOWUP_PROMPT_INPUT_MESSAGE constant with Russian and English versions: "Поменяйте или добавьте любые детали промпта. Если всё верно, просто отправьте этот промпт мне:" / "Modify or add any details to the prompt. If everything is correct, just send this prompt to me:"
  - Create create_prompt_input_reply function to generate ForceReply with improved prompt as placeholder
  - Add unit tests for ForceReply creation with various prompt lengths
  - _Requirements: 3.1, 3.2_

- [x] 20. Add new state for follow-up prompt input waiting





  - Add waiting_for_followup_prompt_input field to UserState dataclass
  - Implement set_waiting_for_followup_prompt_input method in StateManager
  - Update reset_user_state method to reset new state field
  - Add unit tests for new state management
  - _Requirements: 3.1, 3.3_

- [x] 21. Implement follow-up prompt input handler in BotHandler









  - Create _handle_followup_prompt_input method to process user's prompt input

  - Handle both modified and unmodified prompts from input area
  - Start follow-up conversation with received prompt
  - Add proper state transitions from prompt input to conversation
  - Write unit tests for prompt input handling
  - _Requirements: 3.3, 3.4, 3.5_

- [x] 22. Modify follow-up choice handler to use ForceReply





  - Update _handle_followup_choice method to first send instruction message when user clicks ДА
  - Send FOLLOWUP_PROMPT_INPUT_MESSAGE followed by improved prompt wrapped in code blocks (```) with ForceReply
  - Combine code block and ForceReply in single message for better UX (2 messages total instead of 3)
  - Set waiting_for_followup_prompt_input state instead of starting conversation immediately
  - Update state transitions to include new prompt input phase
  - Write integration tests for updated choice handling with instruction message and code blocks
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 23. Update message routing for new prompt input state





  - Add routing logic for waiting_for_followup_prompt_input state in handle_message method
  - Ensure proper state checking order and precedence
  - Maintain existing message routing for other states
  - Write integration tests for message routing with new state
  - _Requirements: 3.3_

- [x] 24. Add comprehensive tests for ForceReply functionality









  - Test ForceReply creation with various prompt lengths and formats
  - Test complete flow from choice to prompt input to conversation start
  - Test user modification of prompts in input area
  - Test state transitions through all phases of enhanced follow-up flow
  - Verify integration with existing follow-up conversation functionality
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

## 🔧 Token Usage Fixes Required

Based on the updated requirements for proper token calculation, the following tasks need to be implemented to fix the current token logging issues:

- [x] 13. Fix token logging for initial optimization phase









  - Remove duplicate token logging in _process_with_llm method before follow-up offer
  - Ensure tokens are logged only once when optimized prompt is generated
  - Log with initial prompt as UserRequest and optimized prompt as Answer
  - Use original method name (CRAFT, LYRA, GGL) for OptimizationModel field
  - _Requirements: 7.1, 7.2_

- [x] 14. Fix token accumulation during follow-up transition









  - Modify reset_to_followup_ready method to preserve token totals instead of resetting them
  - Ensure accumulated tokens from initial optimization are logged before follow-up starts
  - Reset token counters to zero only after logging initial optimization session
  - _Requirements: 7.4, 7.5_

- [x] 15. Implement proper follow-up session token tracking










  - Start new token accumulation when user accepts follow-up questions
  - Track only follow-up conversation tokens (reset counters after initial logging)
  - Log follow-up tokens with optimized prompt as UserRequest and refined prompt as Answer
  - Use "FOLLOWUP" as OptimizationModel field for follow-up sessions
  - _Requirements: 7.4, 7.5, 7.6, 7.7_


- [x] 16. Remove unnecessary token logging on /start command


  - Remove token logging from handle_start method
  - Prevent logging of zero or incomplete token usage on bot initialization
  - Clean up TODO comment about unnecessary logging
  - _Requirements: 7.8_

- [x] 17. Update conversation manager token handling





  - Modify reset_to_followup_ready to not reset token totals
  - Ensure token preservation during follow-up choice state transition
  - Add method to reset tokens only after successful logging
  - _Requirements: 7.5_

- [x] 18. Add comprehensive tests for token usage fixes





  - Test that initial optimization logs tokens exactly once
  - Test that follow-up sessions start with zero token counters
  - Test that follow-up completion logs only follow-up session tokens
  - Test that declining follow-up doesn't cause additional logging
  - Verify all Google Sheets payload fields are correctly populated
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_