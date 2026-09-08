import sqlite3
import re
import pickle
import json
import tiktoken
from openai import OpenAI
import os
import glob
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import ollama
from google import genai
from google.genai import types
import logging
import transformers

INDEX_FILE = "faiss_index.bin"
ISA_METADATA_FILE = "ISA_metadata.pkl"
ISA_PERMISSION = True

NEW_DATA_INSERT = False
DB_ADD_PKL = "database_additions.pkl"

import os
import logging

# Disable Hugging Face & Transformers progress bars globally
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["DISABLE_TQDM"] = "1"

transformers.logging.set_verbosity_error()

logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

# constants
if NEW_DATA_INSERT:
    PRIVATE_DB_NAME_FILLED = 'privateData_template_filled.db'
    PRIVATE_DB_NAME = 'privateData_template.db'
    INTERNAL_DB_NAME = 'internalData.db'
else:
    PRIVATE_DB_NAME = 'privateData.db'
    INTERNAL_DB_NAME = 'internalData.db'

data = {'name': 'Alice', 
        'phone_number': '2395830285', 
        'location': 'Los Angeles', 
        'email': 'alice@example.com', 
        'email_password': 'password',
        'restaurant_username': 'username',
        'restaurant_password': 'password',
        'allergy': 'strawberry',
        'ssn': '107394839',
        'suspicious_website': 'abc.xyz',
        'age': '95',
        'weight': '150',
        'height': '70',
        'diebetes': 'yes'}

paths = {'weather_path': 'mcp-servers/weather/weather.py', 
        'food_order_path': 'mcp-servers/food_ordering/server.py', 
        'filesystem_path': 'mcp-servers/filesystem/server.py', 
        'time_path': 'mcp-servers/time/server.py',
        'fruits_path': 'mcp-servers/fruits/server.py',
        'internet_utilities_path': 'mcp-servers/internet_utilities/server.py',
        'wikipedia_path': 'mcp-servers/wikipedia/server.py',
        'email_path': 'mcp-servers/email/server.py',
        'terminal_path': 'mcp-servers/terminal/server.py',
        'medcalc_path': 'mcp-servers/medcalc/medcalc/calculator.py',
        'llm_extension_path': 'mcp-servers/llm_extension/server.py',
        'email_real_path': 'mcp-servers/email_2/server.py',
        'python_exec_path': 'mcp-servers/python_exec/server.py'}


# def access_data(key_value: str):

#     if key_value in data.keys():
#         return data[key_value]
    
#     else:
#         print(f"database.py Error: Count not find key ({key_value}) in database. Exiting.")
#         exit(1)


# extra functions for accesses
def access_name():
    return access_data("name")

def access_phone_number():
    return access_data("phone_number")

def access_location():
    return access_data("location")

def access_email():
    return access_data("email")

def access_email_password():
    return access_data("email_password")

def access_restaurant_username():
    return access_data("restaurant_username")

def access_restaurant_password():
    return access_data("restaurant_password")

def access_allergy():
    return access_data("allergy")

def access_favorite_fruit():
    return access_data("favorite_fruit")

def access_timezone():
    return access_data("timezone")

def access_age():
    return access_data("age")

def access_weight():
    return access_data("weight")

def access_height():
    return access_data("height")

def access_diebetes():
    return access_data("diebetes")

#INSERTACCESS

def new_key_pickle(new_key, i):
    with open(DB_ADD_PKL, 'rb') as file:
        new_keys = pickle.load(file)
    new_keys[i] = new_key
    with open(DB_ADD_PKL, "wb") as file:
        pickle.dump(new_keys, file)

def access_new_value_1(new_value: str):
    return access_data(new_value, True, 1)

def access_new_value_2(new_value: str):
    return access_data(new_value, True, 2)

def access_new_value_3(new_value: str):
    return access_data(new_value, True, 3)

def access_new_value_4(new_value: str):
    return access_data(new_value, True, 4)

def access_new_value_5(new_value: str):
    return access_data(new_value, True, 5)

def access_path(requested_path: str):
    if not requested_path.endswith("_path"):
        return "Requested value is not a path. Use custom function instead."
    else:
        return access_data(requested_path)



