from pydantic_settings import SettingsConfigDict, BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str
    LLM: str = "openai/gpt-oss-120b"
    STT: str = "whisper-large-v3"
    TTS: str = "canopylabs/orpheus-v1-english"
    BASE_URL: str = "https://api.groq.com/openai/v1"
    TIMEOUT: int = 60

    # session limits (keep these equal to the frontend constants)
    MAX_PROMPT_CHARS: int = 2000
    MAX_FIELD_CHARS: int = 100  # role, field, interview type, difficulty, candidate name
    DEFAULT_QUESTION_COUNT: int = 5  # used when the questions are generated
    MAX_QUESTIONS: int = 20
    MAX_QUESTION_CHARS: int = 500
    MAX_FOLLOWUPS: int = 1       # follow-ups allowed per question
    MAX_CLARIFICATIONS: int = 1  # "unclear" replies + silence nudges allowed per question
    MAX_STAYS: int = 2           # follow-ups + repeats + clarifications before the server forces a move on
    CONFIG_TIMEOUT: int = 10     # seconds to wait for the first (config) message

    # TTS: Groq's Orpheus accepts at most 200 characters per request
    TTS_CHUNK_CHARS: int = 180
    TTS_LEAD_SILENCE_MS: int = 0  # set to ~250 if the first word of a reply is clipped on playback

    # STT junk filter. Starting values only: tune them against your own recordings.
    STT_LANGUAGE: str = "en"       # empty string = auto-detect
    STT_NO_SPEECH_MAX: float = 0.6  # a segment is dropped when no_speech_prob is above this ...
    STT_LOGPROB_MIN: float = -1.0   # ... AND avg_logprob is below this

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.GROQ_API_KEY}"}

    @property
    def json_headers(self) -> dict:
        return {**self.auth_headers, "Content-Type": "application/json"}


setting = Settings()
