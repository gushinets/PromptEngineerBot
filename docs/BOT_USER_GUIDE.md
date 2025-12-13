# Telegram Prompt Engineering Bot — User Guide

**Document Version**: 1.0  
**Last Updated**: December 2024  
**Purpose**: End-user reference documentation for the Prompt Engineering Bot

---

## Table of Contents

1. [Overview](#1-overview)
2. [Core Capabilities](#2-core-capabilities)
3. [Supported Commands & Buttons](#3-supported-commands--buttons)
4. [Usage Examples](#4-usage-examples)
5. [Limitations & Constraints](#5-limitations--constraints)
6. [Errors & Troubleshooting](#6-errors--troubleshooting)
7. [FAQ](#7-faq)
8. [Version & Scope Notes](#8-version--scope-notes)

---

## 1. Overview

### What is this bot?

The **Prompt Engineering Bot** is a Telegram bot that transforms your simple task descriptions into precise, optimized prompts for AI systems like ChatGPT, Gemini, Claude, GROK, and DeepSeek.

### What problem does it solve?

Writing effective prompts for AI can be challenging. This bot takes your everyday language descriptions and automatically restructures them into professional-quality prompts that get better results from AI models.

### Who is it for?

- Professionals who want to get more accurate AI-generated content
- Anyone who struggles with writing effective AI prompts
- Users who want to compare different prompt optimization approaches
- Teams that need consistent, high-quality prompts

### Languages Supported

The bot supports **Russian** and **English** interfaces. All messages, buttons, and responses adapt to the configured language.

---

## 2. Core Capabilities

### 2.1 Prompt Optimization Methods

The bot offers **four distinct optimization methods**, each with its own approach:

| Method | Icon | Description | Best For |
|--------|------|-------------|----------|
| **CRAFT** | 🛠 | Structured approach using Context, Role, Action, Format, and Target Audience framework | Complex tasks requiring detailed structure; professional or technical prompts |
| **LYRA** | ⚡ | Quick, concise optimization focused on efficiency | Simple tasks; when you need fast results |
| **LYRA Detail** | 🧩 | Detailed version of LYRA with comprehensive coverage | When you need LYRA's efficiency with more thoroughness |
| **GGL** | 🔍 | Goal-focused methodology based on Google's prompt engineering guidelines | Outcome-driven tasks; when clear objectives matter most |

### 2.2 Follow-up Question System

After receiving your optimized prompt, the bot can **ask clarifying questions** to refine the result further:

- **Accept follow-up questions (✅YES)**: The bot asks targeted questions about your requirements, then generates an even better prompt based on your answers
- **Decline follow-up questions (❌NO)**: Keep the initial optimized prompt as-is
- **Generate early (🤖Generate Prompt)**: Stop the Q&A at any point and get a refined prompt based on answers provided so far

### 2.3 Email Delivery Service

Instead of optimizing with one method, you can receive **all three methods** (CRAFT, LYRA, GGL) at once via email:

- **One-time email verification**: Verify your email address with a 6-digit code
- **Subsequent uses**: Authenticated users skip verification
- **Email content**: Receive original prompt plus all three optimized versions

### 2.4 Post-Optimization Email

After completing any optimization, you can send your final result to email:

- Available after single-method optimization (when declining follow-up)
- Available after completing follow-up questions
- Sends only your final optimized prompt (not all three methods)

---

## 3. Supported Commands & Buttons

### 3.1 Commands

| Command | Function |
|---------|----------|
| `/start` | Start the bot or reset current conversation |

### 3.2 Button Reference

#### Method Selection Buttons
| Button (RU) | Button (EN) | Function |
|-------------|-------------|----------|
| 📧 Отправить 3 промпта на email | 📧 Send 3 prompts to email | Optimize with all methods and send to email |
| 🛠 CRAFT | 🛠 CRAFT | Optimize using CRAFT method |
| ⚡ LYRA | ⚡ LYRA | Optimize using LYRA Basic method |
| 🧩 LYRA detail | 🧩 LYRA detail | Optimize using LYRA Detail method |
| 🔍 GGL | 🔍 GGL | Optimize using GGL method |

#### Follow-up Buttons
| Button (RU) | Button (EN) | Function |
|-------------|-------------|----------|
| ✅ДА | ✅YES | Accept follow-up questions |
| ❌НЕТ | ❌NO | Decline follow-up questions |
| 🤖Сгенерировать промпт | 🤖Generate Prompt | Generate refined prompt during follow-up |

#### Navigation Buttons
| Button (RU) | Button (EN) | Function |
|-------------|-------------|----------|
| 🔄 Сбросить диалог | 🔄 Reset Conversation | Reset and start over |
| 📧 Отправить промпт на e-mail | 📧 Send prompt to e-mail | Send current result to email |

---

## 4. Usage Examples

### Example 1: Basic Single-Method Optimization

**Your input:**
> "Write a marketing email for my new product"

**Steps:**
1. Send `/start` to begin
2. Type your task description
3. Select an optimization method (e.g., 🛠 CRAFT)
4. Receive your optimized prompt
5. When asked about follow-up questions, click ❌NO to finish

**Result:** A detailed, structured prompt ready to paste into ChatGPT, Claude, or any AI.

---

### Example 2: Optimization with Follow-up Refinement

**Your input:**
> "Create a business plan for a startup"

**Steps:**
1. Send `/start` to begin
2. Type your task description
3. Select 🔍 GGL method
4. Receive initial optimized prompt
5. Click ✅YES to accept follow-up questions
6. Answer 2-4 clarifying questions from the bot:
   - "What industry is your startup in?"
   - "What's your target market?"
7. Click 🤖Generate Prompt (or answer all questions)
8. Receive a refined prompt tailored to your specific situation

---

### Example 3: Email Delivery with All Methods

**Your input:**
> "Prepare a job interview preparation guide"

**Steps:**
1. Send `/start` to begin
2. Type your task description
3. Click 📧 Send 3 prompts to email
4. Enter your email address when prompted
5. Check your inbox for a verification code
6. Enter the 6-digit code
7. Wait for processing (bot optimizes with all 3 methods)
8. Receive email with original prompt + CRAFT + LYRA + GGL versions

**Subsequent uses:** After first verification, you'll skip steps 4-6.

---

### Example 4: Post-Optimization Email

**Scenario:** You completed optimization with LYRA, declined follow-up, and now want to save the result.

**Steps:**
1. After seeing your optimized prompt and declining follow-up
2. Notice the 📧 Send prompt to e-mail button
3. Click it
4. (First-time) Enter email and verify with code
5. (Returning user) Confirm your existing email
6. Receive email with your single optimized prompt

---

## 5. Limitations & Constraints

### 5.1 Rate Limits

| Limit Type | Value | Description |
|------------|-------|-------------|
| **OTP per email** | 3 per hour | Maximum verification codes per email address |
| **OTP per user** | 5 per hour | Maximum verification codes per Telegram account |
| **OTP spacing** | 60 seconds | Minimum wait between verification code requests |

### 5.2 Time Limits

| Operation | Timeout | What happens |
|-----------|---------|--------------|
| **OTP verification** | 5 minutes | Code expires; request a new one |
| **Follow-up conversation** | 5 minutes | Conversation times out; you receive the cached prompt |
| **LLM processing** | ~60 seconds | Request may timeout on very long prompts |

### 5.3 Content Limits

| Limit | Description |
|-------|-------------|
| **Message length** | Very long prompts may be split across multiple messages |
| **Prompt complexity** | Extremely complex or multi-part prompts work best when broken into separate requests |
| **Language** | Works best with clear, standard language (avoid heavy jargon or unclear abbreviations) |

### 5.4 Service Dependencies

The bot requires the following services to function fully:

| Service | Required For | If Unavailable |
|---------|--------------|----------------|
| **LLM API** | All optimization | Bot cannot optimize prompts |
| **Email/SMTP** | Email delivery | Email feature blocked (no fallback to chat) |
| **Redis** | Email flow, OTP storage | Email feature blocked |
| **Database** | User authentication persistence | Authentication may fail |

### 5.5 What the Bot Does NOT Do

- ❌ **Execute prompts**: The bot creates prompts but does not run them
- ❌ **Store conversation history**: Each session is independent
- ❌ **Access external websites**: Cannot fetch content from URLs
- ❌ **Generate images or files**: Text-only optimization
- ❌ **Provide real-time information**: Focuses only on prompt structure

---

## 6. Errors & Troubleshooting

### 6.1 Common Error Messages

#### Email & Authentication Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "❌ Invalid email format" | Email address format incorrect | Enter a valid email (e.g., user@example.com) |
| "⚠️ Too many code sending attempts" | Rate limit exceeded | Wait 1 hour before requesting another code |
| "❌ Invalid code" | Wrong OTP entered | Check email and re-enter correct 6-digit code |
| "❌ Code has expired" | OTP older than 5 minutes | Request a new verification code |
| "❌ Too many attempts" | 3 wrong OTP entries | Request a new code and try again |
| "❌ Email service not available" | Email feature disabled | Try single-method optimization instead |
| "⚠️ Service temporarily unavailable" | Redis/backend issues | Try again later |

#### Processing Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "❌ An error occurred" | Generic processing error | Click 🔄 Reset and try again |
| "🌐 Network error" | Connection issues | Check internet and retry |
| "⚠️ Too many requests" | LLM rate limit | Wait a moment before trying again |
| "Timeout occurred" | Processing took too long | Try a shorter prompt or retry |

#### Follow-up Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Conversation state corrupted" | State inconsistency | Click 🔄 Reset to start over |
| "Failed to generate prompt" | LLM processing failed | You'll receive the cached prompt as fallback |

### 6.2 Troubleshooting Steps

#### Problem: Bot is not responding

1. Check if you're connected to the internet
2. Try sending `/start` to reset the conversation
3. Wait a few seconds and try again
4. If persistent, the bot service may be temporarily unavailable

#### Problem: Didn't receive OTP email

1. Check spam/junk folder
2. Verify email address was typed correctly
3. Wait 2-3 minutes (email delivery can be delayed)
4. Request a new code (after 60 seconds minimum)
5. Try a different email address if issue persists

#### Problem: Optimized prompt doesn't look right

1. The prompt may contain formatting that Telegram displays differently
2. Copy the text and paste into a text editor to see full formatting
3. Try a different optimization method for comparison
4. Use follow-up questions to refine the result

#### Problem: Follow-up questions seem irrelevant

1. The questions are generated by AI and may occasionally miss context
2. Click 🤖Generate Prompt at any time to get your result
3. Your answers help, but you can skip questions you find unhelpful

#### Problem: Button not working

1. Make sure you're clicking the button, not typing its text
2. Try clicking 🔄 Reset and starting over
3. Ensure you're in the correct state for that button (e.g., method selection buttons only work after providing a prompt)

---

## 7. FAQ

### General Questions

**Q: Is my data stored?**  
A: Your email is stored for authentication purposes. Conversation content is not persistently stored between sessions. Token usage statistics may be logged for operational purposes.

**Q: Can I use the bot in groups?**  
A: The bot is designed for private 1-on-1 conversations. Group functionality is not supported.

**Q: What AI model powers the optimization?**  
A: The bot uses GPT-4 or equivalent models (OpenAI or OpenRouter backends) for prompt optimization.

**Q: Is the bot free?**  
A: Usage depends on how the bot is deployed. Contact the bot operator for pricing information.

### Optimization Questions

**Q: Which method should I choose?**  
A: 
- **CRAFT** for complex, professional tasks needing structure
- **LYRA** for quick, simple optimizations
- **LYRA Detail** when you want LYRA's style but more comprehensive
- **GGL** for goal-oriented, outcome-focused prompts
- **Email delivery** when you want to compare all three

**Q: Can I optimize code-related prompts?**  
A: Yes! The bot works well with technical prompts. Consider using CRAFT for structured code tasks or GGL for specific coding goals.

**Q: Why do the optimization results vary?**  
A: Each method uses a different approach. Additionally, AI-generated content has inherent variability. This is normal and often beneficial for creativity.

**Q: What if my prompt is in a different language?**  
A: The bot can process prompts in various languages. Optimization quality may be best in English and Russian.

### Email Questions

**Q: Why do I need to verify my email?**  
A: Email verification ensures delivery to the correct address and prevents misuse of the email delivery feature.

**Q: How long does verification last?**  
A: Once verified, your email remains authenticated for future uses. You won't need to verify again unless there's a system reset.

**Q: Can I change my email?**  
A: Contact the bot operator for email change requests. The current system uses your first verified email.

**Q: Why didn't I receive the optimized prompts email?**  
A: Check spam folders, wait a minute for delivery, verify your email is correct, and ensure the email service was available when you made the request.

### Follow-up Questions

**Q: How many follow-up questions will the bot ask?**  
A: Typically 2-5 questions, depending on your prompt's complexity. You can generate your prompt at any time without answering all questions.

**Q: Can I go back to previous questions?**  
A: No, the conversation is linear. If you want to restart, click 🔄 Reset.

**Q: What if I timeout during follow-up?**  
A: After 5 minutes of inactivity, you'll automatically receive the cached improved prompt. No work is lost.

---

## 8. Version & Scope Notes

### Current Version

- **Bot Version**: Production-ready
- **Supported Methods**: CRAFT, LYRA (Basic & Detail), GGL
- **LLM Backends**: OpenAI, OpenRouter
- **Email Delivery**: Available with OTP verification
- **Languages**: Russian (RU), English (EN)

### Feature Availability

| Feature | Status | Notes |
|---------|--------|-------|
| Single-method optimization | ✅ Available | All 4 methods |
| Follow-up questions | ✅ Available | With timeout fallback |
| Email delivery (3 methods) | ✅ Available | Requires email verification |
| Post-optimization email | ✅ Available | Single-result email |
| Google Sheets logging | ⚙️ Optional | Deployment-dependent |

### Known Behaviors

1. **Long messages are split**: Messages over 4096 characters are automatically split
2. **Markdown formatting**: Some prompts may display with formatting; this is intentional
3. **Processing time varies**: Complex prompts take longer (up to 60 seconds)
4. **Email fallback**: If email fails, prompts are NOT shown in chat (security feature)

### Getting Help

If you encounter issues not covered in this guide:

1. Try the 🔄 Reset button first
2. Wait a few minutes and try again
3. Contact the bot operator for persistent issues

---

## Quick Reference Card

### Basic Workflow
```
/start → Enter prompt → Select method → Get result → (Optional) Follow-up → Done!
```

### Method Quick Guide
- 🛠 **CRAFT** = Structured & comprehensive
- ⚡ **LYRA** = Quick & efficient  
- 🧩 **LYRA detail** = Efficient but thorough
- 🔍 **GGL** = Goal-focused
- 📧 **Email** = Get all three methods

### Key Buttons
- 🔄 **Reset** = Start over (works anywhere)
- ✅ **YES** = Accept follow-up questions
- ❌ **NO** = Skip follow-up, keep prompt
- 🤖 **Generate** = Stop Q&A, get prompt now
- 📧 **Email** = Send result to email

---

*This documentation is for end users of the Telegram Prompt Engineering Bot. For technical documentation, deployment guides, and developer information, please refer to the project's technical documentation.*

