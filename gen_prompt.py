


import argparse
import os
from utils.common_utils import load_json

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", type=str, default="earthquake")
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

if __name__ == "__main__":
    main()











