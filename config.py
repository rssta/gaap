
# Edit for model choices.
use_type = 'openai'   # one of 'local' (ollama), 'openai', or 'google'
if use_type == 'local':
    model = 'gemma4'  # need to install model separately before use
elif use_type == 'google':
    model = 'gemini-3.1-pro-preview'
elif use_type == 'openai':
    model = 'gpt-5.6-sol'


