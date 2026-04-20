import io
import html
import json
import os
import re
from datetime import datetime
from urllib.parse import quote

from flask import Blueprint, jsonify, request, render_template, redirect, url_for, session, send_file
from ..models import (
    db, Truong, KhoaVien, NganhHoc, PhienBanCT, HocPhan, KhungChuongTrinh,
    DeCuongChiTiet, ChuanDauRa, KeHoachGiangDay, DanhGiaHocPhan, HocLieu, User, DeMucDeCuong
)
import google.generativeai as genai
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

course_bp = Blueprint('course', __name__)

DEFAULT_SYLLABUS_SECTIONS = [
    "1. Thông tin chung",
    "2. Mục tiêu học phần",
    "3. Chuẩn đầu ra học phần",
    "4. Nội dung tóm tắt học phần",
    "5. Nội dung chi tiết",
    "6. Phương pháp giảng dạy và học tập",
    "7. Nhiệm vụ của sinh viên",
    "8. Đánh giá học phần",
    "9. Tài liệu học tập"
]


def _normalize_section_payload(items):
    if not isinstance(items, list):
        items = []

    normalized = []
    for idx, default_title in enumerate(DEFAULT_SYLLABUS_SECTIONS, start=1):
        raw = items[idx - 1] if idx - 1 < len(items) and isinstance(items[idx - 1], dict) else {}
        title = (raw.get('title') or default_title).strip()
        content = (raw.get('content') or '').strip()
        normalized.append({
            'position': idx,
            'title': title,
            'content': content
        })
    return normalized


def _extract_syllabus_sections_from_docx(file_storage):
    try:
        from docx import Document
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except Exception as exc:
        raise RuntimeError("Thiếu thư viện python-docx") from exc

    document = Document(file_storage)

    def iter_blocks(doc):
        for child in doc.element.body.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, doc)
            elif isinstance(child, CT_Tbl):
                yield Table(child, doc)

    def table_to_html(tbl):
        rows_html = []
        for row in tbl.rows:
            cell_html = []
            for cell in row.cells:
                cell_text = html.escape((cell.text or '').strip())
                cell_html.append(f"<td>{cell_text}</td>")
            rows_html.append(f"<tr>{''.join(cell_html)}</tr>")
        return f"<table class='docx-table table table-bordered table-sm'><tbody>{''.join(rows_html)}</tbody></table>"

    heading_pattern = re.compile(r'^\s*(?:Mục\s*)?(\d{1,2})[\.)\-:]\s*(.+)\s*$')
    header_lines = []
    buckets = {}
    current_idx = 1
    has_detected_heading = False
    found_first_section = False

    for block in iter_blocks(document):
        if isinstance(block, Paragraph):
            text = (block.text or '').strip()
            if not text:
                continue

            match = heading_pattern.match(text)
            if match:
                idx = int(match.group(1))
                if 1 <= idx <= 9:
                    found_first_section = True
                    current_idx = idx
                    has_detected_heading = True
                    buckets.setdefault(idx, {'title': match.group(2).strip(), 'html_parts': []})
                    continue
            
            # Collect header content before first section heading
            if not found_first_section:
                header_lines.append(f"<p>{html.escape(text)}</p>")
                continue

            bucket = buckets.setdefault(current_idx, {'title': DEFAULT_SYLLABUS_SECTIONS[current_idx - 1], 'html_parts': []})
            bucket['html_parts'].append(f"<p>{html.escape(text)}</p>")
        else:
            if not found_first_section:
                header_lines.append(table_to_html(block))
            else:
                bucket = buckets.setdefault(current_idx, {'title': DEFAULT_SYLLABUS_SECTIONS[current_idx - 1], 'html_parts': []})
                bucket['html_parts'].append(table_to_html(block))

    sections = []
    for idx, default_title in enumerate(DEFAULT_SYLLABUS_SECTIONS, start=1):
        bucket = buckets.get(idx)
        if bucket:
            sections.append({
                'title': (bucket.get('title') or default_title).strip(),
                'content': ''.join(bucket.get('html_parts') or []).strip()
            })
        else:
            sections.append({'title': default_title, 'content': ''})

    if not buckets and not has_detected_heading:
        return {'header': ''.join(header_lines).strip(), 'sections': _normalize_section_payload([])}

    return {'header': ''.join(header_lines).strip(), 'sections': _normalize_section_payload(sections)}

# ==============================================================
# AUTHENTICATION ROUTES
# ==============================================================

@course_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Tìm user trong database
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            # Lưu thông tin vào session
            session['user_id'] = user.id
            session['username'] = user.username
            session['ho_ten'] = user.ho_ten
            session['vai_tro'] = user.vai_tro
            
            # Redirect dựa trên vai trò
            if user.vai_tro == 'Admin':
                return redirect(url_for('course.admin'))
            else:
                return redirect(url_for('course.home'))
        else:
            return render_template('login.html', error='Tên đăng nhập hoặc mật khẩu không chính xác!')

    return render_template('login.html')


@course_bp.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('course.home'))


# ==============================================================
# CONTEXT PROCESSORS
# ==============================================================

@course_bp.app_context_processor
def inject_navbar_data():
    """Cung cấp dữ liệu cho navbar trên tất cả các trang"""
    return dict(
        nav_schools=Truong.query.order_by(Truong.ten_truong.asc()).all(),
        nav_faculties=KhoaVien.query.order_by(KhoaVien.ten_khoa.asc()).all(),
        nav_majors=NganhHoc.query.order_by(NganhHoc.ten_nganh.asc()).all()
    )


# ==============================================================
# MAIN ROUTES
# ==============================================================

@course_bp.route('/', methods=['GET'])
def home():
    return render_template('index.html')

def get_pagination_params():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search_query = request.args.get('q', '')
    cohort = request.args.get('cohort', '')
    return page, limit, search_query, cohort


def _major_versions(major_id):
    return PhienBanCT.query.filter_by(nganh_id=major_id).order_by(PhienBanCT.nam_bat_dau.desc(), PhienBanCT.id.desc()).all()


def _pick_version(major_id, version_code=None):
    versions = _major_versions(major_id)
    if not versions:
        return None, []

    selected = None
    if version_code:
        selected = next((v for v in versions if v.ma_phien_ban == version_code), None)

    if not selected:
        selected = versions[0]

    return selected, versions


def _curriculum_items(version_id):
    return KhungChuongTrinh.query.filter_by(phien_ban_id=version_id).order_by(KhungChuongTrinh.hoc_ky_du_kien.asc()).all()

