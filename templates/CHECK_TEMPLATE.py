"""Шаблон проверки обратного давления (Backpressure check).

Возвращает код 0 при успехе, либо код 1 при нарушении целостности данных/схемы.
"""

from __future__ import annotations

from pathlib import Path
import sys


def run_check(skill_dir: Path) -> int:
    # 1. Проверка структуры обязательных каталогов или файлов
    data_dir = skill_dir / "data"
    if data_dir.exists():
        for item in data_dir.glob("*.json"):
            # Пример валидации формата
            pass

    print("Backpressure проверка пройдена успешно.")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    sys.exit(run_check(target.resolve()))
