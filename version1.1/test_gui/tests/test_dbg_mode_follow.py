"""Test tái hiện DBG-01 và DBG-02: hai trang đi theo test_gui/mode.json lệch nhau.

VÌ SAO CÓ FILE NÀY
    Cả hai trang lấy "mốc" id ở lần poll đầu và chỉ phản ứng khi id ĐỔI.
    Hệ quả:
      DBG-01  chế độ test tắt trong lúc trang test đang nạp -> trang test lấy
              mốc là id "đã tắt", không bao giờ quay về màn bán hàng (kẹt ở
              test_gui dù máy đã nhận đơn lại).
      DBG-02  trình duyệt nạp lại khi chế độ test đang bật -> trang bán hàng
              lấy mốc là id "đang bật", đứng ở menu, không báo gì; mọi lần
              gọi món bị /api/start trả 409.

    Chạy mã JS thật qua node (xem dbg_mode_follow_harness.js). Hai test này
    FAIL khi lỗi còn -- đó là bằng chứng.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent / "dbg_mode_follow_harness.js"


@pytest.fixture(scope="module")
def result():
    node = shutil.which("node")
    if node is None:
        pytest.skip("không có node trên máy này")
    done = subprocess.run([node, str(HARNESS)], capture_output=True,
                          text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_trang_test_phai_quay_ve_khi_che_do_tat_luc_dang_nap(result):
    stranded = result["stranded"]
    assert stranded["jumped"], "trang bán hàng không nhảy sang trang test"
    assert stranded["test_page_went_back"], (
        "Chế độ test tắt trước lần poll đầu của trang test: trang test lấy "
        "mốc id 'đã tắt' và đứng yên mãi ở test_gui."
    )


def test_trang_ban_hang_nap_lai_luc_che_do_bat_khong_duoc_im_lang(result):
    reload = result["reload_while_open"]
    assert reload["store_navigated"] or reload["store_notices"] > 0, (
        "Trang bán hàng nạp lại khi máy đang ở chế độ test: không chuyển "
        "trang, không báo gì, nhưng mọi đơn đều bị từ chối."
    )
