import csv
import json
import re
import planning_language.mcpclient_spec as mcpclient_spec
import asyncio
import io
import agent_helpers.database as database
import ast
import demjson3
import sqlite3
import time
import run_full_query

QUERIES_DB = "queries_4.db"


class SafeDict(dict):
    def __getitem__(self, key):
        return self.get(key, None)


def parse_plaintext(full_plaintext: str, tool_names: dict, print_anything: bool):

    split_segments = full_plaintext.split("\n\n")

    instructions_csv = split_segments[0]

    all_lines = []
    with io.StringIO(instructions_csv) as file:
        reader = csv.reader(file)
        for one_line in reader:
            all_lines.append(one_line)
    output_dict = {}

    other_arguments = {}
    for segment in split_segments[1:]:

        segment_words = segment.split(" ")
        segment_number = int(segment_words[0])
        other_arguments[segment_number] = segment[len(segment_words[0]):].strip()

    
    for single_line in all_lines:
        if print_anything:
            print("single line:",single_line)

        instruction_elements = single_line

        #print(instruction_elements, single_line)

        try:
            instruction_number = int(instruction_elements[0])

        except Exception as e:
            if print_anything:
                print(f"Invalid instruction number: {instruction_elements[0]}")
            continue

        
        instruction_keyword = instruction_elements[1].strip()
        if instruction_keyword not in tool_names.keys():
            #print(f"Could not find instruction: {instruction_keyword}")
            #exit(1)
            pass

        output_dict[instruction_number] = {}
        output_dict[instruction_number]["instr"] = instruction_keyword
        output_dict[instruction_number]["arguments"] = other_arguments[instruction_number].replace("\n", "")
        if print_anything:
            print(output_dict[instruction_number]["arguments"]) 


        # handling control logic
        if instruction_keyword == "if":

            try:
                next_if_instruction_number = int(instruction_elements[2])
                next_not_if_instruction_number = int(instruction_elements[3])
            except Exception as e:
                print(f"Invalid next instruction number: {instruction_elements[2]} or {instruction_elements[3]}")
                #exit(1)
            output_dict[instruction_number]["next_if_true"] = next_if_instruction_number
            output_dict[instruction_number]["next_if_false"] = next_not_if_instruction_number
        
        else:
            # handling instructions
            if instruction_elements[2].strip() in ["str", "int", "float", "bool", "None", "dict"]:
                output_type = instruction_elements[2].strip()
            else:
                output_type = instruction_elements[2].strip()
                if print_anything:
                    print(f"Did not match type of: {instruction_elements[2]}")
                #exit(1)

            try:
                next_instruction_number = int(instruction_elements[3])

            except Exception as e:
                print(f"Invalid next instruction number: {instruction_elements[3]}, {instruction_elements}")
                #exit(1)

            output_dict[instruction_number]["type"] = output_type
            output_dict[instruction_number]["next"] = next_instruction_number


    return output_dict 



def resolve_references(raw_arg_string, output_dict, add_double_quotes=False, print_anything=True):
    """
    Scans a raw string for 'REF:#' and replaces it with the corresponding value from output_dict.
    Gemini function.
    """
    # The regex pattern looks for "REF:" followed by one or more digits (\d+)
    # The parentheses capture the digits so we can extract just the number.
    pattern = re.compile(r"REF:(\d+)")
    
    # This nested function dictates how to handle each match found by re.sub
    def replacer(match):
        # Extract the line number from the match group
        line_num = int(match.group(1)) 
        
        # Look up the value in your dictionary
        if line_num in output_dict:
            val = str(output_dict[line_num])
            if print_anything:
                print("VAL", val)

            if add_double_quotes:
                return f"\"{val}\""
            else:
                return val
        else:
            print(f"Warning: Output for line {line_num} not found in dictionary. Substituting 'None'.")
            return "None"

    # Execute the replacement on the entire raw string
    resolved_string = re.sub(pattern, replacer, raw_arg_string)
    
    return resolved_string


