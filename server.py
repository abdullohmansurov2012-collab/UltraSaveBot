from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import uvicorn
import os

app = FastAPI(title="UltraSave Video Downloader API")

# Allow CORS for the frontend HTML file to interact
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS) from the current directory
# Render will look for these in the root of the repo
app.mount("/static", StaticFiles(directory="."), name="static")

class VideoRequest(BaseModel):
    url: str

@app.get("/")
async def read_index():
    return FileResponse('index.html')

def extract_video_info(url: str):
    # ... (keeping existing logic)
    # Improved options to get more formats and better luck with merged streams
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        # Using different clients can sometimes reveal merged formats and bypass bot detection
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web', 'mweb', 'tv'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Video')
            thumbnail = info.get('thumbnail', '')
            extractor = info.get('extractor', 'unknown').lower()
            
            qualities = []
            seen_resolutions = set()
            
            # Standard resolutions requested by user
            ALLOWED_HEIGHTS = {
                240: "240p",
                360: "360p",
                480: "480p",
                720: "720p",
                1080: "1080p",
                1440: "2K",
                2160: "4K"
            }
            
            if 'formats' in info:
                # We categorize formats: first merged ones (video+audio), then video-only as fallback
                merged_formats = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                video_only_formats = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') == 'none']
                
                # Check merged formats first
                for f in reversed(merged_formats):
                    h = f.get('height')
                    if h in ALLOWED_HEIGHTS:
                        res_str = ALLOWED_HEIGHTS[h]
                        if res_str not in seen_resolutions:
                            qualities.append({
                                "height": res_str,
                                "url": f.get('url'),
                                "ext": f.get('ext', 'mp4'),
                                "size": round(f.get('filesize', 0) / (1024 * 1024), 1) if f.get('filesize') else "Noma'lum"
                            })
                            seen_resolutions.add(res_str)
                
                # If some resolutions are still missing, take them from video_only (inform the user if possible)
                for f in reversed(video_only_formats):
                    h = f.get('height')
                    if h in ALLOWED_HEIGHTS:
                        res_str = ALLOWED_HEIGHTS[h]
                        if res_str not in seen_resolutions:
                            qualities.append({
                                "height": res_str + " (Ovozsiz)",
                                "url": f.get('url'),
                                "ext": f.get('ext', 'mp4'),
                                "size": round(f.get('filesize', 0) / (1024 * 1024), 1) if f.get('filesize') else "Noma'lum"
                            })
                            seen_resolutions.add(res_str)
            
            # Final fallback for simple sites (IG/TikTok)
            if not qualities:
                 download_url = info.get('url')
                 if download_url:
                     qualities.append({
                         "height": "1080p (Tavsiya)",
                         "url": download_url,
                         "ext": info.get('ext', 'mp4'),
                         "size": "Noma'lum"
                     })
                             
            if not qualities:
                raise ValueError("Could not find any downloadable video links.")
                
            # Sort qualities by height usually (rudimentary sort)
            # Qualities list is ready
            return {
                "status": "success",
                "title": title,
                "thumbnail": thumbnail,
                "platform": extractor,
                "qualities": qualities
            }
            
    except Exception as e:
        print(f"Error extracting {url}: {e}")
        raise ValueError(str(e))

@app.post("/api/download")
async def download_video(req: VideoRequest):
    try:
        data = extract_video_info(req.url)
        return data
    except ValueError as ve:
        error_msg = str(ve)
        if "Sign in to confirm you're not a bot" in error_msg:
            error_msg = "YouTube vaqtinchalik blokladi. Iltimos, bir ozdan so'ng qayta urinib ko'ring yoki boshqa havola tashlang."
        elif "Requested format is not available" in error_msg:
            error_msg = "Siz so'ragan format ushbu video uchun mavjud emas."
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    print("UltraSave Backend starting on http://127.0.0.1:8001")
    uvicorn.run(app, host="127.0.0.1", port=8001)
