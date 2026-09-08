CREATE TABLE queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    query TEXT,
    std_output TEXT,
    err_output TEXT,
    generated_script TEXT,
    model_name TEXT,
    current_time TEXT
);

CREATE TABLE requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL,
    request_server TEXT NOT NULL,
    request_tool TEXT NOT NULL,
    request_params TEXT NOT NULL,
    request_result TEXT,
    FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
);

CREATE TABLE disclosures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    taint TEXT NOT NULL,
    principal_disclosed_to TEXT NOT NULL,
    time INTEGER,
    params TEXT,
    arg_names TEXT NOT NULL,
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
)
