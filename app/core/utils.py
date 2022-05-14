from starlette.requests import Request
from core.db import SessionLocal
async def get_db(request:Request):
    yield SessionLocal
    

    
