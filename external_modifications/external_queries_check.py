import sqlite3


def get_queries(query_db: str, all_queries: bool, num_recent_queries: int):
    
    
    with sqlite3.connect(query_db) as conn:
        cursor = conn.cursor()
        if not all_queries:
            cursor.execute("SELECT * FROM queries ORDER BY rowid DESC LIMIT ?", (num_recent_queries,))
            output = cursor.fetchall()
            for index, output_single in enumerate(output):
                print(f"  {index+1}: {output_single}")
        else:
            cursor.execute("SELECT * FROM queries")
            output = cursor.fetchall()
            print(output)

def can_convert_to_int(string_value):
    try:
        int(string_value)
        return True
    except ValueError:
        return False


def get_requests(query_db: str, all_requests: bool, num_recent_requests: int):
    
    
    with sqlite3.connect(query_db) as conn:
        cursor = conn.cursor()
        if not all_requests:
            cursor.execute("SELECT * FROM requests ORDER BY rowid DESC LIMIT ?", (num_recent_requests,))
            output = cursor.fetchall()
            for index, output_single in enumerate(output):
                print(f"  {index+1}: {output_single}")
        else:
            cursor.execute("SELECT * FROM requests")
            output = cursor.fetchall()
            print(output)

def can_convert_to_int(string_value):
    try:
        int(string_value)
        return True
    except ValueError:
        return False


def ask_queries(query_db):

    query_or_request = input("\033[31m/:\033[0m\tWould you like to see queries to the interal GAAP agent or requests to MCP servers? Type \"queries\" or \"requests\":  ")

    if query_or_request == "queries":
        input_arg = input("\033[31m/:\033[0m\tWould you like to see all recorded queries, or a specific number of recent queries? Input \"all\" to see all. Input an integer to see that number of most recent queries:  ")
        if input_arg == "all":
            get_queries(query_db, True, 0)
        elif can_convert_to_int:
            get_queries(query_db, False, int(input_arg))
        else:
            print(f"\033[31m\:\033[0m\tUnrecongized argument {input_arg}")
    if query_or_request == "requests":
        input_arg = input("\033[31m/:\033[0m\tWould you like to see all recorded requests, or a specific number of recent requests? Input \"all\" to see all. Input an integer to see that number of most recent requests:  ")
        if input_arg == "all":
            get_requests(query_db, True, 0)
        elif can_convert_to_int:
            get_requests(query_db, False, int(input_arg))
        else:
            print(f"\033[31m\:\033[0m\tUnrecongized argument {input_arg}")