# API: Schools
@course_bp.route('/api/schools', methods=['GET'])
def get_schools():
    page, limit, q, _ = get_pagination_params()
    query = Truong.query
    if q:
        query = query.filter(Truong.ten_truong.ilike(f'%{q}%') | Truong.ma_truong.ilike(f'%{q}%'))
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    data = [{
        "id": s.id, 
        "ma": s.ma_truong, 
        "ten": s.ten_truong,
        "count_khoa": len(s.khoas)
    } for s in pagination.items]
    
    return jsonify({
        "status": "success",
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "data": data
    })

# API: Faculties
@course_bp.route('/api/faculties', methods=['GET'])
def get_faculties():
    page, limit, q, _ = get_pagination_params()
    query = KhoaVien.query
    if q:
        query = query.filter(KhoaVien.ten_khoa.ilike(f'%{q}%') | KhoaVien.ma_khoa.ilike(f'%{q}%'))
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    data = [{
        "id": f.id,
        "ma": f.ma_khoa,
        "ten": f.ten_khoa,
        "truong": f.truong.ten_truong if f.truong else "",
        "count_nganh": len(f.nganhs)
    } for f in pagination.items]
    
    return jsonify({
        "status": "success",
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "data": data
    })

# API: Majors (Ngành/Chương trình)
@course_bp.route('/api/majors', methods=['GET'])
def get_majors():
    page, limit, q, cohort = get_pagination_params()
    query = NganhHoc.query
    
    if q:
        query = query.filter(NganhHoc.ten_nganh.ilike(f'%{q}%') | NganhHoc.ma_nganh.ilike(f'%{q}%'))
    
    if cohort:
        # Lọc theo phiên bản chương trình
        query = query.join(PhienBanCT).filter(PhienBanCT.ma_phien_ban.ilike(f'%{cohort}%'))
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    data = []
    for m in pagination.items:
        # Lấy phiên bản mới nhất hoặc phiên bản khớp với cohort
        pb = next((p for p in m.phien_ban_cts if cohort in p.ma_phien_ban), m.phien_ban_cts[0]) if m.phien_ban_cts else None
        data.append({
            "id": m.id,
            "ma": m.ma_nganh,
            "ten": m.ten_nganh,
            "khoa": m.khoa.ten_khoa if m.khoa else "",
            "phien_ban": pb.ma_phien_ban if pb else "N/A"
        })
    
    return jsonify({
        "status": "success",
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "data": data
    })

# API: Courses (Học phần)
@course_bp.route('/api/courses', methods=['GET'])
def get_courses():
    page, limit, q, cohort = get_pagination_params()
    query = HocPhan.query.outerjoin(KhoaVien)
    
    if q:
        query = query.filter(HocPhan.ten_hoc_phan.ilike(f'%{q}%') | HocPhan.ma_hoc_phan.ilike(f'%{q}%'))
    
    if cohort:
        # Học phần thuộc khung chương trình của phiên bản đó
        query = query.join(KhungChuongTrinh).join(PhienBanCT).filter(PhienBanCT.ma_phien_ban.ilike(f'%{cohort}%'))
    
    # Remove distinct and use it only on the ID subquery to avoid SQLAlchemy relationship loading issues
    pagination = query.distinct().paginate(page=page, per_page=limit, error_out=False)
    data = []
    for c in pagination.items:
        khoa_name = ""
        try:
            # Explicitly query khoa_vien to avoid relationship loading issues
            if c.khoa_quan_ly_id:
                khoa = KhoaVien.query.get(c.khoa_quan_ly_id)
                if khoa:
                    khoa_name = khoa.ten_khoa
        except Exception:
            khoa_name = ""
        
        data.append({
            "id": c.id,
            "ma": c.ma_hoc_phan,
            "ten": c.ten_hoc_phan,
            "tin_chi": c.so_tin_chi,
            "khoa": khoa_name
        })
    
    return jsonify({
        "status": "success",
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "data": data
    })

# API: Versions
@course_bp.route('/api/versions', methods=['GET'])
def get_versions():
    versions = PhienBanCT.query.with_entities(PhienBanCT.ma_phien_ban, PhienBanCT.nam_bat_dau).distinct().order_by(PhienBanCT.nam_bat_dau.desc()).all()
    data = [{"ma": v.ma_phien_ban, "nam": v.nam_bat_dau} for v in versions]
    return jsonify({"status": "success", "data": data})


@course_bp.route('/api/major/<int:id>/versions', methods=['GET'])
def get_major_versions(id):
    major = NganhHoc.query.get_or_404(id)
    versions = _major_versions(major.id)
    return jsonify({
        "status": "success",
        "major_id": major.id,
        "data": [{"ma": v.ma_phien_ban, "nam": v.nam_bat_dau} for v in versions]
    })


@course_bp.route('/api/major/<int:id>/compare', methods=['GET'])
def compare_major_versions_api(id):
    default_major = NganhHoc.query.get_or_404(id)
    left_major_id = request.args.get('major_left_id', id, type=int)
    right_major_id = request.args.get('major_right_id', type=int)
    left_code = request.args.get('left', '')
    right_code = request.args.get('right', '')

    left_major = NganhHoc.query.get_or_404(left_major_id)
    right_major = NganhHoc.query.get(right_major_id) if right_major_id else None
    if not right_major:
        right_major = default_major if default_major.id != left_major.id else left_major

    left_version, _ = _pick_version(left_major.id, left_code)
    right_version, _ = _pick_version(right_major.id, right_code)

    if not left_version:
        return jsonify({"status": "error", "message": "Chương trình bên trái chưa có phiên bản"}), 404

    if not right_version:
        return jsonify({"status": "error", "message": "Chương trình bên phải chưa có phiên bản"}), 404

    left_items = _curriculum_items(left_version.id)
    right_items = _curriculum_items(right_version.id)

    left_map = {item.hoc_phan.ma_hoc_phan: item.hoc_phan for item in left_items}
    right_map = {item.hoc_phan.ma_hoc_phan: item.hoc_phan for item in right_items}

    common_codes = sorted(set(left_map.keys()) & set(right_map.keys()))
    left_only_codes = sorted(set(left_map.keys()) - set(right_map.keys()))
    right_only_codes = sorted(set(right_map.keys()) - set(left_map.keys()))

    return jsonify({
        "status": "success",
        "left_major": {"id": left_major.id, "ma": left_major.ma_nganh, "ten": left_major.ten_nganh},
        "right_major": {"id": right_major.id, "ma": right_major.ma_nganh, "ten": right_major.ten_nganh},
        "left_version": {"ma": left_version.ma_phien_ban, "nam": left_version.nam_bat_dau},
        "right_version": {"ma": right_version.ma_phien_ban, "nam": right_version.nam_bat_dau},
        "common": [{"ma": code, "ten": left_map[code].ten_hoc_phan, "tin_chi": left_map[code].so_tin_chi} for code in common_codes],
        "left_only": [{"ma": code, "ten": left_map[code].ten_hoc_phan, "tin_chi": left_map[code].so_tin_chi} for code in left_only_codes],
        "right_only": [{"ma": code, "ten": right_map[code].ten_hoc_phan, "tin_chi": right_map[code].so_tin_chi} for code in right_only_codes]
    })


