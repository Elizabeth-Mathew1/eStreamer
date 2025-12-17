from decouple import config


GEMINI_MODEL = config("GEMINI_MODEL", cast=str)
GEMINI_API_KEY = config("GEMINI_API_KEY", cast=str)
COLLECTION_NAME = config("COLLECTION_NAME", cast=str)
FIRESTORE_DB_NAME = config("FIRESTORE_DB_NAME", cast=str)
