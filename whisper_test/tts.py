import os
import subprocess
from os.path import expanduser, join, basename
from time import sleep
from typing import List, Optional, Callable, Union

try:
    from gtts import gTTS
except ImportError:  # Not required for all users
    gTTS = None

from playsound import playsound
from whisper_test.common import (
    logger, DEFAULT_TTS_LANGUAGE, DEFAULT_TTS_PROVIDER, PIPER_MODELS,
    TTS_PROVIDER_GTTS, TTS_AUDIO_ROOT_DIR, MAX_N_VOICE_CMD_TRIES)


class TTSController:

    @staticmethod
    def get_piper_root_dir():
        """Get Piper root directory from config or use default."""
        from whisper_test.common import _config
        default_path = join(expanduser('~'), 'piper')
        return expanduser(_config.get('piper_root_dir', default_path))
    
    PIPER_ROOT_DIR = get_piper_root_dir()
    PIPER_BINARY_PATH = join(PIPER_ROOT_DIR, 'piper')


    KEEP_CHARS_IN_AUDIO_FNAME = ('.', ',', '_')
    AUDIO_FILE_EXT = '.wav'

    SLEEP_BTWN_MULTIPLE_VOICE_CMDS = 0.1

    def __init__(self, tts_provider: Optional[str] = DEFAULT_TTS_PROVIDER,
                 tts_audio_root_dir: Optional[str] = TTS_AUDIO_ROOT_DIR,
                 tts_language: Optional[str] = DEFAULT_TTS_LANGUAGE,
                 verify_func: Optional[Callable[[str], bool]] = None):
        """Initialize the TTS controller."""
        self.tts_provider = tts_provider
        self.tts_language = tts_language
        self.tts_audio_root_dir = tts_audio_root_dir
        self.tts_audio_dir = join(
            self.tts_audio_root_dir, self.tts_provider)
        self.create_audio_dirs()
        # optional: verify voice command success (using system logs)
        self.verify_func = verify_func

    def create_audio_dirs(self) -> None:
        """Create the audio directories for the given TTS provider."""
        os.makedirs(self.tts_audio_root_dir, exist_ok=True)
        os.makedirs(self.tts_audio_dir, exist_ok=True)

    def generate_audio_from_text(self, text: str, audio_file_path: str) -> None:
        """Call the TTS provider to convert text to speech."""
        if self.tts_provider == TTS_PROVIDER_GTTS:
            if not gTTS:
                raise ImportError("gTTS is not installed")
            tts = gTTS(text=text, lang=self.tts_language)
            tts.save(audio_file_path)
        elif self.tts_provider in PIPER_MODELS:
            model_name = self.tts_provider.split('piper_')[1]
            model_path = join(self.get_piper_root_dir(), f'{model_name}.onnx')

            subprocess.run(
                [
                    "piper",
                    "--model", model_path,
                    "--output_file", audio_file_path,
                    "--noise_scale", "0",
                    "--noise_w", "0",
                    "--sentence_silence", "0",
                ],
                input=text,
                capture_output=True, text=True, check=True
            )
        else:
            raise ValueError(f"Unknown TTS provider: {self.tts_provider}")

    def _get_audio_filename(self, phrase: str) -> str:
        """Generate a valid filename for the audio file."""
        phrase = phrase.replace(" ", "_")
        sanitized_phrase = "".join(
            c for c in phrase if c.isalnum() or c in self.KEEP_CHARS_IN_AUDIO_FNAME
        ).rstrip()
        return (sanitized_phrase + self.AUDIO_FILE_EXT).lower()

    def _get_audio_path(self, text: str) -> str:
        """Get the audio path for the given text."""
        audio_filename = self._get_audio_filename(text)
        return join(self.tts_audio_dir, audio_filename)

    def append_comma(self, phrase: str) -> str:
        """Append a comma to the phrase if it doesn't end with one."""
        if phrase.endswith(", "):
            return phrase
        # logger.info("Appended ', ' for better audio synthesis '%s'", phrase)
        return phrase + ", "

    def text_to_speech(self, phrase: str, play_sound: bool = True) -> bool:
        """Convert text to speech and optionally play the audio."""
        TTS_APPEND_COMMA_SINGLE_PHRASE = True
        audio_file_path = self._get_audio_path(phrase)
        if TTS_APPEND_COMMA_SINGLE_PHRASE:
            tts_phrase = self.append_comma(phrase)
        else:
            tts_phrase = phrase

        if not os.path.exists(audio_file_path):
            try:
                self.generate_audio_from_text(tts_phrase, audio_file_path)
            except Exception as e:
                logger.error("❌ Error generating the audio for phrase %s: %s", phrase, e)
                return False

        if play_sound:
            return self.play_audio(audio_file_path)

    def play_audio(self, audio_file_path: str) -> bool:
        """Play the audio file."""
        try:
            logger.info("🗣 Playing the audio file %s", basename(audio_file_path))
            playsound(audio_file_path)
            return True
        except Exception as e:
            logger.error("❌ Error playing the audio file %s: %s", basename(audio_file_path), e)
            return False




    def say(self, phrases: Union[str, List[str]], verify: bool = True,
            n_max_tries: int = MAX_N_VOICE_CMD_TRIES, verify_as_whole: bool = True) -> bool:
        """Send a voice command or multiple commands with retry and optional verification."""
        if isinstance(phrases, str):
            phrases = [phrases]

        for attempt in range(n_max_tries):
            all_said = True

            for phrase_index, phrase in enumerate(phrases):
                # only verify the last phrase if verify_as_whole is True
                verify_part = verify and not verify_as_whole

                if not self.text_to_speech(phrase):
                    all_said = False
                    break

                if verify_part and self.verify_func and not self.verify_func(phrase):
                    all_said = False
                    break

                if phrase_index < len(phrases) - 1:  # Only sleep between phrases, not after the last one
                    sleep(self.SLEEP_BTWN_MULTIPLE_VOICE_CMDS)

            if all_said:
                if not verify or not self.verify_func:
                    return True

                if verify and verify_as_whole and self.verify_func:
                    whole_cmd = " ".join(phrases)
                    logger.info("Verifying the whole command... '%s'", whole_cmd)
                    if self.verify_func(whole_cmd):
                        return True
                    all_said = False

            if not all_said and attempt < n_max_tries - 1:
                logger.info("Retrying the whole sequence... (%d/%d)", attempt + 1, n_max_tries)
                sleep(self.SLEEP_BTWN_MULTIPLE_VOICE_CMDS)

        return all_said


    # Higher-level voice command methods
    def say_tap(self, x: str, **kwargs) -> bool:
        return self.say(["Tap", x], **kwargs)

    def say_choose(self, x: str, **kwargs) -> bool:
        return self.say(["Choose", x], **kwargs)

    def say_swipe(self, direction: str, **kwargs) -> bool:
        assert direction.lower() in ('left', 'right', 'up', 'down')
        return self.say(f"Swipe, {direction}", **kwargs)

    def say_scroll(self, direction: str, **kwargs) -> bool:
        assert direction.lower() in ('up', 'down', 'left', 'right')
        return self.say(f"Scroll, {direction}", **kwargs)

    def say_show_grid(self, columns: int = 0, rows: int = 0, **kwargs) -> bool:
        if columns == 0 and rows == 0:
            return self.say("Show grid", **kwargs)
        else:
            return self.say(["Show grid with", str(columns),
                         "columns and", str(rows), "rows"], **kwargs)

    def say_select(self, x: str, **kwargs) -> bool:
        return self.say(["Select", x], **kwargs)

    def say_type_phrase(self, x: str, **kwargs) -> bool:
        return self.say(["Type", x], **kwargs)

    def say_press_key(self, x: str, **kwargs) -> bool:
        return self.say(["Press", x, "key"], **kwargs)

    def say_drag(self, x: str, y: str, **kwargs) -> bool:
        return self.say(["Drag", x, "to", y], **kwargs)

    def say_start_drag(self, x: str, **kwargs) -> bool:
        return self.say(["Start drag", x], **kwargs)

    def say_drop(self, x: str, **kwargs) -> None:
        return self.say(["Drop,", x], **kwargs)

    def say_tap_and_hold(self, x: str, **kwargs) -> None:
        return self.say(["Tap and hold", x], **kwargs)

    def say_emoji(self, x: str, **kwargs) -> None:
        return self.say([x, "emoji"], **kwargs)

    def say_decrement(self, x: str, count: int = 0, **kwargs) -> None:
        if count == 0:
            return self.say(["Decrement", x], **kwargs)
        else:
            return self.say(["Decrement", x, "by", str(count)], **kwargs)

    def say_increment(self, x: str, count: int = 0, **kwargs) -> None:
        if count == 0:
            return self.say(["Increment", x], **kwargs)
        else:
            return self.say(["Increment", x, "by", str(count)], **kwargs)
