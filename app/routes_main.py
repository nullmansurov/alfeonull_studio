from flask import Blueprint, render_template, redirect, url_for, request, current_app, jsonify, send_from_directory, flash, session, send_file
from . import db
from .models import Preset, LocalUser, RenderJob, StockImage
from .services.render_engine import render_queue, generate_text_image, get_system_fonts
from werkzeug.utils import secure_filename
import os, uuid, json, shutil, zipfile, io

main_bp = Blueprint('main', __name__)

def get_user(): return LocalUser.query.first()

def get_dir_size(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp): total += os.path.getsize(fp)
    return total

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0: return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size} B"

@main_bp.context_processor
def inject_user(): return dict(current_user=get_user())

@main_bp.route('/')
def index(): return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
def dashboard():
    user = get_user()
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = user.fav_presets
    if q: query = query.filter(Preset.name.ilike(f'%{q}%'))
    pagination = query.paginate(page=page, per_page=current_app.config['PRESETS_PER_PAGE'], error_out=False)
    
    total_renders = RenderJob.query.count()
    total_presets = Preset.query.count()
    
    return render_template('dashboard.html', favorites=pagination.items, pagination=pagination, total_renders=total_renders, total_presets=total_presets)

@main_bp.route('/library')
def library():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    
    if q:
        exact_code = Preset.query.filter_by(code=q).first()
        if exact_code:
            class MockPagination:
                items = [exact_code]
                has_prev = False; has_next = False; pages = 1; page = 1; iter_pages = lambda: []
            return render_template('library.html', presets=[exact_code], pagination=MockPagination())
        query = Preset.query.filter_by(is_hidden=False).filter(Preset.name.ilike(f'%{q}%'))
    else:
        query = Preset.query.filter_by(is_hidden=False)
    
    pagination = query.paginate(page=page, per_page=current_app.config['PRESETS_PER_PAGE'], error_out=False)
    return render_template('library.html', presets=pagination.items, pagination=pagination)

@main_bp.route('/export/preset/all')
def export_preset_all():
    memory_file = io.BytesIO()
    presets = Preset.query.all()
    metadata = []
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in presets:
            folder = os.path.join(current_app.config['TEMPLATES_DATA_DIR'], p.folder_path)
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join(p.folder_path, os.path.relpath(file_path, folder))
                        zf.write(file_path, arcname)
            metadata.append({
                'name': p.name, 'code': p.code, 'is_hidden': p.is_hidden, 
                'youtube_url': p.youtube_url, 'notes': p.notes, 'config_json': p.config_json
            })
        zf.writestr('presets_metadata.json', json.dumps(metadata, ensure_ascii=False, indent=4))
    memory_file.seek(0)
    return send_file(memory_file, download_name="all_presets_library.zip", as_attachment=True)

@main_bp.route('/export/preset/<int:pid>')
def export_preset(pid):
    p = Preset.query.get_or_404(pid)
    folder = os.path.join(current_app.config['TEMPLATES_DATA_DIR'], p.folder_path)
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder)
                zf.write(file_path, arcname)
        meta = {'name': p.name, 'code': p.code, 'youtube_url': p.youtube_url, 'notes': p.notes, 'config_json': p.config_json}
        zf.writestr('preset_info.json', json.dumps(meta, ensure_ascii=False, indent=4))
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"preset_{p.code}.zip", as_attachment=True)

@main_bp.route('/stock')
def stock_gallery():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = StockImage.query.order_by(StockImage.uploaded_at.desc())
    if q: query = query.filter(StockImage.name.ilike(f'%{q}%') | StockImage.tags.ilike(f'%{q}%'))
    pagination = query.paginate(page=page, per_page=current_app.config['STOCK_PER_PAGE'], error_out=False)
    return render_template('stock.html', images=pagination.items, pagination=pagination)

@main_bp.route('/export/stock/all')
def export_stock_all():
    memory_file = io.BytesIO()
    stocks = StockImage.query.all()
    metadata = []
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in stocks:
            img_path = os.path.join(current_app.config['STOCK_FOLDER'], img.filename)
            if os.path.exists(img_path):
                zf.write(img_path, f"images/{img.filename}")
            metadata.append({'name': img.name, 'filename': img.filename, 'tags': img.tags})
        zf.writestr('stock_metadata.json', json.dumps(metadata, ensure_ascii=False, indent=4))
    memory_file.seek(0)
    return send_file(memory_file, download_name="all_stock_library.zip", as_attachment=True)

