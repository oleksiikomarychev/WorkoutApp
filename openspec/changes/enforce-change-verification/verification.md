# Проверка enforce-change-verification

Ниже — результаты первоначальной настройки hooks, сохранённые в `906d63ac`.
Последующее исправление сервиса отражено отдельно в конце, исходные результаты не переписаны.

Дата: 2026-11-12. Версия: рабочее дерево над backend `cdcd8c71`, изменения не
закоммичены и не отправлены. Сервисы приложения не изменены; изменены процесс,
hooks и тестовые runners. Установка hooks выполнена в текущем checkout.

## Доказательства изменённых требований

Имена требований и сценариев соответствуют [delta](specs/change-verification/spec.md).

| Требование | Сценарий | Проверка | Результат | Ограничения |
| --- | --- | --- | --- | --- |
| Доказательства завершения требования | Обязательная проверка недоступна | Ручная сверка docs/development/change-completion.md: failed/blocked/not-run обязательной гарантии запрещают завершение; CLI instructions tasks загружают правило, archive guidance записан в config | passed, 2026-11-12 | Содержательная полнота проверяется review, не парсером Markdown |
| Доказательства завершения требования | Проверки завершены | Ручная сверка всех четырёх требований и семи Scenario с этой таблицей, tasks и фактическими результатами | passed, 2026-11-12 | Подтверждён процесс и hook, а не соответствие всех сервисов шести контрактам |
| Быстрая проверка спецификаций | Невалидные артефакты | `python3 -m unittest discover -s scripts/tests -v`: HookTests.test_installed_commit_hook_propagates_validator_failure; `pre-commit run openspec-validate --all-files` с настоящим CLI | passed, 2026-11-12 | В негативном hook-тесте validator stub возвращает ненулевой код; структура реального repo проверена настоящим CLI |
| Выборочные проверки перед push | Документационное изменение | SelectionTests.test_docs_do_not_start_services и HookTests.test_push_range_accepts_docs_and_propagates_failure | passed, 2026-11-12 | В синтетическом Git repo проверяется настоящий pre-commit и local entries, OpenSpec заменён stub |
| Выборочные проверки перед push | Неизвестная область или отказ инструмента | SelectionTests.test_unknown_area_blocks_without_running_suite / test_missing_tool_is_failure / test_failure_stops_following_checks; HookTests.test_push_blocks_unmapped_runtime | passed, 2026-11-12 | Неизвестные suite намеренно не импортируются; набор планов также реально вернул код 1, см. ниже |
| Выборочные проверки перед push | Изменение проверенной области | SelectionTests.test_combines_boundaries_once / test_known_plan_consumer_and_spec; реальные RPE и plan-contracts runners | passed для выбора/передачи статуса, 2026-11-12 | RPE зелёный; исходный набор планов не зелёный — 2 ошибки сервиса, не скрыты и не исправлены этим change |
| Проверка отправляемой версии | Checkout отличается от отправляемого состояния | GitRangeTests.test_wrong_checkout_blocks / test_dirty_tree_blocks_pushed_version / test_parent_hook_git_environment_cannot_redirect_repo | passed, 2026-11-12 | Новая ветка без базы консервативно проверяет всё дерево; иной HEAD требует checkout |
| Проверка отправляемой версии | Checkout отличается от отправляемого состояния — дополнительно диапазон | GitRangeTests.test_range_includes_all_commits_and_deletions / test_first_push_inspects_tree / test_staged_deletion_is_included; реальный pre-push consumer в HookTests | passed, 2026-11-12 | Настоящий push не выполнялся; проверены команды pre-commit с from/to refs |

## Команды и результаты

- `python3 -m unittest discover -s scripts/tests -v`: **20 passed** после исправления
  синтетической настройки тестовых hooks. Промежуточный прогон трёх hook-тестов
  не установил hooks из-за заданного core.hooksPath; ошибка fixture устранена.
- `python3 scripts/test_rpe_contracts.py`: **45 passed**, 1 предупреждение зависимости.
  Временная генерация всех proto, mock внешних HTTP/gRPC вызовов, БД не нужна.
- `python3 scripts/test_plan_contracts.py`: **42 passed, 2 failed**:
  integration 10 passed/2 failed, plans 8 passed, workouts 24 passed. Код выхода 1.
  Существующий [дефект retry logger](../../../docs/edge-cases/EC-20261112-cleanup-retry-logger.md)
  воспроизведён; сервис не исправлялся. Runner теперь проверяет оставшиеся группы
  после ошибки и сохраняет общий неуспешный код; ошибки не игнорируются.
  Итоговый повторный прогон после изоляции URL до импорта дал те же 42 passed/2 failed.
  SelectionTests.test_plan_runner_overrides_application_urls_before_imports проверяет,
  что PLANS/WORKOUTS/SUPPLEMENTS и общий DATABASE_URL указывают на тестовый PostgreSQL,
  включая sync engine supplements; обычный `.env` не выбирает рабочую БД.
- `pre-commit install --hook-type pre-commit --hook-type pre-push`: оба установлены.
- `pre-commit validate-config` и `pre-commit run openspec-validate --all-files`: прошли.
- Ruff и ruff-format для пяти изменённых Python-файлов через существующие pre-commit
  hooks: прошли. В workspace нет отдельного `ruff` executable; используется hook environment.
- `python3 scripts/check_changed.py --files .pre-commit-config.yaml`: реальный выбор
  workflow, OpenSpec validation (6 passed) и 20 тестов прошли. `git diff --check`
  прошёл; локальные ссылки и наличие всех имён Requirement/Scenario в таблице проверены.

## Пределы и критерий завершения

Обязательные свойства этого tooling change — критерий review, выбор, изоляция,
отказ и передача результата — проверены. Зелёный результат существующего plan
runtime-контракта не заявляется и не является реализуемым требованием этого change:
hook корректно блокирует его при ошибке. Исправление обнаруженного бага сервиса —
отдельная работа в рамках ранее принятого требования plan-application.

Hooks обходятся SKIP/--no-verify и не заменяют серверный CI gate. Новых Actions
нет; branch protection не менялась. Неизвестные runtime-области блокируются до
добавления безопасного набора. Карта выбора не доказывает полноту тестов изменения:
конкретный change добавляет недостающие проверки и подтверждает таблицей/review.

В итоговом прогоне Neon/VPS и локальная БД приложения не использовались. В тестах планов созданы
и удалены отдельные Docker PostgreSQL/Redis, случайные схемы и временные proto.
Автоматическое архивирование и объявление продукта полностью проверенным не выполнялись.

## Последующая проверка после исправления logger

2026-11-12 владелец отдельно поручил исправить дефект и отправить изменения в staging.
Стандартный logger теперь принимает ID через позиционный аргумент форматирования.
Новый точечный тест упал на исходном TypeError до правки и прошёл после; политика
очистки и main spec не менялись. [Edge case переведён в verified](../../../docs/edge-cases/EC-20261112-cleanup-retry-logger.md).

`python3 scripts/check_changed.py --worktree`: **45 plan-contracts + 45 RPE + 20 workflow passed**,
OpenSpec validation — 6 passed. Сбой больше не блокирует набор планов. Проверено рабочее
дерево с исправлением поверх `906d63ac`; deployment не выполнялся. Результат push
проверяется отдельно после commit и повторного fetch.
