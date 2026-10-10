"""Kịch bản stress CRC menu: đổi menu liên tục qua flow thật, đối chiếu với oracle độc lập.

Mỗi vòng chọn một kiểu đột biến (giá, bật/tắt, đổi tên trên máy, cập nhật cũ, cập nhật sai...),
sau đó kiểm: version của flow thật == CRC oracle, packet hợp lệ, version đổi <=> menu đổi.
Cuối cùng khôi phục menu gốc (luôn chạy, kể cả khi vòng lặp lỗi).
"""

from __future__ import annotations

import json
import random
import time
import traceback
from dataclasses import dataclass, field

from . import oracle

WEIGHTS = {
    "price_tweak": 25, "toggle_available": 15, "batch_mix": 15, "rename": 15,
    "noop": 10, "stale_update": 10, "invalid_update": 10,
}
CHUNK = 200
SUFFIXES = (" ✨", " đặc biệt", " (mới)", " Phở Ngọt", " 🧋", " ỷ ỡ ặ", " size L", " ít đá")
NAMES = ("Cà phê sữa đá", "Trà đào cam sả", "Sinh tố bơ 🥑", "Nước ép ổi", "Bạc xỉu",
         "Trà sữa trân châu", "Chè khúc bạch", "Ca cao nóng ☕", "Matcha latte", "Soda việt quất")


@dataclass
class Stats:
    checks: dict = field(default_factory=dict)      # tên -> [pass, fail]
    failures: list = field(default_factory=list)    # (vòng, check, chi tiết)
    mutations: dict = field(default_factory=dict)   # kiểu -> số lần
    versions: dict = field(default_factory=dict)    # bytes chuẩn -> version
    collisions: list = field(default_factory=list)  # (version, mô tả)
    iterations: int = 0
    seed: int = 0
    duration: float = 0.0

    def check(self, name: str, cond: bool, it: int, detail: str = "") -> bool:
        cell = self.checks.setdefault(name, [0, 0])
        cell[0 if cond else 1] += 1
        if not cond:
            self.failures.append((it, name, detail))
        return cond

    def fail(self, it: int, name: str, detail: str) -> None:
        self.check(name, False, it, detail)

    def ok(self) -> bool:
        return not self.failures and not self.collisions and bool(self.checks)

    def see(self, data: bytes, version: int, it: int) -> None:
        """Ghi menu đã thấy; cùng version mà khác bytes là va chạm CRC."""
        old = self.versions.get(data)
        if old is not None and old != version:
            self.fail(it, "crc_deterministic", f"cùng menu nhưng version {old} != {version}")
        self.versions[data] = version
        for other, v in self.versions.items():
            if v == version and other != data:
                self.collisions.append((version, f"vòng {it}: 2 menu khác nhau cùng CRC {version}"))
                break

    def to_dict(self) -> dict:
        return {
            "ok": self.ok(), "iterations": self.iterations, "seed": self.seed,
            "duration_s": round(self.duration, 3), "checks": self.checks,
            "mutations": self.mutations, "distinct_menus": len(self.versions),
            "collisions": self.collisions,
            "failures": [{"iteration": i, "check": c, "detail": d} for i, c, d in self.failures],
        }

    def report(self) -> str:
        w = max([len(k) for k in self.checks] + [32])
        lines = ["", "=== BÁO CÁO STRESS CRC MENU ===",
                 f"Số vòng: {self.iterations} | seed: {self.seed} | thời gian: {self.duration:.2f}s",
                 "", f"{'Kiểm tra':<{w}} | {'pass':>6} | {'fail':>6}", "-" * (w + 18)]
        for name, (p, f) in self.checks.items():
            lines.append(f"{name:<{w}} | {p:>6} | {f:>6}")
        lines += ["", "Đột biến đã chạy:"]
        lines += [f"  {k:<18} {v}" for k, v in sorted(self.mutations.items())]
        lines += ["", f"Số menu khác nhau: {len(self.versions)}",
                  f"Va chạm CRC: {len(self.collisions)}"]
        lines += [f"  {d}" for _, d in self.collisions[:10]]
        if self.failures:
            lines += ["", f"Lỗi đầu tiên ({min(10, len(self.failures))}/{len(self.failures)}):"]
            lines += [f"  [vòng {i}] {c}: {d}" for i, c, d in self.failures[:10]]
        lines += ["", "KẾT QUẢ: " + ("PASS" if self.ok() else "FAIL"), ""]
        return "\n".join(lines)


