
import sqlite3
import asyncio
import json

# NOTE: This file is used in the old Python based version of GAAP. See planning_language directory for the new version.

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


async def find_all_tool_names():
    ''' Assumes all items in database ended with "path" describe servers, and then gets all tools from those. '''
    # NOT COMPLETE
    with sqlite3.connect(PRIVATE_DB) as conn:
        cursor = conn.cursor()
        select_query = 'SELECT keyword, datavalue FROM private_data'
        result = cursor.execute(select_query, ())
        list_results = result.fetchall()

    for single_result in list_results:
        if single_result[0][-5:] == "_path":
            mcp_client = MCPClient()
            await mcp_client.connect_to_server(single_result[0][:-5], single_result[1])
            tools = await mcp_client.list_available_tools()


def list_permissions():
    """Lists all of the permissions that exist thus far."""

    with sqlite3.connect(PRIVATE_DB) as conn:
        cursor = conn.cursor()
        select_query = "SELECT * FROM permissions"
        result = cursor.execute(select_query, ())
        all_permissions = result.fetchall()
    
    #print(all_permissions)
    
    with sqlite3.connect(PRIVATE_DB) as conn:
        cursor = conn.cursor()
        select_query = "SELECT * FROM private_data"
        result = cursor.execute(select_query, ())
        all_private_data = result.fetchall()

    #print(all_private_data)

    all_permission_string = ""
    
    try:
        for permission in all_permissions:

            if permission[1] == 1:
                accept = "yes"
            else:
                accept = "no"

            # TODO, fix this to make a dict of some kind. This direct indexing will not work if someone ever removes something from the database
            data_keyword = all_private_data[permission[2]-1][1]

            tool_name = permission[3]

            if permission[4] != 'default':
                extra_information = f" with identifier, {permission[5]}"
            else:
                extra_information = ""

            all_permission_string += f"{tool_name}, {data_keyword}{extra_information}: {accept}\n"
    except IndexError as e:
        all_permission_string = "None specified yet."
    return all_permission_string
    

