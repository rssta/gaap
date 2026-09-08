
import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import sqlite3
import json
import os
import pickle
import database
import time

# constants
QUERIES_DB = "queries_4.db"
TAINTS_PKL = "taints.pkl"
DB_ADD_PKL = "database_additions.pkl"


# taken from MCP specification
class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.server_name = None

    async def connect_to_server(self, server_name: str, path: str):
        """Connect to an MCP server
        
        Args:
            path: Path to the server script (.py or .js)
        """
        with open("all_servers.json", "r") as file:
            annotations = json.load(file)
        if server_name not in annotations.keys():
            print(f"Error: trying to initialize a server {server_name} that is not in all_servers.json.")
            exit(1)
        self.server_name = server_name
        # print("start connect")
        is_python = path.endswith('.py')
        # is_js = server_script_path.endswith('.js')
        # if not (is_python or is_js):
        #     raise ValueError("Server script must be a .py or .js file")
        #print(path)            
        arriving_path = os.environ['ARRIVING_PATH']
        if is_python:
            command = "python3"
            server_params = StdioServerParameters(
                command=command,
                args=[arriving_path + path],
                env=None
            )
            #print("did it get here in the mcp client server setup")
        else:
             command = "npx"
             server_params = StdioServerParameters(
                command=command,
                args=["-y", "@modelcontextprotocol/server-filesystem", arriving_path + "editable_files/"],
                env=None
            )

        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        #print("got past the stdio transport")
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        #print("got past the self session")
        
        await self.session.initialize()
        #print("got past initialization")
        
        # List available tools
        #response = await self.session.list_tools()
        #tools = response.tools
        #print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    async def list_available_tools(self):
        response = await self.session.list_tools()
        tools = response.tools
        return tools

    def find_previous_disclosures(self, tool_name, tool_type, extra_information, server_for_line):
        """
        Find the taints that pertain to a certain tool request in the disclosure log.
        """
        #print("Checking disclosures for", tool_name)
        with sqlite3.connect(QUERIES_DB) as conn:
            cursor = conn.cursor()

            select_query = "SELECT taint, arg_names FROM disclosures WHERE principal_disclosed_to = ?"
            
            principal_disclosed_to = f"{server_for_line}"
            if "tool_ambiguous" not in tool_type:
                principal_disclosed_to += f":{tool_name}"
            if "custom" in tool_type:
                principal_disclosed_to += f":custom:{extra_information}"
            #print(principal_disclosed_to)
            taints_disclosed = cursor.execute(select_query, (principal_disclosed_to,))
            taints_disclosed = taints_disclosed.fetchall()
            #print("taints disclosed", taints_disclosed)

        unique_taints = {}
        for single_taint in taints_disclosed:
            if single_taint[0] not in unique_taints.keys():
                unique_taints[single_taint[0]] = []
            for arg_name in single_taint[1].split(","):
                if arg_name not in unique_taints[single_taint[0]]:
         #           print("append start")
                    unique_taints[single_taint[0]].append(arg_name)
          #          print("append end")
            
        with open("all_servers.json", "r") as file:
            annotations = json.load(file)

        #print(unique_taints)#, annotations) 
        return_taints = []
        for single_taint in unique_taints.keys():
            if server_for_line in annotations.keys():
                # print("server annotations", annotations[server_for_line])
                # all tools for a server must be annotated, otherwise errors
                if annotations[server_for_line]['tools'][tool_name]['argument_passthrough']['all_disclosed'] == 'false':
                    annotations_for_tool = annotations[server_for_line]['tools'][tool_name]['argument_passthrough']['selected']
                    annotations_for_tool.append('preset:control_logic')
                    for single_arg in unique_taints[single_taint]:
                        # print("going through", single_arg)
                        if single_arg in annotations_for_tool:
                            return_taints.append(single_taint)
           #                 print("added")
                else:
                    return_taints.append(single_taint)
            else:
                return_taints.append(single_taint)

        #print('return taints', return_taints)
        return return_taints



    def modify_taints(self, current_taints, chains, current_line_num, lines_reached, tools_per_line, args_taints, args_list, annotations):
        """
        Modify the current taint list based on a couple things:
        1. adding the inherent taints implied by tools, meaning all private information they have ever seen. 
        2. removing the taints for branches that did not get reached, based on broken chains. 
        """
        #print("args taints", args_taints)
        #print(chains)
        #print("current taints", current_taints)
        if current_line_num in chains.keys():
            current_call_chains = chains[current_line_num]
        else:
            current_call_chains = {}
        new_taints = []
        for single_taint in current_taints:
        
            # first, we check the validity that the taint actually made it to the call
            if single_taint in current_call_chains.keys():
                #print("Taint in chains") 
                # if there is any complete chain, we readd it
                for single_chain in []: # TODO temporary bypass  current_call_chains[single_taint]:
                    no_break = True
                    for chain_element in single_chain:
                        if chain_element not in lines_reached:
                            no_break = False
                    if no_break:
                        new_taints.append(single_taint)
                        break
    #                print("above 1", single_chain)
                    if len(single_chain) == 1:
                        #print("below 1")
                        if single_chain[0] == '0':
                            new_taints.append(single_taint)
                            break

                new_taints.append(single_taint)
            else:
                #print("Taint not in chains")
                # if we have no chains, we just assume it was directly used and readd
                new_taints.append(single_taint)

        return_taints = []
        return_taint_arg_matches = {}

        # remove the process_query taints and replace them with the taints of the tools they represent
        #print(new_taints)
        for single_taint in new_taints:
            #print(args_taints[current_line_num])
            if "process_query" in single_taint:
                #print("PROCESS QUERY", new_taints, current_call_chains) 
                for single_pq_key in current_call_chains.keys():
                    #print("current_call_chains", current_call_chains, single_taint, tools_per_line)                    
                    #print("SINGLE PQ")
                     
                    #print(single_pq_key, tools_per_line)
                    if single_pq_key-1 in tools_per_line.keys() and single_pq_key-1 != current_line_num:
                        query_line = single_pq_key-1 #int(single_pq_key[len("process_query"):])
                        tool_for_line, permissions_type, permissions_extra_information, server_for_line = tools_per_line[query_line]