class _Runner:
    """Giữ trạng thái 'app' (app_version) và các bước kiểm sau mỗi đột biến."""

    def __init__(self, h, rng: random.Random, stats: Stats):
        self.h, self.rng, self.st = h, rng, stats
        self.db = h.machine_db
        self.app_version = 0
        self.old_versions: list[int] = []
        self.it = 0

    # --- tiện ích ---
    def rows(self) -> list[list]:
        return oracle.read_rows(self.db)

    def snapshot(self) -> tuple[bytes, int]:
        data = oracle.canonical_bytes(self.rows())
        return data, oracle.crc32(data)

    def col(self, name: str) -> int:
        return oracle.FIELDS.index(name)

    def set_app(self, version: int) -> None:
        if version != self.app_version:
            self.old_versions.append(self.app_version)
            self.old_versions = self.old_versions[-20:]
        self.app_version = version

    def verify_ok(self, status: int, r: dict, label: str) -> bool:
        """Kiểm phản hồi ok: http, version flow == oracle, packet hợp lệ."""
        st, it = self.st, self.it
        if not st.check("http_ok", status == 200 and r.get("status") in ("ok", "conflict", "up_to_date"),
                        it, f"{label}: HTTP {status} {str(r)[:200]}"):
            return False
        expect = oracle.expected_version(self.db)
        st.check("flow_version_eq_oracle", r.get("menu_version") == expect, it,
                 f"{label}: flow={r.get('menu_version')} oracle={expect}")
        if "packet" not in r:
            if r.get("status") != "up_to_date":
                st.fail(it, "packet_valid", f"{label}: status={r.get('status')} mà thiếu packet")
        else:
            errs = oracle.check_packet(r["packet"], self.db)
            st.check("packet_valid", not errs, it, f"{label}: {'; '.join(errs)[:300]}")
        return True

    def check_changed(self, before: tuple[bytes, int], after_version: int, label: str) -> None:
        data_after, _ = self.snapshot()
        b_changed = before[0] != data_after
        v_changed = before[1] != after_version
        if b_changed and not v_changed:
            self.st.collisions.append((after_version, f"vòng {self.it} {label}: menu đổi mà CRC giữ nguyên"))
        self.st.check("version_changed_iff_menu_changed", b_changed == v_changed, self.it,
                      f"{label}: bytes_changed={b_changed} version_changed={v_changed}")
        self.st.see(data_after, after_version, self.it)

    def check_applied(self, before: tuple[bytes, int], changes: list[dict], label: str) -> None:
        """Sau ok: DB phải có đúng price/available đã gửi; có thay đổi thật thì bytes phải đổi."""
        rows = {r[0]: r for r in self.rows()}
        old = {r[0]: r for r in json.loads(before[0])}
        p, a = self.col("price"), self.col("available")
        wrong, differs = [], False
        for c in changes:
            row, prev = rows.get(c["drink_id"]), old.get(c["drink_id"])
            if row is None:
                wrong.append(f"{c['drink_id']}: mất món")
                continue
            if "price" in c:
                differs |= prev is None or prev[p] != c["price"]
                if row[p] != c["price"]:
                    wrong.append(f"{c['drink_id']}: price={row[p]} != {c['price']}")
            if "available" in c:
                differs |= prev is None or prev[a] != int(c["available"])
                if row[a] != int(c["available"]):
                    wrong.append(f"{c['drink_id']}: available={row[a]} != {int(c['available'])}")
        if differs and oracle.canonical_bytes(list(rows.values())) == before[0]:
            wrong.append("có thay đổi thật nhưng menu không đổi")
        self.st.check("update_applied", not wrong, self.it, f"{label}: {'; '.join(wrong)[:300]}")

    def update(self, changes: list[dict], label: str, retry: bool = True) -> None:
        """Cập nhật qua API với version app đang giữ; conflict bất ngờ thì làm mới rồi thử lại."""
        before = self.snapshot()
        status, r = self.h.menu_update(self.app_version, changes)
        if status == 200 and r.get("status") == "conflict" and retry:
            self.st.fail(self.it, "unexpected_conflict", f"{label}: app_version={self.app_version}")
            self.refresh()
            return self.update(changes, label, retry=False)
        if not self.verify_ok(status, r, label):
            return
        if not self.st.check(f"{label}_status_ok", r.get("status") == "ok", self.it, f"status={r.get('status')}"):
            return
        self.check_applied(before, changes, label)
        self.check_changed(before, r.get("menu_version"), label)
        self.set_app(r.get("menu_version"))

    def refresh(self) -> None:
        status, r = self.h.menu_get(self.app_version)
        if self.verify_ok(status, r, "refresh") and "menu_version" in r:
            self.set_app(r["menu_version"])

    def pick(self, k: int) -> list[list]:
        rows = self.rows()
        return self.rng.sample(rows, min(k, len(rows)))

    def price_change(self, row: list) -> dict:
        price = row[self.col("price")] or 0
        for _ in range(20):
            new = max(0, price + self.rng.randint(-5, 5))
            if new != price:
                break
        else:
            new = price + 1
        return {"drink_id": row[0], "price": new}

    # --- các kiểu đột biến ---
    def price_tweak(self) -> None:
        self.update([self.price_change(r) for r in self.pick(self.rng.randint(1, 3))], "price_tweak")

    def toggle_available(self) -> None:
        a = self.col("available")
        self.update([{"drink_id": r[0], "available": not bool(r[a])}
                     for r in self.pick(self.rng.randint(1, 2))], "toggle_available")

    def batch_mix(self) -> None:
        a, changes = self.col("available"), []
        for r in self.pick(self.rng.randint(3, 6)):
            c = self.price_change(r) if self.rng.random() < 0.7 else {"drink_id": r[0]}
            if self.rng.random() < 0.5 or len(c) == 1:
                c["available"] = not bool(r[a])
            changes.append(c)
        self.update(changes, "batch_mix")

    def rename(self) -> None:
        """Đổi tên trực tiếp trên máy (API không cho đổi tên), app phải theo được."""
        n = self.col("drink_name")
        rows, mode = self.rows(), self.rng.choice(("suffix", "diacritics", "swap"))
        before = self.snapshot()
        if mode == "swap" and len(rows) >= 2:
            x, y = self.rng.sample(rows, 2)
            if x[n] == y[n]:
                y[n] = (y[n] or "") + " ♻"
            self.h.db_execute("UPDATE drink SET drink_name=? WHERE drink_id=?", (y[n], x[0]))
            self.h.db_execute("UPDATE drink SET drink_name=? WHERE drink_id=?", (x[n], y[0]))
        else:
            r = self.rng.choice(rows)
            new = (r[n] or "") + self.rng.choice(SUFFIXES) if mode == "suffix" else self.rng.choice(NAMES)
            if new == r[n]:
                new += " 2"
            self.h.db_execute("UPDATE drink SET drink_name=? WHERE drink_id=?", (new, r[0]))
        status, r = self.h.menu_get(self.app_version)
        if not self.verify_ok(status, r, "rename"):
            return
        self.st.check("app_follows", r.get("status") == "ok" and "packet" in r, self.it,
                      f"rename/{mode}: status={r.get('status')}")
        self.check_changed(before, r.get("menu_version"), f"rename/{mode}")
        self.set_app(r.get("menu_version"))

    def noop(self) -> None:
        status, r = self.h.menu_get(self.app_version)
        if not self.verify_ok(status, r, "noop"):
            return
        self.st.check("up_to_date_when_same",
                      r.get("status") == "up_to_date" and r.get("menu_version") == self.app_version,
                      self.it, f"status={r.get('status')} version={r.get('menu_version')} app={self.app_version}")

    def stale_update(self) -> None:
        olds = [v for v in self.old_versions if v != self.app_version]
        if not olds:
            return self.price_tweak()
        rows_before = self.rows()
        status, r = self.h.menu_update(self.rng.choice(olds), [self.price_change(self.pick(1)[0])])
        if not self.verify_ok(status, r, "stale_update"):
            return
        self.st.check("conflict_no_write", r.get("status") == "conflict" and self.rows() == rows_before,
                      self.it, f"status={r.get('status')} db_unchanged={self.rows() == rows_before}")
        if r.get("status") == "conflict":
            self.set_app(r.get("menu_version"))

    def invalid_update(self) -> None:
        row = self.pick(1)[0]
        bad = self.rng.choice((
            [{"drink_id": row[0], "price": -self.rng.randint(1, 50)}],
            [{"drink_id": 999999, "price": 1000}],
            [{"drink_id": row[0], "price": "12000"}],
            [{"drink_id": row[0], "available": "yes"}],
            [{"drink_id": 1006, "price": 1}],  # món đã xoá mềm
        ))
        rows_before = self.rows()
        status, r = self.h.menu_update(self.app_version, bad)
        rejected = status >= 400 and "loi" in r
        self.st.check("invalid_rejected", rejected, self.it, f"{bad}: HTTP {status} {str(r)[:200]}")
        self.st.check("invalid_no_write", self.rows() == rows_before, self.it, f"{bad}: DB bị đổi")

    def restore(self, original: list[list]) -> None:
        """Trả tên qua db_execute, giá/available qua API (chia lô <= 200)."""
        n, p, a = self.col("drink_name"), self.col("price"), self.col("available")
        for r in original:
            self.h.db_execute("UPDATE drink SET drink_name=? WHERE drink_id=?", (r[n], r[0]))
        self.refresh()
        changes = [{"drink_id": r[0], "price": r[p], "available": bool(r[a])} for r in original]
        for i in range(0, len(changes), CHUNK):
            status, r = self.h.menu_update(self.app_version, changes[i:i + CHUNK])
            if status == 200 and r.get("status") == "conflict":
                self.set_app(r["menu_version"])
                status, r = self.h.menu_update(self.app_version, changes[i:i + CHUNK])
            self.st.check("restore_http_ok", status == 200 and r.get("status") == "ok", self.it,
                          f"HTTP {status} {str(r)[:200]}")
            if "menu_version" in r:
                self.set_app(r["menu_version"])


