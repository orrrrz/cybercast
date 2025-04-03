import os
import backoff
import dotenv
import dashscope
from cybercast.tts.base_tts import BaseTTS
from dashscope.audio.tts_v2 import SpeechSynthesizer

dotenv.load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

class CosyVoiceTTS(BaseTTS):

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def generate_from_text(
        self, text: str, voice=None, model=None
    ):
            
        cached_path = self.check_cache(text, model, voice)
        if cached_path:
            return cached_path

        try:
            synthesizer = SpeechSynthesizer(model=model, voice=voice)
            audio = synthesizer.call(text)
            if audio is None:
                raise Exception("Failed to generate audio")
        
            audio_path = self.get_audio_path(text, model, voice)
            self.save_audio(audio, audio_path)
            return audio_path

        except Exception as e:
            raise Exception(
                "CosyVoice TTS gave an error. Please check your API key and internet connection."
            ) from e
