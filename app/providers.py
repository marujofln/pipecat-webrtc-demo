"""Factories de STT/LLM/TTS escolhidas por STT_PROVIDER / LLM_PROVIDER / TTS_PROVIDER."""

from pipecat.transcriptions.language import Language

from app.config import Settings


def make_stt(s: Settings):
    match s.stt_provider:
        case "deepgram":
            from pipecat.services.deepgram.stt import DeepgramSTTService

            return DeepgramSTTService(
                api_key=s.deepgram_api_key,
                settings=DeepgramSTTService.Settings(model="nova-3", language=Language.PT_BR),
            )
        case "openai":
            from pipecat.services.openai.stt import OpenAISTTService

            return OpenAISTTService(
                api_key=s.openai_api_key,
                settings=OpenAISTTService.Settings(model="gpt-4o-transcribe", language=Language.PT),
            )
    raise ValueError(f"STT_PROVIDER desconhecido: {s.stt_provider}")


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
    raise ValueError(f"LLM_PROVIDER desconhecido: {s.llm_provider}")


def make_tts(s: Settings):
    match s.tts_provider:
        case "cartesia":
            from pipecat.services.cartesia.tts import CartesiaTTSService

            return CartesiaTTSService(
                api_key=s.cartesia_api_key,
                settings=CartesiaTTSService.Settings(
                    model="sonic-2",
                    # Voz pt-BR do catálogo Cartesia; troque via TTS_VOICE.
                    voice=s.tts_voice or "700d1ee3-a641-4018-ba6e-899dcadc9e2b",
                    language=Language.PT,
                ),
            )
        case "elevenlabs":
            from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

            return ElevenLabsTTSService(
                api_key=s.elevenlabs_api_key,
                settings=ElevenLabsTTSService.Settings(
                    model="eleven_flash_v2_5",
                    voice=s.tts_voice or "21m00Tcm4TlvDq8ikWAM",
                    language=Language.PT,
                ),
            )
        case "openai":
            from pipecat.services.openai.tts import OpenAITTSService

            return OpenAITTSService(
                api_key=s.openai_api_key,
                settings=OpenAITTSService.Settings(model="gpt-4o-mini-tts", voice=s.tts_voice or "nova"),
            )
    raise ValueError(f"TTS_PROVIDER desconhecido: {s.tts_provider}")