@main_bp.route('/api/stock')
def api_stock_list():
    q = request.args.get('q', '').strip()
    query = StockImage.query.order_by(StockImage.uploaded_at.desc())
    if q: query = query.filter(StockImage.name.ilike(f'%{q}%') | StockImage.tags.ilike(f'%{q}%'))
    return jsonify([img.to_dict() for img in query.limit(50).all()])

@main_bp.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    pagination = RenderJob.query.order_by(RenderJob.created_at.desc())\
        .paginate(page=page, per_page=current_app.config['HISTORY_PER_PAGE'], error_out=False)
    
    cache_dir = current_app.config['CACHE_DIR']
    renders_dir = current_app.config['RENDER_TMP_DIR']
    total_cache_bytes = get_dir_size(cache_dir) + get_dir_size(renders_dir)
    total, used, free = shutil.disk_usage(cache_dir)
    
    return render_template('history.html', pagination=pagination, jobs=pagination.items, 
                           cache_size=format_size(total_cache_bytes), free_space=format_size(free))

@main_bp.route('/history/delete/<job_uuid>', methods=['POST'])
def delete_history(job_uuid):
    job = RenderJob.query.filter_by(job_uuid=job_uuid).first_or_404()
    if job.filename:
        path = os.path.join(current_app.config['RENDER_TMP_DIR'], job.filename)
        if os.path.exists(path): os.remove(path)
    cache_path = os.path.join(current_app.config['CACHE_DIR'], job_uuid)
    if os.path.exists(cache_path): shutil.rmtree(cache_path)
    
    db.session.delete(job)
    db.session.commit()
    flash("Render job deleted.", "success")
    return redirect(url_for('main.history'))

@main_bp.route('/tools/clear_cache', methods=['POST'])
def clear_cache():
    cache_dir = current_app.config['CACHE_DIR']
    renders_dir = current_app.config['RENDER_TMP_DIR']
    try:
        for f in os.listdir(cache_dir):
            path = os.path.join(cache_dir, f)
            if os.path.isdir(path): shutil.rmtree(path)
        for f in os.listdir(renders_dir):
            path = os.path.join(renders_dir, f)
            if os.path.isfile(path): os.remove(path)
        
        RenderJob.query.delete()
        db.session.commit()
        flash("Cache and all render history cleared successfully.", "success")
    except Exception as e:
        flash(f"Error clearing cache: {str(e)}", "danger")
        
    return redirect(url_for('main.history'))

@main_bp.route('/tools/text_gen', methods=['GET', 'POST'])
def text_gen():
    fonts = get_system_fonts()
    preview_url = None
    if request.method == 'POST':
        text = request.form.get('text')
        font = request.form.get('font')
        filename = f"preview_{uuid.uuid4().hex}.png"
        generate_text_image(text, os.path.join(current_app.config['UPLOAD_FOLDER'], filename), font_name=font)
        preview_url = url_for('static', filename=f'uploads/{filename}')
    return render_template('tools_text.html', fonts=fonts, preview_url=preview_url)

@main_bp.route('/api/fav/<int:pid>', methods=['POST'])
def fav(pid):
    user = get_user()
    p = Preset.query.get_or_404(pid)
    if user.fav_presets.filter_by(id=pid).first(): 
        user.fav_presets.remove(p)
        action = 'removed'
    else: 
        user.fav_presets.append(p)
        action = 'added'
    db.session.commit()
    return jsonify({'status': 'ok', 'action': action})

@main_bp.route('/setup/<code_id>')
def setup(code_id):
    p = Preset.query.filter_by(code=code_id).first_or_404()
    job_uuid = str(uuid.uuid4())
    cache_path = os.path.join(current_app.config['CACHE_DIR'], job_uuid)
    shutil.copytree(os.path.join(current_app.config['TEMPLATES_DATA_DIR'], p.folder_path), cache_path)
    session['job_uuid'] = job_uuid
    session['cache_path'] = cache_path
    session['preset_name'] = p.name
    fonts = get_system_fonts()
    return render_template('wizard.html', meta=p.get_config(), preset=p, fonts=fonts)

