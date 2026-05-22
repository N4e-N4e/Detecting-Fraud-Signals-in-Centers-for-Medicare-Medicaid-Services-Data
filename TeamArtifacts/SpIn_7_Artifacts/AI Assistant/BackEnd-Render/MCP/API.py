from fastapi import FastAPI
from pydantic import BaseModel
from MCP import OIG_search
from MCP import SOS_search
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=1)  # MCP is heavy; keep 1 thread
class SearchRequest(BaseModel):
    query: str

@app.post("/api/oig_search")
async def oig_search(req: SearchRequest):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, OIG_search, req.query)
    return {"result": result}

@app.post("/api/sos_search")
async def sos_search(req: SearchRequest):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, SOS_search, req.query)
    return {"result": result}


    