#                        print("GETTING PERMISSIONS", query_line, tools_per_line)
                    
                        #permissions = database.get_all_permissions_held_by_tool(tool_for_line, permissions_type, permissions_extra_information)       
                        #print(permissions, tool_for_line)
           #             print("finding disclosures")
                        permissions = self.find_previous_disclosures(tool_for_line, permissions_type, permissions_extra_information, server_for_line)
                        
                    #print(permissions)
                        #print("server for line", server_for_line)
                        if "new_source" in annotations[server_for_line]['tools'][tool_for_line].keys():
                            if annotations[server_for_line]['tools'][tool_for_line]['new_source'] == 'true':
                                if "custom" in permissions_type:
                                    permissions.append(f"{annotations[server_for_line]['tools'][tool_for_line]['source_header']}:{permissions_extra_information}")
                                else:
                                    permissions.append(f"{annotations[server_for_line]['tools'][tool_for_line]['source_header']}:undefined")
                        #if server_for_line == "filesystem":
                        #    permissions.append(f"file:{permissions_extra_information}")
                        for permission in permissions:
                            #print(permission)
                            for argument in args_taints[current_line_num].keys():
                                    #print(argument)
                                    if permission not in return_taint_arg_matches.keys():
                                        return_taint_arg_matches[permission] = []
                                        #print("here1")
          #                          print(args_taints)
                                    if "process_query" in args_taints[current_line_num][argument]:              
         #                               print("inside", permission)
                                        if argument == 0: # if control flow led to this call
                                            return_taint_arg_matches[permission].append("preset:control_logic")
                                        else:
                                            # ensure we get the argument name, which will be zero indexed 
                                            if argument % 2 == 0:
                                                arg_name_index = argument-2
                                            else:
                                                arg_name_index = argument-1
                                            #print("here2")
                                            return_taint_arg_matches[permission].append(args_list[arg_name_index])
        #                                print(new_taints)
                                        if permission not in return_taints:
                                            #print("here3")
                                            return_taints.append(permission)# = [permissions[permission]]
            elif "new_value_" in single_taint:
                with open(DB_ADD_PKL, 'rb') as file:
                    new_keys = pickle.load(file)
                    new_key_taint = new_keys[int(single_taint[10:])]
                    if new_key_taint != None:
                        for argument in args_taints[current_line_num].keys():
                            if new_key_taint not in return_taint_arg_matches.keys():
                                return_taint_arg_matches[new_key_taint] = []
                            if new_key_taint in args_taints[current_line_num][argument]:
                                if argument == 0: # if control flow led to this call
                                    return_taint_arg_matches[new_key_taint].append("preset:control_logic")
                                else:
                                    # ensure we get the argument name, which will be zero indexed
                                    if argument % 2 == 0:
                                        arg_name_index = argument-2
                                    else:
                                        arg_name_index = argument-1
                 #                   print("Adding", args_list, arg_name_index)
                                    return_taint_arg_matches[new_key_taint].append(args_list[arg_name_index])
                            return_taints.append(new_key_taint)
            else: 
                #print(single_taint, args_taints[current_line_num])
                for argument in args_taints[current_line_num].keys():
                    if single_taint not in return_taint_arg_matches.keys():
                        return_taint_arg_matches[single_taint] = []
                 #   print(single_taint, args_taints[current_line_num][argument])
                    if single_taint in args_taints[current_line_num][argument]:
                        if argument == 0: # if control flow led to this call
                            return_taint_arg_matches[single_taint].append("preset:control_logic")
                        else:
                            # ensure we get the argument name, which will be zero indexed
                            if argument % 2 == 0:
                                arg_name_index = argument-2
                            else:
                                arg_name_index = argument-1
                            #print("adding", argument, args_list[arg_name_index])
                            return_taint_arg_matches[single_taint].append(args_list[arg_name_index])
                    return_taints.append(single_taint)

       # print(return_taint_arg_matches) 
       # print("return taints", return_taints)
        return return_taints, return_taint_arg_matches


    async def process_query(self, current_line_num: int, tool: str, current_id: int, arg1 = None, arg2 = None, arg3 = None, arg4 = None, arg5 = None, arg6 = None, arg7 = None, arg8 = None, arg9 = None, arg10 = None, arg11 = None, arg12 = None, arg13 = None, arg14 = None, arg15 = None, arg16 = None, arg17 = None, arg18 = None, arg19 = None, arg20 = None, arg21 = None, arg22 = None, arg23 = None, arg24 = None, arg25 = None, arg26 = None, arg27 = None, arg28 = None, arg29 = None, arg30 = None) -> str:
         
        args_list = [arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, arg10, arg11, arg12, arg13, arg14, arg15, arg16, arg17, arg18, arg19, arg20, arg21, arg22, arg23, arg24, arg25, arg26, arg27, arg28, arg29, arg30]
        # create a dictionary of argument
        args = {}
        key_ready = None
        for argument in args_list:
            if argument != None:
                if key_ready != None:
                    args[key_ready] = argument
                    key_ready = None
                else:
                    key_ready = argument

        #annotated_call(taint)
        with open(TAINTS_PKL, 'rb') as file:
            taints, chains, lines_reached, tools_per_line, use_taints, bypass_requests, arg_taints, request_name = pickle.load(file)
        
        with open("all_servers.json", "r") as file:
            annotations = json.load(file)

        current_server_annotations = annotations[self.server_name]
        if tool not in current_server_annotations["tools"].keys():
            print(f"Error: Inside of server {self.server_name}, trying to use tool {tool} which does not exist in all_servers.json.")
            exit(1)

        tool_type = ""
        extra_info = ""
        if current_server_annotations["tool_ambiguous"] == "true":
            tool_type += "tool_ambiguous"
        if current_server_annotations["tools"][tool]["custom_permissions"] == "true":
            tool_type += "custom"
            extra_information_arg_name = current_server_annotations["tools"][tool]["custom_field"]
            extra_info = args[extra_information_arg_name]
        else:
            tool_type += "default"
        
        #print(self.server_name, tool, tool_type, extra_info)