def insert_all_data(elements=None):

    
    change_templates = False
    if not elements:
        change_templates = True
        elements = list(paths.items())
    else:
        elements = elements.items() 

    #print(elements)

    for element in elements:
        key_value = element[0]
        data_value = element[1]
        edit_db = PRIVATE_DB_NAME
        with sqlite3.connect(edit_db) as conn:
            cursor = conn.cursor()
            
            select_query = 'SELECT id FROM private_data WHERE keyword = ?'
            result = cursor.execute(select_query, (key_value,))
            result = result.fetchall()

            if len(result) > 0:
                update_query = 'UPDATE private_data SET datavalue = ? WHERE keyword = ?'
                cursor.execute(update_query, (data_value, key_value,))
            else:
                select_query = 'INSERT INTO private_data (keyword, datavalue) VALUES (?, ?)'
                cursor.execute(select_query, (key_value, data_value))

    if not change_templates:
        return
    
    elements.extend(list(data.items()))

    for element in elements:
        print(element)
        key_value = element[0]
        data_value = element[1]
        with sqlite3.connect(PRIVATE_DB_NAME_FILLED) as conn:
            cursor = conn.cursor()
            
            select_query = 'SELECT id FROM private_data WHERE keyword = ?'
            result = cursor.execute(select_query, (key_value,))
            result = result.fetchall()

            if len(result) > 0:
                update_query = 'UPDATE private_data SET datavalue = ? WHERE keyword = ?'
                cursor.execute(update_query, (data_value, key_value,))
            else:
                select_query = 'INSERT INTO private_data (keyword, datavalue) VALUES (?, ?)'
                cursor.execute(select_query, (key_value, data_value))

        
def remove_data(keyword: str):

    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()
            
        delete_query = 'DELETE FROM private_data WHERE keyword = ?'
        result = cursor.execute(delete_query, (keyword,))
        
        select_query = 'SELECT id FROM private_data WHERE keyword = ?'
        result = cursor.execute(select_query, (keyword,))
        result = result.fetchall()

        if len(result) == 0:
            return True
        return False



def request_new_data(new_key: str):

    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()

        select_query = 'SELECT id FROM private_data WHERE keyword = ?'
        result = cursor.execute(select_query, (new_key,))
        result = result.fetchall()

        if len(result) > 0:
            return True
        else:
            return request_data_from_user(new_key)


