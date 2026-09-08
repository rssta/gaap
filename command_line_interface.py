import os
import run_full_query
from openai import OpenAI
import sqlite3
import json
import sys 
import ollama
import threading
import time
import external_modifications.external_permissions_modification as external_permissions_modification 
import external_modifications.external_queries_check as external_queries_check
import external_modifications.external_private_data as external_private_data
import config
from google import genai
import logging

use_type = config.use_type
model = config.model
model_max_chars = 272000
results_database = "queries_4.db"
run_type = "planning_language"
override_pre_message = True
pre_message_type = "ssn"
overridden_pre_message_name = "ssn_swap"
overridden_pre_message = ""
new_keys_allowed = True
bypass = "no"
reuse_permissions_db = True

logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("fastmcp").setLevel(logging.WARNING)
logging.getLogger("mcp.client").setLevel(logging.WARNING)
logging.getLogger("mcp.server").setLevel(logging.WARNING)

with open("model.txt", "w") as file:
    file.write(f"{model} {use_type}")

with open("arriving_path_file.txt", "w") as file:
    file.write(os.environ['ARRIVING_PATH'])
with open("api_key.txt", "w") as file:
    if use_type == "openai":
        file.write(os.environ['OPENAI_API_KEY'])
    elif use_type == "google":
        file.write(os.environ['GEMINI_API_KEY'])
os.makedirs(os.environ['ARRIVING_PATH'] + "editable_files", exist_ok=True)
if not os.path.exists("tokens.txt"):
    with open("tokens.txt", "w") as file:
        file.write("0,0")

# constants
PRIVATE_DB = "privateData.db"

def get_all_keywords():

    with sqlite3.connect(PRIVATE_DB) as conn:
        cursor = conn.cursor()
        select_query = 'SELECT keyword FROM private_data'
        result = cursor.execute(select_query)
        result = result.fetchall()

        used_keywords = []
        for single_keyword in result:
            if ":" not in single_keyword[0]:
                used_keywords.append(single_keyword[0])
        return used_keywords


def spin_worker(stop_event):
    """Worker function that runs in a background thread to animate the spinner."""
    frames = ['|', '/', '-', '\\']
    i = 0
    while not stop_event.is_set():
        # \r moves the cursor back to the start of the line
        sys.stdout.write(f"\rAgent processing.  {frames[i % len(frames)]}")
        sys.stdout.flush()
        i += 1
        time.sleep(0.1)