def resolve_references_obj(obj, output_dict, output_taints):
    """
    Recursively traverses a parsed Python object and replaces 'REF:#' placeholders.
    Returns: (resolved_object, list_of_taints)
    """
    exact_ref_pattern = re.compile(r"^REF:(\d+)$")
    embedded_ref_pattern = re.compile(r"REF:(\d+)")

    if isinstance(obj, dict):
        new_dict = {}
        dict_taints = []
        for k, v in obj.items():
            resolved_v, v_taints = resolve_references_obj(v, output_dict, output_taints)
            new_dict[k] = resolved_v
            dict_taints.extend(v_taints)
        return new_dict, dict_taints

    elif isinstance(obj, list):
        new_list = []
        list_taints = []
        for item in obj:
            resolved_item, item_taints = resolve_references_obj(item, output_dict, output_taints)
            new_list.append(resolved_item)
            list_taints.extend(item_taints)
        return new_list, list_taints

    elif isinstance(obj, str):
        # matching REF as full object
        exact_match = exact_ref_pattern.match(obj.strip())
        if exact_match:
            line_num = int(exact_match.group(1))
            my_taints = list(output_taints.get(line_num, []))
            
            if line_num in output_dict:
                val = output_dict[line_num]
                # Try decoding stringified JSON objects natively
                if isinstance(val, str):
                    val_stripped = val.strip()
                    if (val_stripped.startswith("{") and val_stripped.endswith("}")) or \
                       (val_stripped.startswith("[") and val_stripped.endswith("]")):
                        try:
                            decoded = demjson3.decode(val_stripped)
                            return decoded, my_taints
                        except Exception:
                            pass
                return val, my_taints
            else:
                print(f"Warning: Output for line {line_num} not found. Substituting None.")
                return None, my_taints

        # matching REF inside of string
        my_taints = []
        def replacer(match):
            line_num = int(match.group(1))
            val = output_dict.get(line_num, "None")
            my_taints.extend(output_taints.get(line_num, []))
            return str(val) if val is not None else "None"

        resolved_str = embedded_ref_pattern.sub(replacer, obj)
        return resolved_str, my_taints

    return obj, []


def convert_json(convert_string: str, output_dict: dict, output_taints: dict) -> tuple[SafeDict, list, dict]:
    """
    Parses string into a JSON dict and tracks data taints.
    Returns: (SafeDict_arguments, total_taints_list, taints_per_arg_dict)
    """
    cleaned_string = convert_string.strip().replace("\xa0", " ")
    cleaned_string = cleaned_string.replace(r"\'", "'")

    # Helper to format fallback outputs and distribute taints
    def build_result(resolved_val, taints):
        if isinstance(resolved_val, dict):
            # If the resolved value is a dict, assign the taints to all its keys
            t_per_arg = {k: list(taints) for k in resolved_val.keys()} if taints else {}
            return SafeDict(resolved_val), taints, t_per_arg
        else:
            # Fallback for primitive/list
            t_per_arg = {"prompt": list(taints)} if taints else {}
            return SafeDict({"prompt": resolved_val}), taints, t_per_arg

    # Look for standalone REF
    bare_ref_match = re.match(r'^\s*"?REF:(\d+)"?\s*$', cleaned_string)
    if bare_ref_match:
        line_num = int(bare_ref_match.group(1))
        val = output_dict.get(line_num)
        my_taints = list(output_taints.get(line_num, []))
        
        if isinstance(val, dict):
            return build_result(val, my_taints)
        if isinstance(val, str):
            val_stripped = val.strip()
            try:
                decoded = demjson3.decode(val_stripped)
                if isinstance(decoded, dict):
                    return build_result(decoded, my_taints)
            except Exception:
                pass
            return build_result(val, my_taints)
        if val is None:
            return SafeDict(), my_taints, {}

    pattern = re.compile(r'("(?:[^"\\]|\\.)*")|\bREF:(\d+)\b')
    def quote_bare_refs(match):
        if match.group(1):
            return match.group(1) 
        return f'"REF:{match.group(2)}"' 
    
    quote_normalized = pattern.sub(quote_bare_refs, cleaned_string)

    # Decode JSON 
    try:
        parsed_obj = demjson3.decode(quote_normalized)
    except Exception as e:
        print(f"JSON decode warning: {e}. Attempting fallback prompt extraction.")
        
        # Try resolving on the raw text
        resolved_text, text_taints = resolve_references_obj(cleaned_string, output_dict, output_taints)
        if isinstance(resolved_text, dict):
            return build_result(resolved_text, text_taints)
        if isinstance(resolved_text, str):
            try:
                decoded = demjson3.decode(resolved_text)
                if isinstance(decoded, dict):
                    return build_result(decoded, text_taints)
            except Exception:
                pass

        prompt_match = re.search(r'"prompt"\s*:\s*"(.*?)"\s*,\s*"output_type"', cleaned_string, re.DOTALL)
        raw_prompt = prompt_match.group(1) if prompt_match else cleaned_string
        resolved_prompt, prompt_taints = resolve_references_obj(raw_prompt, output_dict, output_taints)
        return build_result(resolved_prompt, prompt_taints)

    # Resolve keys to build taints_per_arg mapping
    if not isinstance(parsed_obj, dict):
        resolved_obj, obj_taints = resolve_references_obj(parsed_obj, output_dict, output_taints)
        return build_result(resolved_obj, obj_taints)

    final_dict = {}
    all_taints = []
    taints_per_arg = {}

    for k, v in parsed_obj.items():
        resolved_v, v_taints = resolve_references_obj(v, output_dict, output_taints)
        final_dict[k] = resolved_v
        
        if v_taints:
            all_taints.extend(v_taints)
            taints_per_arg[k] = v_taints

    return SafeDict(final_dict), all_taints, taints_per_arg