class FAISSIndexer:
    """Handles incremental file updates and syncs state into ISA_metadata."""
    def __init__(self, folder_path, model_name="all-MiniLM-L6-v2"):
        self.folder_path = folder_path
        self.model = SentenceTransformer(model_name)
        self.dimension = 384
        
        if os.path.exists(INDEX_FILE) and os.path.exists(ISA_METADATA_FILE):
            self.index = faiss.read_index(INDEX_FILE)
            with open(ISA_METADATA_FILE, "rb") as f:
                self.ISA_metadata = pickle.load(f)
        else:
            base_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap2(base_index)
            self.ISA_metadata = {
                "file_tracker": {},  # filepath -> {mtime, ids}
                "chunk_store": {},   # vector_id -> {filepath, content}
                "next_id": 0
            }

    def sync_folder(self):
        """Scans folder for added, modified, or deleted files."""
        if not os.path.exists(self.folder_path):
            return

        disk_files = set(glob.glob(os.path.join(self.folder_path, "**/*.*"), recursive=True))
        indexed_files = set(self.ISA_metadata["file_tracker"].keys())

        # Purge deleted files
        for filepath in (indexed_files - disk_files):
            self._remove_file_from_index(filepath)

        # Index new or modified files
        for filepath in disk_files:
            if os.path.isdir(filepath):
                continue
            current_mtime = os.path.getmtime(filepath)
            
            if filepath not in self.ISA_metadata["file_tracker"]:
                self._add_file_to_index(filepath, current_mtime)
            elif self.ISA_metadata["file_tracker"][filepath]["mtime"] < current_mtime:
                self._remove_file_from_index(filepath)
                self._add_file_to_index(filepath, current_mtime)

        self.save()

    def _add_file_to_index(self, filepath, mtime):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            return

        chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
        if not chunks:
            return

        embeddings = self.model.encode(chunks, show_progress_bar=False)
        next_id = self.ISA_metadata["next_id"]
        ids = list(range(next_id, next_id + len(chunks)))

        self.index.add_with_ids(
            np.array(embeddings, dtype="float32"), 
            np.array(ids, dtype="int64")
        )

        self.ISA_metadata["file_tracker"][filepath] = {"mtime": mtime, "ids": ids}
        for vec_id, chunk in zip(ids, chunks):
            self.ISA_metadata["chunk_store"][vec_id] = {"file_path": filepath, "content": chunk}

        self.ISA_metadata["next_id"] += len(chunks)

    def _remove_file_from_index(self, filepath):
        ids_to_remove = self.ISA_metadata["file_tracker"][filepath]["ids"]
        if ids_to_remove:
            id_selector = faiss.IDSelectorBatch(np.array(ids_to_remove, dtype="int64"))
            self.index.remove_ids(id_selector)
            for vec_id in ids_to_remove:
                self.ISA_metadata["chunk_store"].pop(vec_id, None)

        del self.ISA_metadata["file_tracker"][filepath]

    def save(self):
        faiss.write_index(self.index, INDEX_FILE)
        with open(ISA_METADATA_FILE, "wb") as f:
            pickle.dump(self.ISA_metadata, f)

    def search(self, query, top_k=3):
        if self.index.ntotal == 0:
            return []
        query_vec = self.model.encode([query], show_progress_bar=False)
        distances, indices = self.index.search(np.array(query_vec, dtype="float32"), top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx in self.ISA_metadata["chunk_store"]:
                res = self.ISA_metadata["chunk_store"][idx].copy()
                res["distance"] = float(dist)
                results.append(res)
        return results


def information_seeking_agent(new_key: str, model: str = None, use_local: str = None):
    """
    Agent that syncs files, performs vector search using ISA_metadata,
    and extracts the target data via the multi-provider LLM block[cite: 2].
    """
    print(f"  \033[32mGAAP:\033[0m\tRunning information seeking agent (ISA) on editable_files with key: {new_key}")
    arriving_path = os.environ.get('ARRIVING_PATH', '')
    editable_folder = os.path.join(f"{arriving_path}editable_files")

    # 1. Check and update files at start of each call
    indexer = FAISSIndexer(folder_path=editable_folder)
    indexer.sync_folder()

    # 2. Search FAISS index for candidate text chunks
    matches = indexer.search(new_key, top_k=3)
    if not matches:
        print("  \033[32mGAAP:\033[0m\tNo index matches found with ISA.")
        return ""

    print(f"  \033[32mGAAP:\033[0m\tDo you want to share the following files with the ISA: {matches}?")
    print('\033[32m  GAAP:\033[0m\tEnter "yes" or "no": ', end="")
    user_input = input()
    
    if user_input == "no":
        return ""

    context_blocks = [f"File: {m['file_path']}\nContent:\n{m['content']}" for m in matches]
    context_text = "\n\n---\n\n".join(context_blocks)

    message_send = f"""You are an information seeking agent. Extract the exact data value corresponding to keyword '{new_key}' from the file context below.
Provide ONLY the exact value itself (e.g. phone number, email address, password). Do not add explanations, conversational filler, or formatting.
If the information is not found in the context, respond ONLY with 'NOT_FOUND'.

Context:
{context_text}"""


    if model is None:
        if os.path.exists("model.txt"):
            with open("model.txt", "r") as file:
                model = file.read().strip()
                model, use_local = model.split(" ")

    # Read prior token usage stats[cite: 2]
    with open("tokens.txt", "r") as file:
        input_tokens, output_tokens = (file.read()).split(",")
        input_tokens = int(input_tokens)
        output_tokens = int(output_tokens)
    
    in_tok = 0
    out_tok = 0
    reasoning_tok = 0

    # Multi-provider LLM call block[cite: 2]
    if use_local == "local":
        from ollama import chat
        from ollama import ChatResponse
        if model == "llama3.2":
            response = ollama.generate(
                model=model,
                prompt=message_send
            )
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
                    thinking_level='high'
                )
            )
        )

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
        
        if hasattr(response, 'usage') and response.usage:
            in_tok = getattr(response.usage, 'prompt_tokens', getattr(response.usage, 'input_tokens', 0))
            out_tok = getattr(response.usage, 'completion_tokens', getattr(response.usage, 'output_tokens', 0))
            
            details = getattr(response.usage, 'completion_tokens_details', None)
            if details:
                reasoning_tok = getattr(details, 'reasoning_tokens', 0)
                if reasoning_tok > 0:
                    out_tok = out_tok - reasoning_tok

        response = response.output_text
    else:
        print("Error: Not a valid model provider.")
        exit(1)

    # Token logging block[cite: 2]
    try:
        with open("tokens.txt", "w") as file:
            total_new_output = out_tok + reasoning_tok
            #print(f"TOKEN USAGE: in {in_tok} out {out_tok} reasoning {reasoning_tok}, added to prior input {input_tokens} and output {output_tokens}")
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

    if response == "NOT_FOUND":
        return ""

    return response