@main_bp.route('/wizard/process', methods=['POST'])
def wizard_process():
    job_uuid = session.get('job_uuid')
    cache_path = session.get('cache_path')
    if not job_uuid: return redirect(url_for('main.dashboard'))
    meta = json.loads(request.form.get('meta_json', '{}'))
    
    text_mode = meta.get('text_mode', 'no')
    if meta.get('has_text') and text_mode == 'no': text_mode = 'single'
    
    if text_mode != 'no':
        for i in range(1, (3 if text_mode == 'multi' else 1) + 1):
            txt_val = request.form.get(f'text_{i}')
            if txt_val: generate_text_image(txt_val, os.path.join(cache_path, f"text{i}.png"), font_name=request.form.get(f'font_{i}', 'Arial.ttf'))
        
    if meta.get('has_image'):
        stock_data = request.form.get('stock_selection_data')
        if stock_data and stock_data != '[]':
            for i, filename in enumerate(json.loads(stock_data)):
                src = os.path.join(current_app.config['STOCK_FOLDER'], filename)
                if os.path.exists(src): shutil.copy(src, os.path.join(cache_path, f"image{i+1}.png"))
        else:
            for i, f in enumerate(request.files.getlist('images')):
                if f.filename: f.save(os.path.join(cache_path, f"image{i+1}.png"))
                
    if meta.get('has_video'):
        for i, f in enumerate(request.files.getlist('videos')):
            if f.filename: f.save(os.path.join(cache_path, f"video{i+1}.mp4"))
            
    bg = request.files.get('background')
    if bg and bg.filename: bg.save(os.path.join(cache_path, "fon.png"))
    
    db.session.add(RenderJob(job_uuid=job_uuid, user_id=get_user().id, preset_name=session.get('preset_name', 'Unknown'), status='queued'))
    db.session.commit()
    
    render_queue.put({'job_uuid': job_uuid, 'cache_path': cache_path, 'has_alpha': True})
    return redirect(url_for('main.processing', job_uuid=job_uuid))

@main_bp.route('/processing/<job_uuid>')
def processing(job_uuid): return render_template('processing.html', job_uuid=job_uuid)

@main_bp.route('/api/status/<job_uuid>')
def status(job_uuid): 
    job = RenderJob.query.filter_by(job_uuid=job_uuid).first()
    if not job: return jsonify({'status': 'error', 'error': 'Not found'})
    return jsonify({'status': job.status, 'error': job.error_msg, 'filename': job.filename})

@main_bp.route('/download/<filename>')
def download(filename): 
    if not os.path.exists(os.path.join(current_app.config['RENDER_TMP_DIR'], filename)):
        flash("File deleted or missing.", "warning")
        return redirect(url_for('main.history'))
    return send_from_directory(current_app.config['RENDER_TMP_DIR'], filename, as_attachment=True)

# --- Управление Пресетами и Стоком ---
@main_bp.route('/manage/presets', methods=['GET', 'POST'])
def manage_presets():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    query = Preset.query
    if search: query = query.filter(Preset.name.ilike(f'%{search}%') | Preset.code.ilike(f'%{search}%'))
    
    if request.method == 'POST':
        upload_type = request.form.get('upload_type')
        
        if upload_type == 'zip':
            zip_file = request.files.get('zip_file')
            if zip_file and zip_file.filename.endswith('.zip'):
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    namelist = zf.namelist()
                    if 'presets_metadata.json' in namelist:
                        meta_data = json.loads(zf.read('presets_metadata.json').decode('utf-8'))
                        zf.extractall(current_app.config['TEMPLATES_DATA_DIR'])
                        for item in meta_data:
                            if not Preset.query.filter_by(code=item['code']).first():
                                db.session.add(Preset(
                                    name=item['name'], code=item['code'], is_hidden=item.get('is_hidden', False),
                                    youtube_url=item.get('youtube_url'), notes=item.get('notes'),
                                    folder_path=item['code'], config_json=item.get('config_json', '{}')
                                ))
                        db.session.commit()
                        flash("All Presets Imported from ZIP", "success")
                    elif 'preset_info.json' in namelist:
                        meta_data = json.loads(zf.read('preset_info.json').decode('utf-8'))
                        code = meta_data['code']
                        if Preset.query.filter_by(code=code).first(): code = f"{code}_{uuid.uuid4().hex[:6]}"
                        folder = os.path.join(current_app.config['TEMPLATES_DATA_DIR'], code)
                        os.makedirs(folder, exist_ok=True)
                        for item in namelist:
                            if item != 'preset_info.json': zf.extract(item, folder)
                        db.session.add(Preset(
                            name=meta_data['name'], code=code, is_hidden=False,
                            youtube_url=meta_data.get('youtube_url'), notes=meta_data.get('notes'),
                            folder_path=code, config_json=meta_data.get('config_json', '{}')
                        ))
                        db.session.commit()
                        flash("Preset Imported from ZIP", "success")
                    else:
                        flash("Invalid ZIP: Metadata missing.", "danger")
        else:
            safe_code = secure_filename(request.form.get('code'))
            folder = os.path.join(current_app.config['TEMPLATES_DATA_DIR'], safe_code)
            os.makedirs(folder, exist_ok=True)
            
            if 'mlt' in request.files and request.files['mlt'].filename:
                request.files['mlt'].save(os.path.join(folder, "s01.mlt"))
            
            for sf in request.files.getlist('source_files'):
                if sf.filename: sf.save(os.path.join(folder, sf.filename))
            
            text_mode = request.form.get('text_mode')
            meta = {
                "display_name": request.form.get('name'), "has_text": text_mode != 'no', "text_mode": text_mode,
                "has_image": request.form.get('has_image') != 'no', "image_mode": request.form.get('has_image'),
                "has_video": request.form.get('has_video') != 'no', "video_mode": request.form.get('has_video'),
                "has_background": request.form.get('has_background') == 'yes', "has_alpha": True
            }
            db.session.add(Preset(name=request.form.get('name'), code=request.form.get('code'), is_hidden='is_hidden' in request.form, youtube_url=request.form.get('youtube'), folder_path=safe_code, notes=request.form.get('notes'), config_json=json.dumps(meta)))
            db.session.commit()
            flash("Preset saved successfully!", "success")
            
        return redirect(url_for('main.manage_presets'))
        
    pagination = query.paginate(page=page, per_page=current_app.config['PRESETS_PER_PAGE'], error_out=False)
    return render_template('admin_presets.html', pagination=pagination, presets=pagination.items)

