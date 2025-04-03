# cybercast - 基于 AI 的访谈对话视频生成工具

## 安装

### 安装依赖
```
conda create -n cybercast python=3.12
conda activate cybercast
pip install -r requirements.txt
```

### 安装 ffmpeg
MacOS:
```
brew install ffmpeg
```

Linux:
```
sudo apt-get install ffmpeg
```

### 准备 API_KEY 

本项目依赖 阿里云 DashScope 的 TTS 及 LLM 服务， 请自行申请 DashScope API Key。

### 配置环境变量
```
cp .env.example .env
```

环境变量说明:
* `DASHSCOPE_API_KEY`: DashScope API Key
* `TTS_CACHE_DIR`: TTS 语音合成缓存目录
* `LLM_CACHE_DIR`: LLM 请求缓存目录

## 运行

### 任务配置
在任务目录(默认为`data/tasks`) 下以任务名创建任务目录， 然后创建任务配置文件 `config.json`。

配置示例:
```json
{
    "topic": "美国顶流网红Speed中国行", 
    "column_name": "《赛博21世纪》网络电台", 
    "script_model": "qwq-plus",
    "mcs": {
        "卢不遇": {
            "tts": "cosyvoice",
            "model": "cosyvoice-v1", 
            "voice": "longmiao", 
            "intro": "30岁， 中国资深新闻电台主持人，从事国际、国内社会新闻报导长达二十多年，21世纪全球最有影响力的100位女性之一。 思维敏捷、语言风趣活泼。能够与任何人进行自然、有趣的对话，并善于提出一些有趣的问题。", //必须，可用于脚本生成提示词。

            "wave_color": "#FF6B6B", 
            "gender": "female", 
            "age": 30, 
            "avatar": "avatars/1.png", 
            "looking": "short-hair young woman, cute" 
        },
        "黑眼松": {
            "gender": "male",
            "age": 40,
            "avatar": "avatars/2.png",
            "looking": "short-hair middle-aged man, handsome",
            "tts": "sambert",
            "model": "sambert-zhihao-v1",
            "intro": "50岁， 男，中国当代著名学者，对国际政治、经济有着深入、全面的了解。 对于自然和社会事件背后的经济、社会、政治背景均了如指掌，并对其背后的原因、影响都有着深入的理解。 ",
            "wave_color": "#4ECDC4"
        }
    }
}
```

字段说明:
* `topic`*: 对话话题， 用于生成提示词
* `column_name`*: 栏目名称， 用于生成提示词。
* `script_model`: 脚本生成模型， 非必须
* `mcs`: 主播列表， 每个主播的配置如下:
    - `tts`: TTS 模型， 必须， 可选: "cosyvoice", "sambert"
    - `model`: TTS 模型， 必须， 见阿里云 TTS 模型列表
    - `voice`: TTS 音色， 必须， 见阿里云 TTS 音色列表
    - `intro`: 主播介绍， 必须， 用于生成提示词
    - `wave_color`: 声波颜色， 非必须， 用于在视频上显示声波颜色。
    - `gender`: 主播性别， 非必须， 用于生成提示词
    - `age`: 主播年龄, 非必须， 用于生成提示词
    - `avatar`: 主播头像， 必须， 用于在视频上显示头像。
    - `looking`: 主播形象描述， 非必须， 用于生成提示词

### 脚本生成
```bash
./run.sh script <task_name>
```
其中，  `<task_name>` 为任务目录名。

运行该命令将在任务目录下生成以下文件:
- `prompt.md` 文件： 脚本生成提示词。
- `transcript.txt` 文件： 访谈对话脚本。

也可以指定`-p` 参数只生成提示词， 然后手动丢给任何 AI 模型， 然后手动将模型生成的脚本保存到任务目录下 `transcript.txt` 文件中。
```bash
./run.sh script -n <task_name> -p
``` 

### 生成对话音频
```bash
./run.sh podcast -n <task_name>
```
输出音频名称为 `podcast.mp3` (任务目录下)。

### 生成对话视频
```bash
./run.sh video -n <task_name>
```
输出视频名称为 `<task_name>.mp4` (任务目录下)。

以上三个步骤也可以一键运行:
```bash
./run.sh all -n <task_name>
```