def make_decision(query: str, model: str, use_type: str):
    """
    Decide if we are going to give a text output or make tool calls as a result.
    True means we print out, False means tool calls must be made.
    """

    preamble = """You are the GAAP agent (Guaranteed Accounting for Agent Privacy). You can act as a regular agent, or you can call GAAP tool call mode for data privacy. You were created by UCLA as GAAP, but use another underlying model underneath. Always say something at least to any prompt. You have access to the context that is stated at the end of this. You must decide if you can best handle the user request by just printing out some output to them, or if tool calls, in an agentic manner, are needed. Tool calls also have access to a database of private data about the user, so if you think you would need that, then direct towards tool calls. Any user specific data should be found in database if not in prompt. Specifically, any data that is user specific that is not in your knowledge base, that is not common knowledge, should come from the database. If it is not already in database, have tool calls add it to database. DO NOT ask the user directly for values to put in database, instead let a tool call block do this. It can figure out the key name and everything. The current keys in database are:\n"""

    all_keywords = get_all_keywords()
    for word in all_keywords:
        if "_path" not in word:
            preamble += f"{word}\n"
    
    preamble += "If there is a keyword from the database that you need that doesn't exist, just allow a tool call mode block execute and access it. A tool call block can request from the user new keys for the database. You are not allow to ask the user for any private data, and be clear they shouldn't give it to you."

    preamble += """The following tools are available:"""
    with open("all_servers.json", "r") as all_server:
        all_servers_dict = json.load(all_server)

    for single_server_name in all_servers_dict.keys():
        single_server_text = ""
        single_server_text += f"server name: {single_server_name}\n"
        single_server_text += f"path: {single_server_name}_path\n"
        single_server_text += "Tools available:\n"
        for single_tool in all_servers_dict[single_server_name]["tools"].keys():
            single_server_text += f"{single_tool}: {all_servers_dict[single_server_name]['tools'][single_tool]['info']}\n"
        single_server_text += f"{all_servers_dict[single_server_name]['note']}\n\n"

        preamble += single_server_text

    preamble += """Try to avoid asking too much to the user that you can figure out yourself. Also, things that can be discovered with the database or with the code block fo tool calls should be left up to that. Remember, you must NOT ask for any personal information from the user directly, instead direct a tool call block to be made that inserts new database values."""

    preamble += "If the user wants to end the chat, tell them to type /exit. If they want to view or edit the GAAP databases manually, tell them to type /help to get the options. Avoid markdown style, as this will appear in a regular command line."

    preamble += """As your output, write a single character 1 (if we print out) or 2 (if we need tool calls). If you need to call tools or access database, you MUST use the 2 option. You must always choose either 1 or 2. Never choose nothing or refuse to respond, that is useless. If print out, then also write directly after this first character all of the text to print out. If tool calls, you can write extra instructions into the query by adding text after the first character. This could be useful if you want the internal agent to know your thoughts, or if you think the internal agent should return data out as multishot. The only way for tool calls to impact this chat's context long term is if it is returned in multishot, so instruct that if you think data will be needed later. Often, this is useful for any data a user requests. Remember, you cannot see the output of a tool call unless it returns in multishot, so mention multishot specifically in the instructions.f you need the output. If the latest request is for multishot, then it is your choice if more tool calls are needed or if print out can happen so we have a new query from user. If you have nothing too print, just print blank space. Code execution can allow for getting private data from the database or tools, ans so if that data is to be sent back to this agent for future use, it should be in the multishot flow. Remember to have some kind of return status, if you need to know if something worked. Here is the user context, with the bottom being the newest requests:"""

    message_send = preamble + query 
    
    with open("current_context_to_outer_llm.txt", "w") as file:
        file.write(message_send)

    try:
        encode = tiktoken.encoding_for_model(model)
        tokenized_message = encode.encode(message_send)
    except Exception as e:
        encode = 0
    with open("tokens.txt", "r") as file:
        input_tokens, output_tokens = (file.read()).split(",")
        input_tokens = int(input_tokens)
        output_tokens = int(output_tokens)
    
    if use_type == "local":
        from ollama import chat
        from ollama import ChatResponse
        if model == "llama3.2":

            response = ollama.generate(
                model=model,
                prompt=message_send
            )
            response = response['response']

        else:
            response: ChatResponse = chat(model=model, messages=[
            {
                'role': 'system', 
                'content': message_send,
            },
            ])
            response = response.message.content
    elif use_type == "google":
        client = genai.Client()

        response = client.models.generate_content(
            model=model,
            contents=message_send,
        )

        response = response.text
    elif use_type == "openai":
        client = OpenAI()
        response = client.responses.create(
        model=model,
        input=message_send
        )
        response = response.output_text
    else:
        print("Error: Not a valid model provider.")
        exit(1)
    
    try:
        tokenized_response = encode.encode(response)
        with open("tokens.txt", "w") as file:
            file.write(f"{len(tokenized_message)+input_tokens},{output_tokens+len(tokenized_response)}")
    except Exception as e: 
        encode = 0
 
    if len(response) < 1:
        return True, response
    if response[0] == "1":
        return True, response[1:].strip()
    elif response[0] == "2":
        return False, response[1:].strip()
    else:
        return True, response


def handle_commands(command: str):

    if command == "exit":
        print("\033[31m/:\033[0m\tExiting.")
        exit(0)
    elif command == "clear_context":
        return command
    elif command == "remove_permissions":
        print("\033[31m/:\033[0m\tPermissions Modification.")
        external_permissions_modification.call_all_operations()
    elif command == "check_queries":
        print("\033[31m/:\033[0m\tQueries Check.")
        external_queries_check.ask_queries(results_database) 
    elif command == "private_data":
        print("\033[31m/:\033[0m\tPrivate Data Viewer and Editor.")
        external_private_data.private_data_options()
    elif command == "help":
        print("\033[31m/:\033[0m\tWelcome to the GAAP agent. When you see \033[35mUser\033[0m, you can type your own prompts. Hit enter/return when you are done with a prompt. Do NOT put any private or personal data into your prompts or answers to questions unless you see a green \033[32mGAAP\033[0m indicator. The following commands can be entered during the chat:\n\t\033[31m/exit\033[0m to end chat.\n\t\033[31m/clear_context\033[0m to clear the context.\n\t\033[31m/remove_permissions\033[0m to remove granted permissions.\n\t\033[31m/check_queries\033[0m to check prior queries to GAAP internal agent and requests to MCP servers.\n\t\033[31m/private_data\033[0m to view and modify private data in database.\n\t\033[31m/help\033[0m to repeat these instructions.")
    else:
        print("\033[31m/:\033[0m\tUnknown command: "+command+ "\n\tType /help to see commands.")
        return None


