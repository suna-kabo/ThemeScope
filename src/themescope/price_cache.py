"""Persistent compressed Yahoo chart cache with deterministic date merges."""

from __future__ import annotations

import gzip
import json
import math
import os
import re
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


CACHE_VERSION = 1


def _valid_chart(chart: Any, symbol: str) -> bool:
    if not isinstance(chart, dict) or str(chart.get("symbol", "")).upper() != symbol.upper():
        return False
    observations = chart.get("observations")
    if not isinstance(observations, list) or not observations:
        return False
    dates = set()
    for row in observations:
        if not isinstance(row, dict) or not isinstance(row.get("date"), str):
            return False
        try:
            date.fromisoformat(row["date"])
        except ValueError:
            return False
        if row["date"] in dates:
            return False
        dates.add(row["date"])
        for key in ("close", "adj_close", "volume"):
            value = row.get(key)
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                return False
    return True


class PriceCache:
    def __init__(self, root: Path, revision_refresh_days: int = 30, overlap_days: int = 10):
        self.root = root
        self.prices = root / "prices"
        self.revision_refresh_days = max(1, int(revision_refresh_days))
        self.overlap_days = max(1, int(overlap_days))
        self.stats: dict[str, int] = {key: 0 for key in ("hits", "incremental_updates", "full_refreshes", "failures", "stale_reuses", "requests", "universe_hits", "universe_updates", "universe_requests", "universe_failures", "universe_stale_reuses", "session_failure_reuses")}

    @staticmethod
    def _filename(symbol: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", symbol).replace("^", "IDX-")
        return safe + ".json.gz"

    def path_for(self, symbol: str) -> Path:
        return self.prices / self._filename(symbol)

    def read(self, symbol: str) -> dict[str, Any] | None:
        path = self.path_for(symbol)
        try:
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                wrapper = json.load(handle)
            if wrapper.get("cache_version") != CACHE_VERSION or not _valid_chart(wrapper.get("chart"), symbol):
                return None
            return wrapper
        except (OSError, EOFError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def write(self, symbol: str, chart: dict[str, Any], *, full_refresh_at: str | None = None) -> None:
        if not _valid_chart(chart, symbol):
            raise ValueError(f"Refusing to cache empty or malformed history for {symbol}")
        path = self.path_for(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        wrapper = {
            "cache_version": CACHE_VERSION,
            "symbol": symbol,
            "source": "Yahoo Finance chart API",
            "retrieved_at": chart.get("retrieved_at"),
            "latest_completed_session": max(row["date"] for row in chart["observations"]),
            "full_refresh_at": full_refresh_at,
            "adjustment_metadata": chart.get("events", {}),
            "chart": chart,
        }
        fd, temp = tempfile.mkstemp(prefix=".price-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as raw:
                with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                    compressed.write((json.dumps(wrapper, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
                raw.flush()
                os.fsync(raw.fileno())
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    @staticmethod
    def _merge(old: dict[str, Any] | None, fresh: dict[str, Any], symbol: str) -> dict[str, Any]:
        if old is None:
            return fresh
        observations = {row["date"]: row for row in old.get("observations", [])}
        observations.update({row["date"]: row for row in fresh.get("observations", [])})
        return {
            **old,
            **fresh,
            "symbol": symbol,
            "observations": [observations[key] for key in sorted(observations)],
            "events": fresh.get("events") or old.get("events", {}),
        }

    @staticmethod
    def _overlap_changed(old: dict[str, Any], fresh: dict[str, Any]) -> bool:
        old_rows = {row["date"]: row for row in old.get("observations", [])}
        for row in fresh.get("observations", []):
            before = old_rows.get(row["date"])
            if not before:
                continue
            for key in ("close", "adj_close"):
                a, b = before.get(key), row.get(key)
                if a and b and abs(a - b) / max(abs(a), abs(b)) > 0.001:
                    return True
        return False

    def get_or_fetch(
        self,
        symbol: str,
        required_session: str | None,
        fetcher: Callable[..., dict[str, Any]],
        years: int = 2,
        force: bool = False,
    ) -> tuple[dict[str, Any] | None, str, str | None]:
        wrapper = self.read(symbol)
        old = wrapper.get("chart") if wrapper else None
        latest = wrapper.get("latest_completed_session") if wrapper else None
        if old and not force and (required_session is None or (latest and latest >= required_session)):
            self.stats["hits"] += 1
            return old, "hit", None
        full = old is None
        if wrapper and wrapper.get("full_refresh_at"):
            try:
                full = (datetime.now(timezone.utc).date() - date.fromisoformat(wrapper["full_refresh_at"][:10])).days >= self.revision_refresh_days
            except (TypeError, ValueError):
                full = True
        if old and not full:
            try:
                start = (date.fromisoformat(latest) - timedelta(days=self.overlap_days)).isoformat()
            except (ValueError, TypeError):
                full = True
        try:
            self.stats["requests"] += 1
            if full:
                fresh = fetcher(symbol, years=years)
                self.stats["full_refreshes"] += 1
            else:
                fresh = fetcher(symbol, years=years, start_date=start, end_date=required_session)
                self.stats["incremental_updates"] += 1
            if not _valid_chart(fresh, symbol):
                raise ValueError("provider returned an empty or malformed chart")
            if old and not full and self._overlap_changed(old, fresh):
                self.stats["requests"] += 1
                fresh = fetcher(symbol, years=years)
                if not _valid_chart(fresh, symbol):
                    raise ValueError("full adjustment refresh returned malformed history")
                full = True
                self.stats["full_refreshes"] += 1
            merged = self._merge(old, fresh, symbol)
            if required_session and not any(row["date"] == required_session for row in merged["observations"]):
                raise ValueError(f"provider response did not include required session {required_session}")
            last_full = datetime.now(timezone.utc).isoformat(timespec="seconds") if full else (wrapper.get("full_refresh_at") if wrapper else None)
            self.write(symbol, merged, full_refresh_at=last_full)
            return merged, "full_refresh" if full else "incremental_update", None
        except Exception as exc:
            self.stats["failures"] += 1
            if old:
                self.stats["stale_reuses"] += 1
                return old, "stale_reused", f"{type(exc).__name__}: {exc}"
            return None, "failed", f"{type(exc).__name__}: {exc}"

    def save_universe(self, name: str, data: dict[str, Any]) -> None:
        path = self.root / "universes" / (name.lower() + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps({"cache_version": CACHE_VERSION, "data": data}, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        os.replace(temp, path)

    def read_universe(self, name: str) -> dict[str, Any] | None:
        path = self.root / "universes" / (name.lower() + ".json")
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            return item.get("data") if item.get("cache_version") == CACHE_VERSION and isinstance(item.get("data"), dict) else None
        except (OSError, ValueError, TypeError):
            return None
