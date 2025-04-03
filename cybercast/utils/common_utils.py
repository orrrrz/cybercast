import json
import subprocess
import os

def write_concat_file(audio_file_list: list, concat_file: str):
    if os.path.exists(concat_file):
        os.remove(concat_file)
    with open(concat_file, 'w', encoding='utf-8') as f:
        for audio in audio_file_list:
            # convert to absolute path
            audio = os.path.abspath(audio)
            # 检查文件是否存在
            if not os.path.exists(audio):
                print(f"Warning: Audio file '{audio}' does not exist, skipping")
                continue
            f.write(f"file '{audio}'\n")

def get_task_dir(name: str) -> str:
    task_dir = os.getenv("TASK_DIR")
    if not task_dir:
        task_dir = os.path.join("data/tasks", name)
    else:
        task_dir = os.path.join(task_dir, name)
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)
    return task_dir

def load_json(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = json.load(f)
    return content

def load_transcript(file_path: str) -> list[dict]:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    transcript = []
    for line in content.split('\n'):
        line = line.strip()
        if line == "":
            continue
        if line.find(":") == -1:
            print(f"Unknown line: {line}")
            continue
        [mc, line] = line.split(":", 1)
        transcript.append({
            "mc": mc,
            "line": line
        })
    return transcript

def update_transcript_with_timestamps(transcript_file: str, segment_info_file: str, audio_segment_file: str = None):
    """
    将合并后的音频时间戳信息更新到transcript文件中
    
    Args:
        transcript_file: transcript文件路径
        segment_info_file: 包含音频片段信息的JSON文件路径
        audio_segment_file: 可选，音频片段文件路径，用于确定当前transcript属于哪个片段
    """
    # 读取音频片段信息
    segments = load_json(segment_info_file)
    
    # 读取transcript内容
    transcript_lines = []
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript_lines = f.readlines()
    
    # 确定当前transcript对应的音频片段
    segment_index = 0
    if audio_segment_file:
        # 查找匹配的音频片段
        audio_segment_file = os.path.basename(audio_segment_file)
        for i, segment in enumerate(segments):
            if segment["file"] == audio_segment_file:
                segment_index = i
                break
    
    # 获取该片段的基准时间
    base_time = segments[segment_index]["start_time"]
    
    # 读取原始transcript
    transcript = load_transcript(transcript_file)
    
    # 更新transcript，添加时间戳
    updated_lines = []
    for i, entry in enumerate(transcript):
        # 假设每行均匀分布在音频中
        segment_duration = segments[segment_index]["original_duration"]
        line_count = len(transcript)
        
        if line_count > 1:
            # 计算当前行在片段中的相对时间
            rel_time = segment_duration * (i / (line_count - 1)) if line_count > 1 else 0
        else:
            rel_time = 0
            
        # 计算全局时间
        global_time = base_time + rel_time
        
        # 格式化时间为 [HH:MM:SS]
        time_str = format_time(global_time)
        updated_line = f"[{time_str}] {entry['mc']}: {entry['line']}\n"
        updated_lines.append(updated_line)
    
    # 写入更新后的transcript
    with open(transcript_file + ".with_timestamps.txt", 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    print(f"Updated transcript with timestamps saved to {transcript_file}.with_timestamps.txt")
    return True

def update_all_transcripts(segments_json: str, transcript_dir: str):
    """
    更新指定目录下的所有transcript文件，添加时间戳
    
    Args:
        segments_json: 包含音频片段信息的JSON文件路径
        transcript_dir: 包含transcript文件的目录
    """
    segments = load_json(segments_json)
    
    # 查找目录中的所有txt文件
    transcript_files = []
    for file in os.listdir(transcript_dir):
        if file.endswith(".txt") and not file.endswith(".with_timestamps.txt"):
            transcript_files.append(os.path.join(transcript_dir, file))
    
    if not transcript_files:
        print(f"No transcript files found in {transcript_dir}")
        return False
    
    # 按照音频片段顺序处理transcript
    for i, segment in enumerate(segments):
        segment_name = os.path.splitext(segment["file"])[0]  # 移除扩展名
        
        # 查找匹配的transcript文件
        matching_files = []
        for tf in transcript_files:
            if segment_name in os.path.basename(tf):
                matching_files.append(tf)
        
        # 更新匹配的transcript文件
        for tf in matching_files:
            print(f"Updating timestamps for {tf} (Segment {i+1}: {segment['file']})")
            update_transcript_with_timestamps(tf, segments_json, segment["file"])
    
    return True

def update_podcast_timestamps(podcast_json_path: str, segments_info_file: str):
    """
    更新podcast.json中的时间戳为合并后的准确时间
    
    Args:
        podcast_json_path: podcast.json文件路径
        segments_info_file: 包含音频片段信息的JSON文件路径
    
    Returns:
        bool: 是否成功更新
    """
    # 读取podcast.json
    if not os.path.exists(podcast_json_path):
        print(f"Error: Podcast JSON file {podcast_json_path} does not exist")
        return False
        
    with open(podcast_json_path, 'r', encoding='utf-8') as f:
        podcast_data = json.load(f)
    
    # 读取音频片段信息
    if not os.path.exists(segments_info_file):
        print(f"Error: Segments info file {segments_info_file} does not exist")
        return False
        
    segments = load_json(segments_info_file)
    
    # 建立音频文件到时间偏移的映射
    file_to_offset = {}
    for segment in segments:
        file_path = segment["full_path"]
        file_to_offset[file_path] = segment["start_time"]
        file_to_offset[os.path.basename(file_path)] = segment["start_time"]
    
    # 更新podcast数据中的时间戳
    for item in podcast_data:
        if "audio_path" in item:
            audio_path = item["audio_path"]
            # 尝试直接匹配或匹配文件名
            if audio_path in file_to_offset:
                # 直接使用映射中的时间偏移
                item["ts"] = file_to_offset[audio_path]
            elif os.path.basename(audio_path) in file_to_offset:
                # 使用文件名匹配的时间偏移
                item["ts"] = file_to_offset[os.path.basename(audio_path)]
            else:
                print(f"Warning: Could not find time offset for audio file {audio_path}")
    
    # 保存更新后的podcast.json
    with open(podcast_json_path, 'w', encoding='utf-8') as f:
        json.dump(podcast_data, f, indent=2, ensure_ascii=False)
    
    print(f"Updated timestamps in {podcast_json_path}")
    return True