def get_preamble(insert_new_data_allowed: bool):
    """Get a dynamically created preamble with keys added and current servers."""

    with open("all_servers.json", "r") as all_server:
        all_servers_dict = json.load(all_server)

    total_preamble = ""
    total_preamble += "Assume you have access to an MCP server. You can connect to it inside an async function like this: \nfrom mcpclient_spec import MCPClient\nmcp_client = MCPClient()\nawait mcp_client.connect_to_server(server_name, path)\noutput = await mcp_client.process_query(<tool>, current_query_id, arg1_key, arg1, arg2_key, arg2, ...)  # current_query_id is defined above the scope of this code. DO NOT set it, or reassign it, or modify it within your code. Always write process_query calls entirely on a single line, with no line breaks. It's okay if the line is long. Where the keys are the names of the arugments, and then followed by the argument itself. You can add all the arguments needed by the tool.\nawait mcp_client.cleanup()\nInstead of using loop, use asyncio.run(main()) around your entire function.\n\nRemember that you must make separate MCPClient() objects for each server you want to connect to, otherwise it will not work.\n\nThe following MCP server tools are available:\n"

    for single_server_name in all_servers_dict.keys():

        single_server_text = ""
        single_server_text += f"server name: {single_server_name}\n"
        single_server_text += f"path: {single_server_name}_path\n"
        single_server_text += "Tools available:\n"
        for single_tool in all_servers_dict[single_server_name]["tools"].keys():
            single_server_text += f"{single_tool}: {all_servers_dict[single_server_name]['tools'][single_tool]['info']}\n"
        single_server_text += f"{all_servers_dict[single_server_name]['note']}\n\n"

        total_preamble += single_server_text

    total_preamble += "A database with the following keys is available for use:\n"
    
    list_results = get_all_keywords()

    string_results = ""
    for single_result in list_results:
        string_results += single_result + "\n"

    total_preamble += string_results
    #total_preamble += "Note that the location key points to a string of a city name, height is in inches, and weight is in lbs. All values are strings.\n\n"
    
    #total_preamble += "The following defines what permissions for database keys are allowed for each tool call. Note that, if 'yes', then this information can be used. If 'no', then it can still be attempted, but the user may stop the action. If a certain tool and key pair isn't listed here, then you may attempt to use this key for a certain tool.\n"
    #total_preamble += list_permissions()
    total_preamble += "\nTo access the database, do the following:\nimport database\n# for the paths, use the access_path function\nneeded_path = database.access_path('weather_path')\n# for the non-paths, use custom functions structured 'access_<name of item>'\nneeded_name = database.access_name()\nneeded_allergy = database.access_allergy()\n\n"
    if insert_new_data_allowed:
        total_preamble += "If you want to access some sort of user data that is not among the keys of the database, you can request a new key. You can call the function access_new_value_1(<keyword>) with the new keyword you want. Then, if you want a second new key, you call access_new_value_2(<keyword>), up to 5. These function calls are 1 indexed, so no 0. Try to add things SPARINGLY, only what is completely needed. Note that the location is saved as a city name string in the database.\n\n"
    total_preamble += "Note that getattr() from database will not work. You must write out the function. Some items say 'true' or 'false'.\n\n"
    total_preamble += "If you want to access other keys in database, make new functions. Like, for 'phone_number', use database.access_phone_number(). This function exists, and will work. Do not attempt for values not in the database yet. Phone number may not yet be, if not listed above. If you need a password or username for some server, you can ask the user and add to database. Be sure keywords you choose are specific, such as if multiple passwords may exist." 
    total_preamble += "Remember that paths from the database must be accessed with path=database.access_path(path_name), not by just calling something a string with the word path in it. Then, this path can be passed to initialize an MCP."
    total_preamble += "Note that responses from an MCP server will look like a dictionary like this, with the response being the content inside. There could be multiple TextContent objects:\n{'meta': None, 'content': [TextContent(type='text', text='<response text>', annotations=None, meta=None)], 'structuredContent': None, 'isError': False}\n\n"
    total_preamble += "BE CAREFUL with output from the qllm. Do not make any assumptions of type. It may always be a string of unformatted content.\n"
    total_preamble += "Remember that tool names are single strings, they don't have any . in them, but must be specified with quotes around as strings."
    total_preamble += "Remember that arguments to tools with their keyword names must each be separate arguments, like (...arg_name1, arg1, arg_name2, arg2...)"
    total_preamble += "Remember, if you have any questionable text to parse or write, or any other tasks that would be best done by an LLM with all accessed data visible, send it to the quarantined llm. Or, if you believe additional tool calls or code to execute will be helpful after having an LLM look at some data, use the multishot. Note that the multishot can call access_{data} functions, so you do not need to pass all data into the llm if not needed. But, be sure to pass mcp outputs or other calculated data that is derived from the first block. The multishot is very helpful in cases where you CANNOT DETERMINE WHAT TOOLS need to be used at the time of the initial prompt. USE IT, do not be afraid to use the multishot if it will be easier. Remember, what it allows is for the LLM to see new data passed out of the code block, and generate a new code block based on it. DO NOT WRITE CODE THAT EXECUTES ALL TOOLS IF YOU ARE UNSURE, use the multishot instead. AND, DO NOT DEFINE FUNCTIONS with def. NEVER make a list of all tools that may need to operate, when you don't know what tools. Instead, use multishot, and allow the next block of code generated to contain precisely the right tool.\n\n"
    total_preamble += "Do not use the string 'process_query' anywhere unless it is actually to call the function. Use other terms. Do not even use it in strings, even trying to describe this function for future calls, instead encode those characters.\n\n"
    total_preamble += "Make a Python script. Only output the script, and nothing else. Do not write ``` or python at the top or bottom. Do not put any bash decorator at top. Include everything in a function called async def main, and do not call that function. Write no other helper functions or inner function. 'def' and 'eval' cannot be used UNDER ANY CIRCUMSTANCES other than to define the main function. Do not use input(), as a user cannot give you any; work with what you have. Do not use member functions that modify an existing object, as they will not work. So, function such as 'append' does not work, but function such as 'lower' will work. Assume paths to the servers will be available in database. Always use spaces, and not tabs, for indents. If information needs to be sent, please print it, but also be sure to complete the needed tool calls. Do not print confusing, unclear, or useless information to the user. You can print helpful information first, but then put your final answer in an obviously separated space at the end. The script should complete the following:\n"
    
    with open("operation_helpers/preamble_dynamic.txt", "w") as file:
        file.write(total_preamble)

    return total_preamble


def get_preamble_static():
    """Get up to date preamble from file, with current keys added."""

    with open("operation_helpers/preamble.txt") as preamble_file:
        text = preamble_file.read()

    list_results = get_all_keywords()
    
    string_results = ""
    for single_result in list_results:
        string_results += single_result[0] + "\n"

    preamble = text.replace("INSERT_KEYS_HERE", string_results)

    list_permissions()

    preamble = preamble.replace("INSERT_PERMISSIONS", list_permissions())
    #print(preamble)
    return preamble

def get_prepended_code():
    """Supply the code we want to add to the beginning of the program."""

    prepended_code = "import asyncio\nimport sys\nfrom mcpclient_spec import MCPClient\nimport database\ncurrent_query_id = int(sys.argv[1])\n"

    return prepended_code

def get_pre_message_formatted(pre_message: str):
    """Convert a message into a full header that looks like previous messages."""

    return f"Previous messages in chat context:\n\tMessage 1: '{pre_message}'\n\nNew Message:\n"


def get_appended_code():
    """Supply the code we want at the end of the program."""

    appended_code = '\ntry:\n    asyncio.run(main())\nexcept RuntimeError as e:\n    #print(\'Error: Runtime error occurred in script.\')\n    import pickle\n    with open("multishot.pkl", "rb") as file:\n        all_taints, all_prompts, new_multishot = pickle.load(file)\n    all_prompts.append("Did not exit as expected, potentially.")\n    new_multishot = True\n    with open("multishot.pkl", "wb") as file:\n        pickle.dump([all_taints, all_prompts, new_multishot], file) '

    return appended_code
