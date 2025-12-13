from decouple import config


GEMINI_MODEL = config("GEMINI_MODEL", cast=str)
GEMINI_API_KEY = config("GEMINI_API_KEY", cast=str)
