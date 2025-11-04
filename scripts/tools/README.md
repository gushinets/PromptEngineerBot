# Diagnostic and Maintenance Tools

This directory contains utility tools for diagnosing and maintaining the Telegram Prompt Engineering Bot.

## Google Sheets Tools

### `diagnose_gsheets.py`
Comprehensive diagnostic tool for Google Sheets logging issues.

**Usage:**
```bash
python scripts/tools/diagnose_gsheets.py
```

**Features:**
- Validates environment configuration
- Checks Google Sheets credentials and access
- Analyzes header mismatches
- Identifies common issues like empty cells
- Provides detailed recommendations
- Optional test data writing

**Requirements:**
- `GSHEETS_LOGGING_ENABLED=true`
- Valid Google Sheets credentials
- Access to target spreadsheet

### `repair_gsheets.py`
Automated repair tool for common Google Sheets header issues.

**Usage:**
```bash
python scripts/tools/repair_gsheets.py
```

**Features:**
- Automatically detects header mismatches
- Removes extra empty columns
- Fixes header alignment issues
- Interactive confirmation for safety
- Validates repairs after completion

**Common Fixes:**
- Removes extra empty columns at the beginning of sheets
- Replaces incorrect headers with expected format
- Adds headers to empty sheets

## Usage Examples

### Diagnosing Empty Cells Issue
```bash
# Run comprehensive diagnosis
python scripts/tools/diagnose_gsheets.py

# If issues are found, run repair
python scripts/tools/repair_gsheets.py
```

### Expected Google Sheets Format
The tools expect this exact header format:
```
DateTime | BotID | TelegramID | LLM | OptimizationModel | UserRequest | Answer | prompt_tokens | completion_tokens | total_tokens
```

## Troubleshooting

### Common Issues

1. **"GSHEETS_LOGGING_ENABLED is not set to 'true'"**
   - Set `GSHEETS_LOGGING_ENABLED=true` in your environment

2. **"No credentials configured"**
   - Set either `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`

3. **"Error accessing spreadsheet"**
   - Verify spreadsheet ID/name is correct
   - Ensure service account has access to the spreadsheet
   - Check that Google Sheets API is enabled

4. **"Header mismatch detected"**
   - Run `repair_gsheets.py` to automatically fix
   - Or manually adjust sheet headers to match expected format

### Manual Header Fix
If automatic repair doesn't work:

1. Open your Google Sheet
2. Ensure row 1 contains exactly these headers in order:
   ```
   DateTime, BotID, TelegramID, LLM, OptimizationModel, UserRequest, Answer, prompt_tokens, completion_tokens, total_tokens
   ```
3. Delete any extra empty columns
4. Save the sheet

## Development

### Adding New Tools
When adding new diagnostic tools:

1. Place them in the `scripts/tools/` directory
2. Add proper docstrings and usage instructions
3. Include error handling for common issues
4. Update this README with tool documentation
5. Follow the existing code style and patterns

### Testing Tools
Test tools with various scenarios:
- Empty sheets
- Sheets with wrong headers
- Sheets with extra columns
- Missing credentials
- Invalid spreadsheet IDs
