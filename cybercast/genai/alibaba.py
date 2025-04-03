import os
from dotenv import load_dotenv
from dashscope import Generation
from cybercast.genai.diskcache import llm_disk_cache

load_dotenv()


@llm_disk_cache(cache_dir=os.getenv("LLM_CACHE_DIR", ".cache/llm"))
def dashscope_generate(model: str, prompt: str, enable_search: bool = True, stream: bool = True):
    messages = [
        {'role': 'user', 'content': prompt}
    ]
    response = Generation.call(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx",
        api_key=os.getenv("DASHSCOPE_API_KEY"), 
        model=model,
        messages=messages,
        result_format="message",
        enable_search=enable_search,
        stream=stream,
        incremental_output=True
    )

    if stream:
        content = ""
        for chunk in response:
            chunk_text = chunk.output.choices[0].message.content
            content += chunk_text

        if content.startswith("```"):
            return content.split("```")[1]
        else:
            return content
    elif response.status_code == 200:
        return response.output.choices[0].message.content
    else:
        print(f"HTTP返回码：{response.status_code}")
        print(f"错误码：{response.code}")
        print(f"错误信息：{response.message}")
        print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
        return None
