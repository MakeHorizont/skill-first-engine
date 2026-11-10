"""Валидатор анатомии скилла и обратного давления (Backpressure check).

Проверяет:
1. Соответствие спецификации agentskills.io (name, description, resident token budget).
2. Наличие SKILL.md и корректность YAML-frontmatter.
3. Гигиену текста (дефис '-' вместо тире, прямые кавычки '\"').
4. Синтаксическую целостность скриптов в scripts/ и проверок в checks/.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


def validate_frontmatter(content: str) -> tuple[bool, str, dict[str, str]]:
    match = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)$", content, re.DOTALL)
    if not match:
        return (
            False,
            "SKILL.md не содержит корректного YAML-frontmatter между разделителями '---'",
            {},
        )

    fm_raw = match.group(1)
    body = match.group(2)
    meta: dict[str, str] = {}

    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            meta[key] = val

    if "name" not in meta:
        return False, "В frontmatter отсутствует обязательное поле 'name'", meta
    if "description" not in meta:
        return False, "В frontmatter отсутствует обязательное поле 'description'", meta

    # Спецификация agentskills.io: имя в kebab-case (^[a-z0-9-]+$), длина <= 64
    name = meta["name"]
    if not re.match(r"^[a-z0-9-]+$", name):
        return (
            False,
            f"Имя скилла '{name}' нарушает стандарт agentskills.io (допустимы только [a-z0-9-]).",
            meta,
        )
    if len(name) > 64:
        return False, f"Имя скилла '{name}' превышает лимит 64 символа.", meta

    # Бюджет смарт-зоны: описание не должно превышать 350 символов
    desc = meta["description"]
    if len(desc) > 350:
        return (
            False,
            f"Описание скилла превышает бюджет смарт-зоны ({len(desc)} > 350 символов). Сократите до 1-2 предложений.",
            meta,
        )

    return True, body, meta


def validate_text_hygiene(text: str) -> list[str]:
    errors: list[str] = []
    if "—" in text or "–" in text:
        errors.append("Обнаружено длинное тире. Разрешен только дефис '-'.")
    if "«" in text or "»" in text or "“" in text or "”" in text:
        errors.append(
            "Обнаружены фигурные кавычки. Разрешены только прямые кавычки '\"'."
        )
    return errors


def validate_scripts_syntax(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    for script_path in skill_dir.rglob("*.py"):
        try:
            source = script_path.read_text(encoding="utf-8", errors="ignore")
            compile(source, str(script_path), "exec")
        except Exception as e:
            errors.append(
                f"Синтаксическая ошибка в {script_path.relative_to(skill_dir)}: {e}"
            )
    return errors


def check_skill_dir(skill_dir: Path) -> int:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        print(f"ОШИБКА: Файл не найден: {skill_file}", file=sys.stderr)
        return 1

    content = skill_file.read_text(encoding="utf-8")
    ok, body_or_err, meta = validate_frontmatter(content)
    if not ok:
        print(
            f"ОШИБКА FRONTMATTER (agentskills.io spec): {body_or_err}", file=sys.stderr
        )
        return 1

    name = meta.get("name", "")
    desc = meta.get("description", "")
    print(f"Валидация скилла: {name}")
    print(f"Описание ({len(desc)} симв.): {desc[:80]}...")

    # Проверка гигиены текста
    hygiene_errors = validate_text_hygiene(content)
    if hygiene_errors:
        for err in hygiene_errors:
            print(f"ОШИБКА ГИГИЕНЫ ТЕКСТА: {err}", file=sys.stderr)
        return 1

    # Проверка синтаксиса Python-скриптов
    syntax_errors = validate_scripts_syntax(skill_dir)
    if syntax_errors:
        for err in syntax_errors:
            print(f"СИНТАКСИЧЕСКИЙ СБОЙ: {err}", file=sys.stderr)
        return 1

    # Рекомендованная анатомия
    recommended_dirs = ["scripts", "templates", "checks"]
    missing_dirs = [d for d in recommended_dirs if not (skill_dir / d).is_dir()]
    if missing_dirs:
        print(
            f"ВНИМАНИЕ: Отсутствуют рекомендуемые каталоги: {', '.join(missing_dirs)}"
        )

    print(
        f"УСПЕХ: Скилл '{name}' полностью валиден (agentskills.io & Backpressure OK)."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Валидатор анатомии скилла (agentskills.io)"
    )
    parser.add_argument(
        "skill_dir",
        nargs="?",
        default=".",
        help="Путь к директории скилла (по умолчанию текущая)",
    )
    args = parser.parse_args()
    target_path = Path(args.skill_dir).resolve()
    return check_skill_dir(target_path)


if __name__ == "__main__":
    sys.exit(main())
