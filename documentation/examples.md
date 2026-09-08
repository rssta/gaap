
## Examples

Each example can run starting with a blank database, or the examples can be completed in sequence.  

### Email Phone Number

1. Use the command `/private_data` to add a phone number into the database. This is the manual modification method. 

2. Ask the agent `Email my phone number to Mallory`. The agent should request Mallory's email address, your email address, and your email password. Use `alice@example.com` and `password` for email and password. 

3. The email should get sent. Use `/check_queries` to view "requests". Look at the latest 3 requests. One should contain an email sent to Mallory. 

### Tracking Through File

1. Ask the agent `Write my salary into a file salary.txt`. Give a value for salary when prompted, such as `12345`. 

2. Run the `/clear_context` command, or `/exit` the agent and relaunch with `./gaap_run.sh`. 

3. Ask the agent `Email the file salary.txt to Mallory`. The GAAP prompt should ask if you want to send your salary to Mallory, indicating the taint was carried through the file over time. 
 
