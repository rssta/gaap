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

2. Be sure that [UV](https://docs.astral.sh/uv/) and [SQLite](https://sqlite.org/index.html) (with your preferred package manager) are installed. 

3. Set environment variables in terminal. Set the API key for the service you intend to use. No API key is needed if using local (OLlama) models.
```
export OPENAI_API_KEY="<add-key-here>"
export GEMINI_API_KEY="<add-key-here>"
```

4. Set your model provider and model name in `config.py`. You can determine if you would like to use local (OLlama) or remote (OpenAI or Google), and what model you would prefer. We recommend a relatively large LLM (such as `GPT-5.6-Sol`) for the highest task completion rate, particularly for more complex tasks. Other LLMs (such as `GPT-5.6-Terra`) are capable of operating under GAAP, but may see lower task completion rates for complex tasks. Other configurations can be left at their default. 

5. Execute setup script in the project directory. **This setup script will make a single API call to your configured LLM to test operationally, which will use a small number of tokens. This step may take up to two minutes, depending on the speed of your chosen LLM.** You may be prompted how you want to initialize `privateData.db`. We recommend the default (1) to use a fresh database.
```
./setup.sh
```

6. Run the interactive command line interface in the project directory. Run as follows.
```
./gaap_run.sh
```

7. We recommend you begin with the example task listed below. After that, we invite you to explore what you can achieve with GAAP. 

### Manual Setup

All of the steps in the setup, including those wrapped into `setup.sh` are listed in [manual setup](documentation/manual_setup.md). 

## Operation

### Existing Servers

GAAP currently has built-in servers for checking weather, converting time, mock email sending, real Gmail email sending, ordering food in a mock restaurant, filesystem operations, checking internet utilities, Wikipedia, and medical conversions. Full tool listings and specifications are available in [`all_servers.json`](all_servers.json). We provide further [details about the email servers](documentation/email_instructions.md).  

### Example Task

1. Ask the agent `Email my phone number to Mallory using server email`. We specify the server because we have [two email servers](documentation/email_instructions.md) in the system by default. Note that this prompt does not contain sensitive values, as GAAP requires sensitive private data is not given directly in prompts. 
   
2. Because the system has no information to begin, it will need to ask you for some values to complete this request. These values will be persisted in the future in the private data database. The agent should request your phone number and Mallory's email address. You can give `1234567890` as phone number and `mallory@example.com` as Mallory's email. Also, GAAP may ask to share these values with `mallory@example.com` using the `send_email` tool. During this stage, the LLM generates a plan of actions that may differ between runs. As a result, these requests for data and permissions may come in different orderings. 

3. After this, the email to Mallory should get sent. If you deny any of the requested permissions, the email will not be sent. 

4. The email should get sent. Use the `/check_queries` tool inside of the GAAP chat to view "requests". Look at the latest 3 requests. One should contain an email sent to Mallory.

5. If you'd like to retry the example task, the permissions you have granted will be persisted. So, use the `/remove_permissions` tool inside the GAAP chat to remove permissions before retrying. 
 
We provide some additional [example use cases](documentation/examples.md) to try with GAAP. 