@main_bp.route('/preset/delete/<int:pid>')
def delete_preset(pid):
    p = Preset.query.get(pid)
    try: shutil.rmtree(os.path.join(current_app.config['TEMPLATES_DATA_DIR'], p.folder_path))
    except: pass
    db.session.delete(p)
    db.session.commit()
    flash("Preset deleted.", "success")
    return redirect(url_for('main.manage_presets'))

@main_bp.route('/manage/stock', methods=['GET', 'POST'])
def manage_stock():
    if request.method == 'POST':
        upload_type = request.form.get('upload_type')
        if upload_type == 'zip':
            zip_file = request.files.get('zip_file')
            if zip_file and zip_file.filename.endswith('.zip'):
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    namelist = zf.namelist()
                    if 'stock_metadata.json' in namelist:
                        meta_data = json.loads(zf.read('stock_metadata.json').decode('utf-8'))
                        for item in meta_data:
                            fname = item['filename']
                            zip_path = f"images/{fname}"
                            if zip_path in namelist:
                                extracted = zf.extract(zip_path, current_app.config['STOCK_FOLDER'])
                                dest = os.path.join(current_app.config['STOCK_FOLDER'], fname)
                                if extracted != dest: os.rename(extracted, dest)
                                if not StockImage.query.filter_by(filename=fname).first():
                                    db.session.add(StockImage(name=item['name'], filename=fname, tags=item.get('tags','')))
                        try: shutil.rmtree(os.path.join(current_app.config['STOCK_FOLDER'], 'images'))
                        except: pass
                        db.session.commit()
                        flash("Stock Collection Imported", "success")
                    else:
                        flash("Invalid ZIP: Metadata missing.", "danger")
        else:
            file = request.files.get('file')
            if file and file.filename:
                if file.filename.rsplit('.', 1)[1].lower() == 'png':
                    fname = f"stock_{uuid.uuid4().hex}.png"
                    file.save(os.path.join(current_app.config['STOCK_FOLDER'], fname))
                    db.session.add(StockImage(name=request.form.get('name'), filename=fname, tags=request.form.get('tags')))
                    db.session.commit()
                    flash("Image Added", "success")
                else: flash("Only PNG allowed", "danger")
        return redirect(url_for('main.manage_stock'))

    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = StockImage.query.order_by(StockImage.uploaded_at.desc())
    if q: query = query.filter(StockImage.name.ilike(f'%{q}%') | StockImage.tags.ilike(f'%{q}%'))
    pagination = query.paginate(page=page, per_page=current_app.config['STOCK_PER_PAGE'], error_out=False)
    return render_template('admin_stock.html', images=pagination.items, pagination=pagination)

@main_bp.route('/stock/delete/<int:id>')
def delete_stock(id):
    img = StockImage.query.get_or_404(id)
    try: os.remove(os.path.join(current_app.config['STOCK_FOLDER'], img.filename))
    except: pass
    db.session.delete(img)
    db.session.commit()
    flash("Image Deleted", "success")
    return redirect(url_for('main.manage_stock'))