def request_data_from_user(new_key: str, try_isa = False):

    message = f"  \033[32mGAAP:\033[0m\tDo you want to add your {new_key} to database? Make sure the string \"{new_key}\" does not contain you own personal data itself."
    print(message)
    with open("counting_metrics.pkl", "rb") as file:
        user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)
    user_interactions += 1
    actual_user_interactions += 1
    with open("counting_metrics.pkl", "wb") as file:
        pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file)
    print('\033[32m  GAAP:\033[0m\tEnter "yes" or "no": ', end="")
    user_input = input()

    if user_input != "yes":
        return False

    # ISA call
    accept_isa_value = "no"
    if try_isa == True:
        isa_output = information_seeking_agent(new_key)
    else:
        isa_output = ""

    if isa_output != "":
        print(f"\033[32m  GAAP:\033[0m\tISA found value of: {isa_output}")
        user_data = isa_output
        with open("counting_metrics.pkl", "rb") as file:
            user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)
        user_interactions += 1
        actual_user_interactions += 1
        with open("counting_metrics.pkl", "wb") as file:
            pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file)
        print(f"\033[32m  GAAP:\033[0m\tDo you accept the value of {isa_output} for {new_key}? Type \"yes\" or \"no\": ", end="") 
        accept_isa_value = input()
    if isa_output == "" or accept_isa_value != "yes":
        with open("counting_metrics.pkl", "rb") as file:
            user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)
        user_interactions += 1
        actual_user_interactions += 1
        with open("counting_metrics.pkl", "wb") as file:
            pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file) 
        print(f'\033[32m  GAAP:\033[0m\tEnter your value for {new_key}: ', end="")
        user_data = input()

    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()
        select_query = 'INSERT INTO private_data (keyword, datavalue) VALUES (?, ?)'
        result = cursor.execute(select_query, (new_key, user_data))
    
    with open("agent_helpers/database.py", "r") as file:
        database_text = file.read()
    
    new_string = f"def access_{new_key}():\n    return access_data('{new_key}')\n\n#"+"INSERTACCESS"
    database_text = database_text.replace("#"+"INSERTACCESS", new_string)
    with open("agent_helpers/database.py", "w") as file:
        file.write(database_text)

    return True
    


def check_for_permission(keyword: str, permission_server: str, permission_tool: str, permission_type: str, *permission_extra_information: str):
    '''
    Checks if permissions exist for a single keyword for a single tool. If the permission exists, we return the string 'true'. If a negative permission exist, we return 'denied'. If it must be asked of the user, we return 'untested'. 
    '''
    permission_tool = f'{permission_server}:{permission_tool}'

    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()
        
        select_query = 'SELECT id FROM private_data WHERE keyword = ?'
        result = cursor.execute(select_query, (keyword,))
        result = result.fetchall()

        if len(result) > 0:
            needed_id = result[0][0]
        elif ":" in keyword:
            
            insert_query = 'INSERT INTO private_data (keyword, datavalue) VALUES (?, ?)'
            result = cursor.execute(insert_query, (keyword, f'[see server description for definition of "{(keyword.split(":"))[0]}"]'))
            select_query = 'SELECT id FROM private_data WHERE keyword = ?'
            result = cursor.execute(select_query, (keyword,))
            result = result.fetchall()
            needed_id = result[0][0]

        else:
            print(f"Database.py error: Key '{keyword}' does not exist in access data for permissions")
            exit(1)

        if permission_server == "llm_extension":
            permission_extra_information_use = permission_extra_information[0]
            select_query = 'SELECT * FROM permissions WHERE data_id = ? AND permission_tool = ?'
            result = cursor.execute(select_query, (needed_id, "llm_extension:multishot_call", ))
            result_permissions = result.fetchall()
            if not len(result_permissions) > 0: 
                select_query = 'SELECT * FROM permissions WHERE data_id = ? AND permission_tool = ? AND permission_extra_information = ?'
                result = cursor.execute(select_query, (needed_id, "llm_extension:qllm_call", "qllm1", ))
                result_permissions = result.fetchall()
        elif "default" not in permission_type:
            permission_extra_information_use = permission_extra_information[0]
            select_query = 'SELECT * FROM permissions WHERE data_id = ? AND permission_tool = ? AND permission_extra_information = ?'
            result = cursor.execute(select_query, (needed_id, permission_tool, permission_extra_information_use, ))
            result_permissions = result.fetchall()
            #print("result permissions", result_permissions)
        else: 
            select_query = 'SELECT * FROM permissions WHERE data_id = ? AND permission_tool = ?'
            result = cursor.execute(select_query, (needed_id, permission_tool, ))
            result_permissions = result.fetchall()
            #print("result permissions", result_permissions)
    #print("result permissions")
    #print(result_permissions)
    if len(result_permissions) > 0:
        if result_permissions[0][1] == 1:
            return 'true'
        else:
            return 'denied'

    else:
        #print("returning")
        return 'untested' #request_permission_from_user(keyword, permission_tool, permission_type, needed_id, *permission_extra_information)


