
import operation_helpers.helper_text as helper_text
import os
import subprocess
import json
import operation_helpers.helper_text as helper_text

# NOTE: This file is used in the old Python based version of GAAP. See planning_language directory for the new version.

NUM_ARGS = 14

def apply_taints_by_lines_multi_key(new_taints: list, lines_with_calls: list, private_keys: list, generated_lines: list):
    """
    Set correct key taints into lines with calls based on the new taints.
    """

    lines_arguments = {}

    #print(new_taints)
    for taint in new_taints:

        taint_line = taint['line']-1
        taint_code = taint['code']
        #print("Taint line:", taint_line)
        # if we have a process query case, where we are passing private data to process query
        if taint_code // 100000 == 1:

            line_to_analyze = taint_line
            if line_to_analyze % 2 == 0:
                line_to_analyze += 1
            if line_to_analyze in lines_with_calls:
                lines_with_calls[line_to_analyze].append(private_keys[taint_code % 100000])
            else:
                print(f"Error: Call to process_query at line {taint_line} not found in: {lines_with_calls}")
                exit(1)

        # if we have a control flow case, where we are using private data to influence control flow
        elif taint_code // 100000 == 2:
            #print(taint_code, taint_line) 
            possible_control_flow = ["if", "while", "for", "elif"]
            focus_line = generated_lines[taint_line]

            if any(sub in focus_line for sub in possible_control_flow):
                
                # find indent of the control flow line, with ending value +1 to account for lines being 1 indexed
                num_spaces = 0
                while(focus_line[num_spaces] == " "):
                    num_spaces += 1
                #print("looking at control flow")
                iter_line = taint_line+2
                #print(generated_lines[iter_line], generated_lines[iter_line][:num_spaces+1] ==  focus_line[:num_spaces]+" ", len(generated_lines[iter_line][:num_spaces+1]), len(focus_line[:num_spaces]+" "))
                while(generated_lines[iter_line][:num_spaces+1] == focus_line[:num_spaces]+" " \
                      or generated_lines[iter_line][:num_spaces+5] == focus_line[:num_spaces]+"else:" \
                      or generated_lines[iter_line][:num_spaces+5] == focus_line[:num_spaces]+"else " \
                            or generated_lines[iter_line][:num_spaces+5] == focus_line[:num_spaces]+"elif "):
                    #print("made it")
                    if "process_query" in generated_lines[iter_line]:
                        #print("found control flow pq")
                        lines_with_calls[iter_line+1].append(private_keys[taint_code % 100000])
                        if not iter_line+1 in lines_arguments.keys():
                            lines_arguments[iter_line+1] = {}
                        
                        if not 0 in lines_arguments[iter_line+1].keys():
                            lines_arguments[iter_line+1][0] = [private_keys[taint_code % 100000]]
                        else:
                            lines_arguments[iter_line+1][0].append(lines_arguments[iter_line+1][0])
                    iter_line += 2
                
            else:
                print(f"Error: Could not determine the control flow in line: {focus_line}")
                exit(1)
        
        # if we have a flow from a previous process_query call
        elif taint_code // 100000 == 3:
            #print(lines_with_calls)

            line_to_analyze = taint_line
            if line_to_analyze % 2 == 0:
                line_to_analyze += 1
            if "process_query" not in lines_with_calls[line_to_analyze]:

                lines_with_calls[line_to_analyze].append("process_query")
        # if we have an indication of tainted args
        elif taint_code // 100000 == 4:
            
            arg_num = (taint_code // 1000) - 400
            key_code = taint_code % 1000
            if key_code == 999:
                private_key_in_question = "process_query"
            else:
                private_key_in_question = private_keys[taint_code % 1000]
            iter_line = taint_line

            if not iter_line+1 in lines_arguments.keys():
                lines_arguments[iter_line+1] = {}

            if not arg_num in lines_arguments[iter_line+1].keys():
                lines_arguments[iter_line+1][arg_num] = []

            lines_arguments[iter_line+1][arg_num].append(private_key_in_question)

        else:
            print(f"Error: Unknown taint code {taint_code} returned.")
            exit(1)
    
    #print(lines_arguments)
    return lines_with_calls, lines_arguments




def apply_taints_by_lines(new_taints: list, lines_with_calls: list, current_key: str, generated_lines: list):
    """
    Set correct key taints into lines with calls based on the new taints.
    """
    
    for taint in new_taints:
         
        taint_line = taint['line']-1
        taint_code = taint['code']

        # if we have a process query case, where we are passing private data to process query
        if taint_code == 100:

            if taint_line+1 in lines_with_calls:
                lines_with_calls[taint_line+1].append(current_key)
            else:
                print(f"Error: Call to process_query at line {taint_line} not found.")
                exit(1)

        # if we have a control flow case, where we are using private data to influence control flow
        elif taint_code == 200:
        
            possible_control_flow = ["if", "while", "for", "elif"]
            focus_line = generated_lines[taint_line]

            if any(sub in focus_line for sub in possible_control_flow):
                
                # find indent of the control flow line, with ending value +1 to account for lines being 1 indexed
                num_spaces = 0
                while(focus_line[num_spaces] == " "):
                    num_spaces += 1

                iter_line = taint_line
                while(generated_lines[iter_line][:num_spaces+1] == focus_line[:num_spaces]+" " \
                      or generated_lines[iter_line][:num_spaces+1] == focus_line[:num_spaces]+"else:" \
                        or generated_lines[iter_line][:num_spaces+1] == focus_line[:num_spaces]+"else " \
                            or generated_lines[iter_line][:num_spaces+1] == focus_line[:num_spaces]+"elif "):

                    if "process_query(" in generated_lines[iter_line]:
                        lines_with_calls[iter_line+1].append(current_key)

                
            else:
                print(f"Error: Could not determine the control flow in line: {focus_line}")
                exit(1)

        else:
            print(f"Error: Unknown taint code {taint_code} returned.")
            exit(1)
             
    return lines_with_calls

    
def modify_generated_script(generated_lines: list):
    """
    Add line numbers to calls of "process_query".
    """

    new_lines = []
    for line in generated_lines:
        new_lines.append(line)
        new_lines.append("\n")
    return_lines = []
    for index, line in enumerate(new_lines): 
        line_before_comment = line.split("#")[0]
        line_after_comment = line[len(line_before_comment):]
        if "process_query(" in line_before_comment:
            index_placement = line_before_comment.find("process_query")
            if index_placement != -1:
                index_placement = index_placement + 14
                new_line = line_before_comment[:index_placement] + f"{index+1}," + line_before_comment[index_placement:] + line_after_comment
                #print(new_line)
            else:
                print("Error: process_query( not found, must modify handling.", line)
                exit(1)
        else:
            new_line = line
        return_lines.append(new_line)
    
    return return_lines


def extract_revealed_traces(stderr_output: str):
    """
    Take the raw reveal_output stderr and parse out the individual traces from the final set of outputs in the stderr.
    """
    #print(stderr_output)
    stderr_lines = stderr_output.splitlines()

    trimmed_lines = []
    # remove first couple characters and whitespace from lines
    for line in stderr_lines:
        trimmed_lines.append(line[1:].strip())

    reveal_starting_lines_indices = []
    # find lines where generated_script starts the line
    for index, line in enumerate(trimmed_lines):
        if line[:len("generated_script")] == "generated_script":
            reveal_starting_lines_indices.append(index)

    last_instance_reveal_starting_lines_indices = []
    discovered_lines = []
    stderr_indices_to_discovered = {}
    # find the last instance of each line, because lines get repeated
    for index in reveal_starting_lines_indices[::-1]:
        
        current_analyze_line = trimmed_lines[index]
        current_segments = current_analyze_line.split(":")
        gs_line_num = int(current_segments[1])

        if gs_line_num not in discovered_lines:
            last_instance_reveal_starting_lines_indices.append(index)
            discovered_lines.append(gs_line_num)
            stderr_indices_to_discovered[index] = gs_line_num

    last_instance_reveal_starting_lines_indices.reverse()

    origins_with_tito_lines = {}  # dict where keys are the the gs line numbers, 
    # and containts another dict where keys are origin gs line numbers and containts tito values per origin.
    
    # find the origins, of which there may be multiple for each
    # also, find the tito (taint in taint out) lines associated with it
    for index in range(len(last_instance_reveal_starting_lines_indices)):
        
        if len(last_instance_reveal_starting_lines_indices) > index + 1:
            final_index = last_instance_reveal_starting_lines_indices[index+1]
        else:
            final_index = len(trimmed_lines)
        
        origins_with_tito_lines[stderr_indices_to_discovered[last_instance_reveal_starting_lines_indices[index]]] = {}

        offset_index = last_instance_reveal_starting_lines_indices[index]

        while offset_index < final_index:
            
            current_analyze_line = trimmed_lines[offset_index]

            if "Origin(call_site=" in current_analyze_line:
                character_of_origin = current_analyze_line.find("Origin(call_site=")

                line_segments = current_analyze_line[character_of_origin+len("Origin(call_site="):].split(":")
                line_number_for_this_origin = int(line_segments[0])+1

                offset_index += 1
                if offset_index < final_index:
                    current_analyze_line = trimmed_lines[offset_index]
                
                local_tito_values = []
                # locally, in one origin, look for the tito values
                while "Origin(call_site=" not in current_analyze_line and offset_index < final_index:
                    
                    if "TitoPosition: [" in current_analyze_line:
                        
                        character_of_origin = current_analyze_line.find("TitoPosition: [")

                        line_segments = current_analyze_line[character_of_origin+len("TitoPosition: ["):].split("]")
                        line_segments = line_segments[0].split(", ")
                        
                        for single_tito in line_segments:
                            line_num = single_tito.split(":")[0]
                             
                            local_tito_values.append(line_num)

                    offset_index += 1
                    if offset_index < final_index:
                        current_analyze_line = trimmed_lines[offset_index]

                origins_with_tito_lines[stderr_indices_to_discovered[last_instance_reveal_starting_lines_indices[index]]][line_number_for_this_origin] = local_tito_values
                    
            else:
                offset_index += 1

    return origins_with_tito_lines


def determine_intermediate_reveal_lines(origins_and_intermediate: dict):
    """
    Determine where we should put our reveal lines for the intermediate exploratory stage. Also, track which process_query calls led to taints in following calls.
    """
    all_keys = origins_and_intermediate.keys()
    all_reveals = []
    
    all_actual_lines = []
    for key in all_keys:
        all_actual_lines.append(key-1)
    
    process_query_calls = {} # dict of process query calls, and which preceding process query calls taint them
    for key in all_keys:

        process_query_calls[key-1] = []

        interior_dict = origins_and_intermediate[key]
        all_interior_keys = interior_dict.keys()
        
        for interior_key in all_interior_keys:

            if interior_key in all_actual_lines and interior_key != key -1:
                process_query_calls[key-1].append(interior_key)

            all_reveals.append(interior_key-1)
            #print("appending 2", interior_key-1)

            for reveal_inside in interior_dict[interior_key]:
                
                reveal_inside = int(reveal_inside)
                if (reveal_inside < key - 1) and (reveal_inside not in all_reveals) and (reveal_inside not in all_actual_lines):
                    all_reveals.append(reveal_inside)
                    #print("appending", reveal_inside)
                    #print("appending", reveal_inside, all_actual_lines)
    #print(all_reveals)
    return all_reveals, process_query_calls


def add_reveal_lines(lines_add_reveal: list, arriving_path: str, automatic_process_query: bool, automatic_all_lines: bool):
    """
    Place reveal lines directly below all of the lines specified in argument. 
    If automatic_process_query is true, we apply reveal to all lines that contain process_query. 
    """

    # read generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "r") as generated_script:
        generated_lines = generated_script.readlines()

    if automatic_process_query:
        for index, line in enumerate(generated_lines):
            if "process_query" in line:
                lines_add_reveal.append(index+1)

    if automatic_all_lines:
        for index, line in enumerate(generated_lines):
            lines_add_reveal.append(index+1)
    #print(lines_add_reveal)
    for single_line in lines_add_reveal:

        current_line = generated_lines[single_line-1]
        stripped_line = current_line.strip()

        num_spaces = 0
        space_string = ""
        while(current_line[num_spaces] == " "):
            num_spaces += 1
            space_string += " "

        #print(stripped_line)
        #print("for" in stripped_line)
        # TODO make this more robust?
        # print("Adding new")
        # if the line is a variable assignment
        if "#" in current_line:
            stripped_line = stripped_line.split("#")[0]
        
        if any(element in stripped_line for element in ["for", "if", "while", "try", "elif", "else"]):
            if stripped_line[-1] == ":":
                #space_string += "    "
                continue

        split_line = stripped_line.split()

        if len(split_line) > 1:
            if split_line[1] == "=":
                #print("writing")
                stripped_line = split_line[0] #f"{space_string}reveal_taint({split_line[0]})\n"
        elif "." in stripped_line:
                
            dot_split = stripped_line.split(".")
            stripped_line = dot_split[0]
            print(stripped_line)
            #elif "#" in current_line:
             #   current_split_pound = stripped_line.split(".")
              #  generated_lines[single_line] = f"{space_string}reveal_taint({current_split_pound[0]})\n"
                #print(single_line, generated_lines[single_line])
        
                #print("writing")
                #generated_lines[single_line] = f"{space_string}reveal_taint({stripped_line})\n"
            #if any(element in stripped_line for element in ["for", "if", "while", "try", "elif", "else"]): # TODO is this list complete?
            #print("extra tab")
             #   generated_lines[single_line] = f"{space_string}    reveal_taint({stripped_line})\n"
        #else: # otherwise, we just check it all
            # generated_lines[single_line] = f"{space_string}reveal_taint({stripped_line})\n"
            #print("writing")
        generated_lines[single_line] = f"{space_string}reveal_taint({stripped_line})\n"
        #print("Changed line", generated_lines[single_line])
    # write modified generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "w") as generated_script:
        for line in generated_lines:
            generated_script.write(line)


def remove_reveal_lines(arriving_path: str):
    """
    Remove all calls to reveal_taint.
    """
    # read generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "r") as generated_script:
        generated_lines = generated_script.readlines()

    for index, line in enumerate(generated_lines):
        if "reveal_taint" in line:
            generated_lines[index] = "\n"

    # write modified generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "w") as generated_script:
        for line in generated_lines:
            generated_script.write(line)


def add_comment_lines(lines_comment: list, arriving_path: str):
    """
    Comment out the specified lines.
    """
    # read generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "r") as generated_script:
        generated_lines = generated_script.readlines()

    for index in lines_comment:
        if generated_lines[index-1][0] != "#":
            generated_lines[index-1] = f"#{generated_lines[index-1]}"

    # write modified generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "w") as generated_script:
        for line in generated_lines:
            generated_script.write(line)


def remove_comment_lines(lines_comment: list, arriving_path: str):
    """
    Uncomment lines, only when the comment exists as the first character of the line.
    """
    # read generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "r") as generated_script:
        generated_lines = generated_script.readlines()

    for index in lines_comment:
        #print(generated_lines[index-1:index+1])
        if generated_lines[index-1][0] == "#":
            generated_lines[index-1] = generated_lines[index-1][1:]

    # write modified generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "w") as generated_script:
        for line in generated_lines:
            generated_script.write(line)


def compare_two_chains(chain_one: list, chain_two: list):
    """
    determine if all elements in chain two are contained in chain one, and vice versa, and return the longer train if either is true. 
    """
    #print("comparing", chain_one, chain_two)
    first_compare = True
    for element_of_two in chain_two:
        if element_of_two not in chain_one:
            first_compare = False
    for element_of_one in chain_one:
        if element_of_one not in chain_two:
            if element_of_one < chain_two[-1]:
                first_compare = False
    second_compare = True
    for element_of_one in chain_one:
        if element_of_one not in chain_two:
            second_compare = False
    for element_of_two in chain_two:
        if element_of_two not in chain_one:
            if element_of_two < chain_one[-1]:
                second_compare = False

    if first_compare and second_compare:
        return chain_one
    if first_compare:
        return chain_one
    if second_compare:
        return chain_two
    return False


def determine_source_chains(initial_reveal: dict, secondary_reveal: dict):
    """
    Determine the chains that lead to sources for each of the calls to process_query. 
    Return the independent chains, where if all are broken, then we can remove a taint from the sink. 
    """
    # go through all the process_query calls, and save separate chains for each
    chains_per_process_query = {}

    process_query_keys = initial_reveal.keys()
    #print(initial_reveal)
    for key in process_query_keys:

        chains_per_process_query[key-1] = {}

        # go through all of the sources for this call to process_query
        sources_keys = list(initial_reveal[key].keys())[::-1]

        for source_key in sources_keys:

            if source_key == key-1 or source_key in chains_per_process_query[key-1].keys():
                continue

            chains_per_process_query[key-1][source_key] = []
            continue
            intermediate_keys = list(initial_reveal[key][source_key])[::-1]
            
            for intermediate_key in intermediate_keys:
                
                intermediate_key = int(intermediate_key)+1
                
                if intermediate_key == key:
                    #print("MATCH", key)
                    continue
                # look up each matched intermediate_key in the secoundary_reveal
                if intermediate_key in secondary_reveal.keys():
                    secondary_internal_dict = secondary_reveal[intermediate_key]
                    #print("intermediate key", intermediate_key)
                    secondary_source_keys = secondary_reveal[intermediate_key].keys()
                    
                    if source_key in secondary_source_keys:
                        # see if the secondary chain is one we've already tracked
                        found_match = False
                        
                        current_lists = chains_per_process_query[key-1][source_key]

                        for single_chain in range(len(current_lists)):
                            testing_result = compare_two_chains(current_lists[single_chain], secondary_reveal[intermediate_key][source_key])
                            if testing_result:
                                current_lists[single_chain] = testing_result
                                found_match = True
                                continue
                        chains_per_process_query[key-1][source_key] = current_lists
                        if not found_match:
                            chains_per_process_query[key-1][source_key].append(secondary_reveal[intermediate_key][source_key])


                    else:
                        print(f"Error: Could not find source key '{source_key}' in secondary_reveal[{intermediate_key}]:\n {secondary_reveal[intermediate_key]}, {secondary_reveal}")
                        exit(1)

                else:
                    print(f"Error: Could not find intermediate key '{intermediate_key}' in secondary_reveal:\n {secondary_reveal}")
                    exit(1)
    #print(chains_per_process_query)
    return chains_per_process_query


def find_all_process_query_lines(arriving_path: str):
    """
    Find all lines that call process query.
    """
    pq_lines = []
    with open(f"{arriving_path}agent_helpers/generated_script.py", "r") as generated_script:
        generated_lines = generated_script.readlines()
    for index, line in enumerate(generated_lines):
        if "process_query" in line:
            pq_lines.append(index+1)
    return pq_lines


def insert_annotation_calls(source_chains: dict, arriving_path: str):
    """
    Add calls to annotation function wherever we may have a critical point in the code that leads to a tainted query. 
    """
    all_call_lines = []

    for interior_dict in source_chains.values():
        for interior_value in interior_dict.values():
            for chain in interior_value:
                for single_line in chain:
                    if single_line not in all_call_lines:
                        all_call_lines.append(single_line)

     # read generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "r") as generated_script:
        generated_lines = generated_script.readlines()

    for single_call in all_call_lines:
        num_spaces = 0
        space_string = ""
        while(generated_lines[int(single_call)-1][num_spaces] == " "):
            num_spaces += 1
            space_string += " "

        generated_lines[int(single_call)] = f"{space_string}mcpclient_spec.annotated_call({single_call})\n"

    # write modified generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "w") as generated_script:
        for line in generated_lines:
            generated_script.write(line)


def update_source_chains_with_names(source_chains: dict, arriving_path: str):
    """
    Create a copy of the source_chains but where interior dict keys are private data names instead of where the data is accessed. 
    """
    new_source_chains = {}
    all_keywords_orig = helper_text.get_all_keywords()
    all_keywords = []
    for keyword in all_keywords_orig:
        all_keywords.append(f"access_{keyword[0]}")
    all_keywords.append("process_query")
    #print(all_keywords)

    with open(f"{arriving_path}agent_helpers/generated_script.py", "r") as generated_script:
        generated_lines = generated_script.readlines()

    for key, interior_dict in source_chains.items():
        new_source_chains[key] = {}
        for interior_key, interior_value in interior_dict.items():
            # need to look for the name in the line in the file of one of the private data names
            current_line = generated_lines[interior_key-1]
            found_word = ""
            for keyword in all_keywords:
                if keyword in current_line and len(keyword) > len(found_word):
                    found_word = keyword
            if found_word == "":
                print("Error: Did not find any keyword in current line:", current_line)
                exit(1)
            if found_word == "process_query":
                found_word += str(interior_key)
            else:
                found_word = found_word[len("access_"):]
            new_source_chains[key][found_word] = interior_value

    return new_source_chains


def get_lines_with_accesses(arriving_path):
    """
    Return all line numbers that access private data initially
    """
    lines_with_accesses = []
    with open(f"{arriving_path}agent_helpers/generated_script.py", "r") as generated_script:
        generated_lines = generated_script.readlines()
    all_keywords_orig = helper_text.get_all_keywords()
    all_keywords = []
    for keyword in all_keywords_orig:
        all_keywords.append(f"access_{keyword[0]}")
    
    for index, line in enumerate(generated_lines):
        found_word = ""
        for keyword in all_keywords:
            if keyword in line and len(keyword) > len(found_word):
                found_word = keyword
        if found_word != "":
            lines_with_accesses.append(index+1)
    return lines_with_accesses


def add_untraced_paths_to_chains(chains_orig: dict, commented_taints: dict):
    """
    Add shadow taints that don't have any tito but we must still consider. 
    """
    for single_line in commented_taints.keys():

        for remaining_taint in commented_taints[single_line]:
            
            if remaining_taint == "process_query":
                for check_taint_name in chains_orig[single_line]:
                    if "process_query" in check_taint_name:
                        chains_orig[single_line][check_taint_name].append(['0'])
            else:
                if remaining_taint in chains_orig[single_line].keys():
                    chains_orig[single_line][remaining_taint].append(['0'])
                else:
                    chains_orig[single_line][remaining_taint] = [['0']]

    return chains_orig


def create_taints(local_path: str, reuse_script: bool):
    """
    Create the taint files and run for Pysa for each of the private data values. Return discovered taints.
    local_path: a path to where to store the taints, including closing /
    reuse_script: whether we want to remodify the original script or leave as is
    """

    all_keys = helper_text.get_all_keywords()

    private_keys = []
    for key in all_keys:
        if not key.endswith("_path"):
            private_keys.append(key)

    for index in range(5): # currently, we have 5 possible additions. Change if more are desired. 
        private_keys.append(f'new_value_{index+1}')

    arriving_path = os.environ['ARRIVING_PATH']

    # find all locations in generated script where we call process query
    with open(f"{arriving_path}agent_helpers/generated_script_orig.txt", "r") as generated_script:
        generated_lines = generated_script.readlines()
        generated_lines = modify_generated_script(generated_lines)

    # write modified generated script
    with open(f"{arriving_path}agent_helpers/generated_script.py", "w") as generated_script:
        for line in generated_lines:
            generated_script.write(line)
    
    lines_with_calls = {}  # dict of [line_number, [keys tainted]]
    lines_with_calls_commented = {}
    for index, line in enumerate(generated_lines):
        if "process_query" in line:
             lines_with_calls[index+1] = []  #+1 because line numbers aren't 0 indexed
             lines_with_calls_commented[index+1] = []

    # generate new taint files

    with open(f"{arriving_path}operation_helpers/taint_templates/general.pysa", "r") as read_file:
        read_data = read_file.read()

    total_added_taints = ""
    
    for key in private_keys:
        total_added_taints += f"def database.access_{key}() -> TaintSource[UserPrivate{key}]: ...\n"
   
    total_added_sinks = ""

    for key in range(NUM_ARGS):
        arg_name = f"arg{key+1}"
        total_added_sinks += f"def mcpclient_spec.MCPClient.process_query({arg_name}: TaintSink[MCPCall_{arg_name}]) -> TaintSource[ProcessQuerySource]: ...\n"

    read_data = read_data.replace("TAINT_INSERT", total_added_taints)
    read_data = read_data.replace("SINK_INSERT", total_added_sinks)
    
    with open(f"{arriving_path}{local_path}general.pysa", "w") as write_file:
        write_file.write(read_data)

    with open(f"{arriving_path}operation_helpers/taint_templates/taint.config", "r") as read_file:
        read_data = read_file.read()
    
    total_added_source = ""

    for key in private_keys:
        total_added_source += f"{{\n\"name\": \"UserPrivate{key}\",\n\"comment\": \"Private user data of {key}\"}},\n"

    # remove closing ,\n
    total_added_source = total_added_source[:-2]
    
    read_data = read_data.replace("SOURCES_INSERT", total_added_source)

    total_added_sinks = ""

    if NUM_ARGS >= 100:
        print("Error: 6 digit code number system only works for 99 arguments.")
        exit(1)

    for key in range(NUM_ARGS):
        arg_name = f"arg{key+1}"
        total_added_sinks += f"{{\n\"name\": \"MCPCall_{arg_name}\",\n\"comment\": \"Call to {arg_name}\"\n}},\n"

    read_data = read_data.replace("SINKS_INSERT", total_added_sinks)

    total_added_rules = ""

    if len(private_keys) > 999:
        print("Error: 6 digit code number system only works for 999 private keys.")
        exit(1)

    for index, key in enumerate(private_keys):
        total_added_rules += f"{{\n\"name\": \"{key} in explicit flow\",\n\"code\": {100000+index},\n\"sources\": [\n\"UserPrivate{key}\"\n],\n\"sinks\": [\n\"MCPCall\",\n\"Default\"\n],\n\"message_format\": \"Data from {key} source(s) may reach sink(s)\"\n}},\n"
        total_added_rules += f"{{\n\"name\": \"{key} in implicit flow\",\n\"code\": {200000+index},\n\"sources\": [\n\"UserPrivate{key}\"\n],\n\"sinks\": [\n\"ConditionalTest\"\n],\n\"message_format\": \"Data from {key} source(s) used in control flow\"\n}},\n"

        for arg_key in range(NUM_ARGS):
            arg_name = f"arg{arg_key+1}"
            total_added_rules += f"{{\n\"name\": \"{key} in explicit flow\",\n\"code\": {400000+index+1000*(arg_key+1)},\n\"sources\": [\n\"UserPrivate{key}\"\n],\n\"sinks\": [\n\"MCPCall_{arg_name}\",\n\"Default\"\n],\n\"message_format\": \"Data from {key} source(s) may reach sink(s) {arg_name}\"\n}},\n"

    # add links from process query to each arg
    for arg_key in range(NUM_ARGS):
        arg_name = f"arg{arg_key+1}"
        total_added_rules += f"{{\n\"name\": \"process_query in explicit flow\",\n\"code\": {400000+999+1000*(arg_key+1)},\n\"sources\": [\n\"ProcessQuerySource\"\n],\n\"sinks\": [\n\"MCPCall_{arg_name}\",\n\"Default\"\n],\n\"message_format\": \"Data from process query source(s) may reach sink(s) {arg_name}\"\n}},\n"

    # remove closing ,\n
    total_added_rules = total_added_rules[:-2]

    read_data = read_data.replace("RULES_INSERT", total_added_rules)

    with open(f"{arriving_path}{local_path}taint.config", "w") as write_file:
        write_file.write(read_data)

    with open(f"{arriving_path}operation_helpers/taint_templates/.pyre_configuration", "r") as read_file:
        read_data = read_file.read()
    read_data = read_data.replace("CURRENT_DIRECTORY_OF_TAINTS", f"{local_path}")
    with open(f"{arriving_path}.pyre_configuration", "w") as write_file:
        write_file.write(read_data)
    
    # add initial reveal taints
    remove_reveal_lines(arriving_path)
    add_reveal_lines([], arriving_path, True, False)
    
    # run initial pyre analysis
    output = subprocess.run(["pyre", "analyze", "--output-format=json"], capture_output=True)

    with open(f"{arriving_path}{local_path}general.pysa", "r") as read_file:
        pysa_file = read_file.read()
    pysa_file = pysa_file.replace("def mcpclient_spec.MCPClient.process_query() -> Sanitize[TaintInTaintOut]: ...", "")
    with open(f"{arriving_path}{local_path}general.pysa", "w") as write_file:
        write_file.write(pysa_file)

    second_output = subprocess.run(["pyre", "analyze", "--output-format=json"], capture_output=True)
    stdout = output.stdout.strip()

    stderr = second_output.stderr.strip().decode('utf-8')
    #print(stderr)

    all_orig_traces = extract_revealed_traces(stderr)
    #print(all_orig_traces)
    new_taints = json.loads(stdout)
    #print(new_taints)
    new_reveals, process_query_calls = determine_intermediate_reveal_lines(all_orig_traces)
    #print(new_reveals, process_query_calls)
    
    remove_reveal_lines(arriving_path)
    #add_reveal_lines(new_reveals, arriving_path, False, False)
    
    # run secondary pyre analysis
    #output = subprocess.run(["pyre", "analyze", "--infer-argument-tito", "--output-format=json"], capture_output=True)

    #stdout = output.stdout.strip()

    #stderr = output.stderr.strip().decode('utf-8')
    
    #all_second_traces = extract_revealed_traces(stderr)

    #print(all_orig_traces, all_second_traces)
    all_second_traces = {}
    source_chains = determine_source_chains(all_orig_traces, all_second_traces)
    
    #print("Source chains:", source_chains)
    #print(f"Found {len(new_taints)} data or control taints.")

    remove_reveal_lines(arriving_path)

    # find if there is an untraced path
    #pq_list = find_all_process_query_lines(arriving_path)
    #comment_lines = [item for item in new_reveals if item not in pq_list]
    #access_list = get_lines_with_accesses(arriving_path)
    #print("Line with accesses", access_list, new_reveals)
    #comment_lines = [item for item in comment_lines if item not in access_list]
    #add_comment_lines(comment_lines, arriving_path)
    #print("Comment add lines:", comment_lines, pq_list)
    # run third pyre analysis 
    # output = subprocess.run(["pyre", "analyze", "--infer-argument-tito", "--output-format=json"], capture_output=True)
    
    # stdout = output.stdout.strip()
    # commented_taints = json.loads(stdout)
    #lines_with_call_commented = apply_taints_by_lines_multi_key(commented_taints, lines_with_calls_commented, private_keys, generated_lines)

    #print("Commented", lines_with_call_commented)
    #remove_comment_lines(comment_lines, arriving_path)
    #insert_annotation_calls(source_chains, arriving_path)

    #source_chains = update_source_chains_with_names(source_chains, arriving_path)

    #source_chains = add_untraced_paths_to_chains(source_chains, lines_with_call_commented)
    #print("New source chains:", source_chains)
    lines_with_calls, lines_arguments = apply_taints_by_lines_multi_key(new_taints, lines_with_calls, private_keys, generated_lines) 
     
    #print(lines_with_calls)    
    
    ''' OLD VERSION

    for key in private_keys:
               
        # initialize directory for pyre analysis files
        if not os.path.isdir(f"{arriving_path}{local_path}{key}_taints"):

            os.mkdir(f"{arriving_path}{local_path}{key}_taints")

        with open(f"{arriving_path}operation_helpers/taint_templates/taint.config", "r") as read_file:
            read_data = read_file.read()

        with open(f"{arriving_path}{local_path}{key}_taints/taint.config", "w") as write_file:
            write_file.write(read_data)

        with open(f"{arriving_path}operation_helpers/taint_templates/general.pysa", "r") as read_file:
            read_data = read_file.read()
       
        read_data = read_data.replace("CURRENT_ACCESS", f"access_{key}")
    
        with open(f"{arriving_path}{local_path}{key}_taints/general.pysa", "w") as write_file:
            write_file.write(read_data)

        # reset pyre configuration for current key
        with open(f"{arriving_path}operation_helpers/taint_templates/.pyre_configuration", "r") as read_file:
                read_data = read_file.read()
        read_data = read_data.replace("CURRENT_DIRECTORY_OF_TAINTS", f"{local_path}{key}_taints")
        with open(f"{arriving_path}.pyre_configuration", "w") as write_file:
                write_file.write(read_data)

 e       filename_to_store_temp_analysis = "pyre_analysis_output.json"

        # run pyre analysis for current key
        output = subprocess.run(["pyre", "analyze", "--typeshed", "--infer-argument-tito", "--output-format=json"], capture_output=True)
        
        stdout = output.stdout.strip()
        print(stdout, key)
        new_taints = json.loads(stdout)

        lines_with_calls = apply_taints_by_lines(new_taints, lines_with_calls, key, generated_lines)

    '''
    return lines_with_calls, source_chains, lines_arguments
