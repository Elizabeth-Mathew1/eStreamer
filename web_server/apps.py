from fastapi import FastAPI


def setup_app() -> FastAPI:
    return FastAPI()


app = setup_app()
