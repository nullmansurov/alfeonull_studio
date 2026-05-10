import os
import shutil
import subprocess
import threading
import queue
import platform
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

render_queue = queue.Queue()

class RenderWorker(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app 
        self.app_config = app.config
        self.melt_exe, self.ffmpeg_exe = self._find_executables()

    def _find_executables(self):
        base_dir = self.app_config.get('BASE_DIR', os.path.abspath(os.path.dirname(__file__)))
        
        # Определяем расширение в зависимости от ОС (.exe только на Windows)
        exe_ext = '.exe' if platform.system() == 'Windows' else ''
        
        # Очередь поиска Melt: 
        # 1. Локальная портативная папка (которую скачает GitHub Actions)
        # 2. Установленные системные пути (Windows / Mac)
        # 3. Системный PATH
        melt_paths = [
            os.path.join(base_dir, 'melt', f'melt{exe_ext}'),
            os.path.join(base_dir, 'melt', 'bin', f'melt{exe_ext}'),
            r"C:\Program Files\Shotcut\melt.exe",
            r"C:\Program Files (x86)\Shotcut\melt.exe",
            "/Applications/Shotcut.app/Contents/MacOS/melt",
            "melt"
        ]
        
        # Очередь поиска FFmpeg:
        ffmpeg_paths = [
            os.path.join(base_dir, 'ffmpeg', f'ffmpeg{exe_ext}'),
            os.path.join(base_dir, 'ffmpeg', 'bin', f'ffmpeg{exe_ext}'),
            "ffmpeg"
        ]
        
        melt = next((p for p in melt_paths if shutil.which(p) or os.path.exists(p)), None)
        ffmpeg = next((p for p in ffmpeg_paths if shutil.which(p) or os.path.exists(p)), None)
        return melt, ffmpeg

    def _update_db_status(self, job_uuid, status, filename=None, error=None):
        with self.app.app_context():
            from app.models import RenderJob
            from app import db
            job = RenderJob.query.filter_by(job_uuid=job_uuid).first()
            if job:
                job.status = status
                if filename: job.filename = filename
                if error: job.error_msg = str(error)
                if status == 'done': job.completed_at = datetime.utcnow()
                db.session.commit()

    def run(self):
        print(f"🚀 Local Engine Ready. Melt: {self.melt_exe} | FFmpeg: {self.ffmpeg_exe}")
        while True:
            job = render_queue.get()
            job_uuid = job['job_uuid']
            self._update_db_status(job_uuid, 'processing')
            try:
                filename = self._process_job(job)
                self._update_db_status(job_uuid, 'done', filename=filename)
            except Exception as e:
                print(f"Error {job_uuid}: {e}")
                self._update_db_status(job_uuid, 'error', error=e)
            finally:
                render_queue.task_done()

    def _process_job(self, job):
        if not self.melt_exe or not self.ffmpeg_exe: 
            raise Exception("Executables (melt/ffmpeg) not found")
            
        job_uuid = job['job_uuid']
        cache_path = job['cache_path']
        final_filename = f"render_{job_uuid}.webm"
        output_path = os.path.join(self.app_config['RENDER_TMP_DIR'], final_filename)
        temp_mov = os.path.join(self.app_config['RENDER_TMP_DIR'], f"temp_{job_uuid}.mov")
        mlt_path = os.path.join(cache_path, "s01.mlt")
        
        cmd_png = [self.melt_exe, "-progress", mlt_path, "-consumer", f"avformat:{temp_mov}", "vcodec=png", "pix_fmt=rgba", "movflags=+faststart"]
        subprocess.run(cmd_png, check=True, cwd=cache_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        cmd_webm = [self.ffmpeg_exe, "-i", temp_mov, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "10M", "-auto-alt-ref", "0", "-cpu-used", "1", "-deadline", "good", "-row-mt", "1", "-threads", "4", "-c:a", "libopus", "-b:a", "128k", "-y", output_path]
        subprocess.run(cmd_webm, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(temp_mov): os.remove(temp_mov)
        return final_filename

# --- Кроссплатформенные утилиты для шрифтов ---
def _get_font_directories():
    system = platform.system()
    if system == 'Windows':
        return [r"C:\Windows\Fonts"]
    elif system == 'Darwin': # macOS
        return ["/System/Library/Fonts", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
    else: # Linux
        return ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]

def get_system_fonts():
    fonts_dirs = _get_font_directories()
    fonts = set()
    
    for d in fonts_dirs:
        if os.path.exists(d):
            # Рекурсивно ищем .ttf файлы в папках шрифтов
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith('.ttf'): 
                        fonts.add(f)
                        
    return sorted(list(fonts))

def generate_text_image(text, output_path, font_name="Arial.ttf"):
    width, height = 1920, 1080
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    fonts_dirs = _get_font_directories()
    font_path = None
    
    # Ищем точный путь к выбранному шрифту
    for d in fonts_dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                if font_name in files:
                    font_path = os.path.join(root, font_name)
                    break
        if font_path: break

    font_size = 120
    try: 
        if not font_path: raise Exception("Font path not found")
        font = ImageFont.truetype(font_path, font_size)
    except: 
        font = ImageFont.load_default()
        font_size = 20
        
    while draw.textbbox((0,0), text, font=font)[2] > width - 100 and font_size > 20:
        font_size -= 5
        try: font = ImageFont.truetype(font_path, font_size)
        except: break
        
    bbox = draw.textbbox((0,0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2
    draw.text((x, y), text, font=font, fill="white")
    img.save(output_path)
