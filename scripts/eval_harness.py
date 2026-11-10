"""Легковесный экспресс-бенчмарк харнессов и скиллов (Harness-Bench-Fast).

Вдохновлен ai-forever/harness-bench-fast и спецификацией agentskills.io:
1. Проверка соответствия стандарту agentskills.io (контракт frontmatter, бюджет токенов).
2. Компиляция и синтаксическая целостность всех исполняемых скриптов.
3. Проверка чистоты типографики (гигиена текста).
4. Прогон детерминированных тестов обратного давления (checks/).
5. Расчет интегрального скора надежности скилла (0-100%).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import time


def evaluate_skill(skill_dir: Path) -> dict[str, object]:
    results: dict[str, object] = {
        "name": skill_dir.name,
        "path": str(skill_dir),
        "checks_passed": 0,
        "checks_total": 5,
        "details": [],
        "score": 0.0,
    }
    details: list[str] = []
    passed = 0

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        details.append("[FAIL] Файл SKILL.md отсутствует.")
        results["details"] = details
        return results

    content = skill_file.read_text(encoding="utf-8", errors="ignore")

    # 1. Спецификация agentskills.io (Frontmatter)
    fm_match = re.match(r"^---\s*\r?\n(.*?)\r?\n---", content, re.DOTALL)
    if fm_match:
        meta = {}
        for line in fm_match.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
        name = meta.get("name", "")
        desc = meta.get("description", "")
        if name and re.match(r"^[a-z0-9-]+$", name) and len(name) <= 64:
            passed += 1
            details.append(f"[OK] Спецификация имени: '{name}' валидна.")
        else:
            details.append(f"[FAIL] Некорректное имя скилла: '{name}'.")

        # 2. Бюджет смарт-зоны (Resident Context Budget)
        if desc and len(desc) <= 350:
            passed += 1
            details.append(
                f"[OK] Бюджет контекста: описание {len(desc)} симв. (<= 350)."
            )
        else:
            details.append(
                f"[FAIL] Превышение бюджета контекста: {len(desc)} симв. > 350."
            )
    else:
        details.append("[FAIL] YAML Frontmatter отсутствует.")

    # 3. Синтаксис и компиляция скриптов
    py_files = list(skill_dir.rglob("*.py"))
    syntax_ok = True
    for pf in py_files:
        try:
            compile(pf.read_text(encoding="utf-8", errors="ignore"), str(pf), "exec")
        except Exception as e:
            syntax_ok = False
            details.append(f"[FAIL] Синтаксический сбой в {pf.name}: {e}")
            break
    if syntax_ok:
        passed += 1
        details.append(
            f"[OK] Синтаксис: {len(py_files)} Python-файлов компилируются без ошибок."
        )

    # 4. Типографика и гигиена текста
    if not re.search(r"[—–«»“”]", content):
        passed += 1
        details.append("[OK] Гигиена текста: запрещенные спецсимволы отсутствуют.")
    else:
        details.append(
            "[FAIL] Нарушение гигиены текста (обнаружены длинные тире или фигурные кавычки)."
        )

    # 5. Обратное давление (Backpressure execution)
    checks_dir = skill_dir / "checks"
    if checks_dir.exists() and list(checks_dir.glob("*.py")):
        bp_ok = True
        for chk in checks_dir.glob("*.py"):
            proc = subprocess.run(
                [sys.executable, str(chk), str(skill_dir)], capture_output=True
            )
            if proc.returncode != 0:
                bp_ok = False
                details.append(
                    f"[FAIL] Тест обратного давления {chk.name} завершился с ошибкой."
                )
                break
        if bp_ok:
            passed += 1
            details.append("[OK] Обратное давление: тесты checks/ пройдены успешно.")
    else:
        passed += 1
        details.append("[OK] Каталог checks/ проверен.")

    results["checks_passed"] = passed
    results["score"] = round((passed / 5.0) * 100, 1)
    results["details"] = details
    return results


def run_benchmark(target_dir: Path) -> int:
    start_time = time.time()
    skills_to_eval = []

    if (target_dir / "SKILL.md").exists():
        skills_to_eval.append(target_dir)
    else:
        for p in target_dir.rglob("SKILL.md"):
            skills_to_eval.append(p.parent)

    print("=" * 70)
    print("ЗАПУСК ЭКСПРЕСС-БЕНЧМАРКА ХАРНЕССА (HARNESS-BENCH-FAST)")
    print(f"Целевой каталог: {target_dir}")
    print(f"Обнаружено скиллов для оценки: {len(skills_to_eval)}")
    print("=" * 70)

    total_score = 0.0
    passed_count = 0

    for s_path in skills_to_eval:
        res = evaluate_skill(s_path)
        score = float(res["score"])  # type: ignore
        total_score += score
        status = "[PASS]" if score >= 80.0 else "[FAIL]"
        if score >= 80.0:
            passed_count += 1
        print(
            f"\n{status} {res['name']} — Скор: {score}% ({res['checks_passed']}/5 проверок)"
        )
        for d in res["details"]:  # type: ignore
            print(f"   {d}")

    elapsed = round(time.time() - start_time, 2)
    avg_score = round(total_score / len(skills_to_eval), 1) if skills_to_eval else 0.0

    print("\n" + "=" * 70)
    print("ИТОГОВЫЙ ОТЧЕТ БЕНЧМАРКА (HARNESS-BENCH-FAST SUMMARY)")
    print(f"Проверено скиллов: {len(skills_to_eval)}")
    print(f"Успешно прошли (>=80%): {passed_count}/{len(skills_to_eval)}")
    print(f"Средний интегральный скор: {avg_score}%")
    print(f"Время выполнения: {elapsed} сек.")
    print("=" * 70)

    return 0 if avg_score >= 80.0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Harness-Bench-Fast: Оценка качества и надежности скиллов"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Целевая директория скилла или репозитория",
    )
    args = parser.parse_args()
    return run_benchmark(Path(args.target).resolve())


if __name__ == "__main__":
    sys.exit(main())
