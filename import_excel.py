import random
from app import create_app, db
from app.models import (Truong, KhoaVien, NganhHoc, PhienBanCT, KhungChuongTrinh,
                        HocPhan, DeCuongChiTiet, ChuanDauRa, KeHoachGiangDay, DanhGiaHocPhan, HocLieu)

# =========================================================================
# 1. BỘ DỮ LIỆU ĐƯỢC THIẾT KẾ ĐÚNG CHUẨN: 3 TRƯỜNG - 26 KHOA - 52 NGÀNH - 104 MÔN
# =========================================================================

# ĐÚNG 26 MÔN ĐẠI CƯƠNG CHUNG (Ngành nào cũng phải học)
MON_CHUNG = [
    ("DC01", "Triết học Mác - Lênin"), ("DC02", "Kinh tế chính trị Mác - Lênin"),
    ("DC03", "Chủ nghĩa xã hội khoa học"), ("DC04", "Lịch sử Đảng Cộng sản VN"),
    ("DC05", "Tư tưởng Hồ Chí Minh"), ("DC06", "Ngoại ngữ cơ bản 1"),
    ("DC07", "Ngoại ngữ cơ bản 2"), ("DC08", "Ngoại ngữ chuyên ngành"),
    ("DC09", "Giáo dục thể chất 1"), ("DC10", "Giáo dục thể chất 2"),
    ("DC11", "Giáo dục quốc phòng an ninh"), ("DC12", "Toán cao cấp 1"),
    ("DC13", "Toán cao cấp 2"), ("DC14", "Xác suất thống kê"),
    ("DC15", "Toán kinh tế"), ("DC16", "Pháp luật đại cương"),
    ("DC17", "Tin học đại cương"), ("DC18", "Kỹ năng mềm"),
    ("DC19", "Tâm lý học đại cương"), ("DC20", "Xã hội học đại cương"),
    ("DC21", "Khởi nghiệp kinh doanh"), ("DC22", "Kinh tế vi mô 1"),
    ("DC23", "Kinh tế vĩ mô 1"), ("DC24", "Phương pháp nghiên cứu khoa học"),
    ("DC25", "Lịch sử kinh tế quốc dân"), ("DC26", "Quản trị học căn bản")
]

