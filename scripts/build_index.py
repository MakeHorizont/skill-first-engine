"""Инструмент фасетного индексирования и построения каталога скиллов (Faceted Index Builder).

Функции:
1. Сканирование дерева скиллов (ограничение меры: ровно 2 уровня - Домен / Скилл).
2. Извлечение метаданных (name, description, tags) из YAML frontmatter.
3. Генерация локальных INDEX.md в доменах и общего ROOT_INDEX.md в корне.
4. Режим классификации (--classify): сопоставление плоских скиллов с 5-7 целевыми доменами.
5. Режим миграции (--migrate): перемещение директорий скиллов в домены через git mv.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import sys

# Системные директории, исключаемые из индексации
IGNORE_DIRS = {
    ".git",
    ".github",
    ".ruff_cache",
    "archive",
    "scripts",
    "bin",
    "checks",
    "templates",
    "references",
}

# 6 целевых доменов архитектуры
DEFAULT_DOMAINS: dict[str, dict[str, str]] = {
    "system": {
        "title": "Системные мета-навыки и архитектура",
        "desc": "Диалектическая инженерия, кибернетика, VSM, безопасность, архитектурные регламенты и управление памятью",
    },
    "engineering": {
        "title": "Инженерная разработка и качество кода",
        "desc": "Написание кода, рефакторинг, runtime-отладка, верификация, санитария и git-пайплайны",
    },
    "office": {
        "title": "Документы и офисный контур",
        "desc": "Обработка таблиц, текстовых документов, презентаций и совместная работа с документацией",
    },
    "analytics": {
        "title": "Аналитика, исследования и сбор данных",
        "desc": "Исследование предметных областей, конкурентный анализ, метрики и системный поиск",
    },
    "integrations": {
        "title": "Интеграции, шлюзы и внешние сервисы",
        "desc": "Взаимодействие со сторонними платформами, таск-трекерами, логами и API",
    },
    "media": {
        "title": "Медиа, дизайн интерфейсов и контент",
        "desc": "Инженерный дизайн, визуальные системы, генерация артефактов и работа с медиафайлами",
    },
}

# Точные сопоставления известных имен скиллов с доменами
EXACT_SKILL_DOMAINS: dict[str, str] = {
    # System
    "complex-systems-engineering": "system",
    "cybersyn": "system",
    "doctor": "system",
    "domain-monorepo": "system",
    "dynamic-systems-logic": "system",
    "economic-systems-audit": "system",
    "enterprise-semantic-shield": "system",
    "ogas": "system",
    "platform-systems-audit": "system",
    "security-sentinel": "system",
    "skill-first-engine": "system",
    "tda-architecture": "system",
    # Engineering
    "agent-deep-links": "engineering",
    "ast-grep": "engineering",
    "changelog-generator": "engineering",
    "claude-api": "engineering",
    "codebase-migrate": "engineering",
    "code-sanitizer": "engineering",
    "create-plan": "engineering",
    "deploy-pipeline": "engineering",
    "file-organizer": "engineering",
    "gh-address-comments": "engineering",
    "gh-fix-ci": "engineering",
    "mcp-builder": "engineering",
    "pr-review-ci-fix": "engineering",
    "pytest-watcher": "engineering",
    "runtime-debug": "engineering",
    "runtime-verification": "engineering",
    "simplify": "engineering",
    "skill-creator": "engineering",
    "skill-installer": "engineering",
    "skill-share": "engineering",
    "support-ticket-triage": "engineering",
    "template-skill": "engineering",
    "test-driven-development": "engineering",
    "webapp-testing": "engineering",
    # Office
    "doc-coauthoring": "office",
    "docx": "office",
    "email-draft-polish": "office",
    "internal-comms": "office",
    "invoice-organizer": "office",
    "meeting-notes-and-actions": "office",
    "paperjsx": "office",
    "pdf": "office",
    "pptx": "office",
    "raffle-winner-picker": "office",
    "spreadsheet-formula-helper": "office",
    "tailored-resume-generator": "office",
    "xlsx": "office",
    # Analytics
    "competitive-ads-extractor": "analytics",
    "content-research-writer": "analytics",
    "developer-growth-analysis": "analytics",
    "domain-name-brainstormer": "analytics",
    "lead-research-assistant": "analytics",
    "meeting-insights-analyzer": "analytics",
    # Integrations
    "connect": "integrations",
    "connect-apps": "integrations",
    "composio-skills": "integrations",
    "datadog-logs": "integrations",
    "helium-mcp": "integrations",
    "issue-triage": "integrations",
    "langsmith-fetch": "integrations",
    "linear": "integrations",
    "notion-knowledge-capture": "integrations",
    "notion-meeting-intelligence": "integrations",
    "notion-research-documentation": "integrations",
    "notion-spec-to-implementation": "integrations",
    "sentry-triage": "integrations",
    # Media
    "algorithmic-art": "media",
    "animation-design": "media",
    "brand-guidelines": "media",
    "canvas-design": "media",
    "design-engineering": "media",
    "fable-generative": "media",
    "frontend-design": "media",
    "game-design": "media",
    "image-enhancer": "media",
    "slack-gif-creator": "media",
    "theme-factory": "media",
    "video-downloader": "media",
    "web-artifacts-builder": "media",
}

# Правила классификации скиллов по ключевым словам для новых неизвестных навыков
CLASSIFICATION_RULES: dict[str, list[str]] = {
    "system": [
        "dialectical",
        "cybersyn",
        "hegel",
        "marx",
        "ogas",
        "security-sentinel",
        "tda",
        "monorepo",
        "tektology",
        "skill-first",
    ],
    "media": [
        "animation",
        "art",
        "p5.js",
        "canvas",
        "theme",
        "design",
        "generative",
        "image",
        "video",
        "gif",
        "palette",
    ],
    "office": [
        "docx",
        "xlsx",
        "pptx",
        "pdf",
        "invoice",
        "spreadsheet",
        "excel",
        "presentation",
        "resume",
        "letter",
        "document",
    ],
    "analytics": [
        "competitive",
        "research",
        "analysis",
        "market",
        "leads",
        "insights",
        "metrics",
        "stats",
    ],
    "integrations": [
        "composio",
        "datadog",
        "linear",
        "notion",
        "sentry",
        "langsmith",
        "helium",
        "slack",
        "github",
        "gitlab",
        "webhook",
    ],
    "engineering": [
        "test",
        "debug",
        "code",
        "ast-grep",
        "lint",
        "format",
        "deploy",
        "cli",
        "api",
        "runner",
        "migration",
    ],
}


@dataclass
class SkillEntry:
    name: str
    dir_name: str
    rel_path: str
    description: str
    tags: list[str]
    domain: str


def sanitize_text(text: str) -> str:
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"')
    return text


def parse_skill_meta(skill_md_path: Path) -> tuple[str, str, list[str]]:
    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return skill_md_path.parent.name, "Ошибка чтения SKILL.md", []

    name = skill_md_path.parent.name
    description = ""
    tags: list[str] = []

    fm_match = re.match(r"^---\s*\r?\n(.*?)\r?\n---", content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            line = line.strip()
            if line.startswith("name:"):
                val = line.split(":", 1)[1].strip().strip('"').strip("'")
                if val:
                    name = val
            elif line.startswith("description:"):
                val = line.split(":", 1)[1].strip().strip('"').strip("'")
                if val:
                    description = val
            elif line.startswith("tags:"):
                val = line.split(":", 1)[1].strip().strip("[]").strip()
                tags = [
                    t.strip().strip('"').strip("'") for t in val.split(",") if t.strip()
                ]

    if not description:
        for line in content.splitlines():
            cleaned = line.strip().lstrip("#").strip()
            if (
                cleaned
                and not cleaned.lower().startswith("паспорт")
                and not cleaned.lower().startswith("название")
            ):
                description = cleaned[:120]
                break

    clean_desc = sanitize_text(description) if description else "Описание отсутствует"
    return name, clean_desc, tags


def classify_skill(name: str, desc: str) -> str:
    # 1. Проверка точного соответствия по имени
    clean_name = name.lower().strip()
    if clean_name in EXACT_SKILL_DOMAINS:
        return EXACT_SKILL_DOMAINS[clean_name]

    # 2. Проверка по ключевым словам
    combined = f"{name} {desc}".lower()
    for domain, keywords in CLASSIFICATION_RULES.items():
        if any(re.search(r"\b" + re.escape(kw) + r"\b", combined) for kw in keywords):
            return domain

    return "engineering"  # Базовый домен по умолчанию


def scan_skills(root_dir: Path) -> list[SkillEntry]:
    entries: list[SkillEntry] = []
    for item in root_dir.iterdir():
        if not item.is_dir() or item.name in IGNORE_DIRS or item.name.startswith("."):
            continue

        skill_file = item / "SKILL.md"
        if skill_file.exists():
            name, desc, tags = parse_skill_meta(skill_file)
            domain = classify_skill(item.name, desc)
            rel_path = f"{domain}/{item.name}"
            entries.append(
                SkillEntry(
                    name=name,
                    dir_name=item.name,
                    rel_path=rel_path,
                    description=desc,
                    tags=tags,
                    domain=domain,
                )
            )
            continue

        # Проверка, не является ли item уже доменом верхнего уровня
        for sub_item in item.iterdir():
            if not sub_item.is_dir() or sub_item.name.startswith("."):
                continue
            sub_skill = sub_item / "SKILL.md"
            if sub_skill.exists():
                name, desc, tags = parse_skill_meta(sub_skill)
                entries.append(
                    SkillEntry(
                        name=name,
                        dir_name=sub_item.name,
                        rel_path=f"{item.name}/{sub_item.name}",
                        description=desc,
                        tags=tags,
                        domain=item.name,
                    )
                )

    return sorted(entries, key=lambda x: (x.domain, x.name))


def generate_indexes(root_dir: Path, entries: list[SkillEntry]) -> None:
    by_domain: dict[str, list[SkillEntry]] = {}
    for entry in entries:
        by_domain.setdefault(entry.domain, []).append(entry)

    # 1. Генерация локальных INDEX.md в каталогах доменов
    for domain, domain_skills in by_domain.items():
        domain_dir = root_dir / domain
        domain_dir.mkdir(exist_ok=True)
        domain_info = DEFAULT_DOMAINS.get(
            domain,
            {"title": domain.capitalize(), "desc": "Тематический раздел навыков"},
        )

        lines: list[str] = [
            f"# ДОМЕН: {domain_info['title']}",
            "",
            f"{domain_info['desc']}",
            "",
            "## РЕЕСТР НАВЫКОВ ДОМЕНА",
            "",
        ]
        for s in domain_skills:
            tags_str = f" [теги: {', '.join(s.tags)}]" if s.tags else ""
            lines.append(f"- **{s.name}**: {s.description}{tags_str}")
            lines.append(f"  Файл: `{s.name}/SKILL.md`")
            lines.append("")

        index_path = domain_dir / "INDEX.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Сгенерирован индекс домена: {index_path.relative_to(root_dir)}")

    # 2. Генерация корневого ROOT_INDEX.md
    root_lines: list[str] = [
        "# СВОДНЫЙ РЕЕСТР ДОМЕНОВ И СКИЛЛОВ (ROOT_INDEX)",
        "",
        "Двухтактный протокол: выбери домен -> открой локальный INDEX.md -> запусти нужный SKILL.md.",
        "Для прямого поиска используй: `grep -rn 'ключевое_слово' <домен>/INDEX.md`",
        "",
        "## ДОМЕНЫ ПЕРВОГО УРОВНЯ",
        "",
    ]
    for dom_name, dom_info in DEFAULT_DOMAINS.items():
        skills_in_dom = by_domain.get(dom_name, [])
        root_lines.append(
            f"### {dom_name} - {dom_info['title']} ({len(skills_in_dom)} скиллов)"
        )
        root_lines.append(f"{dom_info['desc']}")
        root_lines.append(f"Индекс раздела: `{dom_name}/INDEX.md`")
        root_lines.append("")
        for s in skills_in_dom:
            root_lines.append(f"- `{dom_name}/{s.name}`: {s.description[:80]}...")
        root_lines.append("")

    root_index_path = root_dir / "ROOT_INDEX.md"
    root_index_path.write_text("\n".join(root_lines), encoding="utf-8")
    print(f"Сгенерирован корневой индекс: {root_index_path}")


def display_classification(entries: list[SkillEntry]) -> None:
    by_domain: dict[str, list[SkillEntry]] = {}
    for e in entries:
        by_domain.setdefault(e.domain, []).append(e)

    print("=" * 70)
    print("ПЛАН КЛАССИФИКАЦИИ БАЗЫ СКИЛЛОВ ПО 6 ДОМЕНАМ (DRY-RUN)")
    print("=" * 70)
    for dom_name, dom_info in DEFAULT_DOMAINS.items():
        dom_skills = by_domain.get(dom_name, [])
        print(
            f"\n[ДОМЕН: {dom_name.upper()}] - {dom_info['title']} ({len(dom_skills)} скиллов)"
        )
        for s in dom_skills:
            print(f"  * {s.name:32} -> {s.description[:60]}...")
    print("\n" + "=" * 70)
    print(f"Всего классифицировано скиллов: {len(entries)}")


def migrate_to_domains(root_dir: Path, entries: list[SkillEntry]) -> None:
    is_git = (root_dir / ".git").exists()
    print(f"Миграция директорий (Git режим: {is_git})...")

    # 1. Архивация устаревших неструктурированных папок
    legacy_dirs = [
        "CODEX_PROMPTS",
        "Claude_Fable_5_system_prompt",
        "Design skills",
        "Programming skills",
        "System disign skills",
    ]
    archive_legacy = root_dir / "archive" / "legacy"
    archive_legacy.mkdir(parents=True, exist_ok=True)
    for leg in legacy_dirs:
        leg_path = root_dir / leg
        if leg_path.exists() and leg_path.is_dir():
            target_leg = archive_legacy / leg
            print(f"Архивация legacy папки: {leg} -> archive/legacy/{leg}")
            if is_git:
                subprocess.run(
                    ["git", "mv", str(leg_path), str(target_leg)], cwd=root_dir
                )
            else:
                shutil.move(str(leg_path), str(target_leg))

    # 2. Перемещение composio-skills в integrations
    composio_dir = root_dir / "composio-skills"
    if composio_dir.exists() and composio_dir.is_dir():
        target_composio = root_dir / "integrations" / "composio-skills"
        target_composio.parent.mkdir(exist_ok=True)
        if not target_composio.exists():
            print("Перемещение composio-skills -> integrations/composio-skills")
            if is_git:
                subprocess.run(
                    ["git", "mv", str(composio_dir), str(target_composio)], cwd=root_dir
                )
            else:
                shutil.move(str(composio_dir), str(target_composio))

    # 3. Перемещение скиллов по доменам
    for entry in entries:
        src_dir = root_dir / entry.dir_name
        if not src_dir.exists() or not src_dir.is_dir():
            continue

        target_domain_dir = root_dir / entry.domain
        target_domain_dir.mkdir(exist_ok=True)
        dest_dir = target_domain_dir / entry.dir_name

        if src_dir.resolve() == dest_dir.resolve():
            continue

        print(f"Перемещение: {entry.dir_name} -> {entry.domain}/{entry.dir_name}")
        if is_git:
            proc = subprocess.run(
                ["git", "mv", str(src_dir), str(dest_dir)],
                cwd=root_dir,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                print(f"Предупреждение git mv: {proc.stderr}. Фолбэк на shutil.move.")
                shutil.move(str(src_dir), str(dest_dir))
        else:
            shutil.move(str(src_dir), str(dest_dir))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Построитель фасетного каталога скиллов"
    )
    parser.add_argument(
        "root_dir", nargs="?", default=".", help="Корневая директория скиллов"
    )
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Отобразить план классификации (dry-run)",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Сгенерировать локальные и корневой INDEX.md",
    )
    parser.add_argument(
        "--migrate", action="store_true", help="Физически переместить папки по доменам"
    )

    args = parser.parse_args()
    root_path = Path(args.root_dir).resolve()

    entries = scan_skills(root_path)

    if args.classify:
        display_classification(entries)

    if args.migrate:
        migrate_to_domains(root_path, entries)
        # Пересканировать после миграции
        entries = scan_skills(root_path)

    if args.index:
        generate_indexes(root_path, entries)

    if not (args.classify or args.index or args.migrate):
        # По умолчанию: отобразить классификацию
        display_classification(entries)

    return 0


if __name__ == "__main__":
    sys.exit(main())
