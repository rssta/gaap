## Manual Setup

This document explains the steps for setup. In the quick setup, some of these steps are combined into the `setup.sh` file. 

1. Complete all steps in quick setup until `setup.sh`.

2. Initialize added databases, or bring copied versions. The required databases to be initialized currently are `internalData.db` and `queries_4.db`. Internal database is used for some server operation. The queries database keeps a record of queries made and the disclosure log. Run the following.
```
sqlite3 internalData.db < agent_helpers/InternalSchema.sql
sqlite3 queries_4.db < operation_helpers/QueriesSchema.sql
```

3. Make copies of needed files from templates for your local instance. The second command sets a copy of a baseline private data database with some values inside. If you want a fresh private data database, run the third command instead. 
```
cp agent_helpers/database_template.py agent_helpers/database.py
cp privateData_template_filled.db privateData.db
# or, for a fresh database,
cp privateData_template.db privateData.db
```

6. Run the interactive command line interface. Run as follows. Note that the permissions database will be persisted over time. 
```
./gaap_run.sh
```

7. If you want to run test cases, set the tests as desired in `run_full_query.py`. Be sure to rerun the taints and the generation if you have a new prompt. Run it as follows. 
```
uv run run_full_query.py
```

