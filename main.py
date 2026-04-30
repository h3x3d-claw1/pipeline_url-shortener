import fastapi
import uvicorn
import string
import random
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from prometheus_client import Counter, Histogram, generate_latest
from typing import Dict

app = FastAPI(title="URL Shortener")

# In-memory storage: short_code -> {"url": original_url, "visits": count}
storage: Dict[str, Dict] = {}

# RED Metrics
# Rate & Errors: request_total
REQUEST_COUNT = Counter(
    "url_shortener_requests_total", 
    "Total number of requests", 
    ["method", "endpoint", "status"]
)
# Duration: request_duration_seconds
REQUEST_LATENCY = Histogram(
    "url_shortener_request_duration_seconds", 
    "Request latency in seconds", 
    ["endpoint"]
)

class ShortenRequest(BaseModel):
    url: HttpUrl

def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    endpoint = request.url.path
    method = request.method
    
    with REQUEST_LATENCY.labels(endpoint=endpoint).time():
        try:
            response = await call_next(request)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
            return response
        except Exception as e:
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=500).inc()
            raise e

@app.post("/shorten")
async def shorten(payload: ShortenRequest):
    code = generate_code()
    storage[code] = {"url": str(payload.url), "visits": 0}
    return {"short_code": code, "short_url": f"/shorten/{code}"}

@app.get("/{short_code}")
async def redirect(short_code: str):
    if short_code not in storage:
        raise HTTPException(status_code=404, detail="Short code not found")
    
    storage[short_code]["visits"] += 1
    return RedirectResponse(url=storage[short_code]["url"])

@app.get("/{short_code}/stats")
async def get_stats(short_code: str):
    if short_code not in storage:
        raise HTTPException(status_code=404, detail="Short code not found")
    
    data = storage[short_code]
    return {
        "short_code": short_code,
        "original_url": data["url"],
        "visit_count": data["visits"]
    }

@app.get("/metrics")
async def metrics():
    return generate_latest()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
