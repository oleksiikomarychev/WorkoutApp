"""Unit and integration tests for rpe-service."""

import math
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
from fastapi.testclient import TestClient
from rpe_service.calculation import (
    calculate_rpe_set_values,
    clear_rpe_table_cache,
    get_rpe_table,
    load_rpe_table,
    round_to_step,
    validate_rpe_table,
)
from rpe_service.config import settings
from rpe_service.grpc_server import HealthServicer, RPEServicer, health_pb2, rpe_pb2
from rpe_service.main import app
from rpe_service.rpc import close_http_client, get_effective_max, get_http_client
from rpe_service.rpe_calculations import (
    EffortNotFoundError,
    IntensityNotFoundError,
    VolumeNotFoundError,
    get_effort,
    get_intensity,
    get_volume,
)
from rpe_service.schemas import (
    PlanNotificationRequest,
    PlanNotificationResponse,
    RpeComputeRequest,
)


class TestRpeCalculations(unittest.TestCase):
    """Test mathematical calculation utilities and table lookups."""

    @classmethod
    def setUpClass(cls):
        cls.table = get_rpe_table()

    def test_round_to_step_modes(self):
        # Nearest (default)
        self.assertEqual(round_to_step(71.2, 2.5, "nearest"), 70.0)
        self.assertEqual(round_to_step(71.3, 2.5, "nearest"), 72.5)
        self.assertEqual(round_to_step(100.0, 2.5, "nearest"), 100.0)

        # Floor
        self.assertEqual(round_to_step(72.4, 2.5, "floor"), 70.0)
        self.assertEqual(round_to_step(72.5, 2.5, "floor"), 72.5)

        # Ceil
        self.assertEqual(round_to_step(70.1, 2.5, "ceil"), 72.5)
        self.assertEqual(round_to_step(70.0, 2.5, "ceil"), 70.0)

        # Non-positive step returns value
        self.assertEqual(round_to_step(82.7, 0, "nearest"), 82.7)
        self.assertEqual(round_to_step(82.7, -1, "nearest"), 82.7)

    def test_round_to_step_case_insensitivity(self):
        # Case insensitivity and whitespace stripping
        self.assertEqual(round_to_step(72.4, 2.5, "FLOOR"), 70.0)
        self.assertEqual(round_to_step(70.1, 2.5, " Ceil "), 72.5)
        self.assertEqual(round_to_step(71.3, 2.5, " Nearest "), 72.5)

    def test_round_to_step_non_finite_values(self):
        # Handling of NaN and Inf
        self.assertTrue(math.isnan(round_to_step(float("nan"), 2.5)))
        self.assertTrue(math.isinf(round_to_step(float("inf"), 2.5)))
        self.assertEqual(round_to_step(75.0, float("nan")), 75.0)

    def test_validate_rpe_table(self):
        self.assertTrue(validate_rpe_table(self.table))
        self.assertFalse(validate_rpe_table({}))
        self.assertFalse(validate_rpe_table("not_a_dict"))
        self.assertFalse(validate_rpe_table({20: {10: 5}}))  # intensity too low (<40)
        self.assertFalse(validate_rpe_table({80: {15: 5}}))  # effort too high (>10)
        # Verify boolean keys or values are rejected (isinstance(True, int) is True)
        self.assertFalse(validate_rpe_table({True: {10: 5}}))
        self.assertFalse(validate_rpe_table({80: {True: 5}}))
        self.assertFalse(validate_rpe_table({80: {10: True}}))

    def test_clear_rpe_table_cache(self):
        clear_rpe_table_cache()
        table = get_rpe_table()
        self.assertTrue(validate_rpe_table(table))

    def test_load_rpe_table_fallback(self):
        # When configured path does not exist, falls back to default path gracefully
        with patch.object(settings, "RPE_TABLE_PATH", "/non/existent/path/table.json"):
            with patch.object(settings, "RPE_TABLE_JSON", None):
                table = load_rpe_table()
                self.assertTrue(validate_rpe_table(table))

    def test_get_volume_exact_and_none(self):
        # 100% intensity at effort 10 is 1 rep
        self.assertEqual(get_volume(self.table, intensity=100, effort=10), 1)

        # None input returns None
        self.assertIsNone(get_volume(self.table, intensity=None, effort=10))
        self.assertIsNone(get_volume(self.table, intensity=100, effort=None))

        # Out of bounds raises
        with self.assertRaises(IntensityNotFoundError):
            get_volume(self.table, intensity=150, effort=10)

        with self.assertRaises(EffortNotFoundError):
            get_volume(self.table, intensity=100, effort=4)

    def test_get_intensity_exact_and_none(self):
        self.assertEqual(get_intensity(self.table, volume=1, effort=10), 100)
        self.assertIsNone(get_intensity(self.table, volume=None, effort=10))
        self.assertIsNone(get_intensity(self.table, volume=1, effort=None))

        with self.assertRaises(VolumeNotFoundError):
            get_intensity(self.table, volume=999, effort=10)

    def test_get_effort_exact_and_none(self):
        self.assertEqual(get_effort(self.table, volume=1, intensity=100), 10.0)
        self.assertIsNone(get_effort(self.table, volume=None, intensity=100))
        self.assertIsNone(get_effort(self.table, volume=1, intensity=None))

        with self.assertRaises(IntensityNotFoundError):
            get_effort(self.table, volume=1, intensity=150)

        with self.assertRaises(VolumeNotFoundError):
            get_effort(self.table, volume=999, intensity=100)

    def test_calculate_rpe_set_values_combinations(self):
        # Case 1: intensity=80, effort=8 -> calculates volume
        intensity, effort, volume, weight = calculate_rpe_set_values(
            self.table, intensity=80, effort=8, volume=None, max_weight=100.0
        )
        self.assertEqual(intensity, 80)
        self.assertEqual(effort, 8.0)
        self.assertIsNotNone(volume)
        self.assertEqual(weight, 80.0)

        # Case 2: volume=reps, effort=8 -> calculates intensity
        computed_intensity, _, _, _ = calculate_rpe_set_values(
            self.table, intensity=None, effort=8, volume=volume, max_weight=100.0
        )
        self.assertIn(computed_intensity, (80, 81, 82))

        # Case 3: volume=reps, intensity=80 -> calculates effort
        intensity, effort, volume, weight = calculate_rpe_set_values(
            self.table, intensity=80, effort=None, volume=volume, max_weight=100.0
        )
        self.assertEqual(effort, 8.0)
        self.assertEqual(weight, 80.0)

    def test_float_volume_handling(self):
        # get_intensity with float volume (e.g. 1.0)
        self.assertEqual(get_intensity(self.table, volume=1.0, effort=10), 100)
        # get_effort with float volume
        self.assertEqual(get_effort(self.table, volume=1.0, intensity=100), 10.0)
        # calculate_rpe_set_values with float volume
        _, effort, volume, _ = calculate_rpe_set_values(self.table, intensity=100, volume=1.0, effort=None)
        self.assertEqual(effort, 10.0)
        self.assertEqual(volume, 1)

    def test_calculate_rpe_set_values_nearest_match_fallback(self):
        # Non-standard intensity that needs nearest matching
        intensity, effort, volume, weight = calculate_rpe_set_values(
            self.table, intensity=80.4, effort=8.2, volume=None
        )
        self.assertIsNotNone(intensity)
        self.assertIsNotNone(effort)
        self.assertIsNotNone(volume)

    def test_round_to_step_precision_edge_cases(self):
        # Verify precision with fractional steps
        self.assertEqual(round_to_step(72.5, 2.5, "ceil"), 72.5)
        self.assertEqual(round_to_step(72.5, 2.5, "floor"), 72.5)
        self.assertEqual(round_to_step(72.5, 2.5, "nearest"), 72.5)
        self.assertEqual(round_to_step(72.5000000001, 2.5, "nearest"), 72.5)

    def test_calculate_rpe_set_values_out_of_bounds_effort_fallback(self):
        # Effort out of standard range (e.g. 15), table fallback resolves gracefully
        table = get_rpe_table()
        intensity, effort, volume, _ = calculate_rpe_set_values(table, volume=5, effort=15, intensity=None)
        self.assertIsNotNone(intensity)
        self.assertIsNotNone(volume)

    def test_get_rpe_table_force_reload(self):
        table = get_rpe_table(force_reload=True)
        self.assertTrue(validate_rpe_table(table))

    def test_calculate_rpe_set_values_all_provided(self):
        intensity, effort, volume, weight = calculate_rpe_set_values(
            self.table, intensity=80, effort=8.0, volume=5, max_weight=100.0
        )
        self.assertEqual(intensity, 80)
        self.assertEqual(effort, 8.0)
        self.assertEqual(volume, 5)
        self.assertEqual(weight, 80.0)

    def test_calculate_rpe_set_values_empty_table(self):
        intensity, effort, volume, weight = calculate_rpe_set_values(
            {}, intensity=80, effort=8.0, volume=None, max_weight=100.0
        )
        self.assertIsNone(intensity)
        self.assertIsNone(effort)
        self.assertIsNone(volume)
        self.assertIsNone(weight)