def convert_output(output, output_type):

    try:
        if output_type == "str":
            return str(output)
        if output_type == "int":
            return int(output)
        if output_type == "float":
            return float(output)
        if output_type == "bool":
            return bool(output)
        if output_type == "None":
            return None
        if output_type == "dict":
            if isinstance(output, str):
                try:
                    return SafeDict(json.loads(output))
                except:
                    try:
                        return SafeDict(demjson3.decode(output))
                    except:
                        pass
            elif isinstance(output, dict):
                return SafeDict(output)
            return output
        return output

    except Exception as e:
        pass
    try:
        return str(output)
    except Exception as e:
        pass
    return None

async def complete_instruction(tool_name, arguments, output_type, query_id, control_taints, data_taints, taints_per_arg, bypass, request_name="", print_anything=True):
    """Execute an instruction."""
    if print_anything:
        print("Complete instruction")
     
    split_tool_name = tool_name.split(":")
    if len(split_tool_name) != 2:
        print(f"Invalid tool name: {tool_name}")
        exit(1)

    server, tool = split_tool_name

    print_out = ""

    if tool == "multishot_call" or tool == "qllm_call":
        server = "llm_extension"
        arguments['prompt'] = str(arguments['prompt'])
    
    # --- Taint Determination Logic ---
    current_call_taints = list(control_taints) # Control taints always propagate
    annotations = {}
    
    if server not in ["database", "print"]:
        with open("all_servers.json", "r") as f:
            annotations = json.load(f)
            
        if server in annotations and tool in annotations[server]["tools"]:
            passthrough = annotations[server]["tools"][tool].get("argument_passthrough", {})
            all_disclosed = passthrough.get("all_disclosed") == "true"
            selected_args = passthrough.get("selected", [])
            
            # Only apply taints from arguments that pass through the tool
            for arg_name, taints in taints_per_arg.items():
                if all_disclosed or arg_name in selected_args:
                    for t in taints:
                        if t not in current_call_taints:
                            current_call_taints.append(t)
        else:
            # Fallback if tool isn't strictly annotated
            for t in data_taints:
                if t not in current_call_taints:
                    current_call_taints.append(t)
                    
    elif server == "database":
        # Add the 'key' argument as a taint if it exists
        db_key = arguments.get('key')
        if db_key and db_key not in current_call_taints:
            current_call_taints.append(db_key)
            
    if server == "print":
        for t in data_taints:
            if t not in current_call_taints:
                current_call_taints.append(t)

    # Clean duplicates

    current_call_taints = list(set(current_call_taints))
    if print_anything:
        print(f"Current taints for call {tool_name}: {current_call_taints}")
    all_taints_multishot, all_prompts, new_multishot = run_full_query.get_multishot_files()
    # --- Permission Check Logic ---
    permission_check_taints = list(set(control_taints + data_taints + all_taints_multishot))

    if server not in ["database", "print"] and permission_check_taints and server in annotations:
        tool_annotations = annotations[server]["tools"].get(tool, {})
        no_permissions_needed = tool_annotations.get("no_permissions_needed") == "true"
        
        if not no_permissions_needed:
            permission_type = ""
            extra_info = ""
            
            if annotations[server].get("tool_ambiguous") == "true":
                permission_type += "tool_ambiguous"
                
            if tool_annotations.get("custom_permissions") == "true":
                permission_type += "custom"
                custom_field = tool_annotations.get("custom_field")
                if custom_field and custom_field in arguments:
                    extra_info = arguments[custom_field]
            else:
                permission_type += "default"
                
            needs_permission = []

            # testing reset db
            #with open("track_no_reset_db.csv", "a") as file:
            #    file.write(f"{len(permission_check_taints)},{1},{tool=='multishot_call' or tool=='qllm_call'}\n")
            
            # Check previously granted/denied permissions
            for taint in permission_check_taints:
                status = database.check_for_permission(taint, server, tool, permission_type, extra_info)
                if status == 'denied':
                    print(f"Permission denied for taint {taint} on {tool_name}.")
                    return convert_output("error", output_type), False, print_out, current_call_taints                
                elif status == 'untested':
                    needs_permission.append(taint)
                    
            # Request all missing permissions dynamically
            if needs_permission:
                #with open("track_reuse_db.csv", "a") as file:
                #    file.write(f"{len(needs_permission)},{1},{tool=='multishot_call' or tool=='qllm_call'}\n")
                granted = database.request_multiple_permissions_from_user(
                    needs_permission, server, tool, permission_type, extra_info, bypass, request_name
                )
                if not granted:
                    if print_anything:
                        print(f"User denied requested permissions for {tool_name}.")
                    return convert_output(f"User denied requested permissions for {tool_name}.", str), False, print_out, current_call_taints   
                # ---------------------------------

    if server == "database":
        
        added_new = False
        if 'new' in arguments.keys():
            if arguments['new'] == 'yes':
                return convert_output(database.access_data(arguments['key'], new_value=True), output_type), False, print_out, current_call_taints
                added_new = True
        if added_new == False:
            return convert_output(database.access_data(arguments['key']), output_type), False, print_out, current_call_taints
    if server == "llm_extension" and tool == "multishot_call":
        return arguments['prompt'], True, print_out, current_call_taints
    if server == "print":
        print_out += arguments['text']
        print(f'\033[34mAgent:\033[0m\t')
        print(arguments['text'])
        return None, False, print_out, current_call_taints

    mcp_client = mcpclient_spec.MCPClient()
    try:
        # Agentdojo change
        current_path = database.access_path(f'{server}_path')
    except Exception as e:
        current_path = "error"
    try:
        if print_anything:
            print("Connecting to server")
        await mcp_client.connect_to_server(server, current_path)  
        if print_anything:
            print(f"Calling {tool_name}, with {arguments}")
        output = await mcp_client.process_query(tool, arguments, query_id)
        await mcp_client.cleanup()
    except Exception as e:
        if print_anything:
            print(e)
        output = "tool call failed"
    if print_anything:
        print("Raw output:", output)
    
    is_error = False
    if isinstance(output, dict) and output.get('isError'):
        is_error = True

    if is_error:
        full_output = None
    else:
        try:
            full_output = ""
            for output_item in output['content']:
                full_output += f"{output_item.text}, "
            full_output = full_output[:-2]
        except:
            full_output = None

    # AgentDojo
    # full_output = output[0]
            
    output_val = convert_output(full_output, output_type)
    
    if print_anything:
        print(full_output)
    return output_val, False, print_out, current_call_taints