@course_bp.route('/api/major/<int:id>/share-info', methods=['GET'])
def major_share_info(id):
    major = NganhHoc.query.get_or_404(id)
    version_code = request.args.get('version', '')
    version, _ = _pick_version(major.id, version_code)

    if not version:
        return jsonify({"status": "error", "message": "Ngành chưa có phiên bản chương trình"}), 404

    share_url = url_for('course.major_detail', id=major.id, version=version.ma_phien_ban, _external=True)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=260x260&data={quote(share_url)}"

    return jsonify({
        "status": "success",
        "share_url": share_url,
        "qr_url": qr_url,
        "version": {"ma": version.ma_phien_ban, "nam": version.nam_bat_dau}
    })


@course_bp.route('/api/favorites/majors', methods=['GET'])
def get_favorite_majors():
    favorites = session.get('favorite_majors', [])
    return jsonify({"status": "success", "data": favorites})


@course_bp.route('/api/favorites/majors', methods=['POST'])
def add_favorite_major():
    payload = request.get_json(silent=True) or {}
    major_id = payload.get('major_id')
    version_code = payload.get('version')

    if not major_id or not version_code:
        return jsonify({"status": "error", "message": "Thiếu major_id hoặc version"}), 400

    major = NganhHoc.query.get_or_404(major_id)
    version = PhienBanCT.query.filter_by(nganh_id=major.id, ma_phien_ban=version_code).first()
    if not version:
        return jsonify({"status": "error", "message": "Phiên bản không hợp lệ"}), 400

    favorites = session.get('favorite_majors', [])
    already_exists = next((x for x in favorites if x.get('major_id') == major.id and x.get('version') == version_code), None)

    if not already_exists:
        favorites.append({
            "major_id": major.id,
            "major_name": major.ten_nganh,
            "major_code": major.ma_nganh,
            "version": version_code
        })
        session['favorite_majors'] = favorites
        session.modified = True
        added = True
    else:
        added = False

    return jsonify({"status": "success", "message": "Đã thêm vào yêu thích", "added": added, "data": favorites})


@course_bp.route('/api/favorites/majors/<int:major_id>', methods=['DELETE'])
def remove_favorite_major(major_id):
    version_code = request.args.get('version', '')
    favorites = session.get('favorite_majors', [])
    next_favorites = [x for x in favorites if not (x.get('major_id') == major_id and x.get('version') == version_code)]
    session['favorite_majors'] = next_favorites
    session.modified = True

    return jsonify({"status": "success", "message": "Đã xóa khỏi yêu thích", "data": next_favorites})


@course_bp.route('/favorites', methods=['GET'])
def favorite_list_page():
    raw_favorites = session.get('favorite_majors', [])
    favorites = []

    for item in raw_favorites:
        major_id = item.get('major_id')
        version_code = item.get('version')
        major = NganhHoc.query.get(major_id)
        if not major:
            continue

        version = PhienBanCT.query.filter_by(nganh_id=major.id, ma_phien_ban=version_code).first()
        if not version:
            continue

        favorites.append({
            "major_id": major.id,
            "major_name": major.ten_nganh,
            "major_code": major.ma_nganh,
            "version": version.ma_phien_ban,
            "year": version.nam_bat_dau
        })

    return render_template('favorites.html', favorites=favorites)


# ==============================================================
# 3. ROUTES CHI TIẾT (DRILL-DOWN)
# ==============================================================

@course_bp.route('/school/<int:id>')
def school_detail(id):
    school = Truong.query.get_or_404(id)
    return render_template('detail.html', type='school', item=school)

@course_bp.route('/faculty/<int:id>')
def faculty_detail(id):
    faculty = KhoaVien.query.get_or_404(id)
    return render_template('detail.html', type='faculty', item=faculty)


@course_bp.route('/major/<int:id>')
def major_detail(id):
    major = NganhHoc.query.get_or_404(id)
    version_code = request.args.get('version', '')
    version, versions = _pick_version(id, version_code)

    if not version:
        return "Chưa có khung chương trình cho ngành này", 404

    curriculum_list = _curriculum_items(version.id)
    favorites = session.get('favorite_majors', [])
    is_favorite = any(x.get('major_id') == major.id and x.get('version') == version.ma_phien_ban for x in favorites)

    total_credits = sum(item.hoc_phan.so_tin_chi for item in curriculum_list)

    return render_template(
        'major_detail.html',
        major=major,
        version=version,
        versions=versions,
        curriculum_list=curriculum_list,
        total_credits=total_credits,
        is_favorite=is_favorite
    )


@course_bp.route('/major/<int:id>/compare', methods=['GET'])
def major_compare_page(id):
    base_major = NganhHoc.query.get_or_404(id)
    left_major_id = request.args.get('major_left_id', id, type=int)
    right_major_id = request.args.get('major_right_id', type=int)
    left_code = request.args.get('left', '')
    right_code = request.args.get('right', '')

    left_major = NganhHoc.query.get_or_404(left_major_id)
    right_major = NganhHoc.query.get(right_major_id) if right_major_id else None
    if not right_major:
        right_major = next((m for m in NganhHoc.query.order_by(NganhHoc.id.asc()).all() if m.id != left_major.id), left_major)

    left_versions = _major_versions(left_major.id)
    right_versions = _major_versions(right_major.id)

    if not left_versions:
        return "Chương trình bên trái chưa có phiên bản để so sánh", 404
    if not right_versions:
        return "Chương trình bên phải chưa có phiên bản để so sánh", 404

    left_version = next((v for v in left_versions if v.ma_phien_ban == left_code), left_versions[0])
    right_version = next((v for v in right_versions if v.ma_phien_ban == right_code), right_versions[0])

    left_items = _curriculum_items(left_version.id)
    right_items = _curriculum_items(right_version.id)

    left_map = {item.hoc_phan.ma_hoc_phan: item.hoc_phan for item in left_items}
    right_map = {item.hoc_phan.ma_hoc_phan: item.hoc_phan for item in right_items}

    common_codes = sorted(set(left_map.keys()) & set(right_map.keys()))
    left_only_codes = sorted(set(left_map.keys()) - set(right_map.keys()))
    right_only_codes = sorted(set(right_map.keys()) - set(left_map.keys()))

    return render_template(
        'major_compare.html',
        major=base_major,
        left_major=left_major,
        right_major=right_major,
        compare_majors=NganhHoc.query.order_by(NganhHoc.ten_nganh.asc()).all(),
        left_versions=left_versions,
        right_versions=right_versions,
        left_version=left_version,
        right_version=right_version,
        common_courses=[left_map[code] for code in common_codes],
        left_only_courses=[left_map[code] for code in left_only_codes],
        right_only_courses=[right_map[code] for code in right_only_codes]
    )