#        if tool == "send_email":
#            tool_type = "custom"
#            extra_info = args['address']
#        elif tool == "qllm_call":
#            tool_type = "custom"
#            extra_info = args['call_name']
#        elif self.server_name == "filesystem": 
#            tool_type = "custom tool_ambiguous"
#            extra_info = args['path']
#        else:
#            tool_type = 'default'
#            extra_info = ''
#
        #print("PROCESS_QUERY")
        #print(self.server_name, tool)
        if use_taints:
        
            #print(taints, current_line_num)
            current_taints = taints[current_line_num]
            tools_per_line[current_line_num] = [tool, tool_type, extra_info, self.server_name]
            
            with open(TAINTS_PKL, 'wb') as file:
                pickle.dump([taints, chains, lines_reached, tools_per_line, use_taints, bypass_requests, arg_taints, request_name], file)

            #print(current_taints, chains[current_line_num], lines_reached, tools_per_line)
            current_taints, taint_arg_matches = self.modify_taints(current_taints, chains, current_line_num, lines_reached, tools_per_line, arg_taints, args_list, annotations)
            #print(current_taints)
            #print('passed modify taints')
            with open("multishot.pkl", "rb") as file:
                # [[all_taints], [prompts], new_multishot]
                all_taints, all_prompts, new_multishot = pickle.load(file)
                #print(all_taints, current_taints)
                #print("MULTISHOT_TAINTS", all_taints, current_taints)
                current_taints.extend(all_taints)
            all_need_testing = [] # the keys that get  response of 'untested' when checking for permission
            #print(self.server_name) 
            no_permission_needed = False
            if "no_permissions_needed" in annotations[self.server_name]['tools'][tool].keys():
                if annotations[self.server_name]['tools'][tool]['no_permissions_needed'] == 'true':
                    no_permission_needed = True
            if not no_permission_needed:
                #print("checking taints")
                #print(current_taints)
                for tainted_key in current_taints:
                    #print("tainted_key", tainted_key) 
                    permission = database.check_for_permission(tainted_key, self.server_name, tool, tool_type, extra_info)    
                    #print("found new permission", permission)
                    if permission == 'denied':
                        print(f"Error: Code tried to execute tool {tool} with private information {tainted_key}, and permission for this was denied previously.")
                        exit(1)
                    #print("permission", permission, permission=='untested')
                    if permission == 'untested':
                        #print("appending", all_need_testing, tainted_key)
                        all_need_testing.append(tainted_key)
                    #print("not matched")
                if len(all_need_testing) > 0:
                    #print("calling")
                    multiple_request_result = database.request_multiple_permissions_from_user(all_need_testing, self.server_name, tool, tool_type, extra_info, bypass_requests, request_name)
                    #print("got results")
                    if multiple_request_result == False:
                        print(f"\033[32m  GAAP:\033[0m\tCode tried to execute tool {tool} with private information, and was declined by user.")
                        exit(1)
        else:
            current_taints = []

        #print("got permissions")
        try:
            json.dumps(args)
        except TypeError:
            print(f"Error: Arguments passed into execute tool {tool} were not json serializable. Args were of type {type(args)} and looked like: {args} \n")
            exit(1)
        

        with sqlite3.connect(QUERIES_DB) as conn:
            cursor = conn.cursor()
            insert_query = "INSERT INTO requests (query_id, request_server, request_tool, request_params) VALUES (?, ?, ?, ?)"
            cursor.execute(insert_query, (current_id, self.server_name, tool, json.dumps(args),))
            #print("first exec")     
            taints_query = "INSERT INTO disclosures (request_id, taint, principal_disclosed_to, time, params, arg_names) VALUES (?, ?, ?, ?, ?, ?)"
            get_last_request_id = "SELECT request_id FROM requests WHERE request_id = last_insert_rowid()"
            last_row_data = cursor.execute(get_last_request_id, ())
            last_request_id = last_row_data.fetchall()[0][0]
            #print("second exec")
            principle_disclosed_to = f"{self.server_name}"
            if "tool_ambiguous" not in tool_type:
                principle_disclosed_to += f":{tool}"
            if "custom" in tool_type:
                principle_disclosed_to += f":custom:{extra_info}"
                
            for single_taint in current_taints:
                all_args = ""    
                if single_taint not in taint_arg_matches:
                    all_args += f"preset:control_logic,"
                else:
                    for one_arg in taint_arg_matches[single_taint]:
                        all_args += f"{one_arg},"
                if len(all_args) > 0:
                    if all_args[-1] == ",":
                        all_args = all_args[:-1]
                #print("third exec", last_request_id, single_taint, principle_disclosed_to)
                cursor.execute(taints_query, (last_request_id, single_taint, principle_disclosed_to, time.time(), json.dumps(args), all_args,)) 
                #print("exec done")
        #print("checking multishot", self.server_name, tool)  
        if self.server_name == "llm_extension" and tool == "multishot_call":
            # We are doing multishot, so we end this script execution
            with open("multishot.pkl", "rb") as file:
                # [[all_taints], [prompts], new_multishot]
                all_taints, all_prompts, new_multishot = pickle.load(file)
            for single_taint_multishot in current_taints:
                if single_taint_multishot not in all_taints:
                    all_taints.append(single_taint_multishot)
            if 'prompt' in args.keys():
                all_prompts.append(args['prompt'])
            else:
                all_prompts.append("Attempt multishot with no prompt.i")
            #print(all_taints)
            new_multishot = True
            with open("multishot.pkl", "wb") as file:
               pickle.dump([all_taints, all_prompts, new_multishot], file) 
            await self.exit_stack.aclose()
            exit(0)
    
        #print(tool, args)
        
        result = await self.session.call_tool(tool, args)
        result = dict(result)

        with open("counting_metrics.pkl", "rb") as file:
            user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)

        mcp_calls += 1

        with open("counting_metrics.pkl", "wb") as file:
            pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file)

        with sqlite3.connect(QUERIES_DB) as conn:
            cursor = conn.cursor()
            new_id = cursor.lastrowid
            insert_query = "UPDATE requests SET request_result = ? WHERE request_id = ?"
            cursor.execute(insert_query, (str(result), new_id,))
        
        return result
    
    async def cleanup(self):
        """Clean up resources"""
    
        await self.exit_stack.aclose()


def annotated_call(line_number: int):
    """
    Add an annotation to the pkl file that a certain line number has been reached. 
    TODO: consider, should this be moved to another file? It doesn't quite fit here.
    """
    
    with open(TAINTS_PKL, 'rb') as file:
        taints, chains, lines_reached, tools_per_line, use_taints, bypass_requests, arg_taints, request = pickle.load(file)

    lines_reached.append(line_number)

    with open(TAINTS_PKL, "wb") as file: 
        pickle.dump([taints, chains, lines_reached, tools_per_line, use_taints, bypass_requests, arg_taints, request], file)


