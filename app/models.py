from . import db
from datetime import datetime


# 0. USER AUTHENTICATION (NGƯỜI DÙNG)
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    ho_ten = db.Column(db.String(255), nullable=False)
    vai_tro = db.Column(db.String(20), default='User')  # 'User' hoặc 'Admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# 1. QUẢN LÝ HÀNH CHÍNH
class Truong(db.Model):
    __tablename__ = 'truong'
    id = db.Column(db.Integer, primary_key=True)
    ma_truong = db.Column(db.String(20), unique=True, nullable=False)
    ten_truong = db.Column(db.String(255), nullable=False)
    khoas = db.relationship('KhoaVien', backref='truong', lazy=True)


class KhoaVien(db.Model):
    __tablename__ = 'khoa_vien'
    id = db.Column(db.Integer, primary_key=True)
    truong_id = db.Column(db.Integer, db.ForeignKey('truong.id'), nullable=False)
    ma_khoa = db.Column(db.String(20), unique=True, nullable=False)
    ten_khoa = db.Column(db.String(255), nullable=False)
    nganhs = db.relationship('NganhHoc', backref='khoa', lazy=True)
    hoc_phans = db.relationship('HocPhan', backref='khoa_quan_ly', lazy=True)


class NganhHoc(db.Model):
    __tablename__ = 'nganh_hoc'
    id = db.Column(db.Integer, primary_key=True)
    khoa_id = db.Column(db.Integer, db.ForeignKey('khoa_vien.id'), nullable=False)
    ma_nganh = db.Column(db.String(20), unique=True, nullable=False)
    ten_nganh = db.Column(db.String(255), nullable=False)
    phien_ban_cts = db.relationship('PhienBanCT', backref='nganh', lazy=True)


# 2. KHUNG CHƯƠNG TRÌNH ĐÀO TẠO
class PhienBanCT(db.Model):
    __tablename__ = 'phien_ban_ct'
    id = db.Column(db.Integer, primary_key=True)
    nganh_id = db.Column(db.Integer, db.ForeignKey('nganh_hoc.id'), nullable=False)
    ma_phien_ban = db.Column(db.String(50), nullable=False)  # VD: K66_KHMT
    nam_bat_dau = db.Column(db.Integer)
    khung_chuong_trinhs = db.relationship('KhungChuongTrinh', backref='phien_ban', lazy=True)


class KhungChuongTrinh(db.Model):
    __tablename__ = 'khung_chuong_trinh'
    phien_ban_id = db.Column(db.Integer, db.ForeignKey('phien_ban_ct.id'), primary_key=True)
    hoc_phan_id = db.Column(db.Integer, db.ForeignKey('hoc_phan.id'), primary_key=True)
    hoc_ky_du_kien = db.Column(db.Integer)
    loai_mon = db.Column(db.String(50))  # Bắt buộc / Tự chọn

    hoc_phan = db.relationship('HocPhan', backref='khung_chuong_trinhs', lazy=True)


# 3. HỌC PHẦN VÀ ĐỀ CƯƠNG CHI TIẾT
class HocPhan(db.Model):
    __tablename__ = 'hoc_phan'
    id = db.Column(db.Integer, primary_key=True)
    khoa_quan_ly_id = db.Column(db.Integer, db.ForeignKey('khoa_vien.id'), nullable=False)
    ma_hoc_phan = db.Column(db.String(20), unique=True, nullable=False)
    ten_hoc_phan = db.Column(db.String(255), nullable=False)
    so_tin_chi = db.Column(db.Integer, nullable=False)
    de_cuongs = db.relationship('DeCuongChiTiet', backref='hoc_phan', lazy=True)


class DeCuongChiTiet(db.Model):
    __tablename__ = 'de_cuong_chi_tiet'
    id = db.Column(db.Integer, primary_key=True)
    hoc_phan_id = db.Column(db.Integer, db.ForeignKey('hoc_phan.id'), nullable=False)
    nam_ap_dung = db.Column(db.String(50), nullable=False)
    trang_thai = db.Column(db.String(20), default='Published')

    clos = db.relationship('ChuanDauRa', backref='de_cuong', lazy=True)
    lich_trinh = db.relationship('KeHoachGiangDay', backref='de_cuong', lazy=True)
    danh_gia = db.relationship('DanhGiaHocPhan', backref='de_cuong', lazy=True)
    hoc_lieu = db.relationship('HocLieu', backref='de_cuong', lazy=True)


# 4. CHI TIẾT NỘI DUNG ĐỀ CƯƠNG
class ChuanDauRa(db.Model):
    __tablename__ = 'chuan_dau_ra'
    id = db.Column(db.Integer, primary_key=True)
    de_cuong_id = db.Column(db.Integer, db.ForeignKey('de_cuong_chi_tiet.id'), nullable=False)
    ma_clo = db.Column(db.String(10))
    mo_ta = db.Column(db.Text)


class KeHoachGiangDay(db.Model):
    __tablename__ = 'ke_hoach_giang_day'
    id = db.Column(db.Integer, primary_key=True)
    de_cuong_id = db.Column(db.Integer, db.ForeignKey('de_cuong_chi_tiet.id'), nullable=False)
    tuan_thu = db.Column(db.Integer)
    chu_de_bai_hoc = db.Column(db.String(255))
    noi_dung_chi_tiet = db.Column(db.Text)


class DanhGiaHocPhan(db.Model):
    __tablename__ = 'danh_gia_hoc_phan'
    id = db.Column(db.Integer, primary_key=True)
    de_cuong_id = db.Column(db.Integer, db.ForeignKey('de_cuong_chi_tiet.id'), nullable=False)
    thanh_phan = db.Column(db.String(100))  # Giữa kỳ, Cuối kỳ
    trong_so = db.Column(db.Float)
    hinh_thuc = db.Column(db.String(255))


class HocLieu(db.Model):
    __tablename__ = 'hoc_lieu'
    id = db.Column(db.Integer, primary_key=True)
    de_cuong_id = db.Column(db.Integer, db.ForeignKey('de_cuong_chi_tiet.id'), nullable=False)
    loai = db.Column(db.String(50))
    ten_tai_lieu = db.Column(db.String(255))
    tac_gia = db.Column(db.String(255))


