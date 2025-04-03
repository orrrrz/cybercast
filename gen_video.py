import os
import tempfile
import argparse
import subprocess
from cybercast.utils.common_utils import load_json
from cybercast.utils.waveform_utils import create_animated_waveform_video_parallel

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", type=str, default="earthquake")


def gen_video():
    args = parser.parse_args()

    task_dir = os.path.join("data/tasks", args.name)
    config_path = os.path.join(task_dir, "config.json")
    config = load_json(config_path)
    mc_data = config["mcs"]

    podcast_scripts = load_json(os.path.join(task_dir, "podcast.json"))

    temp_video_dir = os.path.join(task_dir, "videos")
    os.makedirs(temp_video_dir, exist_ok=True)

    video_mp4s = []
    default_colors = ["#FF6B6B", "#4ECDC4", "#FF6B6B", "#4ECDC4"]
    for i, transcript in enumerate(podcast_scripts):
        mp3_path = transcript["audio_path"]
        mc_name = transcript["mc"]
        color = mc_data[mc_name].get("wave_color", default_colors[i % len(default_colors)])
        
        # 获取主播头像路径
        avatar_path = None
        if mc_name in mc_data:
            avatar_path = os.path.join(task_dir, mc_data[mc_name].get("avatar"))
            if avatar_path and not os.path.exists(avatar_path):
                print(f"警告: 头像文件不存在: {avatar_path}")
                avatar_path = None

        mp4_path = os.path.join(temp_video_dir, f"fragment_{i}.mp4")
        if os.path.exists(mp4_path):
            video_mp4s.append(mp4_path)
            continue

        create_animated_waveform_video_parallel(
            mp3_path=mp3_path,
            output_video_path=mp4_path,
            avatar_path=avatar_path,  # 添加头像路径
            color_hex=color,
            background_color_hex="#333333",
            width=config.get("video_width", 1280),
            height=config.get("video_height", 960),
            fps=30,
            bar_width=4,
            gap_width=1,
            waveform_window_sec=0.4,
            num_workers=None # 自动检测 CPU 核心数
        )

        if os.path.exists(mp4_path):
            print(f"视频生成成功: {mp4_path}")
            video_mp4s.append(mp4_path)
        else:
            print(f"视频生成失败: {mp4_path}")

    if len(video_mp4s) != len(podcast_scripts):
        raise Exception(f"视频生成失败: {len(video_mp4s)} != {len(podcast_scripts)}")

    # merge all video_mp4s into one file
    merge_video_mp4s(video_mp4s, os.path.join(task_dir, f"{args.name}.mp4"))
    return video_mp4s

def merge_video_mp4s(video_mp4s, output_video_path):
    """
    使用ffmpeg合并多个MP4视频文件为一个视频文件
    
    Args:
        video_mp4s (list): 要合并的视频文件路径列表
        output_video_path (str): 输出视频的文件路径
    
    Returns:
        bool: 合并是否成功
    """
    if not video_mp4s:
        raise ValueError("视频列表不能为空")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    video_list_file = os.path.join(temp_dir, "video_list.txt")
    
    try:
        # 为每个视频创建一个没有音频的版本
        silent_videos = []
        audio_files = []
        
        for i, video_file in enumerate(video_mp4s):
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"找不到视频文件: {video_file}")
            
            # 提取没有音频的视频
            silent_video = os.path.join(temp_dir, f"silent_{i}.mp4")
            silent_videos.append(silent_video)
            
            # 提取音频为WAV格式
            audio_file = os.path.join(temp_dir, f"audio_{i}.wav")
            audio_files.append(audio_file)
            
            # 提取没有音频的视频
            subprocess.run([
                "ffmpeg", "-i", video_file, "-c:v", "copy", "-an", "-y", silent_video
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 提取音频为WAV格式
            subprocess.run([
                "ffmpeg", "-i", video_file, "-vn", "-acodec", "pcm_s16le", "-y", audio_file
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 创建静音视频列表文件
        with open(video_list_file, "w") as f:
            for video in silent_videos:
                f.write(f"file '{os.path.abspath(video)}'\n")
        
        # 合并没有音频的视频
        temp_video = os.path.join(temp_dir, "temp_video.mp4")
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", video_list_file, 
            "-c", "copy", "-y", temp_video
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 合并音频文件
        temp_audio = os.path.join(temp_dir, "temp_audio.wav")
        audio_inputs = []
        for audio_file in audio_files:
            audio_inputs.extend(["-i", audio_file])
        
        # 使用filter_complex合并音频
        filter_complex = ""
        for i in range(len(audio_files)):
            filter_complex += f"[{i}:0]"
        filter_complex += f"concat=n={len(audio_files)}:v=0:a=1[outa]"
        
        subprocess.run([
            "ffmpeg", *audio_inputs, "-filter_complex", filter_complex, 
            "-map", "[outa]", "-y", temp_audio
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 最后，将合并的视频和音频组合在一起
        subprocess.run([
            "ffmpeg", "-i", temp_video, "-i", temp_audio, "-c:v", "copy", 
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-y", output_video_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"视频合并成功: {output_video_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"视频合并失败，错误代码: {e.returncode}")
        print(f"错误输出: {e.stderr}")
        return False
    finally:
        # 清理临时文件
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    gen_video()