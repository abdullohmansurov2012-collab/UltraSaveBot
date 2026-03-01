from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import uvicorn
import os

app = FastAPI(title="UltraSave Video Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.get("/style.css")
async def read_css():
    return FileResponse('style.css')

@app.get("/script.js")
async def read_js():
    return FileResponse('script.js')

@app.post("/api/download")
async def download_video(req: VideoRequest):
    try:
        data = extract_video_info(req.url)
        return data
    except ValueError as ve:
        error_msg = str(ve).lower()
        if "sign in to confirm you're not a bot" in error_msg or "bot" in error_msg:
            # Chiroyli o'zbekcha xato xabari
            error_msg = "YouTube serverimizni vaqtinchalik blokladi (bot deb gumon qilmoqda). Iltimos, boshqa havola tashlang yoki keyinroq urinib ko'ring."
        elif "requested format is not available" in error_msg:
            error_msg = "Siz so'ragan sifat ushbu video uchun mavjud emas."
        else:
            error_msg = f"Xatolik: {str(ve)[:50]}..."
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Serverda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")

def extract_video_info(url: str):
    # YouTube Shorts havolasini oddiy holatga keltirish
    if 'youtube.com/shorts/' in url:
        url = url.replace('youtube.com/shorts/', 'youtube.com/watch?v=')

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
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
            
            ALLOWED_HEIGHTS = {240: "240p", 360: "360p", 480: "480p", 720: "720p", 1080: "1080p", 1440: "2K", 2160: "4K"}
            
            if 'formats' in info:
                # Merged (video+audio) va Video-only formatlarni saralash
                for f in reversed(info['formats']):
                    h = f.get('height')
                    if h in ALLOWED_HEIGHTS:
                        res_str = ALLOWED_HEIGHTS[h]
                        if f.get('acodec') == 'none': res_str += " (Ovozsiz)"
                        
                        if res_str not in seen_resolutions:
                            qualities.append({
                                "height": res_str,
                                "url": f.get('url'),
                                "ext": f.get('ext', 'mp4'),
                                "size": round(f.get('filesize', 0) / (1024 * 1024), 1) if f.get('filesize') else "Noma'lum"
                            })
                            seen_resolutions.add(res_str)
            
            if not qualities and info.get('url'):
                 qualities.append({"height": "1080p (Tavsiya)", "url": info.get('url'), "ext": info.get('ext', 'mp4'), "size": "Noma'lum"})
                              
            if not qualities: raise ValueError("Siz so'ragan video uchun yuklash linklari topilmadi.")
                
            return {"status": "success", "title": title, "thumbnail": thumbnail, "platform": extractor, "qualities": qualities}
    except Exception as e:
        raise ValueError(str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
