import os
import json
import argparse
from tqdm import tqdm
from tts import SambertTTS, CosyVoiceTTS
from utils.common_utils import *
from utils.audio_utils import *
parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", type=str, required=True, help="podcast name")
parser.add_argument("--transcript", type=str, default=None)
parser.add_argument("--mc", type=str, default=None)
parser.add_argument("--output", type=str, default=None)
parser.add_argument("--play", type=bool, default=False)

def main():
    args = parser.parse_args()

    # create a task folder
    task_dir = get_task_dir(args.name)

    # load the mc file
    config_path = os.path.join(task_dir, "config.json")
    config = load_json(config_path)

    # load the transcript file
    if args.transcript is None:
        args.transcript = os.path.join(task_dir, "transcript.txt")

    tts_model = SambertTTS()
    mcs = config["mcs"]
    transcript = load_transcript(args.transcript)

    if args.output is None:
        output_path = os.path.join(task_dir, "podcast.mp3")
    else:
        output_path = args.output

    if os.path.exists(output_path):
        os.remove(output_path)

    podcast_meta_path = os.path.join(task_dir, "podcast.json")

    if os.path.exists(podcast_meta_path):
        os.remove(podcast_meta_path)


    for name in mcs:
        tts = mcs[name]["tts"]
        params = {}
        if tts == "cosyvoice":
            tts_model = CosyVoiceTTS(os.path.join(task_dir, "tts"))
            params["model"] = mcs[name]["model"]
            params["voice"] = mcs[name]["voice"]
        elif tts == "sambert":
            tts_model = SambertTTS(os.path.join(task_dir, "tts"))
            params["model"] = mcs[name]["model"]
        else:
            raise ValueError(f"Unknown TTS: {tts}")
        mcs[name]["tts_model"] = tts_model
        mcs[name]["tts_params"] = params
    ts = 0
    audio_file_list = []
    for item in tqdm(transcript):
        mc = item["mc"]
        line = item["line"]
        item["avatar"] = mcs[mc]["avatar"]

        if mc not in mcs:
            print(f"Skipping unknown MC: {mc}")
            continue

        audio_path = mcs[mc]["tts_model"].generate_from_text(line, **mcs[mc]["tts_params"])
        if audio_path is None:
            print(f"Failed to generate audio for {mc}: {line}")
            break
        item["ts"] = ts
        item["audio_path"] = audio_path
        ts += get_mp3_duration(audio_path)
        audio_file_list.append(audio_path)
    
    if len(audio_file_list) != len(transcript):
        print(f"Failed to generate audio for some lines. Please check the transcript_with_audio.txt file.")
        return
    else:
        with open(podcast_meta_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(transcript, indent=2, ensure_ascii=False))

        concat_file = os.path.join(task_dir, "audio_file_list.txt")
        write_concat_file(audio_file_list, concat_file)
        concat_audios(concat_file, output_path)

        if os.path.exists(output_path):
            print(f"Podcast saved to {output_path}")
            
            # 更新podcast.json中的时间戳
            segments_json = os.path.splitext(output_path)[0] + "_segments.json"
            if os.path.exists(segments_json):
                print("Updating timestamps in podcast.json...")
                update_podcast_timestamps(podcast_meta_path, segments_json)
            
            if args.play:
                os.system(f"ffplay -autoexit -nodisp {output_path}")
        else:
            print("Failed to save podcast")


if __name__ == "__main__":
    main()
