from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from openai import AsyncOpenAI
import tiktoken
import ollama
from google import genai

# Initialize FastMCP server
mcp = FastMCP("llm_extension")



@mcp.tool()
async def qllm_call(prompt: str, output_type: str, call_name: str):
    """
    Call a quarantined LLM to produce a response to a question to an LLM of a specified type. Allowed types are str, int, float, bool, and dict.
    """
    desired_output = ""
    if output_type == "str":
        desired_output = "str"
    elif output_type == "int":
        desired_output = "int"
    elif output_type == "float":
        desired_output = "float"
    elif output_type == "bool":
        desired_output = "bool"
    elif output_type == "dict":
        desired_output = "dict"
    else:
        return "Output type was not of an acceptable type."

    prompt = f"You are a quarantined LLM answering a question. Respond to the prompt specified below. You must only return one string that can be directly cast into the specified type. If the specified type is a dict, pass a json that can be cast to dict. The specified type you must return is: {desired_output} \n\n Here is the prompt: {prompt}"

    with open("api_key.txt", "r") as file:
        api_key = file.read()

    with open("model.txt", "r") as file:
        model = file.read()
        if len(model.split()) == 2:
            model, use_local = model.split()

    try:
        with open("tokens.txt", "r") as file:
            input_tokens, output_tokens = (file.read()).split(",")
            input_tokens = int(input_tokens)
            output_tokens = int(output_tokens)
    except Exception:
        input_tokens, output_tokens = 0, 0

    # Initialize variables for API token extraction
    in_tok = 0
    out_tok = 0
    reasoning_tok = 0

    if use_local == "local":
        if model == "llama3.2":

            response = ollama.generate(
                model=model,
                prompt=prompt
            )
            response_text = response['response']
            
            # Extract Ollama generate tokens
            in_tok = response.get('prompt_eval_count', 0)
            out_tok = response.get('eval_count', 0)

        else:
            response: ChatResponse = chat(model=model, messages=[
            {
                'role': 'system', 
                'content': prompt,
            },
            ])
            response_text = response.message.content
            
            # Extract Ollama chat tokens
            in_tok = getattr(response, 'prompt_eval_count', 0)
            out_tok = getattr(response, 'eval_count', 0)
            
    elif use_local == "google":
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        response_text = response.text    
        
        # Extract Google tokens
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            in_tok = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            out_tok = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
            reasoning_tok = getattr(response.usage_metadata, 'thoughts_token_count', 0) or 0

    elif use_local == "openai":
        client = AsyncOpenAI(api_key=api_key)
        response = await client.responses.create(
            model=model,
            input=prompt
        )
        response_text = response.output_text
        
        # Extract OpenAI tokens flexibly to avoid AttributeError
        if hasattr(response, 'usage') and response.usage:
            in_tok = getattr(response.usage, 'prompt_tokens', getattr(response.usage, 'input_tokens', 0))
            out_tok = getattr(response.usage, 'completion_tokens', getattr(response.usage, 'output_tokens', 0))
            
            details = getattr(response.usage, 'completion_tokens_details', None)
            if details:
                reasoning_tok = getattr(details, 'reasoning_tokens', 0) or 0
                if reasoning_tok > 0:
                    out_tok = out_tok - reasoning_tok

    else:
        print("Error: Not a valid model provider.")
        exit(1)

#   try:
#       tokenized_response = encode.encode(response_text)
#       with open("tokens.txt", "w") as file:
#           file.write(f"{len(tokenized_message)+input_tokens},{output_tokens+len(tokenized_response)}")
#   except Exception as e:
#       encode = 0

    # Write the newly extracted tokens to file, combining output and reasoning tokens
    try:
        with open("tokens.txt", "w") as file:
            total_new_output = out_tok + reasoning_tok
            file.write(f"{input_tokens + in_tok},{output_tokens + total_new_output}")
    except Exception as e:
        pass 
 
    try:
        if output_type == "str":
            return str(response_text)
        elif output_type == "int":
            return int(response_text)
        elif output_type == "float":
            return float(response_text)
        elif output_type == "bool":
            return bool(response_text)
        elif output_type == "dict":
            return dict(response_text)
    except (ValueError, TypeError):
        try:
            return str(response_text)
        except (ValueError, TypeError):
            return "Returned value could not be type converted."


@mcp.tool()
async def multishot_call(prompt: str):
    """
    Call to make a second block of code. Prompt must be short enough that it can fit along with the original preamble into the context.
    """
    pass



def main():
    # Initialize and run the server
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()

