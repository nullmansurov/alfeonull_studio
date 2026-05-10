import os
import shutil
import subprocess
import threading
import queue
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
        
        # MELT paths
        melt_paths = [r"C:\Program Files\Shotcut\melt.exe", r"C:\Program Files (x86)\Shotcut\melt.exe", "melt"]
        
        # FFmpeg - Strictly prioritizing the local folder
        ffmpeg_paths = [
            os.path.join(base_dir, 'ffmpeg', 'ffmpeg.exe'),
            os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe'),
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
        if not self.melt_exe or not self.ffmpeg_exe: raise Exception("Executables (melt/ffmpeg) not found")
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

def get_system_fonts():
    fonts_dir = r"C:\Windows\Fonts"
    fonts = []
    if os.path.exists(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith('.ttf'): fonts.append(f)
    return sorted(fonts)

def generate_text_image(text, output_path, font_name="Arial.ttf"):
    width, height = 1920, 1080
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = os.path.join(r"C:\Windows\Fonts", font_name)
    font_size = 120
    try: font = ImageFont.truetype(font_path, font_size)
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