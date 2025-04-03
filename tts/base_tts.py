import os
import dotenv
import hashlib

dotenv.load_dotenv()

class BaseTTS:
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir
        if self.cache_dir is None:
            self.cache_dir = os.getenv("TTS_CACHE_DIR")

        print(f"TTS cache dir: {self.cache_dir}")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get_audio_path(self, text: str, model: str, voice: str = None) -> str:
        assert text is not None and model is not None, "Invalid text or model."
        cache_key = text + model
        if voice:
            cache_key += voice
        return os.path.join(self.cache_dir, f"{self.gen_text_hash(cache_key)}.mp3")

    def save_audio(self, audio_data: bytes, path: str):
        with open(path, "wb") as f:
            f.write(audio_data)

    def gen_text_hash(self, text: str, length: int = 16) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:length]
        
    def generate_from_text(self, text: str, **kwargs):
        raise NotImplementedError("Subclasses must implement generate_from_text method")
        
    def check_cache(self, text: str, model: str, voice: str = None) -> str:
        
        assert text is not None and model is not None, "Invalid text or model."
        cache_key = text + model
        if voice:
            cache_key += voice
        
        output_path = os.path.join(self.cache_dir, f"{self.gen_text_hash(cache_key)}.mp3")
        if os.path.exists(output_path):
            return output_path
        return None
