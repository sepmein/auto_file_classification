# Ollama Setup Guide

This guide explains how to set up and use Ollama for local LLM inference with the auto file classification system.

## What is Ollama?

Ollama is a tool that allows you to run large language models locally on your machine without requiring API keys or internet connectivity for inference.

## Installation

### 1. Install Ollama

**Windows:**

```bash
# Download and install from https://ollama.ai/download
# Or use winget
winget install Ollama.Ollama
```

**macOS:**

```bash
# Download and install from https://ollama.ai/download
# Or use Homebrew
brew install ollama
```

**Linux:**

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Start Ollama Service

```bash
# Start Ollama service (runs on http://localhost:11434)
ollama serve
```

### 3. Pull a Model

For file classification, we recommend lightweight models:

```bash
# Ultra-lightweight model (good for testing)
ollama pull llama3.2:1b

# Small but capable model  
ollama pull qwen2.5:3b

# Larger model for better accuracy
ollama pull llama3.2:3b
```

## Configuration

The system is already configured to use Ollama by default in `rules.yaml`:

```yaml
llm:
  provider: ollama
  model: llama3.2:1b  # Change to your preferred model
  base_url: http://localhost:11434
  api_key: null  # Not needed for Ollama
  temperature: 0.1
  max_tokens: 1000
```

## Testing Ollama Integration

### 1. Verify Ollama is Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Should return JSON with available models
```

### 2. Test with the Classification System

```bash
# Run classification with LLM enabled
python -m ods apply test_documents --dry-run

# You should see log messages like:
# "Ollama客户端设置成功，端点: http://localhost:11434/v1"
# "LLM分类成功"
```

## Model Recommendations

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `llama3.2:1b` | ~1GB | Very Fast | Good | Testing, lightweight classification |
| `qwen2.5:3b` | ~2GB | Fast | Better | Balanced performance |
| `llama3.2:3b` | ~2GB | Fast | Better | Good general purpose |
| `qwen2.5:7b` | ~4GB | Medium | Best | High accuracy needs |

## Troubleshooting

### Common Issues

1. **Connection Refused**

   ```
   Error: Connection refused to http://localhost:11434
   ```

   **Solution:** Make sure Ollama service is running (`ollama serve`)

2. **Model Not Found**

   ```
   Error: model 'llama3.2:1b' not found
   ```

   **Solution:** Pull the model first (`ollama pull llama3.2:1b`)

3. **Memory Issues**

   ```
   Error: insufficient memory
   ```

   **Solution:** Use a smaller model like `llama3.2:1b`

### Fallback Behavior

If Ollama is not available, the system will automatically fall back to rule-based classification:

```
WARNING - LLM分类器将无法工作
INFO - 使用备用分类方法
```

This ensures the system continues to work even without LLM support.

## Advanced Configuration

### Custom Base URL

If running Ollama on a different port or machine:

```yaml
llm:
  provider: ollama
  base_url: http://192.168.1.100:11434  # Remote Ollama instance
  model: llama3.2:1b
```

### Multiple Providers

You can easily switch between providers by changing the configuration:

```yaml
llm:
  # Local Ollama (default)
  provider: ollama
  model: llama3.2:1b
  base_url: http://localhost:11434
  
  # Uncomment for OpenAI
  # provider: openai
  # model: gpt-4o-mini
  # api_key: your_openai_api_key_here
  
  # Uncomment for Anthropic Claude
  # provider: claude
  # model: claude-3-haiku-20240307
  # api_key: your_anthropic_api_key_here
```

## Performance Tips

1. **GPU Acceleration**: Ollama automatically uses GPU if available
2. **Model Caching**: Models are cached after first load
3. **Concurrent Requests**: Ollama handles multiple requests efficiently
4. **Resource Monitoring**: Monitor CPU/Memory usage with `ollama ps`

For more information, visit [Ollama's official documentation](https://ollama.ai/docs).
