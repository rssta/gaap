import operation_helpers.helper_text as helper_text
import agent_helpers.database as database


def remove_element():

    keyword = input("  \033[32mGAAP:\033[0m\tType the keyword you would like to remove:  ")
    if not database.access_data(keyword):
        return
    worked = database.remove_data(keyword)
    if worked:
        print(f"  \033[32mGAAP:\033[0m\tKeyword of {keyword} removed.")


def add_element():

    keyword = input("  \033[32mGAAP:\033[0m\tType the keyword you would like to add:  ")
    value = input(f"  \033[32mGAAP:\033[0m\tType the value you would like for {keyword}:  ")
    
    with open("agent_helpers/database.py", "r") as file:
        database_text = file.read()
    
    new_string = f"def access_{keyword}():\n    return access_data('{keyword}')\n\n#"+"INSERTACCESS"
    database_text = database_text.replace("#"+"INSERTACCESS", new_string)
    with open("agent_helpers/database.py", "w") as file:
        file.write(database_text)

    database.insert_all_data({keyword: value,})
    print(f"  \033[32mGAAP:\033[0m\tKeyword of {keyword} added with value {value}.")


def edit_element():

    keyword = input("  \033[32mGAAP:\033[0m\tType the keyword you would like to edit:  ")
    if not database.access_data(keyword):
        return
    value = input(f"  \033[32mGAAP:\033[0m\tType the value you would like for {keyword}:  ")
    database.insert_all_data({keyword: value,})
    print(f"  \033[32mGAAP:\033[0m\tKeyword of {keyword} updated with value {value}.")


def list_elements():


    all_keywords = helper_text.get_all_keywords()
    #print(all_keywords) 
    all_keywords_non_path = []
    for keyword in all_keywords:
        if keyword[-5:] != "_path":
            all_keywords_non_path.append(keyword)

    if len(all_keywords_non_path) == 0:
        print(f"  \033[32mGAAP:\033[0m\tThe private data database is empty.")
        return

    print(f"  \033[32mGAAP:\033[0m\tCurrent keywords and values in private data database:\n  keyword\t\t\tvalue")


    for keyword in all_keywords_non_path:
        tabs = '\t' * ( (32 - len(keyword)) // 8 + 1)
        print(f"  {keyword}{tabs}{database.access_data(keyword)}")


def private_data_options():

    not_done = True

    while not_done: 
        
        option = input("\033[31m/:\033[0m\tWould you like to list, add, remove, or edit values in the private data database? Type \"list\", \"add\", \"remove\", \"edit\", or \"done\":  ")
        if option == "list":
            list_elements()
        elif option == "add":
            add_element()
        elif option == "remove":
            remove_element()
        elif option == "edit":
            edit_element()
        else:
            not_done = False


