# coding: utf-8

import os
import subprocess
import json


def format_time(seconds):
    """将秒数格式化为 HH:MM:SS 格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"

def get_mp3_duration(mp3_path: str) -> float:
    """Get duration of an MP3 file in seconds using ffmpeg"""
    cmd = ['ffmpeg', '-i', mp3_path, '-hide_banner']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Extract duration from ffmpeg output
        for line in result.stderr.split('\n'):
            if 'Duration:' in line:
                time_str = line.split('Duration:')[1].split(',')[0].strip()
                h, m, s = map(float, time_str.split(':'))
                return h * 3600 + m * 60 + s
    except Exception as e:
        print(f"Error getting duration for {mp3_path}: {e}")
    return 0.0

def concat_audios(concat_file: str, output_path: str):
    """Merge multiple MP3 files into one"""
    # 先验证合并列表文件存在且非空
    if not os.path.exists(concat_file):
        print(f"Error: Concat file {concat_file} does not exist")
        return False
    
    # 读取并验证文件内容
    with open(concat_file, 'r') as f:
        content = f.read().strip()
    
    if not content:
        print(f"Error: Concat file {concat_file} is empty")
        return False
        
    # 验证文件格式是否正确并提取文件路径
    valid_lines = []
    audio_files = []
    lines = content.split('\n')
    for line in lines:
        if not line.strip():
            continue
        if not line.startswith('file '):
            print(f"Error: Line '{line}' in concat file does not follow format 'file PATH'")
            return False
        valid_lines.append(line)
        # 提取文件路径
        file_path = line[5:].strip().strip("'\"")
        audio_files.append(file_path)
    
    if not valid_lines:
        print("Error: No valid audio files found in concat file")
        return False
        
    # 重写concat文件，确保只包含有效行
    with open(concat_file, 'w', encoding='utf-8') as f:
        for line in valid_lines:
            f.write(f"{line}\n")

    # 创建临时的元数据文件，用于添加章节标记
    metadata_file = concat_file + ".metadata"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        f.write(";FFMETADATA1\n")  # 必需的元数据头部
        
        # 为每个音频文件创建一个章节标记
        # 我们无法预先知道合并后的时间点，所以先用占位符
        # 稍后我们将使用ffprobe来获取实际的章节时间
        for i, audio_file in enumerate(audio_files):
            file_name = os.path.basename(audio_file)
            f.write(f"[CHAPTER]\nTIMEBASE=1/1000\n")
            f.write(f"START=0\n")  # 这是占位符
            f.write(f"END=0\n")    # 这是占位符
            f.write(f"title=Segment {i+1}: {file_name}\n\n")
    
    # 先执行音频合并
    temp_output = output_path + ".temp.mp3"
    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-ar', '44100',       # 采样率
        '-ac', '2',           # 双声道
        '-b:a', '192k',       # 比特率
        temp_output
    ]

    print(f"FFMPEG concatenation command:")
    print(' '.join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, stderr=subprocess.PIPE, text=True)
        print(f"Successfully merged audio files")
        
        # 使用ffprobe分析每个原始音频文件，获取实际时长
        segments_info = []
        current_position = 0.0
        
        print("\nAnalyzing segments:")
        print("-----------------------")
        
        # 重新创建元数据文件，这次带有真实时间点
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(";FFMETADATA1\n")  # 必需的元数据头部
            
            for i, audio_file in enumerate(audio_files):
                duration = get_mp3_duration(audio_file)
                start_time = current_position
                end_time = start_time + duration
                
                file_name = os.path.basename(audio_file)
                
                # 写入章节信息
                f.write(f"[CHAPTER]\nTIMEBASE=1/1000\n")
                f.write(f"START={int(start_time*1000)}\n")
                f.write(f"END={int(end_time*1000)}\n")
                f.write(f"title=Segment {i+1}: {file_name}\n\n")
                
                # 格式化为 HH:MM:SS 格式
                start_formatted = format_time(start_time)
                end_formatted = format_time(end_time)
                
                segment_info = {
                    "index": i,
                    "file": file_name,
                    "full_path": audio_file,
                    "original_duration": duration,
                    "start_time": start_time,
                    "end_time": end_time,
                    "start_formatted": start_formatted,
                    "end_formatted": end_formatted
                }
                
                segments_info.append(segment_info)
                current_position = end_time
                
                print(f"Segment {i+1}: {file_name}")
                print(f"  Duration: {format_time(duration)}")
                print(f"  Position: {start_formatted} - {end_formatted}")
        
        print("-----------------------")
        print(f"Total estimated duration: {format_time(current_position)}")
        
        # 将章节元数据添加到合并后的音频
        cmd = [
            'ffmpeg', '-y',
            '-i', temp_output,
            '-i', metadata_file,
            '-map_metadata', '1',
            '-codec', 'copy',
            output_path
        ]
        
        print(f"\nAdding chapter markers:")
        print(' '.join(cmd))
        
        result = subprocess.run(cmd, check=True, stderr=subprocess.PIPE, text=True)
        
        # 删除临时文件
        if os.path.exists(temp_output):
            os.remove(temp_output)
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
            
        # 获取最终输出文件的实际时长
        final_duration = get_mp3_duration(output_path)
        
        # 如果预估时长与实际时长差异较大（超过1秒），打印警告
        if abs(final_duration - current_position) > 1.0:
            print(f"\nWarning: Estimated duration ({format_time(current_position)}) differs from actual duration ({format_time(final_duration)})")
            print("Segment timestamps may not be fully accurate due to re-encoding.")
            
        print(f"\nSuccessfully created merged audio with chapter markers: {output_path}")
        print(f"Final duration: {format_time(final_duration)}")
        
        # 保存片段信息到JSON文件
        segments_json = os.path.splitext(output_path)[0] + "_segments.json"
        with open(segments_json, 'w', encoding='utf-8') as f:
            json.dump(segments_info, f, indent=2)
        print(f"Segments timeline saved to {segments_json}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error processing audio files: {e}")
        print(f"FFMPEG stderr: {e.stderr}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        return False