class TestRpeSchemas(unittest.TestCase):
    """Test schema validation and coercion."""

    def test_volume_float_coercion(self):
        # Plans service RPC can send volume as float
        req = RpeComputeRequest(volume=5.0, effort=8.0)
        self.assertEqual(req.volume, 5)

    def test_rounding_mode_none_and_empty_fallback(self):
        req = RpeComputeRequest(rounding_mode="")
        self.assertEqual(req.rounding_mode, "nearest")
        req2 = RpeComputeRequest(rounding_mode=None)
        self.assertEqual(req2.rounding_mode, "nearest")

    def test_empty_string_and_whitespace_coercion(self):
        req = RpeComputeRequest(intensity="  ", effort=" ", max_weight="")
        self.assertIsNone(req.intensity)
        self.assertIsNone(req.effort)
        self.assertIsNone(req.max_weight)

    def test_plan_notification_schema(self):
        req = PlanNotificationRequest(plan={"id": "plan-1", "name": "Hypertrophy"})
        self.assertEqual(req.plan["id"], "plan-1")
        resp = PlanNotificationResponse()
        self.assertEqual(resp.status, "ok")


class TestRpeRpc(unittest.IsolatedAsyncioTestCase):
    """Test RPC calls to user-max-service."""

    @patch("httpx.AsyncClient.get")
    async def test_get_effective_max_precedence(self, mock_get):
        # verified_1rm > true_1rm > max_weight
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "verified_1rm": 120.0,
            "true_1rm": 115.0,
            "max_weight": 110.0,
        }
        mock_get.return_value = mock_response

        val = await get_effective_max(1, user_id="user-1")
        self.assertEqual(val, 120.0)

    @patch("httpx.AsyncClient.get")
    async def test_get_effective_max_skips_non_positive_values(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "verified_1rm": 0.0,
            "true_1rm": -5.0,
            "max_weight": 105.0,
        }
        mock_get.return_value = mock_response

        val = await get_effective_max(1, user_id="user-1")
        self.assertEqual(val, 105.0)

    @patch("httpx.AsyncClient.get")
    async def test_get_effective_max_true_1rm_fallback(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "verified_1rm": None,
            "true_1rm": 115.0,
            "max_weight": 110.0,
        }
        mock_get.return_value = mock_response

        val = await get_effective_max(1, user_id="user-1")
        self.assertEqual(val, 115.0)

    @patch("httpx.AsyncClient.get")
    async def test_get_effective_max_missing_raises(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"other_field": 123}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            await get_effective_max(1, user_id="user-1")

    @patch("httpx.AsyncClient.get")
    async def test_get_effective_max_non_dict_raises(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["not", "a", "dict"]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            await get_effective_max(1, user_id="user-1")

    async def test_get_effective_max_with_custom_client(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"verified_1rm": 140.0}
        mock_client.get.return_value = mock_response

        val = await get_effective_max(10, user_id="user-xyz", client=mock_client)
        self.assertEqual(val, 140.0)

    async def test_get_and_close_http_client(self):
        client = get_http_client()
        self.assertIsNotNone(client)
        self.assertFalse(client.is_closed)
        await close_http_client()
        self.assertTrue(client.is_closed)


class TestRpeApi(unittest.TestCase):
    """Test HTTP API routes using FastAPI TestClient."""

    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-User-Id": "test-user-123"}

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_get_table_auth(self):
        # Missing auth header
        resp = self.client.get("/rpe/table")
        self.assertEqual(resp.status_code, 401)

        # With auth header
        resp = self.client.get("/rpe/table", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("100", data)

    def test_compute_rpe_basic(self):
        payload = {"intensity": 80, "effort": 8, "max_weight": 100.0}
        resp = self.client.post("/rpe/compute", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intensity"], 80)
        self.assertEqual(data["effort"], 8.0)
        self.assertIsNotNone(data["volume"])
        self.assertEqual(data["weight"], 80.0)

    def test_compute_rpe_without_auth_header(self):
        # Pure mathematical calculation works without X-User-Id
        payload = {"intensity": 80, "effort": 8, "max_weight": 100.0}
        resp = self.client.post("/rpe/compute", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intensity"], 80)
        self.assertEqual(data["weight"], 80.0)

    def test_compute_rpe_case_insensitive_rounding(self):
        payload = {
            "intensity": 80,
            "effort": 8,
            "max_weight": 98.0,
            "rounding_step": 2.5,
            "rounding_mode": "Floor",
        }
        resp = self.client.post("/rpe/compute", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # 98.0 * 0.8 = 78.4 -> floor to 2.5 is 77.5
        self.assertEqual(data["weight"], 77.5)

    def test_compute_rpe_float_types(self):
        payload = {
            "intensity": 75,
            "effort": 8.0,
            "max_weight": 95.0,
            "rounding_step": 2.5,
            "rounding_mode": "nearest",
        }
        resp = self.client.post("/rpe/compute", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data["weight"], float)

    @patch("rpe_service.main.get_effective_max", new_callable=AsyncMock)
    def test_compute_rpe_with_user_max_id(self, mock_get_max):
        mock_get_max.return_value = 100.0
        payload = {
            "intensity": 80,
            "effort": 8,
            "user_max_id": 999,
        }
        resp = self.client.post("/rpe/compute", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        mock_get_max.assert_called_once_with(999, user_id="test-user-123")
        self.assertEqual(data["weight"], 80.0)

    def test_internal_purge_endpoint(self):
        with patch.object(settings, "INTERNAL_GATEWAY_SECRET", "secret-123"):
            resp = self.client.post(
                "/internal/users/user-abc/purge",
                headers={"X-Internal-Secret": "wrong-secret"},
            )
            self.assertEqual(resp.status_code, 403)

            resp = self.client.post(
                "/internal/users/user-abc/purge",
                headers={"X-Internal-Secret": "secret-123"},
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "ok", "deleted": 0})

    def test_compute_rpe_failure_response(self):
        with patch("rpe_service.main.calculate_rpe_set_values", side_effect=ValueError("Invalid compute params")):
            payload = {"intensity": 80, "effort": 8}
            resp = self.client.post("/rpe/compute", json=payload, headers=self.headers)
            self.assertEqual(resp.status_code, 400)
            data = resp.json()
            self.assertEqual(data["error"], "COMPUTE_ERROR")
            self.assertIn("RPE calculation failed", data["message"])

    def test_plan_notification_endpoint(self):
        payload = {"plan": {"name": "Test Plan", "weeks": 4}}
        resp = self.client.post("/rpe/plans", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("notification received", data["message"])

    def test_plan_notification_without_auth(self):
        payload = {"plan": {"name": "Test Plan Unauthenticated"}}
        resp = self.client.post("/rpe/plans", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")


class TestRpeGrpc(unittest.IsolatedAsyncioTestCase):
    """Test gRPC servicer endpoints."""

    async def test_grpc_compute_success(self):
        servicer = RPEServicer()
        request = rpe_pb2.RPEComputeRequest(
            intensity=80.0,
            effort=8.0,
            max_weight=100.0,
            rounding_step=2.5,
            rounding_mode="nearest",
        )
        context = MagicMock()
        response = await servicer.Compute(request, context)
        self.assertEqual(response.computed_weight, 80.0)
        self.assertEqual(response.suggested_weight, 80.0)
        self.assertIn("successfully", response.message)

    async def test_grpc_compute_without_weight(self):
        servicer = RPEServicer()
        request = rpe_pb2.RPEComputeRequest(
            intensity=80.0,
            effort=8.0,
        )
        context = MagicMock()
        response = await servicer.Compute(request, context)
        self.assertFalse(response.HasField("computed_weight"))
        self.assertIn("successfully", response.message)

    @patch("rpe_service.grpc_server.get_effective_max", new_callable=AsyncMock)
    async def test_grpc_compute_with_user_max_id(self, mock_get_max):
        mock_get_max.return_value = 100.0
        servicer = RPEServicer()
        request = rpe_pb2.RPEComputeRequest(
            intensity=80.0,
            effort=8.0,
            user_max_id=123,
        )
        context = MagicMock()
        response = await servicer.Compute(request, context)
        self.assertEqual(response.computed_weight, 80.0)
        mock_get_max.assert_called_once_with(123, user_id=None)

    async def test_grpc_compute_invalid_argument(self):
        servicer = RPEServicer()
        with patch("rpe_service.grpc_server.calculate_rpe_set_values", side_effect=ValueError("Test compute error")):
            request = rpe_pb2.RPEComputeRequest(intensity=50.0)
            context = MagicMock()
            response = await servicer.Compute(request, context)
            context.set_code.assert_called_with(grpc.StatusCode.INVALID_ARGUMENT)
            self.assertIsNone(response.computed_weight if response.HasField("computed_weight") else None)

    async def test_grpc_health_servicer(self):
        servicer = HealthServicer()
        context = MagicMock()
        resp = await servicer.Check(None, context)
        self.assertEqual(resp.status, health_pb2.HealthCheckResponse.SERVING)

    async def test_grpc_health_watch(self):
        servicer = HealthServicer()
        context = MagicMock()
        context.cancelled.side_effect = [False, True]
        results = []
        async for item in servicer.Watch(None, context):
            results.append(item.status)
            break
        self.assertEqual(results, [health_pb2.HealthCheckResponse.SERVING])


if __name__ == "__main__":
    unittest.main()
