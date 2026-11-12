# Карта возможностей и доказательств

Обзор 2026-11-12. Факты ниже установлены чтением файлов, если явно не указано иное.
Статусы — локальные характеристики, а не итоговая оценка готовности сервиса.
«Тесты найдены» означает только наличие tracked test-файлов, не покрытие и не успех.
Исторический прогон `plan-operation-contracts` подтверждает только свои сценарии.

## Возможности и границы

| ID / область | Где и с кем взаимодействует | Контракт / доказательства сейчас | Что ещё неизвестно |
| --- | --- | --- | --- |
| IDENTITY / аккаунты и доступ | gateway → accounts; principal передаётся HTTP/gRPC; удаление затрагивает сервисы | [Gateway](../../gateway/gateway_app/main.py), [общая зависимость](../../libs/backend-common/backend_common/dependencies.py), тесты accounts + auth/profile E2E найдены | Полнота ролевых правил, доверенная граница внутренних заголовков и сквозное удаление |
| COACHING / CRM | gateway → crm; отношения тренер/спортсмен используются планами/агентом | [CRM main](../../services/crm-service/crm_service/main.py), сервисный тест и CRM E2E найдены | Какие данные тренер может читать/изменять в каждой capability; отзыв доступа и кеш |
| EXERCISES / каталог и экземпляры | exercises-service; workout instances также живут в workouts-service; клиенты plans/agent/RPE | [Exercise service](../../services/exercises-service/exercises_service/services/exercise_service.py), [workout instances](../../services/workouts-service/workouts_service/services/exercise_instance_service.py), тесты exercises найдены | Какая модель является владельцем каких экземпляров; единицы и семантика идентификаторов на границах |
| CALCULATIONS / RPE и силовые максимумы | rpe-service ↔ user-max; используются plans/workouts/agent и Flutter | [RPE](../../services/rpe-service/rpe_service/calculation.py), [схема максимумов](../../services/user-max-service/user_max_service/schemas.py), тесты обоих сервисов найдены | Единая семантика вводов, округления, неизвестных значений, create/update и HTTP/gRPC |
| PLAN / шаблоны и применённые планы | plans → exercises/user-max/RPE/workouts; gateway/Flutter/agent | Три [основные specs](../../openspec/specs/plan-application/spec.md) вместе с переносом/правкой; [исторический отчёт](../development/plan-contract-verification.md) | Это часть capability: каталог, макросы, версии шаблона и другие жизненные циклы не покрыты этим отчётом |
| WORKOUT / тренировки и сессии | workouts + instances/sets/sessions; планы, импорт, история, аналитика | [Workouts](../../services/workouts-service/workouts_service/services/workout_service.py), [сессии](../../services/workouts-service/workouts_service/services/session_service.py); есть точечные проверки плановых операций | Полная модель переходов сессий, импорт, смешанные изменения и единая граница истории |
| MACROS / правила адаптации | plans MacroEngine → MacroApplier → HTTP instances; agent создаёт/интерпретирует правила | [Движок](../../services/plans-service/plans_service/services/macro_engine.py), [применение](../../services/plans-service/plans_service/services/macro_apply.py), [AI manager](../../services/agent-service/agent_service/services/macros_manager.py) | Пустая выборка против недоступного источника; конфликт правил, повтор, частичный результат; есть ORM-проверка PlanMacro; тесты исполнения Engine/Applier в просмотренных tracked tests не найдены |
| NUTRITION / питание, добавки, лекарства | JSON nutrition_plan в plans + отдельный supplements модуль в workouts; gateway проксирует CRUD | [Модели](../../services/workouts-service/workouts_service/supplements/models.py), [router](../../services/workouts-service/workouts_service/supplements/routers.py), [gateway](../../gateway/gateway_app/routes/workouts.py); [принято: продукты общие, рационы персональные](../decisions/DEC-20261112-shared-foods-personal-diets.md) | Соответствие моделей принятому разделению; права редактирования каталога/доступа к рациону; назначение supplement/medication; тип user_id; единицы; сохранность при отказе БД; связь двух моделей питания |
| AI / контекст и действия агента | WebSocket → EventDispatcher → ToolAgent → HTTP tools/FSM; Celery и клиенты | [Dispatcher](../../services/agent-service/agent_service/services/event_dispatcher.py), [tools](../../services/agent-service/agent_service/services/tool_agent.py), [результаты](../../services/agent-service/agent_service/services/tool_result_dispatcher.py); один tracked test-файл agent | Систематические eval-сценарии, проверка сущностей и прав на эффект, транспортные ошибки и правильность сообщения результата |
| EVENTS / social, messaging, webhooks | отдельные DB/outbox → Redis streams → webhook-dispatcher → внешние получатели | [Outbox](../../social-service/outbox.py), [доставка](../../webhook-dispatcher/event_processor.py); тесты каждого контура найдены | Семантика восстановления retry после перезапуска, дубликатов, подтверждения и удаления данных |
| CDC / репликация и витрины | 7 Postgres connectors → Debezium → Kafka → ClickHouse; UI analytics и serving-аналитика требуют отдельной сверки | [Коннектор](../../analytics/debezium/connectors/workouts-connector.json), [raw](../../analytics/clickhouse/init/09_raw_workouts.sql), [README](../../analytics/README.md) | Корректность snapshot/update/delete/replay и задержка; связь витрин с реальными UI-запросами не установлена; отдельного CDC E2E не найдено |
| RUNTIME / запуск, конфигурация и очереди | compose profiles, env, Alembic, API и worker; общие cache/http/logging helpers | [Production compose](../../docker-compose.prod.yml), [общий app factory](../../libs/backend-common/backend_common/fastapi_app.py) | Матрица обязательных/опциональных возможностей, readiness, согласование очередей и реальный deployment state |
| CLIENT / Flutter и Telegram | Flutter в соседнем repo → gateway, включая WebSocket; tg_bot имеет собственные модели/сервисы | [Flutter repo](https://github.com/oleksiikomarychev/athletic-performance-clients), [бот](../../tg_bot/README.md), проверен контракт замены плана | Широкая проверка вызывающих сценариев не проводилась; совпадение доменных правил разных клиентов не доказано |
| DELIVERY / тесты и выпуск | scripts/test_plan_contracts.py, pytest, pre-commit, GitHub publish | [Проверочный runner](../../scripts/test_plan_contracts.py), [workflow](../../.github/workflows/publish-images.yml) | Обязательный test gate перед merge/publish и безопасный запуск всех suite пока не подтверждены |

## Наблюдения, требующие отдельного change или решения

| ID | Что действительно видно | Следствие / вопрос | Уверенность |
| --- | --- | --- | --- |
| OBS-01 | Supplements при отсутствии URL или исключении подключения создаёт in-memory SQLite и таблицы: `supplements/models.py` | Расхождение с [принятым запретом SQLite и in-memory fallback](../decisions/DEC-20261112-postgresql-without-sqlite-fallback.md). Код ещё не исправлен; отладочное происхождение fallback лишь предположение | По коду; сбой и перезапуск не воспроизводились |
| OBS-02 | Supplements session routes принимают user_id из payload/URL; `get_all_sessions` вызывает выборку всех записей; общего principal Depends в этих handlers нет | Нужна модель персональности и ролевого доступа. Это не доказательство внешнего эксплойта: gateway/network deployment не проверялись | По коду router/services |
| OBS-03 | `MacroApplier._fetch_instances` возвращает `[]` при недоступности/невалидном ответе; apply может вернуть `applied=0, errors=[]` | Недоступный источник может выглядеть как нормальное отсутствие работы. Нужен контракт результата исполнения | По коду; fault injection не запускался |
| OBS-04 | MacroApplier читает instances из exercises-service, тогда как плановые операции меняют instances в workouts-service | Проверить владельца данных и совместимость адресов; нельзя считать это багом только по именам каталогов | Открытая архитектурная граница |
| OBS-05 | UserMaxCreate задаёт обычные float/int, UserMaxUpdate использует `gt=0`; RPE volume округляется при coercion | Нет общей явно закреплённой политики числовых вводов на create/update и между сервисами | По схемам; все ветки валидаторов/HTTP/gRPC не проверены |
| OBS-06 | `/health` нескольких API возвращает статическое `ok`; supplements выбирает БД отдельно; очереди и CDC включаются разными конфигурациями | Liveness не подтверждает готовность конкретной capability. Нужна матрица enabled/required dependencies | По main/compose; readiness может существовать в другом месте, полный поиск deployment не проводился |
| OBS-07 | Analytics README описывает запуск CDC через prod compose; текущий prod compose не содержит analytics services, они есть в dev analytics profile | Документация и профиль запуска расходятся. Нужен выбранный способ production-развёртывания CDC | Сопоставление файлов, без запуска |
| OBS-08 | CDC connector использует delete rewrite/tombstones; raw ClickHouse — ReplacingMergeTree и materialized views | Наличие конфигурации не доказывает удаление/дедупликацию в итоговом чтении. Нужна проверка всей цепочки с replay | По JSON/SQL, не обнаруженный дефект доставки |
| OBS-09 | Просмотренный GitHub workflow строит и публикует образы; шагов tests/spec validation в нём нет | Общие гарантии сейчас не обеспечиваются обязательным CI gate этого workflow | По workflow; branch protection и внешние checks не проверены |
| OBS-10 | Agent test suite импортирует app/engine, вызывает `Base.metadata.create_all` и удаляет записи через импортированный SessionLocal | Общий запуск тестов требует изоляции конфигурации до импорта. Запуск с обычным `.env` может затронуть выбранную там БД | По test-коду; потенциально опасный прогон намеренно не выполнялся |
| OBS-11 | Имеются `services/principles.md` и prompt-инструкции AI, но они не равны проверяемым API/domain контрактам | Нужно выбрать, какие принципы являются требованиями продукта, а какие — советами/эвристиками | Документы прочитаны, принятие их как SHALL не предполагается |

## Дополнительная проверенная граница маршрутизации

OBS-12: `workouts_service/main.py` подключает supplements router с префиксом
`/workouts`, то есть ожидается `/workouts/supplements/...`. Просмотренные handlers
`gateway/routes/workouts.py` обращаются к upstream `/supplements/...`. Это
статическое расхождение маршрутов, которое нужно проверить consumer contract test;
HTTP-запросы в данном обзоре не выполнялись. Поэтому факт наличия gateway handler
сам по себе не доказывает доступность nutrition/supplements пользователю.

## Цепочки, которые определяют область влияния

1. Изменение exercise identity / единиц → exercises, user-max, RPE, расчёт plans/workouts,
   AI tool schemas, Flutter и возможные CDC-проекции. Проверяем затронутые рёбра.
2. Исполнение правила → источник контекста, MacroEngine, MacroApplier, владелец
   записываемых instances, отображение результата агентом/клиентом.
3. Состояние фоновой операции → enqueue, broker, выбранная очередь, worker,
   result backend, HTTP/WebSocket adapter, клиентский polling и recovery.
4. Изменение SQL-схемы → ORM/миграция, producer event или Debezium schema,
   consumer/raw table, витрина и читающий API. Связи нужно доказывать, а не предполагать.

## Срез найденных тестов

Подсчёт только tracked `test_*.py`, без virtualenv. Функции и параметризации не равны
числу сценариев или проценту покрытия. Тесты в этом обзоре не запускались.

| Контур | Файлы / test-функции |
| --- | --- |
| Accounts / CRM | 1 / 24; 1 / 14 |
| Exercises / RPE / User-max | 1 / 8; 1 / 45; 1 / 20 |
| Plans / Workouts / Agent | 5 / 24; 3 / 21; 1 / 17 |
| Social / Messaging / Webhook dispatcher | 7 / 63; 8 / 34; 1 / 14 |
| Telegram | 0 / 0 в просмотренном tracked Python tree |
| Общие E2E / интеграционные | 6 / 19; 1 / 7 |

Вывод этого среза — требуется выбрать сквозные проверяемые свойства и изолированные
стенды. Из количества функций нельзя заключить, что RPE или social уже защищены.