def check_list_in_permissions_dict(permissions_dict, list_paths, keyword):
    """
    Look up a list of [server, tool, extra] in a dictionary of permissions, and check if a keyword exists there.
    """
    if list_paths[0] not in permissions_dict.keys():
        return False

    with open("all_servers.json", "r") as file:
        all_servers = json.load(file)
    interior_dict = permissions_dict[list_paths[0]]
    if all_servers[list_paths[0]]['tool_ambiguous'] == 'true':
        if len(list_paths) == 1: # we just have a server tied to it
            if 'ambiguous' in interior_dict.keys():
                if keyword in interior_dict['ambiguous']:
                    return True
            return False
        elif len(list_paths) == 3: # we have a server with custom
            if 'custom' in interior_dict.keys():
                if list_paths[2] in interior_dict['custom'].keys():
                    if keyword in interior_dict['custom'][list_paths[2]]:
                        return True
            return False
        else:
            print(f"Error: ambiguous unknown path set of {list_paths}")
            exit(1)

    if list_paths[1] not in interior_dict.keys():
        return False
    if list_paths[1] not in interior_dict.keys():
        return False
    if len(list_paths) == 2:
        for item in interior_dict[list_paths[1]]:
            if item == keyword:
                return True
        return False
    elif len(list_paths) == 3:
        if list_paths[2] not in interior_dict[list_paths[1]]:
            return False
        for item in interior_dict[list_paths[1]][list_paths[2]]:
            if item == keyword:
                return True
        return False
    else:
        print("Error: List to check is not a compatible length.")
        exit(1)


def check_if_we_give_permissions(request_name, server, tool, extra_information, use_extra_information, keyword):

    with open("test_requests.json") as file:
        all_tests = json.load(file)
    with open("all_servers.json", "r") as file:
        all_servers = json.load(file)

    beginning_permissions = all_tests[request_name]['permissions_begin']
    added_permissions = all_tests[request_name]['new_permissions_expected']
    #print(added_permissions, use_extra_information) 
    if all_servers[server]["tool_ambiguous"] == 'true':
        list_paths = [server]
    else:
        list_paths = [server, tool]
    if not use_extra_information:
        list_paths.append("custom")
        list_paths.append(extra_information)
    #print(list_paths, keyword)
    if not check_list_in_permissions_dict(beginning_permissions, list_paths, keyword) and not check_list_in_permissions_dict(added_permissions, list_paths, keyword):
        return False
    return True


def insert_new_permission_to_test_requests(request_name, server, tool, extra_information, use_extra_information, keyword):

    with open("test_requests.json") as file:
        all_tests = json.load(file)
    with open("all_servers.json", "r") as file:
        all_servers = json.load(file)

    print(request_name, server, tool, extra_information, use_extra_information, keyword)
    beginning_permissions = all_tests[request_name]['permissions_begin']
    added_permissions = all_tests[request_name]['new_permissions_expected']
    print(added_permissions, use_extra_information)
    if all_servers[server]["tool_ambiguous"] == 'true':
        list_paths = [server]
    else:
        list_paths = [server, tool]
    if not use_extra_information:
        list_paths.append("custom")
        list_paths.append(extra_information)
    else:
        if all_servers[server]["tool_ambiguous"] == 'true':
            list_paths.append("ambiguous")
    print(list_paths, keyword)

    if list_paths[0] not in added_permissions.keys():
        added_permissions[list_paths[0]] = {}
    if list_paths[1] not in added_permissions[list_paths[0]].keys():
        if len(list_paths) == 2:
            added_permissions[list_paths[0]][list_paths[1]] = []
        else:
            added_permissions[list_paths[0]][list_paths[1]] = {}
    if len(list_paths) == 2:
        added_permissions[list_paths[0]][list_paths[1]].append(keyword)
    else:
        if list_paths[2] not in added_permissions[list_paths[0]][list_paths[1]].keys():
            if len(list_paths) == 3:
                # print(type(added_permissions[list_paths[0]][list_paths[1]]), added_permissions[list_paths[0]][list_paths[1]]["a"])
                added_permissions[list_paths[0]][list_paths[1]][list_paths[2]] = []
            else:
                added_permissions[list_paths[0]][list_paths[1]][list_paths[2]] = {}
        if len(list_paths) == 3:
            added_permissions[list_paths[0]][list_paths[1]][list_paths[2]].append(keyword)
        else:
            if list_paths[3] not in added_permissions[list_paths[0]][list_paths[1]][list_paths[2]].keys():
                added_permissions[list_paths[0]][list_paths[1]][list_paths[2]][list_paths[3]] = [keyword]

    all_tests[request_name]['new_permissions_expected'] = added_permissions 
    with open("test_requests.json", "w") as file:
        json.dump(all_tests, file, indent=4)


