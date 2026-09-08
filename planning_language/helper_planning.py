

import sqlite3
import json

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



def make_preamble(insert_data=False):

    with open("all_servers.json", "r") as all_server:
        all_servers_dict = json.load(all_server)

    total_preamble = 'I need to write instructions for an agent to complete a task. My agent is able to execute in the follow language. Each instruction gets a new line, for commands: \nrow#, server_name:tool_name, output_type, next_row_to_execute,\n…\nArguments for all instructions are listed below all instructions csv. Note that the types can be one of str, int, float, bool, or None.\nPossible commands include:'

    for single_server_name in all_servers_dict.keys():

        single_server_text = ""
        single_server_text += f"server name: {single_server_name}\n"
        single_server_text += f"path: {single_server_name}_path\n"
        single_server_text += "Tools available:\n"
        for single_tool in all_servers_dict[single_server_name]["tools"].keys():
            single_server_text += f"{single_tool}: {all_servers_dict[single_server_name]['tools'][single_tool]['info']}\n"
        single_server_text += f"{all_servers_dict[single_server_name]['note']}\n\n"

        total_preamble += single_server_text

    total_preamble += 'Other commands are: '#\npython_exec:python_run(code, func_name, input_val) → str, a block of python that can execute anything using built-in python libraries (must import in function) to create an output, the python code should be expressed in one string where new lines can exist, but NO sets of two newlines together. input_val is an object of your choosing that acts as arguments to the function. If you want to format strings or handle unstructured data, it is highly recommended to use the qllm instead of python_exec, to avoid errors, but you can use python_run for structured data such as csv, as qllm may mess up with big data, use qllm for ANY writing of plaintext, you CANNOT access or write files with the Python, and you CANNOT use os or sys libraries, instead use the filesystem for that, also be sure to have a backup if the Python returns nothing in the case that there was a failure, also, be careful that inputs are valid, such as by checking them with qllm, because if an error occurred prior, it will fail as well because the Python input object will be wrong, DO NOT USE python_run in cases where there is not computation to happen, instead USE qllm as it will have less errors, use python_run only when absolutely useful,'
    total_preamble += '\nprint:user(text), print out information in a string called text to the user. This is helpful when they request something. This is the only way to ensure they see what you want them to see.\ndatabase:access_data(key), access a users private data, note that location is a city name string — to use it with time tools you must first convert it to an IANA timezone string (e.g. America/Los_Angeles) via qllm_call. Bool-typed keys return the string \"yes\" or \"no\", NOT a JSON boolean; if a tool requires true/false, convert with python_run or qllm_call first. Available keys are:\n'
    list_results = get_all_keywords()

    string_results = ""
    for single_result in list_results:
        string_results += single_result + "\n"

    if insert_data:
        string_results += "You can attempt to add new keys to the database by calling database:access_data(key, new) with a new key and an argument 'new' that is set to 'yes'. YOU MUST provide the argument of 'new': 'yes' whenever the key you request is not listed above. Only do this if the key's values doesn't exist in the database and you are sure this is private that that will be useful in persistance.\n"

    total_preamble += string_results

    total_preamble += 'You can also make an instruction that is an if statement. This can be used for loops too:\nrow#, if, next_row_if_true, next_row_if_false,\nThen, arguments are placed below among the others, with (left, sign, and right), see example below.\nWhere, we execute the sign such as if left is 5 and right is 4, and we have sign is =, then 5 = 4 is not true, so we skip next row to execute to be the next_row_if_false. The possible signs are =, <, >. These can execute on strings or ints. DO NOT try to have the left or right be a dict or list, only an int or string, as they will be compared as Python objects, and it will fail with complex objects. You need to REMEMBER TO HAVE QUOTES in your argument list, specifically when you will use a REF (see below). Something that compares an int to a str, or a str to an undefined type will fail. Put quotes around the REF, so that when it is substituted, it will be a string. If the output of another call is in a dict, you must pull out only a str or int in order to make control flow — use a step that takes the dict as input and returns just the one field you need, then use that REF in the if. After listing all instructions, but two newlines, and then list each line number, a space, and a json dict of the arguments for that line. Separate each json with two newlines. See below for example. Remember that the server name for multishot_call and qllm_call is llm_extension. When you are writing to the user or sending an email, be sure to use the format specified in instructions EXACTLY. Emails dont need to be json. \nIf you want to use the output of one instructionline for another line, you can use that prior line number. For example, line 1’s output is always available in later lines as REF:1. So, an arg could be written as REF:1, and it would pull the output of line 1. Always put quotes around your REFs. The quotes will be removed if the item inserted is just a raw type, and REF:X is the only item in the quotes. Such, as, items from the database, which are strings, you should use "REF:1". The filesystem outputs strings with no quotes, so REF of filesystem output needs quotes. Do not allow REF:X to appear unquoted, add quotes if unsure. If you want REF to leave a type other than a string, just put "REF:X" with no other characters inside the quote, and the type will be entirely substituted. If you put other characters in the quotes, it will then just be a string. The substitution will not add quotes, so the json will have a decode error if there is a string with no quotes, such as if REF:1 is "hi", we could have json that looks like "name":REF:1, decode to "name":hi, which is invalid json. "name" is just an example, and do not use in your code. Remember that the substitution is direct, so if you get a dict from qllm, for instance, it will be placed as a dict inside of your arguments. You CANNOT index into a REF, it will only be placed in its entirety. So, form the exact item you want with python_run or qllm_call beforehand. Type errors will cause the program to crash and fail, so do not make them.\nRemember that strings may be spelled differently in places, or missing, in which case use qllm to check, or have error handling to send to multishot before incorrect actions happen. If you want to have the qllm or Python make an entire argument dict, you can do that, but just make the entire argument spot a REF, with no braces. \nWhen you are done, call the multishot, or have the final instruction lead to 0, and execution finishes.\n'

    total_preamble += 'Example instructions:\n1,email:send_email,str,2,\n2,database:access_data,int,3,\n3,if,4,3,\n4,email:send_email,str,5,\n'
    #5,python_exec:python_run,int,0,
    total_preamble += '\n\n{"address":"123", "content":"3"}"\n\n2 {"key":"name"}\n\n3 {"left":"REF:1", "sign":"!=", "right":"hi"}\n\n{"address":"123@abc.com", "content":"REF:1"}\n\n'
    #{"code":"def multiply(input_item: list):\\n    return input_item[0]*input_item[1]", "func_name":"multiply","input_val":[4,5]}\n
    total_preamble += 'Here is an incorrect argument list, because you see a dict was substituted as a REF, when only the one item should be:  {\'username\': \'samucla\', \'password\': \'secrets123\', \'order_items\': ["{\'action\':\'order\',\'payload\':\'coffee\'}"]} \nRemember that the arguments are listed after all the instructions. The qllm_call should ONLY HAVE A SINGLE STRING AS ARGUMENT under prompt, along with the output_type and call_name. The prompt cannot be anything other than a string. Remember that output type can include dict, so use this if you want json, dont use string then. If you need to determine more execution based on the first block of code, USE MULTISHOT, and give it instructions of what to do next, including any inofmration passed from the prior block. Such as, if you need information from the first block to determine the next instructions, pass them into the multishot prompt. The multishot prompt should not just be the same as the first prompt, instead be acting on the next step, not repeating what already happened. Multishot allows another block of code to be made, but it should not repeat the same tasks, so pass information into the prompt. Still, dont just call multishot immediately, make use of the first code block to make tool calls. And remember that all instructions need a server name, a colon, then tool name. If the user asks for information, you must print it to them with print:user, otherwise they wont see it, such as if you called another tool. You can call multishot for further code to be made, but DO NOT ask questions to the user, you need to figure this out. If the task involves reading a file and then acting on its contents, do not ask for clarification — use the tools available to resolve any missing context (e.g. check a menu, look up a value) and proceed. Note: If a tool or lookup fails or has an error, it returns None. Downstream steps should check for and handle None values gracefully. '#Here is an example of extracting a single field from a dict (REF:3) using python_run to avoid passing the whole dict: {"code":"def get_val(item):\n    return item.get(\'key_name\') if isinstance(item, dict) else None", "func_name":"get_val", "input_val":REF:3}. 
    total_preamble += 'If you ever see "User denied requested permissions", then you must give up on your action. YOU MUST give up that action, as the user has rejected the request, and you must fully change course or give up entirely. Otherwise, remember, your goal is to complete the task with whatever information you have. Try to avoid errors if possible. If information is sparse or missing, do your best, and dont just give up on the task. DO NOT GIVE UP. KEEP TRYING workarounds or other methods, such as when errors arise. Use multishot or qllm in the case you are unsure, such as you need to do any checking of correctness or if a tool call worked, or use multishot if you think information should per persisted in context. Do not waste tokens, by spinning or writing overly verbose text. Make a set of instructions that completes the following task:'

    return total_preamble




