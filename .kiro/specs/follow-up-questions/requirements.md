# Requirements Document

## Introduction

The Follow-up questions feature enhances the prompt improvement process by allowing the LLM to ask clarifying questions after providing an improved prompt. This creates an interactive refinement cycle where users can provide additional context to further improve their prompts through a guided question-and-answer session. All new messages introduced must have both Russian and English versions following the existing localization pattern in messages.py.

## Requirements

### Requirement 1

**User Story:** As a user, I want to be offered the option to answer follow-up questions after receiving an improved prompt, so that I can further refine my prompt with additional context.

#### Acceptance Criteria

1. WHEN the system sends an improved prompt to the user THEN the system SHALL reset the current conversation
2. WHEN the conversation is reset THEN the system SHALL send the message "Ваш промпт уже готов к использованию, но мы можем сделать его ещё лучше. Готовы ответить на несколько вопросов?"
3. WHEN the follow-up offer message is sent THEN the system SHALL display two buttons: [ДА] and [НЕТ]

### Requirement 2

**User Story:** As a user, I want to decline follow-up questions and start with a new prompt, so that I can quickly move to improving a different prompt.

#### Acceptance Criteria

1. WHEN the user clicks the [НЕТ] button THEN the system SHALL send the RESET_CONFIRMATION message from messages.py
2. WHEN the decline message is sent THEN the system SHALL be ready to receive a new prompt from the user
3. WHEN ready for new prompt THEN the system SHALL enter the standard method selection flow

### Requirement 3

**User Story:** As a user, I want to engage in a follow-up question session, so that I can provide additional context to improve my prompt further.

#### Acceptance Criteria

1. WHEN the user clicks the [ДА] button THEN the system SHALL start a new conversation for follow-up questions
2. WHEN starting follow-up conversation THEN the system SHALL load the prompt from "prompts/Follow_up_questions_prompt.txt" as system context
3. WHEN system context is loaded THEN the system SHALL add the improved prompt from previous conversation as user context
4. WHEN conversation context is prepared THEN the system SHALL send the conversation to LLM and wait for response
5. WHEN LLM responds THEN the system SHALL send the LLM's questions back to the user

### Requirement 4

**User Story:** As a user, I want to answer follow-up questions in an interactive session, so that I can provide detailed context for prompt refinement.

#### Acceptance Criteria

1. WHEN the user provides answers to LLM questions THEN the system SHALL add all messages to conversation history with appropriate roles
2. WHEN in question-answer phase THEN the system SHALL display a [Сгенерировать промпт] button to the user
3. WHEN user clicks [Сгенерировать промпт] button THEN the system SHALL send the exact message "<GENERATE_PROMPT>" to the LLM
4. WHEN "<GENERATE_PROMPT>" is sent THEN the LLM SHALL stop asking questions and return a refined prompt

### Requirement 5

**User Story:** As a user, I want to receive a refined prompt after the follow-up session, so that I can use the improved version of my original prompt.

#### Acceptance Criteria

1. WHEN LLM finishes asking questions THEN the LLM SHALL send a refined prompt starting with tag "<REFINED_PROMPT>"
2. WHEN user responds with "<GENERATE_PROMPT>" message THEN the LLM SHALL return a refined prompt with "<REFINED_PROMPT>" tag
3. WHEN system receives refined prompt THEN the system SHALL parse and remove "<REFINED_PROMPT>" opening tag
4. WHEN parsing refined prompt THEN the system SHALL look for and remove closing tag "</REFINED_PROMPT>" or additional "<REFINED_PROMPT>" if present
5. WHEN refined prompt is parsed THEN the system SHALL return only the refined prompt content to the user
6. WHEN refined prompt is sent to user THEN the system SHALL send the PROMPT_READY_FOLLOW_UP message from messages.py
7. WHEN follow-up message is sent THEN the system SHALL reset conversation to ready state for receiving new prompts
#
## Requirement 6

**User Story:** As a system, I want to provide localized messages for all new functionality, so that users can interact with the bot in their preferred language.

#### Acceptance Criteria

1. WHEN implementing new messages THEN all messages SHALL have both Russian and English versions
2. WHEN creating new messages THEN they SHALL follow the existing localization pattern in messages.py using the _() helper function
3. WHEN adding new button labels THEN they SHALL be localized and follow the BTN_ naming convention
4. WHEN referencing existing messages THEN the system SHALL use the message constants from messages.py (RESET_CONFIRMATION, PROMPT_READY_FOLLOW_UP)

### Requirement 7

**User Story:** As a system administrator, I want accurate token usage tracking with separate logging for initial optimization and follow-up conversations, so that I can monitor costs and usage patterns for each phase correctly.

#### Acceptance Criteria

1. WHEN a user sends their initial prompt THEN the system SHALL start accumulating token usage for the initial optimization session
2. WHEN the system generates an optimized prompt THEN the system SHALL log the accumulated tokens to Google Sheets with all standard fields: BotID, TelegramID, LLM, OptimizationModel, UserRequest (initial prompt), Answer (optimized prompt), prompt_tokens, completion_tokens, total_tokens
3. WHEN a user declines follow-up questions THEN the system SHALL NOT perform any additional token logging
4. WHEN a user accepts follow-up questions THEN the system SHALL start a new token accumulation session for the follow-up conversation
5. WHEN follow-up conversation starts THEN the system SHALL reset token counters to zero and begin accumulating tokens for follow-up session only
6. WHEN the system generates a refined prompt from follow-up THEN the system SHALL log the follow-up session tokens to Google Sheets with all standard fields: BotID, TelegramID, LLM, OptimizationModel ("FOLLOWUP"), UserRequest (improved prompt from step 2), Answer (refined prompt), prompt_tokens, completion_tokens, total_tokens
7. WHEN logging tokens THEN each session SHALL be logged as a separate entry with appropriate method names (initial method vs "FOLLOWUP")
8. WHEN token logging fails THEN the system SHALL continue normal operation without affecting user experience