@course_bp.route('/major/<int:id>/pdf', methods=['GET'])
def major_pdf(id):
    major = NganhHoc.query.get_or_404(id)
    version_code = request.args.get('version', '')
    version, _ = _pick_version(major.id, version_code)

    if not version:
        return "Ngành chưa có phiên bản chương trình", 404

    curriculum_list = _curriculum_items(version.id)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception:
        return jsonify({
            "status": "error",
            "message": "Thiếu thư viện reportlab. Cài bằng lệnh: pip install reportlab"
        }), 500

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    try:
        font_candidates = [
            'DejaVuSans.ttf',
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/tahoma.ttf'
        ]
        font_path = next((path for path in font_candidates if os.path.exists(path)), None)
        if font_path:
            pdfmetrics.registerFont(TTFont('AppFont', font_path))
            font_name = 'AppFont'
        else:
            font_name = 'Helvetica'
    except Exception:
        font_name = 'Helvetica'

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=14, leading=18)
    text_style = ParagraphStyle('TextStyle', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=13)
    table_text_style = ParagraphStyle('TableTextStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=11)

    table_data = [[
        'STT',
        'Ma HP',
        'Ten hoc phan',
        'Tin chi',
        'Ky',
        'Loai',
        'Khoa/Vien'
    ]]

    total_credits = 0
    for idx, item in enumerate(curriculum_list, start=1):
        total_credits += item.hoc_phan.so_tin_chi
        table_data.append([
            str(idx),
            item.hoc_phan.ma_hoc_phan,
            Paragraph(item.hoc_phan.ten_hoc_phan, table_text_style),
            str(item.hoc_phan.so_tin_chi),
            str(item.hoc_ky_du_kien or ''),
            item.loai_mon or '',
            Paragraph(item.hoc_phan.khoa_quan_ly.ten_khoa if item.hoc_phan.khoa_quan_ly else '', table_text_style)
        ])

    table = Table(
        table_data,
        colWidths=[10 * mm, 20 * mm, 56 * mm, 12 * mm, 10 * mm, 28 * mm, 36 * mm],
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#085CA7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (4, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#F9FCFF')])
    ]))

    story = [
        Paragraph(f'Chuong trinh dao tao: {major.ten_nganh}', title_style),
        Spacer(1, 6),
        Paragraph(f'Ma nganh: {major.ma_nganh}', text_style),
        Paragraph(f'Phien ban: {version.ma_phien_ban} - Nam bat dau: {version.nam_bat_dau}', text_style),
        Paragraph(f'Tong so tin chi: {total_credits}', text_style),
        Spacer(1, 10),
        table
    ]

    doc.build(story)
    pdf_buffer.seek(0)

    filename = f"CTDT_{major.ma_nganh}_{version.ma_phien_ban}.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


@course_bp.route('/course/<int:id>')
def course_detail(id):
    course = HocPhan.query.get_or_404(id)
    # Lấy đề cương mới nhất
    syllabus = DeCuongChiTiet.query.filter_by(hoc_phan_id=id).order_by(DeCuongChiTiet.nam_ap_dung.desc()).first()
    return render_template('syllabus.html', course=course, syllabus=syllabus)


