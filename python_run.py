import pickle

def build_message(input_item):
    cleaned = []
    for x in input_item:
        s = str(x)
        s = s.replace("\\", "/").replace(""", "'").replace("
", " ").replace("", " ")
        cleaned.append(s)
    item, order_resp, status_resp = cleaned
    return f"Coffee order update: item ordered: {item}; order response: {order_resp}; current status: {status_resp}"

with open("/Users/rsta/Documents/agentAI/agent-ai-privacy/python_input.pkl", "rb") as file:
    input_val = pickle.load(file)

output = build_message(input_val)

with open("/Users/rsta/Documents/agentAI/agent-ai-privacy/python_output.pkl", "wb") as file:
    pickle.dump(output, file)