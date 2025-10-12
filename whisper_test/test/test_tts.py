# WIP tests for the tts.py file
import unittest
from os.path import exists, isfile, getsize, join
from tempfile import NamedTemporaryFile
from whisper_test.tts import TTSController
from whisper_test.common import TTS_PROVIDER_PIPER_EN_US_RYAN_HIGH, TTS_PROVIDER_PIPER_EN_US_LESSAC_MEDIUM

class TestTTS(unittest.TestCase):

    def setUp(self):
        self.tts = TTSController(verify_func=None)

    def test_audio_dirs(self):
        assert exists(self.tts.tts_audio_root_dir)
        assert exists(self.tts.tts_audio_dir)

    def test_generate_audio_from_text(self):

        with NamedTemporaryFile(
                suffix='.mp3', delete=False) as audio_file:
            audio_file_path = audio_file.name
            self.tts.generate_audio_from_text("Hello, World!", audio_file_path=audio_file_path)
            assert isfile(audio_file_path), "Audio file not found"
            assert getsize(audio_file_path) > 0, f"Audio file {audio_file_path} is empty"

    def test_hard_words(self):
        self.tts.say("rows")
        self.tts.say("choose")

    def test_say_all(self):
        assert self.tts.say(["Hello", "World"], verify=False)

    def test_say_choose(self):
        assert self.tts.say_choose("1", verify=False)

    def test_say_scroll(self):
        assert self.tts.say_scroll("up", verify=False)

    def test_say_show_grid(self):
        assert self.tts.say_show_grid(3, 3, verify=False)
        assert self.tts.say_show_grid(10, 15, verify=False)

    def test_say_swipe(self):
        assert self.tts.say_swipe("left", verify=False)

    def test_say_tap(self):
        assert self.tts.say_tap("1", verify=False)

    def test_lessac_scroll(self):
        # piper_en_US-lessac-mediumL: "scroll" and "swipe" are off
        tts = TTSController(tts_provider=TTS_PROVIDER_PIPER_EN_US_LESSAC_MEDIUM)
        tts.say('scroll')
        tts.say('swipe')

    def test_non_default_model(self):
        tts = TTSController(tts_provider=TTS_PROVIDER_PIPER_EN_US_RYAN_HIGH)
        assert tts.tts_provider == TTS_PROVIDER_PIPER_EN_US_RYAN_HIGH
        assert tts.tts_audio_dir == join(tts.tts_audio_root_dir, TTS_PROVIDER_PIPER_EN_US_RYAN_HIGH)
        assert tts.say("Hello, world", verify=False)
        assert exists(tts.tts_audio_dir)
        assert exists(tts.PIPER_BINARY_PATH)