def complete_if(arguments):
    """Execute an if statement, and return the truth value."""

    left_side = arguments['left']
    right_side = arguments['right']
    sign = arguments['sign']

    if sign == ">":
        return left_side > right_side
    if sign == "<":
        return left_side < right_side
    if sign == "=":
        return left_side == right_side
    if sign == "!=":
        return left_side != right_side
    print(f"Unknown sign: {sign}")
    return False


def validate_plan(instruction_dict):
    """Performs a quick validation check on instructions to identify invalid REFs."""
    all_instr_keys = set(instruction_dict.keys())
    pattern = re.compile(r"REF:(\d+)")
    for key, val in instruction_dict.items():
        arg_str = val.get("arguments", "")
        for match in pattern.finditer(arg_str):
            ref_num = int(match.group(1))
            if ref_num not in all_instr_keys:
                print(f"Warning: Instruction {key} references line {ref_num} which does not exist in the plan.")

def compute_control_dependencies(instruction_dict):
    """
    Statically maps every 'if' instruction to the list of instructions that are 
    control-dependent on it by computing the post-dominator tree.
    Returns: dict mapping if_instr_id -> list of dependent_instr_ids.
    """
    nodes = set(instruction_dict.keys())
    all_nodes = nodes.union({0}) # 0 is the terminal node
    succ = {n: [] for n in all_nodes}

    for n, data in instruction_dict.items():
        if data["instr"] == "if":
            succ[n].extend([data.get("next_if_true", 0), data.get("next_if_false", 0)])
        else:
            succ[n].append(data.get("next", 0))

    # Normalize reachability to Exit (0)
    rev_succ = {n: [] for n in all_nodes}
    for n, tgts in succ.items():
        for t in tgts:
            rev_succ[t].append(n)

    can_reach_exit = set()
    queue = [0]
    while queue:
        curr = queue.pop(0)
        if curr not in can_reach_exit:
            can_reach_exit.add(curr)
            queue.extend(rev_succ[curr])

    for n in nodes:
        if n not in can_reach_exit:
            succ[n].append(0)

    # Post-dominator calculation
    pdom = {n: set(all_nodes) for n in all_nodes}
    pdom[0] = {0}
    
    changed = True
    while changed:
        changed = False
        for n in nodes:
            intersect = set.intersection(*(pdom[s] for s in succ[n]))
            new_pdom = {n}.union(intersect)
            if new_pdom != pdom[n]:
                pdom[n] = new_pdom
                changed = True

    control_deps = {}
    for n, data in instruction_dict.items():
        if data["instr"] == "if":
            pdoms_of_target = pdom[n] - {n}
            ipd = 0
            for candidate in pdoms_of_target:
                is_ipd = True
                for other in pdoms_of_target:
                    if other != candidate and other not in pdom[candidate]:
                        is_ipd = False
                        break
                if is_ipd:
                    ipd = candidate
                    break

            visited = set()
            dep_nodes = set()
            queue = [t for t in succ[n]]

            while queue:
                curr = queue.pop(0)
                if curr == ipd or curr in visited:
                    continue
                visited.add(curr)
                if curr != 0:
                    dep_nodes.add(curr)
                    queue.extend(succ[curr])
            control_deps[n] = list(dep_nodes)

    return control_deps


