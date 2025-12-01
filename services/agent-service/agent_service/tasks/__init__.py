"""Celery tasks package for agent-service.

This module imports submodules that actually define Celery tasks so that
`celery_app.autodiscover_tasks(["agent_service"])` (which looks for
`agent_service.tasks`) will execute their module-level `@shared_task`
decorators and register tasks such as ``agent.applied_mass_edit.direct``.
"""

# Import task modules for their side effects (task registration).
from . import mass_edit_tasks as _mass_edit_tasks  # noqa: F401
from . import plan_tasks as _plan_tasks  # noqa: F401
