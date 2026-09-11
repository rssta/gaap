
# Edit for model choices.
use_type = 'openai'   # One of 'local' (ollama), 'openai', or 'google'.
if use_type == 'local':
    model = 'gemma4'  # Need to install model separately before use.
elif use_type == 'google':
    model = 'gemini-3.1-pro-preview'
elif use_type == 'openai':
    model = 'gpt-5.6-sol'

# Edit for information seeking agent (ISA) use.
use_ISA = False         # Default is False.

# Edit for default permissions denial behavior. One of 'false', 'true', 'skip', or 'none'.
denial_choice = 'skip'  # Default is 'skip'.

# Edit for permissions checks to send private data to the LLM provider. One of True or False.
check_llm_permissions = False
