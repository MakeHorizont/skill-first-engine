"""Контроллер внешнего цикла Ralph Loop и Meta Loop анти-схлапывания.

Реализует Правило 4.2 и 4.3:
- Чтение и обновление STATE.md (метрика, журнал гипотез, следующий шаг).
- Запуск тестов/бенчмарка после внесения изменений.
- При успехе: git commit + фиксация прогресса в STATE.md.
- При регрессии/сбое: git reset --hard HEAD + запись неудачной гипотезы.
- Детектор 3 последовательных неудач: сигнал Meta Loop для ортогонального маневра.
"""

from __future__ import annotations

import argparse
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


def count_consecutive_failures(state_file: Path) -> int:
    if not state_file.exists():
        return 0
    content = state_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    failures = 0
    # Проход с конца по списку проверенных гипотез
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("- [x] [REJECTED]") or line.startswith("- [FAIL]"):
            failures += 1
        elif line.startswith("- [x] [ACCEPTED]") or line.startswith("- [OK]"):
            break
    return failures


def append_hypothesis_result(
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
    parser = argparse.ArgumentParser(description="Ralph Loop Controller")
    parser.add_argument(
        "--test-cmd",
        required=True,
        help="Команда запуска объективного теста или бенчмарка",
    )
    parser.add_argument(
        "--hypothesis",
        required=True,
        help="Формулировка проверяемой гипотезы текущей итерации",
    )
    parser.add_argument(
        "--new-metric",
        default="",
        help="Новое значение целевой метрики (если применимо)",
    )
    parser.add_argument(
        "--work-dir",
        default=".",
        help="Рабочая директория задачи",
    )

    args = parser.parse_args()
    work_dir = Path(args.work_dir).resolve()
    state_file = work_dir / "STATE.md"

    print(f"[Ralph Loop] Проверка гипотезы: {args.hypothesis}")
    print(f"Запуск команды верификации: {args.test_cmd}")

    code, output = run_benchmark(args.test_cmd, work_dir)
    print(f"Вывод теста (код {code}):\n{output[:500]}")

    if code == 0:
        print("\n[УСПЕХ] Тесты пройдены. Фиксация изменений...")
        append_hypothesis_result(
            state_file, args.hypothesis, "ACCEPTED", args.new_metric or "PASS"
        )
        # Git commit
        subprocess.run(["git", "add", "."], cwd=work_dir)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"feat(loop): гипотеза принята - {args.hypothesis}",
            ],
            cwd=work_dir,
        )
        print("Коммит зафиксирован. Итерация завершена успешно.")
        return 0

    print("\n[СБОЙ] Тесты не пройдены. Откат к последнему стабильному состоянию...")
    append_hypothesis_result(
        state_file, args.hypothesis, "REJECTED", args.new_metric or "FAIL"
    )
    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=work_dir)
    print("Выполнен git reset --hard HEAD. Сессия очищена.")

    failures = count_consecutive_failures(state_file)
    print(f"Последовательных неудачных попыток: {failures}")
    if failures >= 3:
        print("\n" + "=" * 60)
        print("ВНИМАНИЕ: СРАБОТАЛ META LOOP (АНТИ-СХЛАПЫВАНИЕ)!")
        print("Три попытки подряд не дали результата.")
        print("1. Сохраните текущие наработки в archive/attempt_N/")
        print("2. Сбросьте задачу до исходного состояния.")
        print("3. Смените парадигму и начните с нуля по ортогональному пути.")
        print("=" * 60)
        return 3

    return 1


if __name__ == "__main__":
    sys.exit(main())
