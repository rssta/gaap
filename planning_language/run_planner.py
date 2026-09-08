
import planning_language.helper_planning as helper_planning
from openai import OpenAI
import tiktoken
import ollama
from google import genai
import planning_language.interpreter as interpreter
import sys
import time
import sqlite3

def generate_plan(query: str, model: str, use_local: bool, arriving_path="", pre_message=None, use_pre_message=False, insert_new=False, print_anything=True):

    preamble = helper_planning.make_preamble(insert_new)

    if use_pre_message:
        message_send = preamble + "\nuser message:\n" + pre_message + "\nuser message:\n" + query
    else:
        message_send = preamble + "\nuser message:\n" +  query

    with open("tokens.txt", "r") as file:
        input_tokens, output_tokens = (file.read()).split(",")
        input_tokens = int(input_tokens)
        output_tokens = int(output_tokens)
    
    # Initialize variables for API token extraction
    in_tok = 0
    out_tok = 0
    reasoning_tok = 0

    if use_local == "local":
        from ollama import chat
        from ollama import ChatResponse
        if model == "llama3.2":

            response = ollama.generate(
                model=model,
                prompt=message_send
            )
            # Extract Ollama tokens
            in_tok = response.get('prompt_eval_count', 0)
            out_tok = response.get('eval_count', 0)
            
            response = response['response']

        else:
            response: ChatResponse = chat(model=model, messages=[
            {
                'role': 'system', 
                'content': message_send,
            },
            ])
            # Extract Ollama Chat tokens
            in_tok = getattr(response, 'prompt_eval_count', 0)
            out_tok = getattr(response, 'eval_count', 0)
            
            response = response.message.content
    elif use_local == "google":
        client = genai.Client()

        response = client.models.generate_content(
            model=model,
            contents=message_send,
            config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level='high' # Or types.ThinkingLevel.HIGH
        )
    )

        )

        # Extract Google tokens
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            in_tok = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            out_tok = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
            reasoning_tok = getattr(response.usage_metadata, 'thoughts_token_count', 0) or 0

        response = response.text
    elif use_local == "openai":
        client = OpenAI()
        response = client.responses.create(
        model=model,
        reasoning={"effort":"high"},
        input=message_send
        )
        
        # Extract OpenAI tokens
        if hasattr(response, 'usage') and response.usage:
            # Safely check for standard names or alternative wrapper names
            in_tok = getattr(response.usage, 'prompt_tokens', getattr(response.usage, 'input_tokens', 0))
            out_tok = getattr(response.usage, 'completion_tokens', getattr(response.usage, 'output_tokens', 0))
            
            # Check for reasoning tokens
            details = getattr(response.usage, 'completion_tokens_details', None)
            if details:
                reasoning_tok = getattr(details, 'reasoning_tokens', 0)
                # Isolate base output by subtracting reasoning tokens
                if reasoning_tok > 0:
                    out_tok = out_tok - reasoning_tok

        response = response.output_text
    else:
        print("Error: Not a valid model provider.")
        exit(1)
    
#   try:
#       tokenized_response = encode.encode(response)
#       with open("tokens.txt", "w") as file:
#           file.write(f"{len(tokenized_message)+input_tokens},{output_tokens+len(tokenized_response)}")
#   except Exception as e: 
#       encode = 0

    # Write the newly extracted tokens to file, combining output and reasoning tokens as requested
    try:
        with open("tokens.txt", "w") as file:
            total_new_output = out_tok + reasoning_tok
            if print_anything:
                print(f"TOKEN USAGE: in {in_tok} out {out_tok} reasoning {reasoning_tok}, added to prior input {input_tokens} and output {output_tokens}")
            file.write(f"{input_tokens + in_tok},{output_tokens + total_new_output}")
    except Exception as e:
        pass
 
    if response[:3] == "```":
        response = response[3:]
    if response[:6] == '```csv':
        response = response[6:]
    if response[-3:] == '```':
        response = response[:-3]
    response = response.strip()

    with open(f"{arriving_path}planning_language/plan.txt", "w") as file:
        file.write(response)

    return response


def run_planning(query, model, use_local, stop_spin, spin_thread, print_anything, arriving_path="", bypass='no', request_name='', pre_message=None, use_pre_message=False):

    try:
        if print_anything:
            print("GENERATING PLAN")
        if not print_anything:
            insert_new = True
        else:
            insert_new = False
        plan = generate_plan(query, model, use_local, arriving_path, insert_new=insert_new, print_anything=print_anything)
        #with open(f"{arriving_path}planning_language/plan.txt", "r") as file:
        #    plan = file.read()

        tools = {}
        instruction_dict = interpreter.parse_plaintext(plan, tools, print_anything=print_anything)

        if not print_anything:
            stop_spin.set()
            spin_thread.join()
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()
            #print(f'\033[34mAgent:\033[0m\t')

    except Exception as e:
        
        if not print_anything:
            stop_spin.set()
            spin_thread.join()
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()
            #print(f'\033[34mAgent:\033[0m\t')

        # We retry the generation
        plan = generate_plan(query, model, use_local, arriving_path, pre_message, use_pre_message, print_anything=print_anything)

        tools = {}
        instruction_dict = interpreter.parse_plaintext(plan, tools, print_anything=print_anything)


    current_time = time.time()

    with sqlite3.connect('queries_4.db') as conn:
        cursor = conn.cursor()
        insert_query = 'INSERT INTO queries (query, model_name, generated_script, current_time) VALUES (?, ?, ?, ?)'
        cursor.execute(insert_query, (query, model, plan, current_time))
        current_query_id = cursor.lastrowid


    multishot_text, print_out, multishot_taints = interpreter.run_script(instruction_dict, current_query_id, bypass=bypass, request_name=request_name, print_anything=print_anything)

    with open("tokens.txt", "r") as file:
        input_tokens, output_tokens = (file.read()).split(",")
        input_tokens = int(input_tokens)
        output_tokens = int(output_tokens)

    if input_tokens > 300000 or output_tokens > 50000:
        multishot_text = ""
        print_out += f"Execution cut off because token limit reached with input_tokens {input_tokens} and output_tokens {output_tokens}"


    return multishot_text, current_query_id, print_out, multishot_taints

