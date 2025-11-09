# API Key Configuration Guide

## 📍 API Key Location and Configuration

### Where the API Key is Stored:

1. **Configuration File**: `config.py`
   - **Line 30-31**: API key configuration
   - Supports both `GEMINI_API_KEY` and `ANTHROPIC_API_KEY` environment variables
   - Code:
     ```python
     GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '') or os.getenv('ANTHROPIC_API_KEY', '')
     ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')  # Kept for backward compatibility
     ```

2. **Service File**: `services/gemini_api.py`
   - **Line 14-18**: API key initialization
   - Accepts API key from constructor or environment variables
   - Code:
     ```python
     self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
     ```

3. **Usage in Routes**:
   - `routes/analysis_routes.py` - Line 124: Uses API key for analysis
   - `routes/conversion_routes.py` - Line 94: Uses API key for conversion

### How to Set the API Key:

#### Option 1: Environment Variable (Recommended)
Create a `.env` file in the project root directory:

```env
GEMINI_API_KEY=your-gemini-api-key-here
```

Or use `ANTHROPIC_API_KEY` for backward compatibility:
```env
ANTHROPIC_API_KEY=your-gemini-api-key-here
```

#### Option 2: System Environment Variable
Set it in your system environment variables:
- Windows: `set GEMINI_API_KEY=your-key-here`
- Linux/Mac: `export GEMINI_API_KEY=your-key-here`

#### Option 3: Direct Configuration (Not Recommended for Production)
You can set it directly in `config.py`, but this is NOT recommended for security reasons.

### How to Verify API Key is Set:

Run this command to check if the API key is configured:
```bash
python -c "import os; print('GEMINI_API_KEY:', 'SET' if os.getenv('GEMINI_API_KEY') else 'NOT SET')"
```

### Important Notes:

1. **The API key should be a Gemini API key** (not Anthropic/Claude key)
2. **Never commit the `.env` file to version control** (add it to `.gitignore`)
3. **The application will show an error** if the API key is not set when trying to use AI features
4. **Both `GEMINI_API_KEY` and `ANTHROPIC_API_KEY` are supported** for backward compatibility

### Error Messages:

If the API key is missing, you'll see:
- `"API key not configured. Please set GEMINI_API_KEY or ANTHROPIC_API_KEY environment variable."`
- `"GEMINI_API_KEY or ANTHROPIC_API_KEY is required. Please set it in environment variables or pass it to the constructor."`

### Getting a Gemini API Key:

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the API key
5. Set it in your `.env` file or environment variables

