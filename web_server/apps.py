from fastapi import FastAPI
from routers import router


def setup_app() -> FastAPI:
    return FastAPI()


app = setup_app()


app.include_router(router=router)