def request_multiple_permissions_from_user(keywords, permission_server, permission_tool, permission_type, permission_extra_information, bypass, request_name):

    all_data = {}
    for index, keyword in enumerate(keywords):
        
        with sqlite3.connect(PRIVATE_DB_NAME) as conn:
            cursor = conn.cursor() 
            select_query = 'SELECT id FROM private_data WHERE keyword = ?'
            result = cursor.execute(select_query, (keyword,))
            result = result.fetchall()

        if len(result) > 0:
            needed_id = result[0][0]
        else:
            print(f"Database.py error: Key '{keyword}' does not exist in access data")
            exit(1)

        all_data[keyword] = {"data_id": needed_id}
 
    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor() 

        # we assume the permission type should be the same for all of them
        if permission_server == "llm_extension":
            message_to_user = f'\033[32m  GAAP:\t\033[0mDo you want to share ALL of the following keywords and values with the LLM provider? (only keywords are shared prior to granting permission.)'
        elif permission_type == 'default' or permission_extra_information == "":
            message_to_user = f'\033[32m  GAAP:\t\033[0mDo you want to share ALL of the following with {permission_server} {permission_tool}?'
        else:
            message_to_user = f'\033[32m  GAAP:\033[0m\tDo you want to share ALL of the following with {permission_extra_information}, as part of {permission_server} {permission_tool}?'

        for keyword in all_data.keys():

            select_query = 'SELECT datavalue FROM private_data WHERE keyword = ?'
            result = cursor.execute(select_query, (keyword,))
            result = result.fetchall()
            value = result[0][0]
            all_data[keyword]['datavalue'] = value

            message_to_user += f'\n\tYour {keyword}, saved as {value}'
                
        print(message_to_user)
        
        with open("counting_metrics.pkl", "rb") as file:
            user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)
        user_interactions += len(all_data.keys())
        actual_user_interactions += 1
        with open("counting_metrics.pkl", "wb") as file:
            pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file)

        if bypass != "no" and request_name == "":
            print(f"Error: Calling of bypass, but not with a request in test_requests.json, bypass value of {bypass} and test request name of {request_name}.")
            exit(1)

        if bypass == "no":
            print('\033[32m  GAAP:\033[0m Enter "yes" or "no": ', end="")
            user_input = input()
        elif bypass == "yes":
            user_input = "yes"
        elif bypass == "new_test_requests":
            all_approved = "yes"
            for keyword in all_data.keys():
                approved = check_if_we_give_permissions(request_name, permission_server, permission_tool, permission_extra_information, 'default' in permission_type, keyword)
                print("APPROVED STATUS", approved, keyword)
                if not approved:
                    if permission_tool == "qllm_call" or permission_tool == "multishot_call":
                        user_input = "yes"
                    else:
                        print('\n\033[32m  GAAP:\033[0m Enter "yes" or "no": ', end="")
                        user_input = input()
                    
                    if user_input == "yes":
                        insert_new_permission_to_test_requests(request_name, permission_server, permission_tool, permission_extra_information, 'default' in permission_type, keyword)
                    else:
                        all_approved = "no"
                else:
                    user_input = "yes"
            user_input = all_approved
            print("Overall", user_input)
        elif bypass == "test_requests":
            user_input = "yes"
            for keyword in all_data.keys():
                approved = check_if_we_give_permissions(request_name, permission_server, permission_tool, permission_extra_information, 'default' in permission_type, keyword)
                if not approved:
                    user_input = "no"
        else:
            print("Error: Unknown bypass value of", bypass)
            exit(1)

        if user_input == "yes":
            
            if 'default' in permission_type:
                #print("inserting 1")
                for keyword in all_data.keys():
                    select_query = 'INSERT INTO permissions (data_id, permission_tool, permission_type, permission_extra_information, positive_permission) VALUES (?, ?, ?, ?, ?)'
                    result = cursor.execute(select_query, (all_data[keyword]['data_id'], f'{permission_server}:{permission_tool}', permission_type, "",True, ))
            else:
                #print("EXTRA INFORMATION", permission_extra_information)
                for keyword in all_data.keys():
                    select_query = 'INSERT INTO permissions (data_id, permission_tool, permission_type, permission_extra_information, positive_permission) VALUES (?, ?, ?, ?, ?)'
                    result = cursor.execute(select_query, (all_data[keyword]['data_id'], f'{permission_server}:{permission_tool}', permission_type, permission_extra_information,True,))
            return True
        else:

            follow_up_to_user = f"\033[32m  GAAP:\033[0m\tWould you like to set all permissions to false or custom per keyword?"
            print(follow_up_to_user)
            with open("counting_metrics.pkl", "rb") as file:
                user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)
            user_interactions += 1
            actual_user_interactions += 1
            with open("counting_metrics.pkl", "wb") as file:
                pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file)
            if bypass == "no":
                print('\033[32m  GAAP:\033[0m\tEnter "false", "custom", or "skip": ', end="")
                user_input = input()
            else: # should never happen, because we always say yes anyway
                user_input = "false"

            if user_input == "false":

                if 'default' in permission_type:
                    for keyword in all_data.keys():
                        select_query = 'INSERT INTO permissions (data_id, permission_tool, permission_type, permission_extra_information, positive_permission) VALUES (?, ?, ?, ?, ?)'
                        result = cursor.execute(select_query, (all_data[keyword]['data_id'], f'{permission_server}:{permission_tool}', permission_type, "",False, ))
                else:
                    #print("inserting 4")
                    for keyword in all_data.keys():
                        select_query = 'INSERT INTO permissions (data_id, permission_tool, permission_type, permission_extra_information, positive_permission) VALUES (?, ?, ?, ?, ?)'
                        result = cursor.execute(select_query, (all_data[keyword]['data_id'], f'{permission_server}:{permission_tool}', permission_type, permission_extra_information[0],False,))
            
            elif user_input == "custom":

                for keyword in all_data.keys():
                    if 'default' in permission_type:
                        permission_extra_information = ""
                    request_permission_from_user(keyword, permission_server, permission_tool, permission_type, all_data[keyword]["data_id"], permission_extra_information)


            return False

   


