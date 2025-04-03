import librosa
import numpy as np
import cv2
import subprocess
import os
import math
import tempfile
import shutil
import time
import multiprocessing # 导入并行处理模块

# --- 全局变量，用于工作进程初始化，避免重复传递大数据 ---
worker_audio_data = None
worker_params = {}

def init_worker(audio_data_global, params_global):
    """
    多进程池的初始化函数。
    将大的、只读的数据加载到每个工作进程的内存中一次。
    """
    global worker_audio_data, worker_params
    worker_audio_data = audio_data_global
    worker_params = params_global
    # print(f"工作进程 {os.getpid()} 初始化完毕。") # 用于调试

def process_frame(frame_n):
    """
    由每个工作进程执行的函数，用于生成单帧图像。
    
    这个版本创建的是固定 x 位置的正弦波曲线，y 值随音频变化。
    并在中心位置显示带圆形蒙版的头像。

    Args:
        frame_n (int): 需要处理的帧序号。

    Returns:
        tuple[int, np.ndarray]: 包含帧序号和生成的图像 NumPy 数组的元组。
                                返回帧序号是为了在主进程中排序。
    """
    # 从全局变量访问数据
    y = worker_audio_data
    params = worker_params
    sr = params['sr']
    width = params['width']
    height = params['height']
    fps = params['fps']
    background_bgr = params['background_bgr']
    waveform_bgr = params['waveform_bgr']
    avatar_img = params.get('avatar_img')
    total_samples = len(y)
    
    # 根据当前帧计算音频位置
    current_sample = int(frame_n * (total_samples / params['total_frames']))
    
    # 创建帧图像
    frame_image = np.full((height, width, 3), background_bgr, dtype=np.uint8)
    
    # 在固定位置创建正弦波曲线
    points = []
    
    # 定义波形需要采样的点数
    num_points = width
    
    # 计算中心线
    center_y = height // 2
    
    # 获取当前时间点的音频振幅
    if 0 <= current_sample < total_samples:
        amplitude = abs(y[current_sample]) * 4.0  # 放大振幅以使波形更加明显
        # 限制最大振幅为画面高度的40%
        max_amplitude = height * 0.4
        amplitude = min(amplitude * max_amplitude, max_amplitude)
    else:
        amplitude = 0
    
    # 生成正弦波的点
    for i in range(num_points):
        # 使用正弦函数创建波形
        # 根据x坐标变化正弦的相位
        phase = i / width * 8 * np.pi  # 控制波形周期数
        y_offset = int(amplitude * np.sin(phase))
        point_y = center_y + y_offset
        
        # 确保y坐标在图像范围内
        point_y = max(0, min(height - 1, point_y))
        points.append((i, point_y))
    
    # 绘制正弦波曲线
    if len(points) > 1:
        # 使用线条连接所有点
        for i in range(len(points) - 1):
            pt1 = points[i]
            pt2 = points[i + 1]
            cv2.line(frame_image, pt1, pt2, waveform_bgr, 2)  # 线宽为2
    
    # 如果有头像，在中心位置绘制带圆形蒙版的头像
    if avatar_img is not None:
        # 获取头像尺寸
        avatar_h, avatar_w = avatar_img.shape[:2]
        
        # 计算头像在视频中的位置（中心）
        avatar_size = min(height // 3, width // 3)  # 限制头像大小为视频尺寸的1/3
        avatar_resized = cv2.resize(avatar_img, (avatar_size, avatar_size), interpolation=cv2.INTER_AREA)
        
        # 创建圆形蒙版
        mask = np.zeros((avatar_size, avatar_size), dtype=np.uint8)
        center = (avatar_size // 2, avatar_size // 2)
        radius = avatar_size // 2
        cv2.circle(mask, center, radius, 255, -1)
        
        # 计算头像在视频中的位置
        x_offset = (width - avatar_size) // 2
        y_offset = (height - avatar_size) // 2
        
        # 应用圆形蒙版并合并头像到帧
        for c in range(0, 3):
            roi = frame_image[y_offset:y_offset+avatar_size, x_offset:x_offset+avatar_size, c]
            masked_avatar = cv2.bitwise_and(avatar_resized[:, :, c], avatar_resized[:, :, c], mask=mask)
            masked_roi = cv2.bitwise_and(roi, roi, mask=cv2.bitwise_not(mask))
            frame_image[y_offset:y_offset+avatar_size, x_offset:x_offset+avatar_size, c] = masked_roi + masked_avatar
    
    # 返回帧序号和图像数据
    return frame_n, frame_image

# --- hex_to_bgr 函数保持不变 ---
def hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    """
    将十六进制颜色代码 (例如 "#RRGGBB") 转换为 OpenCV 使用的 BGR 元组。
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f"无效的十六进制颜色格式: {hex_color}")
    try:
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (rgb[2], rgb[1], rgb[0]) # OpenCV 使用 BGR 顺序
    except ValueError:
        raise ValueError(f"无法将十六进制转换为整数: {hex_color}")

def create_animated_waveform_video_parallel(
    mp3_path: str,
    output_video_path: str,
    avatar_path: str = None,
    color_hex: str = "#00FF00",
    background_color_hex: str = "#000000",
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    bar_width: int = 4,  # 保留参数但不再使用
    gap_width: int = 1,  # 保留参数但不再使用
    waveform_window_sec: float = 0.5,  # 保留参数但不再使用
    ffmpeg_path: str = "ffmpeg",
    num_workers: int | None = None # 新增：允许指定工作进程数
) -> None:
    """
    (并行版本) 从 MP3 文件生成带有正弦波曲线波形图的视频，x 轴固定，y 值随音频变化。
    可以在视频中心位置显示带圆形蒙版的头像。

    Args:
        mp3_path (str): 输入 MP3 文件路径。
        output_video_path (str): 输出视频文件路径。
        avatar_path (str, optional): 主播头像路径，如果提供则在视频中心显示带圆形蒙版的头像。
        color_hex (str, optional): 波形颜色的十六进制代码。默认为 "#00FF00"（绿色）。
        background_color_hex (str, optional): 背景颜色的十六进制代码。默认为 "#000000"（黑色）。
        width (int, optional): 视频宽度（像素）。默认为 1280。
        height (int, optional): 视频高度（像素）。默认为 720。
        fps (int, optional): 帧率。默认为 30。
        ffmpeg_path (str, optional): ffmpeg 可执行文件路径。默认为 "ffmpeg"。
        num_workers (int | None, optional): 用于生成帧的工作进程数。
                                           如果为 None, 会尝试使用 CPU 核心数减 1。
                                           如果为 1, 则等同于顺序执行。默认为 None。
    """
    # --- 0. 检查依赖 ---
    if not shutil.which(ffmpeg_path):
        raise FileNotFoundError(f"ffmpeg 未找到: {ffmpeg_path}")
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"MP3 文件未找到: {mp3_path}")

    # --- 1. 转换颜色和加载音频 ---
    try:
        waveform_bgr = hex_to_bgr(color_hex)
        background_bgr = hex_to_bgr(background_color_hex)
    except ValueError as e:
        raise ValueError(f"颜色格式错误: {e}")

    print(f"正在加载音频文件: {mp3_path}...")
    start_load_time = time.time()
    try:
        y, sr = librosa.load(mp3_path, sr=None, mono=True)
    except Exception as e:
        raise RuntimeError(f"使用 librosa 加载音频失败: {e}")

    duration = librosa.get_duration(y=y, sr=sr)
    print(f"音频加载完成: 时长={duration:.2f}s, 采样率={sr}Hz (耗时 {time.time() - start_load_time:.2f}s)")

    if duration <= 0: raise ValueError("音频时长必须大于 0")

    total_samples = len(y)
    total_frames = int(duration * fps)

    # 加载头像（如果提供）
    avatar_img = None
    if avatar_path and os.path.exists(avatar_path):
        try:
            print(f"正在加载头像: {avatar_path}")
            avatar_img = cv2.imread(avatar_path)
            if avatar_img is None:
                print(f"警告: 无法加载头像 {avatar_path}")
            else:
                # 转换为 BGR 格式（如果需要）
                if len(avatar_img.shape) == 2:  # 灰度图
                    avatar_img = cv2.cvtColor(avatar_img, cv2.COLOR_GRAY2BGR)
                elif avatar_img.shape[2] == 4:  # 带 alpha 通道
                    # 如果图像有 alpha 通道，提取 RGB 部分
                    avatar_img = avatar_img[:, :, :3]
        except Exception as e:
            print(f"警告: 加载头像时出错: {e}")
            avatar_img = None

    # --- 准备工作进程所需参数 ---
    params = {
        'sr': sr, 'width': width, 'height': height, 'fps': fps,
        'background_bgr': background_bgr, 'waveform_bgr': waveform_bgr,
        'total_frames': total_frames,
        'avatar_img': avatar_img
    }

    # --- 2. 初始化视频写入器 (无声) 和进程池 ---
    temp_video_file = None
    video_writer = None
    pool = None # 初始化 pool 变量

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_f:
            temp_video_file = tmp_f.name
        print(f"创建临时无声视频文件: {temp_video_file}")

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(temp_video_file, fourcc, float(fps), (width, height))
        if not video_writer.isOpened():
             raise RuntimeError("无法打开视频写入器。")

        # 确定工作进程数
        if num_workers is None:
            cpu_count = os.cpu_count() or 1
            num_workers = max(1, cpu_count - 1) # 留一个核心给主进程/系统
        num_workers = max(1, num_workers) # 至少一个进程

        print(f"使用 {num_workers} 个工作进程进行帧生成...")

        # 创建进程池，使用 initializer 传递共享数据
        pool = multiprocessing.Pool(processes=num_workers,
                                    initializer=init_worker,
                                    initargs=(y, params)) # y 是大的音频数据

        # --- 3. 并行生成帧并顺序写入 ---
        frame_buffer = {}           # 存储已生成但未写入的帧 {frame_n: frame_data}
        next_frame_to_write = 0     # 下一个需要写入的帧序号
        frames_written = 0          # 已写入的帧数
        start_frame_gen_time = time.time()
        last_print_time = time.time()

        print(f"开始并行生成 {total_frames} 帧...")

        # 使用 imap_unordered 获取结果，提高效率
        results_iterator = pool.imap_unordered(process_frame, range(total_frames), chunksize=max(1, total_frames // (num_workers * 4)))

        while frames_written < total_frames:
            try:
                # 从迭代器获取下一个结果
                try:
                    # 在 Python 3 中使用 next() 而不是 .next()
                    frame_n, frame_data = next(results_iterator)
                    frame_buffer[frame_n] = frame_data # 存入缓冲区
                except StopIteration:
                    # 所有任务都已提交且处理完成
                    print("\n所有工作进程任务都已完成。")
                    break
            except Exception as e:
                print(f"\n处理帧结果时出错: {e}")
                raise e

            # 检查缓冲区，写入所有按顺序准备好的帧
            while next_frame_to_write in frame_buffer:
                frame_to_write = frame_buffer.pop(next_frame_to_write)
                video_writer.write(frame_to_write)
                frames_written += 1
                next_frame_to_write += 1

                # 更新进度显示
                current_time = time.time()
                if current_time - last_print_time >= 1.0 or frames_written == total_frames:
                    elapsed = current_time - start_frame_gen_time
                    progress = frames_written / total_frames
                    eta = (elapsed / progress) * (1 - progress) if progress > 0 else 0
                    print(f"  写入帧: {frames_written}/{total_frames} ({progress:.1%}), "
                          f"已耗时: {elapsed:.1f}s, 预计剩余: {eta:.1f}s", end='\r')
                    last_print_time = current_time
        
        # 处理缓冲区中剩余的帧
        if frames_written < total_frames and frame_buffer:
            print("\n处理剩余帧缓冲区...")
            # 尝试按顺序处理尽可能多的帧
            while next_frame_to_write in frame_buffer and frames_written < total_frames:
                frame_to_write = frame_buffer.pop(next_frame_to_write)
                video_writer.write(frame_to_write)
                frames_written += 1
                next_frame_to_write += 1

        # 结束进度显示
        print()

        if frames_written != total_frames:
            # 如果发生这种情况，说明逻辑可能有问题
            raise RuntimeError(f"处理完成，但只写入了 {frames_written}/{total_frames} 帧！")

        print(f"帧生成和写入完成。总耗时: {time.time() - start_frame_gen_time:.2f}s")

    except Exception as e:
        print(f"\n并行处理过程中发生错误: {e}")
        if pool:
            print("正在终止工作进程...")
            pool.terminate() # 强制终止所有工作进程
            pool.join()
        raise e # 重新抛出异常
    finally:
        # 确保资源被释放
        if pool:
            pool.close()
            pool.join()
            print("工作进程池已关闭。")
        if video_writer is not None and video_writer.isOpened():
            video_writer.release()
            print("无声视频写入器已释放。")

    # --- 4. 使用 ffmpeg 合并音频和无声视频 (与之前相同) ---
    print(f"正在使用 ffmpeg 将音频合并到视频中...")
    start_merge_time = time.time()
    cmd = [
        ffmpeg_path, '-i', temp_video_file, '-i', mp3_path,
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-y',
        output_video_path
    ]
    process = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding='utf-8')

    if process.returncode != 0:
        print("--- ffmpeg 合并时 标准错误 ---")
        print(process.stderr)
        print("--- ffmpeg 合并时 标准输出 ---")
        print(process.stdout)
        print(f"警告: ffmpeg 合并失败。临时无声视频文件保留在: {temp_video_file}")
        raise RuntimeError(f"ffmpeg 合并失败，返回码: {process.returncode}")
    else:
        print(f"音频视频合并成功！合并耗时: {time.time() - start_merge_time:.2f}s")
        # --- 5. 清理临时文件 ---
        if temp_video_file and os.path.exists(temp_video_file):
            try:
                os.remove(temp_video_file)
                print(f"已清理临时无声视频文件: {temp_video_file}")
            except OSError as e:
                print(f"警告: 无法删除临时文件 {temp_video_file}: {e}")

# --- 示例用法 ---
if __name__ == "__main__":
    # !!! 必须将 multiprocessing 相关代码放在此保护块内 !!!
    multiprocessing.freeze_support() # 对 Windows 打包成 exe 可能需要


    mp3_file = "output/podcast.mp3"
    output_file = "output/podcast.mp4"
    # 可选头像文件
    avatar_file = None  # 如果有头像，将这里改为头像文件路径

    try:
        print("\n开始生成动态波形视频 (并行版本)...")
        overall_start_time = time.time()
        create_animated_waveform_video_parallel(
            mp3_path=mp3_file,
            output_video_path=output_file,
            avatar_path=avatar_file,  # 传递头像路径
            color_hex="#00FFFF", # 青色
            background_color_hex="#333333", # 深灰色
            width=1280,
            height=720,
            fps=30,
            bar_width=4,
            gap_width=1,
            waveform_window_sec=0.4,
            num_workers=None # 自动检测 CPU 核心数
            # num_workers=1 # 设置为 1 可以对比顺序执行的速度
        )
        overall_end_time = time.time()
        print(f"\n测试完成！总耗时: {overall_end_time - overall_start_time:.2f}s")
        print(f"视频文件应该在: {output_file}")

    except Exception as e:
        print(f"\n生成视频时出错: {e}")
        import traceback
        traceback.print_exc() # 打印详细错误堆栈

        # finally:
        #     shutil.rmtree(test_dir)
        #     print(f"测试目录 {test_dir} 已删除。")