def find_previous_disclosures(tool_name, tool_type, extra_information, server_for_line, annotations):
    """
    Find the taints that pertain to a certain tool request in the disclosure log.
    Filtered by argument passthrough rules so they only pass if authorized.
    """
    with sqlite3.connect(QUERIES_DB) as conn:
        cursor = conn.cursor()
        select_query = "SELECT taint, arg_names FROM disclosures WHERE principal_disclosed_to = ?"
        
        principal_disclosed_to = f"{server_for_line}"
        if "tool_ambiguous" not in tool_type:
            principal_disclosed_to += f":{tool_name}"
        if "custom" in tool_type:
            principal_disclosed_to += f":custom:{extra_information}"

        taints_disclosed = cursor.execute(select_query, (principal_disclosed_to,))
        taints_disclosed = taints_disclosed.fetchall()

    unique_taints = {}
    for single_taint in taints_disclosed:
        if single_taint[0] not in unique_taints.keys():
            unique_taints[single_taint[0]] = []
        for arg_name in single_taint[1].split(","):
            if arg_name and arg_name not in unique_taints[single_taint[0]]:
                unique_taints[single_taint[0]].append(arg_name)
        
    return_taints = []
    for single_taint, arg_names in unique_taints.items():
        if server_for_line in annotations:
            try:
                passthrough = annotations[server_for_line]['tools'][tool_name]['argument_passthrough']
                if passthrough.get('all_disclosed') == 'false':
                    annotations_for_tool = passthrough.get('selected', [])
                    annotations_for_tool.append('preset:control_logic')
                    
                    # Only pass through if it was previously disclosed on a permitted argument
                    if any(arg in annotations_for_tool for arg in arg_names):
                        return_taints.append(single_taint)
                else:
                    return_taints.append(single_taint)
            except KeyError:
                return_taints.append(single_taint)
        else:
            return_taints.append(single_taint)

    return return_taints