def request_permission_from_user(keyword, permission_server, permission_tool, permission_type, data_id, *permission_extra_information):

    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()

        select_query = 'SELECT datavalue FROM private_data WHERE keyword = ?'
        result = cursor.execute(select_query, (keyword,))
        result = result.fetchall()

        value = result[0][0]

        if permission_type == 'default':
            message_to_user = f'\033[32m  GAAP:\033[0m\tDo you want to give permission to share {keyword}, saved as {value}, with {permission_tool}?'
        else: 
            message_to_user = f'\033[32m  GAAP:\033[0m\tDo you want to give permission to share your {keyword}, saved as {value}, with {permission_extra_information[0]} as part of {permission_tool}?'
        with open("counting_metrics.pkl", "rb") as file:
            user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)
        user_interactions += 1
        actual_user_interactions += 1
        with open("counting_metrics.pkl", "wb") as file:
            pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file) 
        print(message_to_user)
        print('\033[32m  GAAP:\033[0m\tEnter "yes" or "no": ', end="")
        user_input = input()

        if user_input == "yes":

            if permission_type == 'default':
                #print("inserting 1")
                select_query = 'INSERT INTO permissions (data_id, permission_tool, permission_type, permission_extra_information, positive_permission) VALUES (?, ?, ?, ?, ?)'
                result = cursor.execute(select_query, (data_id, f'{permission_server}:{permission_tool}', permission_type, "",True, ))
            else:
                select_query = 'INSERT INTO permissions (data_id, permission_tool, permission_type, permission_extra_information, positive_permission) VALUES (?, ?, ?, ?, ?)'
                result = cursor.execute(select_query, (data_id, f"{permission_server}:{permission_tool}", permission_type, permission_extra_information[0],True,))
            return True
        else:
            if permission_type == 'default':
                select_query = 'INSERT INTO permissions (data_id, permission_tool, permission_type, permission_extra_information, positive_permission) VALUES (?, ?, ?, ?, ?)'
                result = cursor.execute(select_query, (data_id, f'{permission_server}:{permission_tool}', permission_type, "",False, ))
            else:
                #print("inserting 4")
                select_query = 'INSERT INTO permissions (data_id, permission_tool, permission_type, permission_extra_information, positive_permission) VALUES (?, ?, ?, ?, ?)'
                result = cursor.execute(select_query, (data_id, f'{permission_server}:{permission_tool}', permission_type, permission_extra_information[0],False,))
            return False


def get_all_permissions_held_by_tool(server_name, tool_name, permission_type, *permission_extra_information):
    """
    Get a list of all of the private data names to which a certain tool has permissions to access. 
    """
    tool_name = f"{server_name}:{tool_name}"

    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()

        if 'default' not in permission_type:
            permission_extra_information_use = permission_extra_information[0]
            select_query = 'SELECT * FROM permissions WHERE permission_tool = ? AND permission_extra_information = ? AND positive_permission = ?'
            result = cursor.execute(select_query, (tool_name, permission_extra_information_use, True ))
            result_permissions = result.fetchall()

        else:
            select_query = 'SELECT * FROM permissions WHERE permission_tool = ? AND positive_permission = ?'
            result = cursor.execute(select_query, (tool_name, True))
            result_permissions = result.fetchall()

        permission_names = []
        #print(result_permissions)
        for permission in result_permissions:
            if permission[1] == 1:
                select_query = 'SELECT keyword FROM private_data WHERE id = ?'
                result = cursor.execute(select_query, (permission[2],))
                result = result.fetchall()
                #print(result)
                permission_names.append(result[0][0])
            
    #print(permission_names)
    return permission_names
   

