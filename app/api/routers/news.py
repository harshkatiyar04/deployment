from fastapi import APIRouter
import httpx
import logging
import time

router = APIRouter(prefix="/news", tags=["news"])
logger = logging.getLogger(__name__)

# --- Simple In-Memory Cache ---
CACHE_TTL = 900  # 15 minutes in seconds
news_cache = {
    "timestamp": 0,
    "data": []
}

@router.get("/guardian")
async def get_guardian_news():
    """
    Fetches live news from The Guardian API from the backend
    to bypass strict browser CORS and frontend rate-limiting issues.
    Utilizes a 15-minute in-memory cache to prevent 429 Rate Limit bottlenecks.
    """
    global news_cache
    current_time = time.time()

    # 1. Return Cache if valid
    if current_time - news_cache["timestamp"] < CACHE_TTL and news_cache["data"]:
        logger.info("Serving Guardian News from Cache")
        return {"status": "success", "fallback": False, "results": news_cache["data"], "cached": True}

    # 2. If cache is stale, try to fetch new data
    url = "https://content.guardianapis.com/search"
    params = {
        "q": "education india",
        "api-key": "test",
        "show-fields": "trailText,thumbnail",
        "page-size": "10"
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            
            # If hit rate limit, use stale cache instead of breaking if we have it
            if response.status_code == 429:
                logger.warning("Guardian API Rate Limit Hit (429)")
                if news_cache["data"]:
                    logger.info("Serving stale cached data instead of mock fallback.")
                    return {"status": "success", "fallback": False, "results": news_cache["data"], "cached": True, "stale": True}
                else:
                    return {"status": "rate_limited", "fallback": True, "results": []}
                
            response.raise_for_status()
            data = response.json()
            
            # Update Cache
            results = data.get("response", {}).get("results", [])
            news_cache["data"] = results
            news_cache["timestamp"] = current_time
            
            logger.info("Fetched fresh Guardian News and updated cache")
            return {"status": "success", "fallback": False, "results": results, "cached": False}

    except httpx.RequestError as exc:
        logger.error(f"Network error while fetching Guardian News: {exc}")
        if news_cache["data"]: return {"status": "success", "fallback": False, "results": news_cache["data"], "cached": True, "stale": True}
        return {"status": "error", "fallback": True, "results": []}
    except Exception as e:
        logger.error(f"Unexpected error when parsing news: {e}")
        if news_cache["data"]: return {"status": "success", "fallback": False, "results": news_cache["data"], "cached": True, "stale": True}
        return {"status": "error", "fallback": True, "results": []}