# ĐÚNG 3 TRƯỜNG, 26 KHOA, 52 NGÀNH VÀ 78 MÔN CHUYÊN NGÀNH
NGANH_DATA = {
    "Trường Công nghệ": {  # 9 KHOA
        "Viện Công nghệ thông tin": {"nganh": ["Khoa học máy tính", "Kỹ thuật phần mềm"],
                                     "mon": ["Lập trình C++", "Cấu trúc dữ liệu", "Hệ điều hành"]},
        "Khoa Khoa học dữ liệu": {"nganh": ["Khoa học dữ liệu", "Trí tuệ nhân tạo"],
                                  "mon": ["Toán cho AI", "Machine Learning", "Deep Learning"]},
        "Khoa Hệ thống thông tin": {"nganh": ["HTTT Quản lý", "Thương mại điện tử"],
                                    "mon": ["Phân tích thiết kế hệ thống", "Hệ thống ERP", "Quản trị dự án CNTT"]},
        "Khoa Toán kinh tế": {"nganh": ["Toán kinh tế", "Toán tài chính"],
                              "mon": ["Quy hoạch tuyến tính", "Mô hình toán kinh tế", "Tối ưu hóa"]},
        "Khoa Thống kê": {"nganh": ["Thống kê kinh tế", "Thống kê kinh doanh"],
                          "mon": ["Nguyên lý thống kê", "Thống kê ứng dụng", "Phân tích dữ liệu"]},
        "Khoa Mạng máy tính": {"nganh": ["An toàn thông tin", "Mạng máy tính"],
                               "mon": ["Mạng căn bản", "Mật mã học", "An ninh mạng"]},
        "Khoa Kỹ thuật điện tử": {"nganh": ["IoT và Vi mạch", "Kỹ thuật điện tử"],
                                  "mon": ["Mạch điện tử", "Vi điều khiển", "Hệ thống nhúng"]},
        "Khoa Công nghệ giáo dục": {"nganh": ["Sư phạm công nghệ", "Công nghệ giáo dục"],
                                    "mon": ["E-Learning", "Thiết kế bài giảng số", "Tâm lý giáo dục số"]},
        "Khoa Cơ sở tự nhiên": {"nganh": ["Khoa học tự nhiên", "Kỹ thuật môi trường"],
                                "mon": ["Môi trường học", "Sinh thái học", "Biến đổi khí hậu"]}
    },
    "Trường Kinh doanh": {  # 9 KHOA
        "Khoa Quản trị Kinh doanh": {"nganh": ["Quản trị doanh nghiệp", "Khởi nghiệp"],
                                     "mon": ["Quản trị chiến lược", "Lãnh đạo", "Quản trị rủi ro"]},
        "Khoa Marketing": {"nganh": ["Marketing số", "Quản trị thương hiệu"],
                           "mon": ["Nghiên cứu thị trường", "Hành vi khách hàng", "PR và Sự kiện"]},
        "Khoa Du lịch & Khách sạn": {"nganh": ["Quản trị khách sạn", "Quản trị lữ hành"],
                                     "mon": ["Tổng quan du lịch", "Nghiệp vụ Lễ tân", "Quản trị nhà hàng"]},
        "Viện Kế toán": {"nganh": ["Kế toán doanh nghiệp", "Kế toán công"],
                         "mon": ["Nguyên lý kế toán", "Kế toán tài chính", "Kế toán quản trị"]},
        "Viện Kiểm toán": {"nganh": ["Kiểm toán độc lập", "Kiểm toán nội bộ"],
                           "mon": ["Kiểm toán căn bản", "Đạo đức nghề nghiệp", "Kiểm toán BCTC"]},
        "Khoa Bất động sản": {"nganh": ["Kinh doanh BĐS", "Quản lý đất đai"],
                              "mon": ["Thị trường BĐS", "Định giá BĐS", "Quản lý dự án BĐS"]},
        "Viện Ngân hàng": {"nganh": ["Ngân hàng thương mại", "Ngân hàng đầu tư"],
                           "mon": ["Tài chính tiền tệ", "Nghiệp vụ NHTM", "Thanh toán quốc tế"]},
        "Viện Tài chính": {"nganh": ["Tài chính doanh nghiệp", "Thuế"],
                           "mon": ["Tài chính công", "Nghiệp vụ Thuế", "Phân tích tài chính"]},
        "Viện Thương mại & Kinh tế quốc tế": {"nganh": ["Kinh tế quốc tế", "Logistics"],
                                              "mon": ["Giao dịch TMQT", "Vận tải quốc tế", "Chuỗi cung ứng"]}
    },
    "Trường Kinh tế và Quản lý công": {  # 8 KHOA
        "Khoa Kinh tế học": {"nganh": ["Kinh tế vi mô", "Kinh tế vĩ mô"],
                             "mon": ["Kinh tế vi mô 2", "Kinh tế vĩ mô 2", "Lịch sử các học thuyết KT"]},
        "Khoa Khoa học quản lý": {"nganh": ["Quản lý công", "Quản lý kinh tế"],
                                  "mon": ["Khoa học quản lý", "Chính sách công", "Quản lý nhà nước"]},
        "Khoa Luật": {"nganh": ["Luật Kinh tế", "Luật thương mại"],
                      "mon": ["Luật Dân sự", "Luật Hình sự", "Luật Doanh nghiệp"]},
        "Khoa Ngoại ngữ Kinh tế": {"nganh": ["Ngôn ngữ Anh", "Tiếng Anh thương mại"],
                                   "mon": ["Biên dịch kinh tế", "Phiên dịch", "Giao tiếp liên văn hóa"]},
        "Khoa Kế hoạch & Phát triển": {"nganh": ["Kinh tế phát triển", "Kế hoạch hóa"],
                                       "mon": ["Kinh tế phát triển", "Kế hoạch phát triển", "Đánh giá dự án"]},
        "Khoa Nguồn nhân lực": {"nganh": ["Quản trị nhân lực", "Kinh tế lao động"],
                                "mon": ["Quản trị nhân sự", "Luật lao động", "Tiền lương"]},
        "Khoa Lý luận chính trị": {"nganh": ["Triết học", "Kinh tế chính trị"],
                                   "mon": ["Triết học chuyên sâu", "KTCT ứng dụng", "Lịch sử Đảng chuyên sâu"]},
        "Khoa Đầu tư": {"nganh": ["Kinh tế đầu tư", "Quản lý đầu tư"],
                        "mon": ["Lập dự án đầu tư", "Thẩm định dự án", "Đầu tư quốc tế"]}
    }
}


