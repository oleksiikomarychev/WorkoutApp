"""Unit and integration tests for user-max-service."""

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from user_max_service.config import settings
from user_max_service.database import Base, get_db
from user_max_service.main import app
from user_max_service.models import UserMax
from user_max_service.repositories import UserMaxRepository
from user_max_service.schemas import UserMaxCreate, UserMaxUpdate
from user_max_service.services.true_1rm_service import calculate_true_1rm
from user_max_service.services.user_max_service import UserMaxService


class TestTrue1rmCalculation(unittest.TestCase):
    """Test calculation of true 1RM via Epley formula and recorded values."""

    def test_explicit_true_1rm_returned(self):
        record = UserMax(max_weight=100, rep_max=5, true_1rm=120.0)
        self.assertEqual(calculate_true_1rm(record), 120.0)

    def test_explicit_true_1rm_from_dict(self):
        data = {"max_weight": 100, "rep_max": 5, "true_1rm": 118.5}
        self.assertEqual(calculate_true_1rm(data), 118.5)

    def test_epley_formula_calculation(self):
        # 100 * (1 + 10 / 30) = 133.333...
        record = UserMax(max_weight=100, rep_max=10, true_1rm=None)
        expected = 100.0 * (1.0 + 10.0 / 30.0)
        self.assertAlmostEqual(calculate_true_1rm(record), expected, places=4)

    def test_epley_formula_reps_zero_or_none(self):
        record = UserMax(max_weight=100, rep_max=0, true_1rm=None)
        self.assertEqual(calculate_true_1rm(record), 100.0)

        record_none = UserMax(max_weight=80, rep_max=None, true_1rm=None)
        self.assertEqual(calculate_true_1rm(record_none), 80.0)

    def test_none_or_empty_input(self):
        self.assertEqual(calculate_true_1rm(None), 0.0)
        self.assertEqual(calculate_true_1rm({}), 0.0)


