# Ошибка логирования прерывает повтор компенсационной очистки

- Статус: reproduced
- Область / сервисы: plans-service, cleanup_failed_application_task
- Класс: retry / partial-failure
- Обнаружен: 2026-11-12 при подключении локальных проверок
- Связи: [Очистка неуспешного применения](../../openspec/specs/plan-application/spec.md), [проверки change](../../openspec/changes/enforce-change-verification/proposal.md), [временная видимость](../decisions/DEC-20261110-temporary-workout-visibility.md)

## Условие и влияние

Генерация первого пакета прошла, следующий пакет упал, inline-очистка недоступна.
Первая попытка фоновой очистки тоже получает 503. Обработчик ошибки должен поставить
повтор, но вызов логгера сам выбрасывает исключение. Не начатые тренировки могут
остаться после неуспешного применения.

## Ожидаемое и фактическое поведение

Ожидаемое по принятому контракту: повторить очистку после временного сбоя.
Фактическое: `TypeError: Logger._log() got an unexpected keyword argument
'applied_plan_id'` возникает до `self.retry`; тест ожидает очистку и завершается timeout.

## Воспроизведение

- Версия: runtime поверх `cdcd8c71`, без изменений кода сервиса в текущем change.
- Окружение: disposable Docker PostgreSQL 16 / Redis 7, HTTP gateway/plans/workouts,
  настоящий Celery worker; синтетический pipeline-user, случайные схемы и локальные порты.
- Команда из корня: `python3 scripts/test_plan_contracts.py`.
- Первый прогон 2026-11-12: 2 failed, 10 passed в integration group;
  исходный runner остановился, группы plans/workouts не запускались.
- Runner удаляет временные контейнеры и proto; fixtures удаляют случайные схемы.

## Причина и исправление

`get_task_logger` возвращает стандартный logger, а обработчик передаёт структурный
keyword `applied_plan_id` непосредственно в `logger.exception`. Stack trace подтверждает
сбой перед `self.retry`. Исправление сервиса не входит в текущую настройку проверок;
код не изменён, случай остаётся reproduced.

## Регрессионная проверка

- `tests/integration/test_plan_operation_pipeline.py::test_second_batch_failure_rolls_back_plan_and_cleans_workouts[False-True]`
- Тот же тест `[True-True]`; последний параметр включает отказ очистки.
- До исправления: 2026-11-12, оба теста падают по timeout; stack trace выявляет ошибку logger.
- После исправления: не запускалось, исправление не выполнено.

## История повторных проверок

| Дата | Версия | Команда / сценарий | Результат и ограничения |
| --- | --- | --- | --- |
| 2026-11-12 | cdcd8c71 runtime | test_plan_contracts.py | Воспроизведено в изолированном стенде; production/VPS не проверялись |
| 2026-11-12 | тот же runtime, runner с URL изоляцией до импорта | test_plan_contracts.py | Повторно 42 passed, 2 failed; код выхода 1, временные контейнеры удалены |
