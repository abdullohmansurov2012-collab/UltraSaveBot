from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import uvicorn
import os

app = FastAPI(title="UltraSave Video Downloader API")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# --- ROUTES FOR FRONTEND ---

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.get("/style.css")
async def read_css():
    return FileResponse('style.css')

@app.get("/script.js")
async def read_js():
    return FileResponse('script.js')

# --- API ROUTES ---

@app.post("/api/download")
async def download_video(req: VideoRequest):
    try:
        data = extract_video_info(req.url)
        return data
    except ValueError as ve:
        error_msg = str(ve)
        # Bosh harflarga sezgirlikni yo'qotish va aniqroq tekshirish
        if "sign in to confirm you're not a bot" in error_msg.lower() or "bot" in error_msg.lower():
            error_msg = "YouTube xavfsizlik tizimi (bot detection) bizning serverimizni blokladi. Iltimos, boshqa havola tashlab ko'ring yoki bir ozdan so'ng qayta urinib ko'ring."
        elif "requested format is not available" in error_msg.lower():
            error_msg = "Siz so'ragan format ushbu video uchun mavjud emas."
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail="Serverda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")

def extract_video_info(url: str):
    # YouTube uchun maxsus sozlamalar
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # YouTube Shorts uchun havolani to'g'irlash (ba'zida yordam beradi)
            if 'youtube.com/shorts/' in url:
                url = url.replace('youtube.com/shorts/', 'youtube.com/watch?v=')
            
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
                raise ValueError("Video yuklash uchun havolalar topilmadi.")
                
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
        raise ValueError(str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
