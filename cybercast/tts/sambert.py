import os
import backoff
from dashscope.audio.tts import SpeechSynthesizer
from cybercast.tts.base_tts import BaseTTS

class SambertTTS(BaseTTS):

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def generate_from_text(
        self, text: str, model: str
    ):
        cached_path = self.check_cache(text, model)
        if cached_path:
            return cached_path
            
        result = SpeechSynthesizer.call(model=model,
                                    text=text,
                                    sample_rate=48000,
                                    format='mp3')
        if result.get_audio_data() is None:
            raise Exception("Failed to generate audio")
        output_path = self.get_audio_path(text, model)
        self.save_audio(result.get_audio_data(), output_path)
        return output_path
