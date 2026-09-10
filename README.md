# GAAP

Welcome to GAAP (Guaranteed Accounting for Agent Privacy). This agent execution environment keeps your private data safe. Below are setup instructions and more information about the system. 

Find details about the concept of GAAP on [ArXiv](https://arxiv.org/abs/2604.19657). 

```
@misc{gaap,
      title={An {AI} Agent Execution Environment to Safeguard User Data}, 
      author={Robert Stanley and Avi Verma and Lillian Tsai and Konstantinos Kallas and Sam Kumar},
      year={2026},
      eprint={2604.19657},
      archivePrefix={arXiv},
      primaryClass={cs.CR},
      url={https://arxiv.org/abs/2604.19657}, 
}
```

## Demo

Below is a demonstration of GAAP in action. We see that the user has a file [`poem.txt`](documentation/poem.txt). This file contains words, along with a prompt injection. The user asks the agent to read the file, putting the untrusted content of the file into the agent context. As a result, the agent attempts an unintended action of sending a file `important_plans.txt` to an external email address. GAAP detects this action, and because the user has not given permission for this action prior, it prompts the user, and the user declines. 

https://github.com/user-attachments/assets/4ce35ea8-f1a6-4a7c-8c0f-253ba7914eb6

## Setup

### Quick Setup

1. Clone repository. 

2. Be sure that [UV](https://docs.astral.sh/uv/) and [SQLite](https://sqlite.org/index.html) are installed. 

3. Set environment variables in terminal. Set the API key for the service you intend to use. No API key is needed if using local (OLlama) models.
```
export OPENAI_API_KEY="<add-key-here>"
export GEMINI_API_KEY="<add-key-here>"
```

4. Open `config.py`, and set parameters as desired. You can determine if you would like to use local (OLlama) or remote (OpenAI or Google), and what model you would prefer. 

5. Execute setup script in the project directory. This setup script will make a single call to your configured LLM to test operationality. You may be prompted how you want to initialize `privateData.db`. If you initialize fresh, it will have no private data to begin. If you initialize with a template, it will have example user private data contained inside. 
```
./setup.sh
```

6. Run the interactive command line interface in the project directory. Run as follows. Note that the permissions database will be persisted over time. 
```
./gaap_run.sh
```

### Manual Setup

All of the steps in the setup, including those wrapped into `setup.sh` are listed in [manual setup](documentation/manual_setup.md). 

## Operation

### Existing Servers

GAAP currently has built-in servers for checking weather, converting time, mock email sending, real Gmail email sending, ordering food in a mock restaurant, filesystem operations, checking internet utilities, Wikipedia, and medical conversions. Full tool listings and specifications are available in [`all_servers.json`](all_servers.json). We provide further [details about the email servers](documentation/email_instructions.md).  

### Example Uses

Each example can run starting with a blank database, or the examples can be completed in sequence.  

#### Email Phone Number

1. Use the command `/private_data` to add a phone number into the database. This is the manual modification method. 

2. Ask the agent `Email my phone number to Mallory using server email`. We specify the server so that it does not user server [`email_real`](documentation/email_instructions.md) to send a real email. The agent should request Mallory's email address, your email address, and your email password. You can choose Mallory's email address. Use `alice@example.com` and `password` for your email and password. 

3. The email should get sent. Use `/check_queries` to view "requests". Look at the latest 3 requests. One should contain an email sent to Mallory. 

#### Tracking Through File

1. Ask the agent `Write my salary into a file salary.txt`. Give a value for salary when prompted, such as `12345`. 

2. Run the `/clear_context` command, or `/exit` the agent and relaunch with `./gaap_run.sh`. 

3. Ask the agent `Email the file salary.txt to Mallory with server email`. The GAAP prompt should ask if you want to send your salary to Mallory, indicating the taint was carried through the file over time. 
 
We provide some additional [example use cases](documentation/examples.md) to try with GAAP. 