# GAAP External Control Loop

current_context = ""
more_queries = True
skip_user_input = False
run_full_query.set_multishot_files(all_taints=[], all_prompts=[], new_multishot=False)

print("\nWelcome to the GAAP agent. When you see \033[35mUser\033[0m, you can type your own prompts. Hit enter/return when you are done with a prompt. Do NOT put any private or personal data into your prompts or answers to questions unless you see a green \033[32mGAAP\033[0m indicator. \n\nThe following commands can be entered during the chat:\n  \033[31m/exit\033[0m to end chat.\n  \033[31m/clear_context\033[0m to clear the context.\n  \033[31m/remove_permissions\033[0m to remove granted permissions.\n  \033[31m/check_queries\033[0m to check prior queries to GAAP internal agent and requests to MCP servers.\n  \033[31m/private_data\033[0m to view and modify private data in database.\n  \033[31m/help\033[0m to repeat these instructions.\n")
while more_queries: 

    if not skip_user_input:
        next_query = input("\033[35mUser:\033[0m\t")
        if len(next_query) <= 0:
            continue
        if next_query[0] == "/":
            result_command = handle_commands(next_query[1:])
            if result_command == "clear_context":
                current_context = ""
                run_full_query.set_multishot_files(all_taints=[], all_prompts=[], new_multishot=False)
                print("\033[31m/:\033[0m\tContext cleared.")
            continue

        previous_context = current_context
        current_context += f"\nNext user prompt: {next_query}"
    
    stop_spin = threading.Event()
    spin_thread = threading.Thread(target=spin_worker, args=(stop_spin,))
    spin_thread.start()
    #print(current_context)
    decision, output_text = make_decision(current_context, model, use_type)
    skip_user_input = False

    if decision == True:

        # we are in standard chat
        stop_spin.set()
        spin_thread.join()
        sys.stdout.write("\r" + " " * 50 + "\r")
        sys.stdout.flush()
        print(f'\033[34mAgent:\033[0m\t{output_text}')
        current_context += f"\nNext LLM output: {output_text}"

    else:
        
        # we go to GAAP
        override_query = next_query + output_text
        overridden_pre_message = previous_context
        #try:
        run_full_query.run_all_tests(model, model_max_chars, results_database, ["testing"], False, run_type, override_pre_message, new_keys_allowed, bypass, overridden_pre_message, reuse_permissions_db, pre_message_type, overridden_pre_message_name, override_query, True, True, False, use_type, stop_spin, spin_thread)
        #except Exception as e:
        #    pass
        
        if run_type == "ours":
            with open("agent_helpers/generated_script_orig.txt") as file:
                latest_script = file.read()
                current_context += f"The following script was executed to complete tasks and execute tools: {latest_script}\n Unless the script above returned something or you have indication it shouldn't have worked, the tasks in it completed. Do not do them over again unless necessary."
        if run_type == "planning_language":
            with open(f"planning_language/plan.txt","r") as file:
                plan_text = file.read()
            current_context += f"The following instructions were executed in order, where the last column defines the next instruction to execute, starting with 1: {plan_text}\n Unless the script above returned something or you have indication it shouldn't have worked, the tasks in it completed. Do not do them over again unless necessary."

        all_taints, all_prompts, new_multishot = run_full_query.get_multishot_files()
        #print(all_prompts, new_multishot)

        if new_multishot:
            current_context += f"\nNext multishot agent output: {all_prompts[-1]}"
            skip_user_input = True
            
