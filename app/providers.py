"""STT/LLM/TTS factories selected by STT_PROVIDER / LLM_PROVIDER / TTS_PROVIDER.

STT gets the locale's full language (e.g. pt-BR); TTS gets the base language (e.g. pt),
since some TTS services (Cartesia) pass the code through unchanged and only accept the base.
"""

from app.config import Settings
from app.locales import Locale


def make_stt(s: Settings, locale: Locale):
    match s.stt_provider:
        case "deepgram":
            from pipecat.services.deepgram.stt import DeepgramSTTService

            return DeepgramSTTService(
                api_key=s.deepgram_api_key,
                settings=DeepgramSTTService.Settings(model="nova-3", language=locale.language),
            )
        case "openai":
            from pipecat.services.openai.stt import OpenAISTTService

            return OpenAISTTService(
                api_key=s.openai_api_key,
                settings=OpenAISTTService.Settings(model="gpt-4o-transcribe", language=locale.language),
            )
        case "groq":
            from pipecat.services.groq.stt import GroqSTTService

            return GroqSTTService(
                api_key=s.groq_api_key,
                settings=GroqSTTService.Settings(model="whisper-large-v3-turbo", language=locale.language),
            )
    raise ValueError(f"Unknown STT_PROVIDER: {s.stt_provider}")


def make_llm(s: Settings):
    match s.llm_provider:
        case "anthropic":
            from pipecat.services.anthropic.llm import AnthropicLLMService

            return AnthropicLLMService(
                api_key=s.anthropic_api_key,
                settings=AnthropicLLMService.Settings(model=s.llm_model or "claude-sonnet-5-5"),
            )
        case "openai":
            from pipecat.services.openai.llm import OpenAILLMService

            return OpenAILLMService(
                api_key=s.openai_api_key,
                settings=OpenAILLMService.Settings(model=s.llm_model or "gpt-4.1"),
            )
        case "google":
            from pipecat.services.google.llm import GoogleLLMService

            return GoogleLLMService(
                api_key=s.google_api_key,
                settings=GoogleLLMService.Settings(model=s.llm_model or "gemini-2.5-flash"),
            )
        case "groq":
            from pipecat.services.groq.llm import GroqLLMService

            model = s.llm_model or "openai/gpt-oss-120b"
            # Below "high", gpt-oss often answers a tool result with several turns glued together,
            # inventing the caller's replies ("Obrigado, [Nome]"). "high" costs ~0.7 s more.
            effort = "high" if model.startswith("openai/gpt-oss") else None
            return GroqLLMService(
                api_key=s.groq_api_key,
                settings=GroqLLMService.Settings(model=model, reasoning_effort=effort),
            )
    raise ValueError(f"Unknown LLM_PROVIDER: {s.llm_provider}")


def make_tts(s: Settings, locale: Locale):
    voice = s.tts_voice or locale.voices.get(s.tts_provider)
    if not voice:
        raise ValueError(f"No {s.tts_provider} voice for {locale.code}: set voices in locale.yaml or TTS_VOICE")
    match s.tts_provider:
        case "cartesia":
            from pipecat.services.cartesia.tts import CartesiaTTSService

            return CartesiaTTSService(
                api_key=s.cartesia_api_key,
                settings=CartesiaTTSService.Settings(model="sonic-2", voice=voice, language=locale.base_language),
            )
        case "elevenlabs":
            from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

            return ElevenLabsTTSService(
                api_key=s.elevenlabs_api_key,
                settings=ElevenLabsTTSService.Settings(
                    model="eleven_flash_v2_5", voice=voice, language=locale.base_language
                ),
            )
        case "openai":
            from pipecat.services.openai.tts import OpenAITTSService

            return OpenAITTSService(
                api_key=s.openai_api_key,
                settings=OpenAITTSService.Settings(
                    model="gpt-4o-mini-tts", voice=voice, instructions=locale.tts_instructions
                ),
            )
        case "groq":
            from pipecat.services.groq.tts import GroqTTSService

            return GroqTTSService(
                api_key=s.groq_api_key,
                settings=GroqTTSService.Settings(model="canopylabs/orpheus-v1-english", voice=voice),
            )
    raise ValueError(f"Unknown TTS_PROVIDER: {s.tts_provider}")
