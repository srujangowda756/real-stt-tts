from pydantic_settings import SettingsConfigDict,BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str
    LLM: str = "openai/gpt-oss-120b"
    STT: str = "whisper-large-v3"
    TTS: str = "canopylabs/orpheus-v1-english"
    BASE_URL: str = "https://api.groq.com/openai/v1"    
    TIMEOUT: int = 60
    SYSTEM_PROMPT: str = (
    "You are a voice assistant. Reply in one or two short spoken sentences. only in english. dont respond to any other language"
    "No markdown, lists or emojis."
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    

    # config.py  (replace the headers property)
    @property
    def auth_headers(self) -> dict:
        # for multipart requests (STT): httpx sets Content-Type itself
        return {"Authorization": f"Bearer {self.GROQ_API_KEY}"}

    @property
    def json_headers(self) -> dict:
        return {**self.auth_headers, "Content-Type": "application/json"}
        
    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
setting=Settings() 