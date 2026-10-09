"""Cấu hình riêng của agent; thiếu định danh thì dừng trước khi kết nối.

VÌ SAO TÁCH RIÊNG
    Máy bán hàng có thể chạy khi server mẹ mất mạng. Agent phải tự kiểm ID,
    URL HTTPS và CA trước khi tạo kênh, thay vì mượn mặc định ID=1 của POS.

CÁCH DÙNG VÀ KIỂM
    from agent.config import load_config
    config = load_config()  # đọc biến môi trường của service agent
    python3 -m unittest agent.tests.test_config -v

    Cần QRPROTO_MACHINE_ID, FLEXMIX_AGENT_URL, FLEXMIX_AGENT_CA; có thể đặt
    FLEXMIX_AGENT_STATE_DIR. Lệnh kiểm chỉ dùng dữ liệu giả, không gọi mạng.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agent.net import Endpoint


@dataclass(frozen=True)
class AgentConfig:
    machine_id: int
    endpoint: Endpoint
    state_dir: Path


def load_config(environ=None) -> AgentConfig:
    env = os.environ if environ is None else environ
    raw_id = env.get("QRPROTO_MACHINE_ID", "")
    if not raw_id.isascii() or not raw_id.isdecimal():
        raise ValueError("Thiếu hoặc sai QRPROTO_MACHINE_ID")
    machine_id = int(raw_id)
    if not 1 <= machine_id <= 999999:
        raise ValueError("QRPROTO_MACHINE_ID ngoài miền")
    ca_path = env.get("FLEXMIX_AGENT_CA", "")
    if not ca_path:
        raise ValueError("Thiếu FLEXMIX_AGENT_CA")
    endpoint = Endpoint(env.get("FLEXMIX_AGENT_URL", ""), Path(ca_path))
    state_dir = Path(env.get("FLEXMIX_AGENT_STATE_DIR", "/var/lib/flexmix-agent"))
    if not state_dir.is_absolute():
        raise ValueError("Thư mục trạng thái phải là đường dẫn tuyệt đối")
    return AgentConfig(machine_id, endpoint, state_dir)
