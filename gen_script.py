import argparse
import os
from cybercast.utils.common_utils import load_json
from cybercast.genai.models import get_model, generate
from cybercast.genai.alibaba import dashscope_generate

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", type=str, required=True)
parser.add_argument("-p", "--prompt_only", action="store_true", help="是否只生成提示词，不生成脚本")
args = parser.parse_args()

def main():
    args = parser.parse_args()

    task_dir = os.path.join("data/tasks", args.name)
    config_path = os.path.join(task_dir, "config.json")
    config = load_json(config_path)


    mcs = config["mcs"]
    mc_intros = ""
    for mc_name, mc_info in mcs.items():
        mc_intros += f"* {mc_name}: {mc_info['intro']}\n"

    examples = ""
    max_examples = 4
    mc_names = list(mcs.keys())
    for i in range(max_examples):
        mc = mc_names[i % len(mc_names)]
        if i == 0:
            examples += f"{mc}: <开场语>\n"
        else:
            examples += f"{mc}: <>\n"

    # load prompt template
    with open(os.path.join("data/prompts", "script_template.md"), "r") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{{topic}}", config["topic"]).replace("{{column_name}}", config["column_name"]).replace("{{mc_intros}}", mc_intros).replace("{{output_example}}", examples)
    print(prompt)

    # save prompt
    with open(os.path.join(task_dir, "prompt.md"), "w") as f:
        f.write(prompt)

    if args.prompt_only:
        return
    


    model_name = config.get("script_model", "qwq-plus")
    
    if model_name.startswith("qwen") or model_name.startswith("qwq"):
        transcript = dashscope_generate(model_name, prompt, enable_search=True)
    else:
        model = get_model(model_name)
        transcript = generate(model, prompt)

    print(f"Script generated: \n{transcript}")
    
    with open(os.path.join(task_dir, "transcript.txt"), "w") as f:
        f.write(transcript)
    

if __name__ == "__main__":
    main()