@course_bp.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"reply": "Bạn hãy nhập câu hỏi nhé!"})

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"reply": "Lỗi hệ thống: Chưa cấu hình API."})

        genai.configure(api_key=api_key)
        # Vẫn dùng bản Flash Lite cho nhẹ và an toàn với tài khoản Free
        model = genai.GenerativeModel('gemini-flash-lite-latest')

        # 1. Lấy dữ liệu tổng quan chung (Bảng Truong, KhoaVien, NganhHoc)
        so_truong = Truong.query.count()
        so_khoa = KhoaVien.query.count()
        so_nganh = NganhHoc.query.count()

        # =================================================================
        # 2. SMART ROUTER: RÚT TRÍCH DỮ LIỆU TỪ 11 BẢNG DỰA THEO CÂU HỎI
        # =================================================================
        thong_tin_db = ""
        user_msg_lower = user_message.lower()

        # TRƯỜNG HỢP A: User hỏi về NGÀNH HỌC (Liên kết bảng NganhHoc, PhienBanCT, KhungChuongTrinh)
        for nganh in NganhHoc.query.all():
            if nganh.ten_nganh.lower() in user_msg_lower:
                thong_tin_db += f"\n[THÔNG TIN NGÀNH HỌC]\n- Tên ngành: {nganh.ten_nganh} (Mã: {nganh.ma_nganh}, Thuộc {nganh.khoa.ten_khoa})\n"
                # Tìm Khung chương trình của ngành này
                phien_ban = PhienBanCT.query.filter_by(nganh_id=nganh.id).first()
                if phien_ban:
                    so_mon_hoc = KhungChuongTrinh.query.filter_by(phien_ban_id=phien_ban.id).count()
                    thong_tin_db += f"- Phiên bản đào tạo: {phien_ban.ma_phien_ban} ({phien_ban.nam_bat_dau})\n"
                    thong_tin_db += f"- Tổng số môn phải học: {so_mon_hoc} môn.\n"
                break  # Tìm thấy 1 ngành khớp là dừng

        # TRƯỜNG HỢP B: User hỏi về MÔN HỌC (Liên kết bảng HocPhan, DeCuong, DanhGia, HocLieu, ChuanDauRa)
        for mon in HocPhan.query.all():
            if mon.ten_hoc_phan.lower() in user_msg_lower or mon.ma_hoc_phan.lower() in user_msg_lower:
                thong_tin_db += f"\n[THÔNG TIN MÔN HỌC]\n- Môn: {mon.ten_hoc_phan} (Mã: {mon.ma_hoc_phan})\n"
                thong_tin_db += f"- Số tín chỉ: {mon.so_tin_chi}\n"

                # Tìm Đề cương chi tiết
                de_cuong = DeCuongChiTiet.query.filter_by(hoc_phan_id=mon.id).first()
                if de_cuong:
                    # Rút bảng Đánh giá
                    danh_gia = DanhGiaHocPhan.query.filter_by(de_cuong_id=de_cuong.id).all()
                    if danh_gia:
                        thong_tin_db += "- Điểm đánh giá: " + ", ".join(
                            [f"{dg.thanh_phan} ({int(dg.trong_so * 100)}%)" for dg in danh_gia]) + "\n"

                    # Rút bảng Học liệu
                    hoc_lieu = HocLieu.query.filter_by(de_cuong_id=de_cuong.id).all()
                    if hoc_lieu:
                        thong_tin_db += "- Giáo trình/Tài liệu: " + ", ".join(
                            [hl.ten_tai_lieu for hl in hoc_lieu]) + "\n"

                    # Rút bảng Chuẩn đầu ra (CLO)
                    clo = ChuanDauRa.query.filter_by(de_cuong_id=de_cuong.id).all()
                    if clo:
                        thong_tin_db += "- Mục tiêu môn học: " + " và ".join([c.mo_ta for c in clo]) + "\n"
                break  # Tìm thấy 1 môn khớp là dừng
        dinh_huong = {
            "web": ["lập trình", "web", "phần mềm", "cơ sở dữ liệu", "hệ thống thông tin"],
            "cloud": ["mạng", "bảo mật", "hệ điều hành", "đám mây", "an toàn", "nhúng"],
            "data": ["dữ liệu", "thống kê", "ai", "trí tuệ nhân tạo", "machine", "toán"],
            "marketing": ["marketing", "thương hiệu", "hành vi", "khách hàng", "pr", "thị trường"]
        }

        is_career_question = False
        for nghe, tu_khoa_list in dinh_huong.items():
            if nghe in user_msg_lower or "lộ trình" in user_msg_lower or "định hướng" in user_msg_lower:
                is_career_question = True
                thong_tin_db += f"\n[CÁC MÔN HỌC TRONG TRƯỜNG PHÙ HỢP VỚI NGHỀ NÀY]\n"

                # Quét tất cả môn học, môn nào có tên chứa từ khóa thì gom lại
                mon_goi_y = []
                for mon in HocPhan.query.all():
                    if any(tk in mon.ten_hoc_phan.lower() for tk in tu_khoa_list):
                        mon_goi_y.append(f"- {mon.ten_hoc_phan} ({mon.so_tin_chi} TC)")

                # Lấy tối đa 10 môn để AI không bị ngợp
                thong_tin_db += "\n".join(mon_goi_y[:10]) + "\n"
                break

        for truong in Truong.query.all():
            if truong.ten_truong.lower() in user_msg_lower and truong.ma_truong != "NEU_BASE":
                so_khoa_truong_nay = len(truong.khoas)
                thong_tin_db += f"\n[THÔNG TIN CHI TIẾT TRƯỜNG: {truong.ten_truong}]\n"
                thong_tin_db += f"- Số lượng Khoa/Viện trực thuộc: {so_khoa_truong_nay}\n"

                # Liệt kê luôn tên các khoa cho AI biết đường mà kể
                ten_cac_khoa = [k.ten_khoa for k in truong.khoas]
                thong_tin_db += f"- Danh sách gồm: {', '.join(ten_cac_khoa)}\n"
                break

        # =================================================================
        # 3. TIÊM TOÀN BỘ VÀO PROMPT CHO AI XỬ LÝ
        # =================================================================
        prompt = f"""
        Bạn là "NEU Assistant", trợ lý ảo tư vấn học tập của hệ thống NEU Course.

        [DỮ LIỆU TỔNG QUAN]
        - Trường có {so_truong} khối/trường, {so_khoa} khoa/viện, {so_nganh} ngành đào tạo.

        [DỮ LIỆU CHI TIẾT TRÍCH XUẤT TỪ DATABASE CHÍNH XÁC 100%]
        Hãy dùng Dữ liệu dưới đây để trả lời. Nếu trống, nghĩa là hệ thống chưa có thông tin chi tiết.
        {thong_tin_db}

        [QUY TẮC CỐT LÕI]
        1. Xưng "mình", gọi "bạn". Trả lời thân thiện, năng động.
        2. NẾU USER HỎI VỀ ĐỊNH HƯỚNG/LỘ TRÌNH (như Web, Cloud, Data...):
           - Hãy sử dụng CÁC MÔN HỌC TRONG TRƯỜNG ở mục Dữ liệu chi tiết để vẽ ra lộ trình.
           - Sắp xếp logic theo: Cơ bản -> Chuyên sâu -> Kỹ năng bổ trợ.
           - KHÔNG tự bịa ra môn học mà trường không dạy. Trình bày dạng danh sách (bullet points) cho dễ nhìn.
        3. Nếu user hỏi thông tin tra cứu thông thường, trả lời cực kỳ ngắn gọn (2-3 câu).
        Câu hỏi của sinh viên: {user_message}
        """

        response = model.generate_content(prompt)
        reply = response.text.replace('**', '<b>').replace('*', '<br>-')

    except Exception as e:
        print(f"Lỗi AI: {e}")
        reply = "Hệ thống AI đang bảo trì. Bạn đợi chút rồi hỏi lại nhé!"

    return jsonify({"reply": reply})
# ==============================================================
# ADMIN ROUTES
# ==============================================================

def check_admin():
    """Kiểm tra xem user có phải admin không"""
    if not session.get('user_id') or session.get('vai_tro') != 'Admin':
        return False
    return True


@course_bp.route('/admin', methods=['GET'])
def admin():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_dashboard.html')


@course_bp.route('/admin/schools', methods=['GET'])
def admin_schools():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_schools.html')


@course_bp.route('/admin/schools/create', methods=['GET', 'POST'])
def admin_school_create():
    if not check_admin():
        return redirect(url_for('course.login'))
    
    if request.method == 'POST':
        ma = request.form.get('ma_truong')
        ten = request.form.get('ten_truong')
        
        if not ma or not ten:
            return render_template('admin_school_form.html', error='Vui lòng nhập đầy đủ thông tin')
        
        school = Truong(ma_truong=ma, ten_truong=ten)
        db.session.add(school)
        db.session.commit()
        return redirect(url_for('course.admin_schools'))
    
    return render_template('admin_school_form.html')