def generate_database():
    app = create_app()
    with app.app_context():
        print("⏳ Đang reset Database (Cảnh báo: Dữ liệu cũ sẽ bị xóa sạch)...")
        db.drop_all()
        db.create_all()

        # =========================================================
        # TẠO 26 MÔN ĐẠI CƯƠNG VÀO DATABASE (Tổng môn: 26)
        # =========================================================
        print("⏳ Đang tạo 26 môn đại cương chung...")
        khoa_chung = KhoaVien(ma_khoa="K_CHUNG", ten_khoa="Khối kiến thức chung",
                              truong=Truong(ma_truong="NEU_BASE", ten_truong="Khối Đại Cương"))
        db.session.add(khoa_chung)
        db.session.flush()

        dict_mon_chung = []
        for ma, ten in MON_CHUNG:
            mon = HocPhan(khoa_quan_ly_id=khoa_chung.id, ma_hoc_phan=ma, ten_hoc_phan=ten, so_tin_chi=3)
            db.session.add(mon)
            dict_mon_chung.append(mon)
        db.session.flush()

        # =========================================================
        # TẠO 3 TRƯỜNG, 26 KHOA, 52 NGÀNH VÀ 78 MÔN CHUYÊN NGÀNH (Tổng môn: 104)
        # =========================================================
        print("⏳ Đang tạo Hệ thống 3 Trường, 26 Khoa, 52 Ngành và Khung chương trình...")
        ma_nganh_counter = 7000
        ma_mon_chuyen_counter = 100

        for ten_truong, khoas in NGANH_DATA.items():
            truong = Truong(ma_truong=f"TR_{random.randint(10, 99)}", ten_truong=ten_truong)
            db.session.add(truong)
            db.session.flush()

            for ten_khoa, data_khoa in khoas.items():
                khoa = KhoaVien(truong_id=truong.id, ma_khoa=f"KHOA_{random.randint(100, 999)}", ten_khoa=ten_khoa)
                db.session.add(khoa)
                db.session.flush()

                # Tạo 3 môn chuyên ngành cho Khoa này
                danh_sach_mon_chuyen_cua_khoa = []
                for ten_mc in data_khoa["mon"]:
                    ma_mon_chuyen_counter += 1
                    mon_cn = HocPhan(khoa_quan_ly_id=khoa.id, ma_hoc_phan=f"CN{ma_mon_chuyen_counter}",
                                     ten_hoc_phan=ten_mc, so_tin_chi=3)
                    db.session.add(mon_cn)
                    danh_sach_mon_chuyen_cua_khoa.append(mon_cn)
                db.session.flush()

                # Tạo 2 Ngành cho Khoa này
                for ten_nganh in data_khoa["nganh"]:
                    ma_nganh_counter += 1
                    nganh = NganhHoc(khoa_id=khoa.id, ma_nganh=str(ma_nganh_counter), ten_nganh=ten_nganh)
                    db.session.add(nganh)
                    db.session.flush()

                    phien_ban = PhienBanCT(nganh_id=nganh.id, ma_phien_ban="K66", nam_bat_dau=2024)
                    db.session.add(phien_ban)
                    db.session.flush()

                    # GẮN MÔN VÀO KHUNG CHƯƠNG TRÌNH CHO NGÀNH NÀY (Mỗi ngành sẽ học 29 môn)
                    # 1. Gắn 26 môn chung (Phân bổ từ Kỳ 1 đến Kỳ 4)
                    for idx, mon_c in enumerate(dict_mon_chung):
                        ky_du_kien = (idx // 7) + 1  # 7 môn mỗi kỳ
                        db.session.add(
                            KhungChuongTrinh(phien_ban_id=phien_ban.id, hoc_phan_id=mon_c.id, hoc_ky_du_kien=ky_du_kien,
                                             loai_mon="Bắt buộc"))

                    # 2. Gắn 3 môn chuyên ngành (Phân bổ vào Kỳ 5)
                    for mon_cn in danh_sach_mon_chuyen_cua_khoa:
                        db.session.add(
                            KhungChuongTrinh(phien_ban_id=phien_ban.id, hoc_phan_id=mon_cn.id, hoc_ky_du_kien=5,
                                             loai_mon="Chuyên ngành"))

        db.session.commit()

        # =========================================================
        # AUTO SINH ĐỀ CƯƠNG CHI TIẾT CHO ĐÚNG 104 MÔN
        # =========================================================
        print("⏳ Đang sinh tự động Đề cương, CLO, Lịch trình cho chính xác 104 môn học...")
        tat_ca_mon = HocPhan.query.all()
        for mon in tat_ca_mon:
            de_cuong = DeCuongChiTiet(hoc_phan_id=mon.id, nam_ap_dung="2024-2025", trang_thai='Published')
            db.session.add(de_cuong)
            db.session.flush()

            # Sinh CLO
            db.session.add(
                ChuanDauRa(de_cuong_id=de_cuong.id, ma_clo="CLO1", mo_ta=f"Nắm vững lý thuyết {mon.ten_hoc_phan}"))
            db.session.add(ChuanDauRa(de_cuong_id=de_cuong.id, ma_clo="CLO2",
                                      mo_ta="Vận dụng kỹ năng phân tích và giải quyết vấn đề"))

            # Sinh Đánh giá
            db.session.add(
                DanhGiaHocPhan(de_cuong_id=de_cuong.id, thanh_phan="Chuyên cần", trong_so=0.1, hinh_thuc="Điểm danh"))
            db.session.add(
                DanhGiaHocPhan(de_cuong_id=de_cuong.id, thanh_phan="Giữa kỳ", trong_so=0.4, hinh_thuc="Bài tập lớn"))
            db.session.add(
                DanhGiaHocPhan(de_cuong_id=de_cuong.id, thanh_phan="Cuối kỳ", trong_so=0.5, hinh_thuc="Thi tập trung"))

            # Sinh Lịch trình
            for tuan in range(1, 16):
                db.session.add(
                    KeHoachGiangDay(de_cuong_id=de_cuong.id, tuan_thu=tuan, chu_de_bai_hoc=f"Chủ đề tuần {tuan}",
                                    noi_dung_chi_tiet=f"Nội dung trọng tâm môn {mon.ten_hoc_phan}"))

            db.session.add(HocLieu(de_cuong_id=de_cuong.id, loai="Giáo trình",
                                   ten_tai_lieu=f"Giáo trình {mon.ten_hoc_phan} căn bản",
                                   tac_gia="NXB Đại học Kinh tế Quốc dân"))
            db.session.add(
                HocLieu(de_cuong_id=de_cuong.id, loai="Tham khảo", ten_tai_lieu=f"Tài liệu bài tập {mon.ten_hoc_phan}",
                        tac_gia="Bộ môn biên soạn"))
            # ----------
        db.session.commit()

        print("\n" + "=" * 50)
        print("🚀 HOÀN TẤT SINH DỮ LIỆU SIÊU KHỦNG!")
        print(f"Tổng số Trường: {Truong.query.count() - 1} (Không tính khối chung)")
        print(f"Tổng số Khoa/Viện: {KhoaVien.query.count() - 1} (Không tính khối chung)")
        print(f"Tổng số Ngành Đào tạo: {NganhHoc.query.count()}")
        print(f"Tổng số Môn học (Học phần): {HocPhan.query.count()}")
        print(f"Tổng số Đề cương chi tiết: {DeCuongChiTiet.query.count()}")
        print("=" * 50)


if __name__ == '__main__':
    generate_database()