class BaseDatabaseTestCase(unittest.TestCase):
    """Base test class providing an isolated in-memory SQLite database."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)


class TestUserMaxRepository(BaseDatabaseTestCase):
    """Test repository operations."""

    def setUp(self):
        super().setUp()
        self.repo = UserMaxRepository(self.db)
        self.user_id = "test-user-1"

    def test_create_and_get_by_id(self):
        data = {
            "user_id": self.user_id,
            "exercise_id": 15,
            "exercise_name": "Bench Press",
            "max_weight": 100,
            "rep_max": 5,
            "date": date(2026, 1, 1),
            "true_1rm": 116.67,
            "verified_1rm": 115.0,
            "source": "manual",
        }
        created = self.repo.create_user_max(data)
        self.db.commit()

        self.assertIsNotNone(created.id)
        fetched = self.repo.get_user_max_by_id(created.id, self.user_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.exercise_name, "Bench Press")
        self.assertEqual(fetched.max_weight, 100)

    def test_get_user_maxes_by_exercises_and_ids(self):
        today = date.today()
        um1 = self.repo.create_user_max({
            "user_id": self.user_id,
            "exercise_id": 15,
            "max_weight": 100,
            "rep_max": 5,
            "date": today,
        })
        um2 = self.repo.create_user_max({
            "user_id": self.user_id,
            "exercise_id": 35,
            "max_weight": 140,
            "rep_max": 3,
            "date": today,
        })
        self.db.commit()

        by_ex = self.repo.get_user_maxes_by_exercises(self.user_id, [15, 35])
        self.assertEqual(len(by_ex), 2)

        by_ids = self.repo.get_user_maxes_by_ids(self.user_id, [um1.id, um2.id])
        self.assertEqual(len(by_ids), 2)
        self.assertEqual([x.id for x in by_ids], [um1.id, um2.id])

    def test_bulk_create_and_find_bulk(self):
        today = date.today()
        entries = [
            {"user_id": self.user_id, "exercise_id": 15, "max_weight": 100, "rep_max": 5, "date": today},
            {"user_id": self.user_id, "exercise_id": 16, "max_weight": 40, "rep_max": 8, "date": today},
        ]
        results = self.repo.bulk_create_user_maxes(entries)
        self.db.commit()
        self.assertEqual(len(results), 2)

        found = self.repo.find_existing_user_max_bulk(self.user_id, [(15, today), (16, today)])
        self.assertEqual(len(found), 2)
        self.assertIn((15, 5, today), found)

    def test_daily_agg_and_purge(self):
        today = date.today()
        self.repo.create_or_update_daily_agg(self.user_id, 15, today, sum_true_1rm=230.0, cnt=2)
        self.db.commit()

        agg = self.repo.get_daily_agg_record(self.user_id, 15, today)
        self.assertIsNotNone(agg)
        self.assertEqual(agg.sum_true_1rm, 230.0)
        self.assertEqual(agg.cnt, 2)

        self.repo.purge_user_data(self.user_id)
        self.db.commit()

        self.assertIsNone(self.repo.get_daily_agg_record(self.user_id, 15, today))
        self.assertEqual(len(self.repo.get_daily_agg_for_user(self.user_id)), 0)


class TestUserMaxServiceBusinessLogic(BaseDatabaseTestCase):
    """Test service layer methods and bug fixes."""

    def setUp(self):
        super().setUp()
        self.service = UserMaxService(self.db)
        self.user_id = "test-user-service"

    @patch("user_max_service.services.user_max_service.get_exercise_name_by_id", return_value="Squat")
    def test_create_user_max_fetches_exercise_name_without_error(self, mock_get_name):
        # Verifies the NameError bug fix where get_exercise_name_by_id was not imported
        dto = UserMaxCreate(
            exercise_id=35,
            max_weight=140.0,
            rep_max=5,
            date=date.today(),
        )
        res = self.service.create_user_max(dto, self.user_id)
        self.assertEqual(res.exercise_name, "Squat")
        self.assertEqual(res.max_weight, 140)

    @patch("user_max_service.services.user_max_service.get_all_exercises_meta")
    def test_bulk_create_returns_both_updated_and_created_records(self, mock_get_meta):
        # Verifies bug fix where bulk_create_user_max previously discarded updated records
        mock_get_meta.return_value = [
            {"id": 15, "name": "Bench Press"},
            {"id": 35, "name": "Squat"},
        ]
        today = date.today()

        # Pre-seed one record
        initial = UserMaxCreate(exercise_id=15, max_weight=90.0, rep_max=5, date=today)
        self.service.create_user_max(initial, self.user_id)

        # Bulk input: 1 existing with greater weight, 1 brand new
        bulk_items = [
            UserMaxCreate(exercise_id=15, max_weight=100.0, rep_max=5, date=today),  # update
            UserMaxCreate(exercise_id=35, max_weight=140.0, rep_max=3, date=today),  # create
        ]
        results = self.service.bulk_create_user_max(bulk_items, self.user_id)

        # Both records must be present in the returned list
        self.assertEqual(len(results), 2)
        ex_ids = {r.exercise_id for r in results}
        self.assertEqual(ex_ids, {15, 35})

    def test_update_user_max_rejects_date_change(self):
        dto = UserMaxCreate(exercise_id=15, max_weight=90.0, rep_max=5, date=date.today())
        with patch.object(self.service, "_get_exercise_name_cached", return_value="Bench Press"):
            created = self.service.create_user_max(dto, self.user_id)

        update_dto = UserMaxUpdate(max_weight=95.0, date=date(2025, 1, 1))

        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            self.service.update_user_max(created, update_dto)


class TestUserMaxApi(BaseDatabaseTestCase):
    """Test HTTP API endpoints using FastAPI TestClient."""

    def setUp(self):
        super().setUp()
        self.client = TestClient(app)
        self.user_id = "api-test-user-123"
        self.headers = {"X-User-Id": self.user_id}

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self):
        app.dependency_overrides.clear()
        super().tearDown()

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_internal_purge_endpoint(self):
        with patch.object(settings, "INTERNAL_GATEWAY_SECRET", "secret-xyz"):
            # Forbidden without valid secret
            resp = self.client.post(
                f"/internal/users/{self.user_id}/purge",
                headers={"X-Internal-Secret": "wrong"},
            )
            self.assertEqual(resp.status_code, 403)

            # Success with correct secret
            resp = self.client.post(
                f"/internal/users/{self.user_id}/purge",
                headers={"X-Internal-Secret": "secret-xyz"},
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "ok"})

    @patch("user_max_service.services.user_max_service.get_exercise_name_by_id", return_value="Deadlift")
    def test_crud_lifecycle(self, mock_get_name):
        today_str = date.today().isoformat()
        create_payload = {
            "exercise_id": 29,
            "max_weight": 180.0,
            "rep_max": 5,
            "date": today_str,
            "true_1rm": 210.0,
            "source": "manual",
        }
        resp = self.client.post("/user-max/", json=create_payload, headers=self.headers)
        self.assertEqual(resp.status_code, 201)
        created = resp.json()
        self.assertIn("id", created)
        record_id = created["id"]
        self.assertEqual(created["exercise_name"], "Deadlift")
        self.assertEqual(created["max_weight"], 180.0)

        # GET /user-max/{id} (critical contract for rpe-service)
        resp = self.client.get(f"/user-max/{record_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        fetched = resp.json()
        self.assertEqual(fetched["id"], record_id)
        self.assertEqual(fetched["max_weight"], 180.0)
        self.assertEqual(fetched["true_1rm"], 210.0)

        # GET /user-max/ list
        resp = self.client.get("/user-max/", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

        # GET /user-max/by_exercise/{exercise_id} (contract for plans-service)
        resp = self.client.get("/user-max/by_exercise/29", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

        # GET /user-max/by-exercises?exercise_ids=29 (contract for workouts-service)
        resp = self.client.get("/user-max/by-exercises?exercise_ids=29", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

        # GET /user-max/by-ids?ids={record_id}
        resp = self.client.get(f"/user-max/by-ids?ids={record_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

        # PUT /user-max/{id} update
        update_payload = {"max_weight": 185.0}
        resp = self.client.put(f"/user-max/{record_id}", json=update_payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["max_weight"], 185.0)

        # GET /user-max/{id}/calculate-true-1rm
        resp = self.client.get(f"/user-max/{record_id}/calculate-true-1rm", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), float)

        # PUT /user-max/{id}/verify
        resp = self.client.put(f"/user-max/{record_id}/verify?verified_1rm=215.0", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["verified_1rm"], 215.0)

        # DELETE /user-max/{id}
        resp = self.client.delete(f"/user-max/{record_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 204)

        # Verify 404 after delete
        resp = self.client.get(f"/user-max/{record_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    @patch("user_max_service.services.user_max_service.get_all_exercises_meta")
    def test_bulk_create_endpoint(self, mock_meta):
        mock_meta.return_value = [{"id": 19, "name": "Overhead Press"}]
        today_str = date.today().isoformat()
        payload = [
            {"exercise_id": 19, "max_weight": 70.0, "rep_max": 5, "date": today_str},
        ]
        resp = self.client.post("/user-max/bulk", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["exercise_name"], "Overhead Press")
        self.assertEqual(items[0]["max_weight"], 70.0)


class TestExerciseServiceAndAnalysis(unittest.TestCase):
    """Test exercise service integration helpers and analysis fallback logic."""

    @patch("user_max_service.services.exercise_service.get_exercise_name_by_id_async")
    def test_get_exercise_name_by_id_sync_call(self, mock_async):
        from user_max_service.services.exercise_service import get_exercise_name_by_id

        mock_async.return_value = "Squat"
        name = get_exercise_name_by_id(1)
        self.assertEqual(name, "Squat")

    def test_algorithmic_llm_helper_fallbacks(self):
        from user_max_service.services.analysis_service import AlgorithmicLLMHelper, _utc_today

        self.assertEqual(_utc_today(), date.today())

        helper = AlgorithmicLLMHelper()
        helper.client = None

        res_high = helper.classify_muscle_priority({"z": -1.5, "muscle": "Chest"})
        self.assertEqual(res_high["priority"], "high")

        res_low = helper.classify_muscle_priority({"z": 0.8, "muscle": "Biceps"})
        self.assertEqual(res_low["priority"], "low")

        res_med = helper.classify_muscle_priority({"z": 0.0, "muscle": "Triceps"})
        self.assertEqual(res_med["priority"], "medium")

    def test_batch_sync_exercise_names_coercion(self):
        dummy_db = MagicMock()
        service = UserMaxService(dummy_db)

        service._all_exercises_cache = [
            {"id": "10", "name": "Bench Press"},
            {"id": 20, "name": "Lat Pulldown"},
        ]
        service._all_exercises_cache_timestamp = float("inf")

        names = service._get_exercise_names_batch_sync([10, 20, 999])
        self.assertEqual(names[10], "Bench Press")
        self.assertEqual(names[20], "Lat Pulldown")
        self.assertEqual(names[999], "Unknown")

    def test_invalid_exercise_ids_validation(self):
        from fastapi import HTTPException

        dummy_db = MagicMock()
        service = UserMaxService(dummy_db)

        with self.assertRaises(HTTPException) as ctx:
            service.get_user_maxes_by_exercises("test-user", ["not-an-int"])  # type: ignore[list-item]
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid exercise IDs", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