@course_bp.route('/admin/schools/<int:id>/edit', methods=['GET', 'POST'])
def admin_school_edit(id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    school = Truong.query.get_or_404(id)
    
    if request.method == 'POST':
        school.ma_truong = request.form.get('ma_truong', school.ma_truong)
        school.ten_truong = request.form.get('ten_truong', school.ten_truong)
        db.session.commit()
        return redirect(url_for('course.admin_schools'))
    
    return render_template('admin_school_form.html', school=school)


@course_bp.route('/admin/schools/<int:id>', methods=['GET'])
def admin_school_detail(id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    school = Truong.query.get_or_404(id)
    return render_template('admin_school_detail.html', school=school)


@course_bp.route('/admin/schools/<int:school_id>/faculties/create', methods=['GET', 'POST'])
def admin_faculty_create_in_school(school_id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    school = Truong.query.get_or_404(school_id)
    
    if request.method == 'POST':
        faculty_id = request.form.get('faculty_id')
        
        if not faculty_id:
            # Get all available faculties not in this school
            all_faculties = KhoaVien.query.filter(KhoaVien.truong_id != school_id).all()
            return render_template('admin_faculty_form_in_school.html', school=school, faculties=all_faculties, error='Vui lòng chọn Khoa/Viện')
        
        faculty = KhoaVien.query.get_or_404(faculty_id)
        faculty.truong_id = school_id
        db.session.commit()
        return redirect(url_for('course.admin_school_detail', id=school_id))
    
    # Get all available faculties not in this school
    all_faculties = KhoaVien.query.filter(KhoaVien.truong_id != school_id).all()
    return render_template('admin_faculty_form_in_school.html', school=school, faculties=all_faculties)


@course_bp.route('/admin/faculties/<int:faculty_id>/edit', methods=['GET', 'POST'])
def admin_faculty_edit(faculty_id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    faculty = KhoaVien.query.get_or_404(faculty_id)
    
    if request.method == 'POST':
        faculty.ma_khoa = request.form.get('ma_khoa', faculty.ma_khoa)
        faculty.ten_khoa = request.form.get('ten_khoa', faculty.ten_khoa)
        db.session.commit()
        return redirect(url_for('course.admin_school_detail', id=faculty.truong_id))
    
    # Get all available faculties not in this school for edit mode
    all_faculties = KhoaVien.query.filter(KhoaVien.truong_id != faculty.truong_id).all()
    return render_template('admin_faculty_form_in_school.html', school=faculty.truong, faculty=faculty, faculties=all_faculties)


@course_bp.route('/admin/majors/<int:major_id>', methods=['GET', 'POST'])
def admin_major_detail(major_id):
    if not check_admin():
        return redirect(url_for('course.login'))

    major = NganhHoc.query.get_or_404(major_id)

    # Handle POST request (form submission)
    if request.method == 'POST':
        major.ma_nganh = request.form.get('ma_nganh', major.ma_nganh).strip()
        major.ten_nganh = request.form.get('ten_nganh', major.ten_nganh).strip()
        khoa_id = request.form.get('khoa_id')

        if not major.ma_nganh or not major.ten_nganh or not khoa_id:
            return render_template('admin_major_detail.html', major=major,
                                 error='Vui lòng nhập đầy đủ thông tin')

        try:
            major.khoa_id = int(khoa_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return render_template('admin_major_detail.html', major=major,
                                 error='Lỗi khi cập nhật ngành')

    # Get version - either from query param or first available
    version_id = request.args.get('version_id', type=int)

    if version_id:
        version = PhienBanCT.query.filter_by(id=version_id, nganh_id=major_id).first()
    else:
        version = PhienBanCT.query.filter_by(nganh_id=major_id).first()

    curriculum_list = []
    total_credits = 0

    if version:
        curriculum_list = KhungChuongTrinh.query.filter_by(phien_ban_id=version.id) \
            .order_by(KhungChuongTrinh.hoc_ky_du_kien.asc()) \
            .all()
        total_credits = sum(item.hoc_phan.so_tin_chi for item in curriculum_list)

    return render_template('admin_major_detail.html', major=major, version=version,
                         curriculum_list=curriculum_list, total_credits=total_credits)


@course_bp.route('/admin/faculties/<int:faculty_id>/majors/create', methods=['GET', 'POST'])
def admin_faculty_major_create(faculty_id):
    if not check_admin():
        return redirect(url_for('course.login'))

    faculty = KhoaVien.query.get_or_404(faculty_id)

    if request.method == 'POST':
        major_id = request.form.get('major_id', '').strip()

        if not major_id:
            # Get all available majors not in this faculty
            all_majors = NganhHoc.query.filter(NganhHoc.khoa_id != faculty_id).all()
            return render_template(
                'admin_major_form_in_faculty.html',
                school=faculty.truong,
                faculty=faculty,
                majors=all_majors,
                error='Vui lòng chọn ngành học'
            )

        try:
            major = NganhHoc.query.get_or_404(major_id)
            major.khoa_id = faculty_id
            db.session.commit()
            return redirect(url_for('course.admin_faculty_detail', faculty_id=faculty_id))
        except Exception:
            db.session.rollback()
            all_majors = NganhHoc.query.filter(NganhHoc.khoa_id != faculty_id).all()
            return render_template(
                'admin_major_form_in_faculty.html',
                school=faculty.truong,
                faculty=faculty,
                majors=all_majors,
                error='Lỗi khi thêm ngành'
            )

    # Get all available majors not in this faculty
    all_majors = NganhHoc.query.filter(NganhHoc.khoa_id != faculty_id).all()
    return render_template('admin_major_form_in_faculty.html', school=faculty.truong, faculty=faculty, majors=all_majors)


@course_bp.route('/admin/major/create', methods=['GET', 'POST'])
def admin_major_create():
    if not check_admin():
        return redirect(url_for('course.login'))

    if request.method == 'POST':
        ma = request.form.get('ma_nganh', '').strip()
        ten = request.form.get('ten_nganh', '').strip()
        khoa_id = request.form.get('khoa_id')

        if not ma or not ten or not khoa_id:
            return render_template('admin_major_form.html', error='Vui lòng nhập đầy đủ thông tin')

        try:
            major = NganhHoc(khoa_id=int(khoa_id), ma_nganh=ma, ten_nganh=ten)
            db.session.add(major)
            db.session.commit()
            return redirect(url_for('course.admin_faculty_detail', faculty_id=int(khoa_id)))
        except Exception:
            db.session.rollback()
            return render_template('admin_major_form.html', error='Lỗi khi tạo ngành hoặc mã ngành đã tồn tại')

    return render_template('admin_major_form.html')


@course_bp.route('/admin/majors/<int:major_id>/edit', methods=['GET', 'POST'])
def admin_major_edit(major_id):
    if not check_admin():
        return redirect(url_for('course.login'))

    # Redirect to detail page (which now has the form integrated)
    version_id = request.args.get('version_id')
    if version_id:
        return redirect(url_for('course.admin_major_detail', major_id=major_id, version_id=version_id))
    return redirect(url_for('course.admin_major_detail', major_id=major_id))


@course_bp.route('/api/admin/majors/<int:id>', methods=['DELETE'])
def admin_delete_major(id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401

    major = NganhHoc.query.get_or_404(id)

    try:
        # Xóa các phiên bản CT và khung chương trình liên quan trước
        for version in list(major.phien_ban_cts):
            KhungChuongTrinh.query.filter_by(phien_ban_id=version.id).delete(synchronize_session=False)
            db.session.delete(version)

        faculty_id = major.khoa_id
        db.session.delete(major)
        db.session.commit()
        return jsonify({"status": "success", "faculty_id": faculty_id})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Không thể xóa ngành"}), 400


@course_bp.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify({
        "schools": Truong.query.count(),
        "faculties": KhoaVien.query.count(),
        "majors": NganhHoc.query.count(),
        "courses": HocPhan.query.count()
    })


@course_bp.route('/api/admin/schools/<int:id>', methods=['DELETE'])
def admin_delete_school(id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    school = Truong.query.get_or_404(id)
    db.session.delete(school)
    db.session.commit()
    return jsonify({"status": "success"})


@course_bp.route('/api/admin/courses/<int:id>', methods=['DELETE'])
def admin_delete_course(id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    course = HocPhan.query.get_or_404(id)
    # Delete related syllabus entries and their sections
    syllabi = DeCuongChiTiet.query.filter_by(hoc_phan_id=id).all()
    for syllabus in syllabi:
        DeMucDeCuong.query.filter_by(de_cuong_id=syllabus.id).delete(synchronize_session=False)
        db.session.delete(syllabus)
    
    db.session.delete(course)
    db.session.commit()
    return jsonify({"status": "success"})


@course_bp.route('/admin/faculties', methods=['GET'])
def admin_faculties():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_faculties.html')


@course_bp.route('/admin/majors', methods=['GET'])
def admin_majors():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_majors.html')


@course_bp.route('/admin/courses', methods=['GET'])
def admin_courses():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_courses.html')


@course_bp.route('/admin/users', methods=['GET'])
def admin_users():
    if not check_admin():
        return redirect(url_for('course.login'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)


@course_bp.route('/admin/school/create', methods=['GET'])
def admin_school_create_page():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_school_form.html')


@course_bp.route('/admin/faculty/create', methods=['GET', 'POST'])
def admin_faculty_create_form():
    if not check_admin():
        return redirect(url_for('course.login'))

    if request.method == 'POST':
        ma = request.form.get('ma_khoa')
        ten = request.form.get('ten_khoa')
        truong_id = request.form.get('truong_id')

        if not ma or not ten or not truong_id:
            return render_template('admin_faculty_create_form.html', error='Vui lòng nhập đầy đủ thông tin')

        try:
            faculty = KhoaVien(truong_id=int(truong_id), ma_khoa=ma, ten_khoa=ten)
            db.session.add(faculty)
            db.session.commit()
            return redirect(url_for('course.admin_faculties'))
        except:
            return render_template('admin_faculty_create_form.html', error='Lỗi khi tạo Khoa/Viện')

    schools = Truong.query.all()
    return render_template('admin_faculty_create_form.html', schools=schools)


@course_bp.route('/admin/major/create-page', methods=['GET'])
def admin_major_create_page():
  if not check_admin():
    return redirect(url_for('course.login'))
  return redirect(url_for('course.admin_major_create'))


@course_bp.route('/admin/course/create', methods=['GET', 'POST'])
def admin_course_create():
    if not check_admin():
        return redirect(url_for('course.login'))

    if request.method == 'POST':
        ma_hoc_phan = request.form.get('ma_hoc_phan', '').strip()
        ten_hoc_phan = request.form.get('ten_hoc_phan', '').strip()
        so_tin_chi = request.form.get('so_tin_chi', type=int)
        khoa_quan_ly_id = request.form.get('khoa_quan_ly_id', type=int)
        nam_ap_dung = request.form.get('nam_ap_dung', '').strip() or f"{datetime.now().year}-{datetime.now().year + 1}"
        trang_thai = request.form.get('trang_thai', 'Published').strip() or 'Published'
        sections_json = request.form.get('syllabus_sections_json', '').strip()
        header_content = request.form.get('header_content', '').strip()

        if not ma_hoc_phan or not ten_hoc_phan or not so_tin_chi or not khoa_quan_ly_id:
            return render_template('admin_course_form.html', error='Vui lòng nhập đầy đủ thông tin')

        sections = _normalize_section_payload([])
        if sections_json:
            try:
                sections = _normalize_section_payload(json.loads(sections_json))
            except Exception:
                return render_template('admin_course_form.html', error='Dữ liệu đề cương không hợp lệ')

        try:
            course = HocPhan(
                ma_hoc_phan=ma_hoc_phan,
                ten_hoc_phan=ten_hoc_phan,
                so_tin_chi=so_tin_chi,
                khoa_quan_ly_id=khoa_quan_ly_id
            )
            db.session.add(course)
            db.session.flush()

            de_cuong = DeCuongChiTiet(
                hoc_phan_id=course.id,
                nam_ap_dung=nam_ap_dung,
                trang_thai=trang_thai,
                header_content=header_content
            )
            db.session.add(de_cuong)
            db.session.flush()

            for section in sections:
                db.session.add(DeMucDeCuong(
                    de_cuong_id=de_cuong.id,
                    position=section['position'],
                    title=section['title'],
                    content=section['content']
                ))

            db.session.commit()
            return redirect(url_for('course.admin_courses'))
        except Exception:
            db.session.rollback()
            return render_template('admin_course_form.html', error='Lỗi khi tạo học phần. Vui lòng kiểm tra mã học phần có bị trùng không')

    return render_template('admin_course_form.html')


@course_bp.route('/admin/course/<int:id>/edit', methods=['GET', 'POST'])
def admin_course_edit(id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    course = HocPhan.query.get_or_404(id)
    syllabus = DeCuongChiTiet.query.filter_by(hoc_phan_id=id).order_by(DeCuongChiTiet.nam_ap_dung.desc()).first()
    
    if not syllabus:
        return render_template('admin_course_form.html', error='Đề cương chi tiết không tồn tại')
    
    if request.method == 'POST':
        ten_hoc_phan = request.form.get('ten_hoc_phan', '').strip()
        so_tin_chi = request.form.get('so_tin_chi', type=int)
        khoa_quan_ly_id = request.form.get('khoa_quan_ly_id', type=int)
        nam_ap_dung = request.form.get('nam_ap_dung', '').strip() or syllabus.nam_ap_dung
        trang_thai = request.form.get('trang_thai', 'Published').strip() or 'Published'
        sections_json = request.form.get('syllabus_sections_json', '').strip()
        header_content = request.form.get('header_content', '').strip()

        if not ten_hoc_phan or not so_tin_chi or not khoa_quan_ly_id:
            return render_template('admin_course_form.html', error='Vui lòng nhập đầy đủ thông tin', is_edit=True, course=course, syllabus=syllabus)

        sections = _normalize_section_payload([])
        if sections_json:
            try:
                sections = _normalize_section_payload(json.loads(sections_json))
            except Exception:
                return render_template('admin_course_form.html', error='Dữ liệu đề cương không hợp lệ', is_edit=True, course=course, syllabus=syllabus)

        try:
            course.ten_hoc_phan = ten_hoc_phan
            course.so_tin_chi = so_tin_chi
            course.khoa_quan_ly_id = khoa_quan_ly_id
            
            syllabus.nam_ap_dung = nam_ap_dung
            syllabus.trang_thai = trang_thai
            syllabus.header_content = header_content
            
            # Delete old sections
            DeMucDeCuong.query.filter_by(de_cuong_id=syllabus.id).delete()
            
            # Add new sections
            for section in sections:
                db.session.add(DeMucDeCuong(
                    de_cuong_id=syllabus.id,
                    position=section['position'],
                    title=section['title'],
                    content=section['content']
                ))
            
            db.session.commit()
            return redirect(url_for('course.admin_courses'))
        except Exception as e:
            db.session.rollback()
            return render_template('admin_course_form.html', error='Lỗi khi cập nhật học phần', is_edit=True, course=course, syllabus=syllabus)
    
    # GET request - populate form with existing data
    sections_data = [
        {
            'position': s.position,
            'title': s.title,
            'content': s.content
        }
        for s in syllabus.de_mucs
    ]
    
    return render_template('admin_course_form.html', is_edit=True, course=course, syllabus=syllabus, sections_data=sections_data)


@course_bp.route('/api/admin/syllabus/parse-docx', methods=['POST'])
def admin_parse_syllabus_docx():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401

    uploaded = request.files.get('file')
    if not uploaded:
        return jsonify({"error": "Thiếu file upload"}), 400

    filename = (uploaded.filename or '').lower()
    if not filename.endswith('.docx'):
        return jsonify({"error": "Chỉ hỗ trợ định dạng .docx"}), 400

    try:
        sections = _extract_syllabus_sections_from_docx(uploaded)
        return jsonify({"status": "success", "data": sections})
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception:
        return jsonify({"error": "Không đọc được file Word. Vui lòng kiểm tra lại mẫu đề cương."}), 400


@course_bp.route('/admin/user/create', methods=['GET'])
def admin_user_create():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_user_form.html')


@course_bp.route('/api/admin/versions/major/<int:major_id>', methods=['GET'])
def admin_get_versions(major_id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    versions = PhienBanCT.query.filter_by(nganh_id=major_id).all()
    data = [{
        "id": v.id,
        "ma_phien_ban": v.ma_phien_ban,
        "nam_bat_dau": v.nam_bat_dau
    } for v in versions]

    return jsonify({"status": "success", "data": data})


@course_bp.route('/api/admin/versions', methods=['POST'])
def admin_create_version():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        nganh_id = data.get('nganh_id')
        ma_phien_ban = data.get('ma_phien_ban', '').strip()
        nam_bat_dau = data.get('nam_bat_dau')

        if not ma_phien_ban or not nam_bat_dau:
            return jsonify({"error": "Thiếu mã phiên bản hoặc năm"}), 400

        # Check if version already exists
        existing = PhienBanCT.query.filter_by(
            nganh_id=int(nganh_id),
            ma_phien_ban=ma_phien_ban
        ).first()

        if existing:
            return jsonify({"error": "Phiên bản này đã tồn tại"}), 400

        version = PhienBanCT(
            nganh_id=int(nganh_id),
            ma_phien_ban=ma_phien_ban,
            nam_bat_dau=int(nam_bat_dau)
        )
        db.session.add(version)
        db.session.commit()
        return jsonify({"status": "success", "data": {
            "id": version.id,
            "ma_phien_ban": version.ma_phien_ban,
            "nam_bat_dau": version.nam_bat_dau
        }})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Lỗi: {str(e)}"}), 400


@course_bp.route('/api/admin/courses/available', methods=['GET'])
def admin_get_available_courses():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401

    major_id = request.args.get('major_id', type=int)
    version_id = request.args.get('version_id', type=int)

    # Lấy danh sách học phần chưa được thêm vào phiên bản này
    existing = db.session.query(KhungChuongTrinh.hoc_phan_id).filter_by(phien_ban_id=version_id).all()
    existing_ids = [e[0] for e in existing]

    # Lấy tất cả học phần trừ những cái đã có
    if existing_ids:
        courses = HocPhan.query.filter(HocPhan.id.notin_(existing_ids)).all()
    else:
        courses = HocPhan.query.all()

    data = [{
        "id": c.id,
        "ma": c.ma_hoc_phan,
        "ten": c.ten_hoc_phan,
        "tin_chi": c.so_tin_chi,
        "khoa": c.khoa_quan_ly.ten_khoa if c.khoa_quan_ly else ""
    } for c in courses]

    return jsonify({"status": "success", "data": data})


@course_bp.route('/api/admin/curriculum', methods=['POST'])
def admin_add_curriculum():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        phien_ban_id = data.get('phien_ban_id')
        hoc_phan_id = data.get('hoc_phan_id')
        hoc_ky = data.get('hoc_ky', 1)
        loai_mon = data.get('loai_mon', 'Bắt buộc')

        if not phien_ban_id or not hoc_phan_id:
            return jsonify({"error": "Thiếu phiên bản hoặc học phần"}), 400

        # Check if already exists
        existing = KhungChuongTrinh.query.filter_by(
            phien_ban_id=int(phien_ban_id),
            hoc_phan_id=int(hoc_phan_id)
        ).first()

        if existing:
            return jsonify({"error": "Học phần này đã có trong phiên bản này"}), 400

        curriculum = KhungChuongTrinh(
            phien_ban_id=int(phien_ban_id),
            hoc_phan_id=int(hoc_phan_id),
            hoc_ky_du_kien=int(hoc_ky),
            loai_mon=loai_mon
        )
        db.session.add(curriculum)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Lỗi: {str(e)}"}), 400


@course_bp.route('/api/admin/curriculum/<int:phien_ban_id>/<int:hoc_phan_id>', methods=['DELETE'])
def admin_delete_curriculum(phien_ban_id, hoc_phan_id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        curriculum = KhungChuongTrinh.query.filter_by(
            phien_ban_id=phien_ban_id,
            hoc_phan_id=hoc_phan_id
        ).first()

        if not curriculum:
            return jsonify({"error": "Không tìm thấy"}), 404

        db.session.delete(curriculum)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
