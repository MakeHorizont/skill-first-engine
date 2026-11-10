"""Контроллер циклической оптимизации (Ralph Loop / AutoResearch Controller).

Реализует инженерные паттерны:
1. karpathy/autoresearch: атомарная проверка 1 гипотезы, замер метрики, commit при росте / git reset при падении, ведение машиночитаемого журнала experiments.jsonl.
2. thirdlayerinc/autoagent: автономная итерация над промптами и конфигурацией харнесса.
3. Meta Loop: анти-схлапывание после 3 последовательных неудач с уходом в ортогональный поиск.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys


def parse_state(state_file: Path) -> dict[str, str]:
    if not state_file.exists():
        return {}
    content = state_file.read_text(encoding="utf-8")
    data: dict[str, str] = {}

    m_goal = re.search(r"##\s*Цель\s*\r?\n(.*?)(?=\r?\n##|\Z)", content, re.DOTALL)
    if m_goal:
        data["goal"] = m_goal.group(1).strip()

    m_metric = re.search(
        r"##\s*Текущая метрика\s*\r?\n(.*?)(?=\r?\n##|\Z)", content, re.DOTALL
    )
    if m_metric:
        data["metric"] = m_metric.group(1).strip()

    m_next = re.search(
        r"##\s*Следующий шаг\s*\r?\n(.*?)(?=\r?\n##|\Z)", content, re.DOTALL
    )
    if m_next:
        data["next_step"] = m_next.group(1).strip()

    return data


def extract_numeric_metric(text: str) -> float | None:
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def is_metric_better(
    old_val: float | None, new_val: float | None, direction: str
) -> bool:
    if old_val is None or new_val is None:
        return True  # Если метрика не числовая, полагаемся на код возврата теста
    if direction == "higher":
        return new_val > old_val
    return new_val < old_val


def count_consecutive_failures(experiments_file: Path) -> int:
    if not experiments_file.exists():
        return 0
    failures = 0
    lines = experiments_file.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("status") in ("REJECTED", "FAIL"):
                failures += 1
            else:
                break
        except Exception:
            continue
    return failures


def log_experiment_jsonl(
    experiments_file: Path,
    hypothesis: str,
    status: str,
    old_metric: str,
    new_metric: str,
    commit_hash: str | None = None,
) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis": hypothesis,
        "status": status,
        "old_metric": old_metric,
        "new_metric": new_metric,
        "commit": commit_hash,
    }
    with open(experiments_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def update_state_markdown(
    state_file: Path, hypothesis: str, status: str, metric_value: str
) -> None:
    if not state_file.exists():
        return
    content = state_file.read_text(encoding="utf-8")
    entry = f"- [x] [{status}] {hypothesis} (Метрика: {metric_value})\n"

    marker = "## Журнал проверенных гипотез\n"
    if marker in content:
        parts = content.split(marker, 1)
        new_content = parts[0] + marker + entry + parts[1]
    else:
        new_content = content + f"\n## Журнал проверенных гипотез\n{entry}"

    state_file.write_text(new_content, encoding="utf-8")


def run_benchmark(cmd: str, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ralph Loop / AutoResearch Benchmark Runner"
    )
    parser.add_argument(
        "--test-cmd",
        required=True,
        help="Команда запуска объективного бенчмарка или теста",
    )
    parser.add_argument(
        "--hypothesis",
        required=True,
        help="Проверяемая гипотеза текущей итерации",
    )
    parser.add_argument(
        "--new-metric",
        default="",
        help="Новое значение целевой метрики",
    )
    parser.add_argument(
        "--direction",
        choices=["higher", "lower"],
        default="higher",
        help="Направление улучшения метрики (higher - больше лучше, lower - меньше лучше)",
    )
    parser.add_argument(
        "--work-dir",
        default=".",
        help="Рабочая директория задачи",
    )

    args = parser.parse_args()
    work_dir = Path(args.work_dir).resolve()
    state_file = work_dir / "STATE.md"
    experiments_file = work_dir / "experiments.jsonl"

    state_data = parse_state(state_file)
    old_metric_str = state_data.get("metric", "")
    old_metric_num = extract_numeric_metric(old_metric_str)
    new_metric_num = extract_numeric_metric(args.new_metric)

    print(f"[AutoResearch Loop] Проверка гипотезы: {args.hypothesis}")
    print(f"Базовая метрика: {old_metric_str or 'не задана'}")
    print(f"Запуск бенчмарка: {args.test_cmd}...")

    code, output = run_benchmark(args.test_cmd, work_dir)
    print(f"Вывод теста (код {code}):\n{output[:500]}")

    improved = code == 0 and is_metric_better(
        old_metric_num, new_metric_num, args.direction
    )

    if improved:
        print("\n[УСПЕХ] Тесты пройдены и метрика улучшена. Фиксация в Git...")
        delta_str = f"[{args.new_metric}]" if args.new_metric else "[PASS]"
        commit_msg = f"feat(loop): {args.hypothesis} {delta_str}"

        subprocess.run(["git", "add", "."], cwd=work_dir)
        proc_commit = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=work_dir,
            capture_output=True,
            text=True,
        )
        commit_hash = "HEAD"
        if proc_commit.returncode == 0:
            proc_rev = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=work_dir,
                capture_output=True,
                text=True,
            )
            commit_hash = proc_rev.stdout.strip()

        log_experiment_jsonl(
            experiments_file,
            args.hypothesis,
            "ACCEPTED",
            old_metric_str,
            args.new_metric or "PASS",
            commit_hash,
        )
        update_state_markdown(
            state_file, args.hypothesis, "ACCEPTED", args.new_metric or "PASS"
        )
        print(f"Итерация зафиксирована: commit {commit_hash}. Прогресс сохранен.")
        return 0

    print("\n[ОТКАТ] Сбой тестов или регрессия метрики. Сброс к стабильному коммиту...")
    log_experiment_jsonl(
        experiments_file,
        args.hypothesis,
        "REJECTED",
        old_metric_str,
        args.new_metric or "FAIL",
    )
    update_state_markdown(
        state_file, args.hypothesis, "REJECTED", args.new_metric or "FAIL"
    )

    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=work_dir)
    print(
        "Выполнен git reset --hard HEAD. Рабочий каталог возвращен к исходному состоянию."
    )

    consecutive_fails = count_consecutive_failures(experiments_file)
    print(f"Последовательных неудачных попыток: {consecutive_fails}")
    if consecutive_fails >= 3:
        print("\n" + "=" * 65)
        print("ВНИМАНИЕ: СРАБОТАЛ META LOOP (АНТИ-СХЛАПЫВАНИЕ ПО КАРПАТОМУ)!")
        print("Три итерации подряд не дали прироста метрики.")
        print("1. Текущие попытки архивируются в archive/attempt_N/.")
        print("2. Рабочая ветка сбрасывается к начальному базису.")
        print("3. Смена парадигмы: запрет прежнего подхода, ортогональный перезапуск.")
        print("=" * 65)
        return 3

    return 1


if __name__ == "__main__":
    sys.exit(main())
