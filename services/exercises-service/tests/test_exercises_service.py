import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

proto_gen_path = Path(__file__).resolve().parent.parent / "proto_gen"
if str(proto_gen_path) not in sys.path:
    sys.path.insert(0, str(proto_gen_path))

import common_pb2  # noqa: F401, E402
import exercises_pb2  # noqa: E402
import pytest  # noqa: E402
from exercises_service import schemas  # noqa: E402
from exercises_service.grpc_server import (  # noqa: E402
    ExercisesServicer,
    _proto_exercise_definition,
    _proto_exercise_instance,
)
from exercises_service.main import app  # noqa: E402
from exercises_service.redis_client import (  # noqa: E402
    exercise_definition_key,
    exercise_definitions_list_key,
    generate_filters_hash,
)
from exercises_service.services.exercise_service import ExerciseService  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def test_schemas_enums_and_models():
    """Verify schema models and StrEnum serialization."""
    assert schemas.MovementType.compound == "compound"
    assert schemas.MovementType.isolation == "isolation"
    assert schemas.Region.upper == "upper"
    assert schemas.Region.lower == "lower"
    assert schemas.EffortType.RPE == "RPE"
    assert schemas.EffortType.RIR == "RIR"

    payload = schemas.ExerciseListCreate(
        name="Bench Press",
        muscle_group="Chest",
        equipment="Barbell",
        movement_type=schemas.MovementType.compound,
        region=schemas.Region.upper,
    )
    assert payload.name == "Bench Press"
    assert payload.movement_type == "compound"

    response = schemas.ExerciseListResponse(
        id=1,
        name="Bench Press",
        muscle_group="Chest",
        equipment="Barbell",
        movement_type=schemas.MovementType.compound,
        region=schemas.Region.upper,
    )
    assert response.id == 1
    assert response.model_dump()["movement_type"] == "compound"


def test_redis_key_generation():
    """Verify consistent Redis keys and filter hash generation."""
    key = exercise_definition_key(42)
    assert key == "exercises:def:42"

    list_key_all = exercise_definitions_list_key(None)
    assert list_key_all == "exercises:def:list:all"

    list_key_ids = exercise_definitions_list_key((1, 2, 3))
    assert list_key_ids == "exercises:def:list:1,2,3"

    hash1 = generate_filters_hash(["chest"], ["barbell"], 10, 0)
    hash2 = generate_filters_hash(["chest"], ["barbell"], 10, 0)
    assert hash1 == hash2
    assert len(hash1) == 8


def test_proto_conversion():
    """Verify conversion between Pydantic models and Protobuf messages."""
    defn = schemas.ExerciseListResponse(
        id=10,
        name="Squat",
        muscle_group="Legs",
        equipment="Barbell",
        image_url="http://example.com/img.png",
        gif_url="http://example.com/squat.gif",
    )
    proto_msg = _proto_exercise_definition(defn)
    assert proto_msg is not None
    assert proto_msg.id == 10
    assert proto_msg.name == "Squat"
    assert proto_msg.muscle_group == "Legs"
    assert proto_msg.equipment == "Barbell"
    assert proto_msg.media_image == "http://example.com/img.png"
    assert proto_msg.media_gif == "http://example.com/squat.gif"

    assert _proto_exercise_definition(None) is None
    assert _proto_exercise_instance(None) is None


def test_health_endpoints():
    """Verify health endpoints return ok."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    resp2 = client.get("/exercises/health")
    assert resp2.status_code == 200
    assert resp2.json() == {"status": "ok"}


def test_muscles_endpoint():
    """Verify muscles endpoint returns list of MuscleInfo."""
    ExerciseService.MUSCLE_LABELS = {
        "chest": {"label": "Chest", "group": "Upper Body"},
        "quads": {"label": "Quadriceps", "group": "Lower Body"},
    }
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/exercises/muscles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert any(m["key"] == "chest" and m["label"] == "Chest" for m in data)


@pytest.mark.asyncio
async def test_list_definitions_route_mocked():
    """Verify list exercise definitions endpoint routing and parsing."""
    client = TestClient(app, raise_server_exceptions=False)

    fake_exercises = [
        schemas.ExerciseListResponse(
            id=1,
            name="Bench Press",
            muscle_group="Chest",
            equipment="Barbell",
        )
    ]

    with patch(
        "exercises_service.services.exercise_definition_service.ExerciseDefinitionService.list_definitions",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = fake_exercises

        # Test route with trailing slash
        resp1 = client.get("/exercises/definitions/")
        assert resp1.status_code == 200
        assert len(resp1.json()) == 1
        assert resp1.json()[0]["name"] == "Bench Press"

        # Test route without trailing slash (no redirect)
        resp2 = client.get("/exercises/definitions")
        assert resp2.status_code == 200
        assert len(resp2.json()) == 1


@pytest.mark.asyncio
async def test_create_and_compat_get_definition_route():
    """Verify create definition and backward-compatible GET /exercises/{id} route."""
    client = TestClient(app, raise_server_exceptions=False)

    sample_ex = schemas.ExerciseListResponse(
        id=7,
        name="Deadlift",
        muscle_group="Back",
        equipment="Barbell",
    )

    with patch(
        "exercises_service.services.exercise_definition_service.ExerciseDefinitionService.create_definition",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = sample_ex
        resp = client.post(
            "/exercises/definitions/",
            json={"name": "Deadlift", "muscle_group": "Back", "equipment": "Barbell"},
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == 7
        assert resp.json()["name"] == "Deadlift"

    # Test backward compatibility alias /exercises/{id}
    with patch(
        "exercises_service.services.exercise_definition_service.ExerciseDefinitionService.get_definition",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = sample_ex
        resp_compat = client.get("/exercises/7")
        assert resp_compat.status_code == 200
        assert resp_compat.json()["name"] == "Deadlift"


@pytest.mark.asyncio
async def test_grpc_servicer_get_exercise():
    """Verify gRPC servicer GetExercise method."""
    servicer = ExercisesServicer()
    mock_context = MagicMock()

    sample_ex = schemas.ExerciseListResponse(
        id=15,
        name="Pull-up",
        muscle_group="Back",
        equipment="Bodyweight",
    )

    request = exercises_pb2.GetExerciseRequest(exercise_id=15)

    with patch(
        "exercises_service.services.exercise_definition_service.ExerciseDefinitionService.get_definition",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = sample_ex
        response = await servicer.GetExercise(request, mock_context)
        assert response.exercise.id == 15
        assert response.exercise.name == "Pull-up"
        assert response.exercise.muscle_group == "Back"

    # Test not found
    with patch(
        "exercises_service.services.exercise_definition_service.ExerciseDefinitionService.get_definition",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None
        response = await servicer.GetExercise(request, mock_context)
        mock_context.set_code.assert_called_once()
