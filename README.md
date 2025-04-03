

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

### 配置环境变量
```
cp .env.example .env
```

至少需配置 `DASHSCOPE_API_KEY` 和 `TTS_CACHE_DIR` 两个环境变量。

## 运行

### 任务配置
在 `data/tasks` 目录下创建任务目录， 配置 `config.json` 文件。

配置说明:
```json
{
    "topic": "美国顶流网红Speed中国行", # 必须，用于生成提示词
    "column_name": "《赛博21世纪》网络电台", # 必须，用于生成提示词
    "mcs": {
        "卢不遇": {
            "tts": "cosyvoice", // 必须， TTS 模型, 可选: "cosyvoice", "sambert"
            "model": "cosyvoice-v1", // 必须， TTS 模型, 见阿里云 TTS 模型列表
            "voice": "longmiao", // 必须， TTS 音色, 见阿里云 TTS 音色列表
            "intro": "30岁， 中国资深新闻电台主持人，从事国际、国内社会新闻报导长达二十多年，21世纪全球最有影响力的100位女性之一。 思维敏捷、语言风趣活泼。能够与任何人进行自然、有趣的对话，并善于提出一些有趣的问题。", //必须，可用于脚本生成提示词。

            "wave_color": "#FF6B6B", // 非必须， 视频声波颜色
            "gender": "female", // 非必须， 主播性别
            "age": 30, // 非必须， 主播年龄
            "avatar": "avatars/1.png", // 非必须， 主播头像
            "looking": "short-hair young woman, cute" // 非必须， 主播形象描述
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

### 脚本生成
```
./run.sh prompt <task_name>
```
其中，  `<task_name>` 为任务目录名。

运行该命令将在任务目录下生成 `prompt.md` 文件。 复制该文件中的提示词， 丢给任何 AI 模型， 都可以生成一个对话脚本。请将模型生成的脚本保存在任务目录下的 `transcript.txt` 文件中。

### 生成对话音频
```
./run.sh podcast <task_name>
```
输出音频路径为 `data/tasks/<task_name>/podcast.mp3`。

### 生成对话视频
```
./run.sh video <task_name>
```
输出视频路径为 `data/tasks/<task_name>/<task_name>.mp4`。

