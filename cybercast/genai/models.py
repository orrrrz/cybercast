# coding: utf-8

import json
import backoff
import dotenv
import os
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

def load_models():
    with open("models.json", "r") as f:
        models = json.load(f)

    config = {}
    for model in models:
        config[model["name"]] = model
    return config
    


def get_model(model_name: str, temperature: float = 0, enable_search: bool = True):
    models = load_models()
    
    if model_name not in models:
        raise ValueError(f"Model {model_name} not found")
    
    print(f"Loading model {model_name} with api_key {models[model_name]['api_key']} and base_url {models[model_name]['base_url']}")
    return ChatOpenAI(model=model_name, 
                      api_key=os.getenv(models[model_name]["api_key"]), 
                      base_url=models[model_name]["base_url"],
                      temperature=temperature,
                      metadata={"enable_search": enable_search}
                      )

@backoff.on_exception(backoff.expo, (Exception), max_tries=3)
def generate(model: ChatOpenAI, prompt: str):
    messages = [
        {"role": "user", "content": prompt},
    ]
    response = model.invoke(messages)
    return response.content


if __name__ == "__main__":
    model = get_model("qwen-max")
    prompt = "2025年缅甸地震是哪一天发生的？"
    print(generate(model, prompt))