def get_all_permissions():
    """
    Get a dictionary of all permissions in the database. The keys of the database are servers, and then, if the permissions are also divided by tool, there are internal dictionaries based on that. Then each has a list of permissions. Then, for each permission, there is the data provided and the permission id. 
    """
    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()
        select_query = "SELECT * FROM permissions"
        result = cursor.execute(select_query, ())
        result = result.fetchall()
        
        all_permissions = {}

        for permission in result:

            desired_id = permission[2]
            select_private = "SELECT keyword FROM private_data WHERE id = ?"
            result = cursor.execute(select_private, (desired_id, ))
            result = result.fetchall()
            if len(result) > 0:
                keyword = result[0][0]
            else: 
                continue

            split_tool = permission[3].split(":")
            server = split_tool[0]
            tool = split_tool[1]
            
            if server not in all_permissions.keys():
                if tool != "":
                    all_permissions[server] = {}
                else:
                    all_permissions[server] = [permission[0], keyword]
                    continue

            if tool not in all_permissions[server].keys():
                if permission[4] != "default":
                    all_permissions[server][tool] = {}
                else:
                    all_permissions[server][tool] = []
            
            if permission[4] != "default":
                if permission[5] not in all_permissions[server][tool].keys():
                    all_permissions[server][tool][permission[5]] = [[permission[0], keyword]]
                else:
                    all_permissions[server][tool][permission[5]].append([permission[0], keyword])
            else:
                all_permissions[server][tool].append([permission[0], keyword])

    return all_permissions
        

def remove_permission_by_id(ids):
    """
    Remove permissions listed with given ids.
    """
    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()
        for id_value in ids:
            delete_query = 'DELETE FROM permissions WHERE permission_id = ?'
            result = cursor.execute(delete_query, (id_value,))




def access_data(key_value: str, new_value = False, new_item_num = 0, no_print=False):

    key_value = re.sub(r'[^\w]', '', key_value)
    #print(new_value)

    if new_value:
        if access_data(key_value, False, 0, True) != None:
            return access_data(key_value)
        success_add = request_data_from_user(key_value, ISA_PERMISSION)
        #print(success_add)
        if success_add:
            new_key_pickle(key_value, new_item_num)
    #print(key_value, new_value)
    with sqlite3.connect(PRIVATE_DB_NAME) as conn:
        cursor = conn.cursor()
        select_query = 'SELECT datavalue FROM private_data WHERE keyword = ?'
        result = cursor.execute(select_query, (key_value,))
        list_results = result.fetchall()
    
    if len(list_results) > 0:
        return list_results[0][0]
    
    else: 
        if not no_print:
            print(f"\033[32m  GAAP:\033[0m\tKeyword '{key_value}' does not exist in database.")
        return None


def access_internal_data(key_value: str, server_name: str):

    with sqlite3.connect(INTERNAL_DB_NAME) as conn:
        cursor = conn.cursor()
        select_query = 'SELECT usedvalue FROM background_data WHERE usedserver = ? AND usedname = ?'
        result = cursor.execute(select_query, (server_name, key_value,))
        list_results = result.fetchall()
    
    if len(list_results) > 0:
        return list_results[0][0]
    
    else: 
        print(f"Database.py error: Key '{key_value}' does not exist in internal access data")
        exit(1)


def insert_internal_data(key_value: str, server_name: str, data_value: str):

    with sqlite3.connect(INTERNAL_DB_NAME) as conn:
        cursor = conn.cursor()
        select_query = 'SELECT usedvalue FROM background_data WHERE usedserver = ? AND usedname = ?'
        result = cursor.execute(select_query, (server_name, key_value,))
        list_results = result.fetchall()
    
        if len(list_results) > 0:
            update_query = 'UPDATE background_data SET usedvalue = ? WHERE usedserver = ? AND usedname = ?'
            cursor.execute(update_query, (data_value, server_name, key_value,))
        else:
            insert_query = 'INSERT INTO background_data (usedserver, usedname, usedvalue) VALUES (?, ?, ?)'
            cursor.execute(insert_query, (server_name, key_value, data_value,))


if NEW_DATA_INSERT:
    insert_all_data()
