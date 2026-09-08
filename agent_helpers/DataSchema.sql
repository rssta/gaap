CREATE TABLE private_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    keyword TEXT,
    datavalue TEXT
);

CREATE TABLE permissions (
    permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    positive_permission BOOlEAN NOT NULL,
    data_id INTEGER NOT NULL,
    permission_tool TEXT NOT NULL,
    permission_type TEXT NOT NULL,
    permission_extra_information TEXT NOT NULL,
    FOREIGN KEY (data_id) REFERENCES private_data(id) ON DELETE CASCADE
)