def run(harness, iterations: int = 300, seed: int = 42, log=print) -> Stats:
    rng = random.Random(seed)
    st = Stats(iterations=iterations, seed=seed)
    ru = _Runner(harness, rng, st)
    t0 = time.monotonic()

    # 1. Mốc ban đầu
    original_rows = oracle.read_rows(harness.machine_db)
    status, r = harness.menu_get(0)
    ru.verify_ok(status, r, "baseline")
    st.check("baseline_ok", status == 200 and r.get("status") == "ok", 0, f"HTTP {status} {str(r)[:200]}")
    original_version = r.get("menu_version")
    ru.set_app(original_version or 0)
    st.see(oracle.canonical_bytes(original_rows), original_version, 0)
    log(f"[baseline] version={original_version} món={len(original_rows)}")

    kinds, weights = list(WEIGHTS), list(WEIGHTS.values())
    try:
        for it in range(1, iterations + 1):
            ru.it = it
            kind = rng.choices(kinds, weights)[0]
            st.mutations[kind] = st.mutations.get(kind, 0) + 1
            getattr(ru, kind)()
            if it % 50 == 0:
                log(f"[{it}/{iterations}] lỗi={len(st.failures)} menu khác nhau={len(st.versions)}")
    except Exception as exc:  # noqa: BLE001 - ghi lại rồi vẫn khôi phục
        st.fail(ru.it, "exception", f"{exc!r}\n{traceback.format_exc()[-800:]}")
        log(f"[lỗi] vòng {ru.it}: {exc!r}")
    finally:
        ru.it = iterations + 1
        try:
            ru.restore(original_rows)
            st.check("restore_rows", oracle.read_rows(harness.machine_db) == original_rows, ru.it,
                     "DB sau khôi phục khác menu gốc")
            status, r = harness.menu_get(0)
            expect = oracle.expected_version(harness.machine_db)
            st.check("restore_version", status == 200 and r.get("menu_version") == original_version == expect,
                     ru.it, f"flow={r.get('menu_version')} gốc={original_version} oracle={expect}")
        except Exception as exc:  # noqa: BLE001
            st.fail(ru.it, "restore_exception", repr(exc))
        st.duration = time.monotonic() - t0
        log(f"[xong] {iterations} vòng, {st.duration:.1f}s")
    return st