def filter_taints_for_passthrough(taints_per_arg_dict, server_name, tool_name, annotations):
    """
    Filters current argument taints based on all_servers.json argument_passthrough rules.
    This prevents overpainting output with taints from arguments that don't pass through.
    """
    passthrough = annotations.get(server_name, {}).get("tools", {}).get(tool_name, {}).get("argument_passthrough", {})
    all_disclosed = passthrough.get("all_disclosed", "false")
    selected_args = passthrough.get("selected", [])
    
    output_taints_set = set()
    
    for taint, arg_names in taints_per_arg_dict.items():
        if all_disclosed == "true":
            output_taints_set.add(taint)
        else:
            # If the taint is tied to ANY argument in the 'selected' list, it survives
            if any(arg in selected_args for arg in arg_names):
                output_taints_set.add(taint)
                
    return list(output_taints_set)





def run_script(instruction_dict, current_query_id, max_instructions=200, bypass='no', request_name='', print_anything=True):

    validate_plan(instruction_dict)
    registers = {}
    multishot_text = ""
    
    # Pre-compute control dependencies once statically
    control_deps = compute_control_dependencies(instruction_dict)

    # taint tracking
    output_taints = {} # dict of lists of the taints existing in the outputs of lines
    control_taints = {k: [] for k in instruction_dict.keys()} # dict of lists of the taints that must be allowed for a instruction to execute

    with open("all_servers.json", "r") as file:
        annotations = json.load(file)

    continuing = True
    next_instr = 1
    total_executed = 0
    total_print = ""

    while continuing:
        
        # read instruction
        current_instruction = instruction_dict[next_instr]
        arguments, current_output_taints, taints_per_arg = convert_json(current_instruction['arguments'], registers, output_taints)
        instr_type = current_instruction['instr']

        # Temporarily assign input taints (vital for 'if' statements)
        output_taints[next_instr] = current_output_taints
        
        # if branch
        if instr_type == "if":
            try:
                result_if = complete_if(arguments)
            except Exception as e:
                result_if = True
            registers[next_instr] = result_if
            if print_anything:
                print(f"Decided if: {result_if}")
            
            # Apply condition taints to all dependent instructions
            if current_output_taints:
                for dep_instr in control_deps.get(next_instr, []):
                    for t in current_output_taints:
                        if t not in control_taints[dep_instr]:
                            control_taints[dep_instr].append(t)

            if result_if:
                next_instr = current_instruction["next_if_true"]
            else:
                next_instr = current_instruction["next_if_false"]
        
        # otherwise execute tool
        else:
            server_name, tool_name = instr_type.split(":") if ":" in instr_type else (instr_type, "")
            
            # Prepare contextual variables for logging and DB tracking
            tool_type_str = ""
            extra_info = ""
            
            if server_name in annotations and tool_name in annotations[server_name].get("tools", {}):
                tool_ann = annotations[server_name]["tools"][tool_name]
                if annotations[server_name].get("tool_ambiguous") == "true":
                    tool_type_str += "tool_ambiguous "
                if tool_ann.get("custom_permissions") == "true":
                    tool_type_str += "custom "
                    custom_field = tool_ann.get("custom_field")
                    if custom_field and custom_field in arguments:
                        extra_info = arguments[custom_field]
                        
            principal_disclosed_to = f"{server_name}"
            if "tool_ambiguous" not in tool_type_str:
                principal_disclosed_to += f":{tool_name}"
            if "custom" in tool_type_str:
                principal_disclosed_to += f":custom:{extra_info}"

            # Transform taints_per_arg from {arg_name: [taints]} -> {taint: [arg_names]} for database formatting
            taints_to_args = {}
            for arg_name, taints in taints_per_arg.items():
                for t in taints:
                    if t not in taints_to_args:
                        taints_to_args[t] = []
                    taints_to_args[t].append(arg_name)

            # Complete Instruction and check for permissions
            if print_anything:
                print("calling instr")
            
            instr_output, multishot_yes, print_current, taints_added = asyncio.run(complete_instruction(
                instr_type, arguments, current_instruction['type'], 
                current_query_id, control_taints[next_instr], 
                current_output_taints, taints_per_arg, bypass, request_name, print_anything
            ))

            # Check for Denial and Log to Database ONLY if Authorized
            output_str = str(instr_output)
            is_denied = output_str == "error" or "User denied requested permissions" in output_str

            if not is_denied:
                with sqlite3.connect(QUERIES_DB) as conn:
                    cursor = conn.cursor()
                    
                    # Insert request with the final result (combines previous Step 2 and Step 4)
                    cursor.execute(
                        """
                        INSERT INTO requests 
                        (query_id, request_server, request_tool, request_params, request_result) 
                        VALUES (?, ?, ?, ?, ?)
                        """, 
                        (current_query_id, server_name, tool_name, str(arguments), output_str)
                    )
                    request_id = cursor.lastrowid
                    
                    current_time = int(time.time())
                    
                    # Insert fully populated disclosures linked to the request_id
                    for taint, arg_names in taints_to_args.items():
                        cursor.execute(
                            """
                            INSERT INTO disclosures 
                            (request_id, taint, principal_disclosed_to, time, params, arg_names) 
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (request_id, taint, principal_disclosed_to, current_time, str(arguments), ",".join(arg_names))
                        )

            
            # Append Previous Disclosures to Output Taints
            prev_taints = find_previous_disclosures(tool_name, tool_type_str, extra_info, server_name, annotations)
            for pt in prev_taints:
                if pt not in taints_added:
                    taints_added.append(pt)
                    
            # Apply New Source Annotations
            tool_annotations = annotations.get(server_name, {}).get("tools", {}).get(tool_name, {})
            if tool_annotations.get("new_source") == "true":
                source_header = tool_annotations.get("source_header", "unknown_source")
                
                custom_field = tool_annotations.get("custom_field")
                if custom_field and custom_field in arguments:
                    custom_value = arguments[custom_field]
                else:
                    custom_value = "undefined"
                    
                new_taint = f"{source_header}:{custom_value}"
                
                if new_taint not in taints_added:
                    taints_added.append(new_taint)

            output_taints[next_instr] = taints_added
            
            total_executed += 1
            total_print += print_current
            registers[next_instr] = instr_output
            next_instr = current_instruction["next"]
        
        if next_instr == 0:
            continuing = False
        # if mulitshot, end loop
        if multishot_yes:
            continuing = False
            multishot_text = instr_output
        if total_executed > max_instructions:
            continuing = False

    if print_anything:
        print("MULTISHOT", multishot_text, total_print, output_taints)

    # Mark all llm_extension disclosures as old so they don't need permissions in future plans. We only expect they pass through in the immediate plan.
    with sqlite3.connect(QUERIES_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE disclosures
            SET principal_disclosed_to = REPLACE(principal_disclosed_to, 'llm_extension', 'llm_extensionold')
            WHERE principal_disclosed_to LIKE 'llm_extension%'
            """
        )

    return multishot_text, total_print, output_taints
#test_str = '1,email:send_email,"{""address"":""123"", ""content"":""3""}",str,2,\n2,database:access_data,"{""key"":""name""}",int,3,\n3,if,"{""left"":REF:1, ""sign"":""!="", ""right"":""hi""}",4,3,\n4,email:send_email,"{""address"":""123"", ""content"":""REF:1""}",str,5,\n5,python_exec:python_run,"{""code"":""def multiply(input_item: list):\\n    return input_item[0]*input_item[1]"", ""func_name"":""multiply"",""input_val"":[4,5]}",int,0,'

#with open("instructions.csv", "r") as file:
#    test_str = file.read()

#instruction_dict = parse_plaintext(test_str, {'email:send_email':'hi', 'database:access_data':'hii', 'if':'hiii', 'python_exec:python_run':"hiii"})

#print(instruction_dict)

#print(convert_json(instruction_dict[3]['arguments'], {1:45}))

#run_script(instruction_dict)
