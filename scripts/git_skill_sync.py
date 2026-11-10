"""Скрипт транзакционного Git-протокола для скиллов (Git-Skill Sync).

Выполняет 4 фазы протокола:
1. ingress: синхронизация входящих изменений (git pull / status).
2. check: запуск проверок обратного давления (checks/ или линтера).
3. egress: атомарный коммит и отправка (git add, commit, push).
4. resolve: проверка наличия маркеров конфликтов слияния.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def run_git(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *cmd],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def check_merge_conflicts(skill_dir: Path) -> list[Path]:
    conflicts: list[Path] = []
    conflict_markers = ["<<<<<<<", "=======", ">>>>>>>"]
    for path in skill_dir.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                if any(marker in content for marker in conflict_markers):
                    conflicts.append(path)
            except Exception:
                continue
    return conflicts


def run_backpressure_checks(skill_dir: Path) -> bool:
    checks_dir = skill_dir / "checks"
    if not checks_dir.exists():
        print("ВНИМАНИЕ: Каталог checks/ не найден. Пропуск backpressure проверки.")
        return True

    py_checks = list(checks_dir.glob("*.py"))
    if not py_checks:
        print("Каталог checks/ пуст.")
        return True

    all_passed = True
    for check_script in py_checks:
        print(f"Запуск проверки: {check_script.name}...")
        proc = subprocess.run(
            [sys.executable, str(check_script), str(skill_dir)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            print(f"СБОЙ: {check_script.name} завершился с ошибкой:", file=sys.stderr)
            if proc.stdout:
                print(proc.stdout, file=sys.stderr)
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)
            all_passed = False
        else:
            print(f"OK: {check_script.name}")
            if proc.stdout:
                print(proc.stdout)

    return all_passed


def phase_ingress(skill_dir: Path) -> int:
    print(f"[Фаза 1: Синхронизация на входе] Директория: {skill_dir}")
    # Проверка, является ли директория частью git
    code, out, err = run_git(["rev-parse", "--is-inside-work-tree"], skill_dir)
    if code != 0:
        print(
            f"ВНИМАНИЕ: {skill_dir} не находится внутри Git-репозитория. Пропуск git pull."
        )
        return 0

    code, out, err = run_git(["status", "--porcelain"], skill_dir)
    if out:
        print(f"Локальные изменения перед синхронизацией:\n{out}")

    # Попытка pull с авто-слиянием
    print("Выполнение git pull --rebase=false...")
    code, out, err = run_git(["pull", "--no-edit"], skill_dir)
    if code != 0:
        print(f"Ошибка или предупреждение git pull: {err or out}")
        conflicts = check_merge_conflicts(skill_dir)
        if conflicts:
            print("ОБНАРУЖЕНЫ КОНФЛИКТЫ СЛИЯНИЯ в файлах:")
            for c in conflicts:
                print(f" - {c.relative_to(skill_dir)}")
            print("Требуется логическое разрешение конфликтов без потери данных.")
            return 2
    else:
        print(f"Синхронизация успешна: {out or 'Up to date'}")
    return 0


def phase_egress(skill_dir: Path, message: str) -> int:
    print(f"[Фаза 3: Фиксация на выходе] Сообщение: {message}")
    code, out, err = run_git(["rev-parse", "--is-inside-work-tree"], skill_dir)
    if code != 0:
        print(
            f"ВНИМАНИЕ: {skill_dir} не является Git-репозиторием. Завершено без коммита."
        )
        return 0

    # Проверка статуса
    code, out, err = run_git(["status", "--porcelain"], skill_dir)
    if not out:
        print("Нет изменений для фиксации.")
        return 0

    # git add
    run_git(["add", "."], skill_dir)

    # git commit
    code, out, err = run_git(["commit", "-m", message], skill_dir)
    if code != 0:
        print(f"Ошибка коммита: {err or out}", file=sys.stderr)
        return 1
    print(f"Коммит зафиксирован: {out.splitlines()[0] if out else 'OK'}")

    # git push
    code, out, err = run_git(["push"], skill_dir)
    if code != 0:
        print(f"Предупреждение git push: {err or out}")
    else:
        print("Изменения успешно отправлены в удаленный репозиторий.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Git-Skill Sync Controller")
    parser.add_argument(
        "--action",
        choices=["ingress", "check", "egress", "full"],
        default="full",
        help="Действие протокола",
    )
    parser.add_argument(
        "--skill-dir",
        default=".",
        help="Путь к директории скилла",
    )
    parser.add_argument(
        "--message",
        "-m",
        default="chore(skill): обновление данных и состояния по протоколу",
        help="Сообщение коммита",
    )

    args = parser.parse_args()
    skill_path = Path(args.skill_dir).resolve()

    if args.action in ("ingress", "full"):
        res = phase_ingress(skill_path)
        if res != 0 and args.action == "full":
            return res

    if args.action in ("check", "full"):
        print("[Фаза 2: Проверка обратным давлением (Backpressure)]")
        if not run_backpressure_checks(skill_path):
            print(
                "ОШИБКА: Проверка обратным давлением не пройдена. Коммит заблокирован.",
                file=sys.stderr,
            )
            return 1
        print("Backpressure проверки успешно пройдены.")

    if args.action in ("egress", "full"):
        return phase_egress(skill_path, args.message)

    return 0


if __name__ == "__main__":
    sys.exit(main())
