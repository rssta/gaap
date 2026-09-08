
from openai import OpenAI
import sys
import os
import ollama
from google import genai

sys.path.insert(0, os.environ['ARRIVING_PATH'])

import config

use_local = config.use_type
model = config.model

message_send = "hi, please include the concatenation of 'fed'|'cba' in your response."

try:
    if use_local == "openai":
        client = OpenAI()
        response = client.responses.create(
        model=model,
        input=message_send
        )
        #print(response)
        response = response.output_text
        #print(response)
    elif use_local == "google":
        client = genai.Client()

        response = client.models.generate_content(
            model=model,
            contents=message_send,
        )

        response = response.text
    elif use_local == "local":
        from ollama import chat
        from ollama import ChatResponse
        if model == "llama3.2":

            response = ollama.generate(
                model=model,
                prompt=message_send
            )
            response = response['response']

        else:
            response: ChatResponse = chat(model=model, messages=[
            {
                'role': 'system', 
                'content': message_send,
            },
            ])
            response = response.message.content
    else:
        print("Error: Not a valid model provider.")
        exit(1)


except Exception as e:
    print(f"Exception in LLM call: {e}")
    response = "None"

if "fedcba" not in response:
    print(f"Output did not contain desired string 'fedcba': {response}")
    exit(1)
