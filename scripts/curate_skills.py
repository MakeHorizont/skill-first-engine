"""Скрипт ревизии и курирования скиллов (Skill Curation & Pruning).

Реализует Правило 3:
- Поиск скиллов, не обновлявшихся >30 дней (кандидаты на сокращение описания).
- Поиск скиллов, не обновлявшихся >90 дней (кандидаты на перенос в archive/).
- Выявление дубликатов и близких по описанию скиллов для консолидации.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import sys


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    match = re.match(r"^---\s*\r?\n(.*?)\r?\n---", content, re.DOTALL)
    if not match:
        return {}
    res: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            res[k.strip()] = v.strip().strip('"').strip("'")
    return res


def get_last_commit_date(path: Path) -> datetime | None:
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", str(path)],
            cwd=path.parent if path.is_file() else path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return datetime.fromisoformat(proc.stdout.strip())
    except Exception:
        pass

    # Фолбэк на дату модификации файла
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc)
    except Exception:
        return None


def audit_skills(root_dir: Path, archive_stale: bool = False) -> None:
    now = datetime.now(timezone.utc)
    skills: list[dict[str, object]] = []

    print(f"Аудит базы скиллов в: {root_dir}")
    for item in root_dir.iterdir():
        if not item.is_dir() or item.name.startswith(".") or item.name == "archive":
            continue

        skill_file = item / "SKILL.md"
        if not skill_file.exists():
            continue

        meta = parse_frontmatter(skill_file)
        name = meta.get("name", item.name)
        desc = meta.get("description", "")
        last_date = get_last_commit_date(skill_file)

        days_inactive = (now - last_date).days if last_date else 0
        skills.append(
            {
                "path": item,
                "name": name,
                "desc": desc,
                "days": days_inactive,
                "last_date": last_date,
            }
        )

    print(f"Найдено зарегистрированных скиллов: {len(skills)}\n")

    stale_30 = [s for s in skills if int(s["days"]) > 30]
    stale_90 = [s for s in skills if int(s["days"]) > 90]

    print("--- КАНДИДАТЫ НА СЖАТИЕ ОПИСАНИЯ (>30 ДНЕЙ БЕЗ ОБНОВЛЕНИЙ) ---")
    if not stale_30:
        print("Нет скиллов старше 30 дней.")
    else:
        for s in stale_30:
            print(
                f"- {s['name']} (неактивен {s['days']} дн.): {str(s['desc'])[:70]}..."
            )

    print("\n--- КАНДИДАТЫ НА АРХИВИРОВАНИЕ (>90 ДНЕЙ БЕЗ ОБНОВЛЕНИЙ) ---")
    if not stale_90:
        print("Нет скиллов старше 90 дней.")
    else:
        for s in stale_90:
            skill_path = Path(s["path"])  # type: ignore
            print(f"- {s['name']} (неактивен {s['days']} дн.): {skill_path}")
            if archive_stale:
                archive_dir = root_dir / "archive"
                archive_dir.mkdir(exist_ok=True)
                dest = archive_dir / skill_path.name
                print(f"  Перемещение в архив: {dest}")
                shutil.move(str(skill_path), str(dest))

    # Анализ похожих описаний для консолидации
    print("\n--- АНАЛИЗ ДУБЛИКАТОВ И СХОДСТВА (КОНСОЛИДАЦИЯ) ---")
    words_map: dict[str, set[str]] = {}
    for s in skills:
        words = set(re.findall(r"\w{4,}", str(s["desc"]).lower()))
        words_map[str(s["name"])] = words

    names = list(words_map.keys())
    similar_pairs: list[tuple[str, str, float]] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            n1, n2 = names[i], names[j]
            w1, w2 = words_map[n1], words_map[n2]
            if not w1 or not w2:
                continue
            jaccard = len(w1 & w2) / len(w1 | w2)
            if jaccard > 0.4:
                similar_pairs.append((n1, n2, jaccard))

    if not similar_pairs:
        print("Сильно пересекающихся скиллов не выявлено.")
    else:
        for n1, n2, score in similar_pairs:
            print(
                f"- Пересечение {score:.2f}: '{n1}' и '{n2}' -> Рекомендуется объединение."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Аудит и курирование скиллов")
    parser.add_argument(
        "--root",
        default=".",
        help="Корневая директория базы скиллов",
    )
    parser.add_argument(
        "--archive-stale",
        action="store_true",
        help="Автоматически переместить скиллы старше 90 дней в каталог archive/",
    )
    args = parser.parse_args()
    audit_skills(Path(args.root).resolve(), args.archive_stale)
    return 0


if __name__ == "__main__":
    sys.exit(main())
