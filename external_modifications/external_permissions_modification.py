
import agent_helpers.database as database
import wikipediaapi

def nicely_print_permissions(all_permissions):
    """
    Print out permissions in a readable format.
    """
    #print(all_permissions)
    tab = "\t"
    print("\033[32m  GAAP:\033[0m\tBelow are all the existing permissions for servers and tools. For servers that are listed without any specific tool mentions, all permissions apply to all tools for the server.")
    print("ID\tServer\t\tTool\t\tPermission\t\t\t\t\tExtra Information")
    for one_key in all_permissions.keys():
        server_permissions = all_permissions[one_key]
        if type(server_permissions) == list:
            for single_permissions in server_permissions:
                tool_name = "all tools"
                first_tabs = (16 - len(one_key)) // 8 + 1
                second_tabs = (16 - len(tool_name)) // 8 + 1 
                print(f"{single_permissions[0]}\t{one_key}{first_tabs*tab}{tool_name}{second_tabs*tab}{single_permissions[1]}")

        elif type(server_permissions) == dict:
            for interior_key in server_permissions.keys():
                interior_permissions = server_permissions[interior_key]
                if type(interior_permissions) == list:
                    for single_permissions in interior_permissions:
                        first_tabs = (16 - len(one_key)) // 8 + 1
                        second_tabs = (16 - len(interior_key)) // 8 + 1 
                        print(f"{single_permissions[0]}\t{one_key}{first_tabs*tab}{interior_key}{second_tabs*tab}{single_permissions[1]}")
                elif type(interior_permissions) == dict:
                    for extra_key in interior_permissions.keys():
                        extra_permissions = interior_permissions[extra_key]
                        for extra_permission in extra_permissions:
                            first_tabs = (16 - len(one_key)) // 8 + 1
                            second_tabs = (16 - len(interior_key)) // 8 + 1 
                            third_tabs = (48 - len(extra_permission[1])) // 8 + 1
                            print(f"{extra_permission[0]}\t{one_key}{first_tabs*tab}{interior_key}{second_tabs*tab}{extra_permission[1]}{third_tabs*tab}{extra_key}")

                else:
                    print("Error: interior permissions incorrect format.")
                    exit(1)
        else:
            print("Error: Server permissions incorrect format.")
            exit(1)


def accept_permission_removals():
    """
    Ask for IDs of permissions to remove.
    """
    
    ids = input("\033[32m  GAAP:\033[0m\tPlease select the IDs you want to remove. Then, type them in as a space separated list. Hit enter when completed with list:  ")
    
    validated_ids = []
    for id_value in ids.split():
        try:
            int_id = int(id_value)
            validated_ids.append(int_id)
        except ValueError as e:
            pass

    database.remove_permission_by_id(validated_ids)
    
    print(f"\033[32m  GAAP:\033[0m\tIDs of {validated_ids} removed.")


def call_all_operations():
    all_permissions = database.get_all_permissions() 
    nicely_print_permissions(all_permissions)
    accept_permission_removals()


def main():
    all_permissions = database.get_all_permissions() 
    nicely_print_permissions(all_permissions)

    accept_permission_removals()


if __name__ == '__main__':
    main()
