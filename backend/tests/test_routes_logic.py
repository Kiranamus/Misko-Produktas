import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api import routes


class RoutesLogicTests(unittest.TestCase):
    def test_get_current_user_uses_token_credentials(self):
        token = SimpleNamespace(credentials="jwt")
        db = object()

        with patch.object(routes, "get_current_user_from_token", return_value="user") as mocked_get:
            self.assertEqual(routes.get_current_user(token, db), "user")

        mocked_get.assert_called_once_with(db, "jwt")

    def test_auth_endpoints_delegate_to_services(self):
        with patch.object(routes, "register_user", return_value={"ok": True}) as mocked_register:
            self.assertEqual(asyncio.run(routes.register("request", "db")), {"ok": True})
        mocked_register.assert_called_once_with("db", "request")

        with patch.object(routes, "login_user", return_value={"token": "x"}) as mocked_login:
            self.assertEqual(asyncio.run(routes.login("request", "db")), {"token": "x"})
        mocked_login.assert_called_once_with("db", "request")

        with patch.object(routes, "create_password_reset_token", return_value="sent") as mocked_forgot:
            self.assertEqual(asyncio.run(routes.forgot_password("request", "db")), "sent")
        mocked_forgot.assert_called_once_with("db", "request")

        with patch.object(routes, "reset_user_password", return_value={"message": "ok"}) as mocked_reset:
            self.assertEqual(asyncio.run(routes.reset_password("request", "db")), {"message": "ok"})
        mocked_reset.assert_called_once_with("db", "request")

    def test_simple_public_endpoints(self):
        user = SimpleNamespace(full_name="Matas")

        self.assertEqual(
            asyncio.run(routes.protected_route(user)),
            {"message": "Hello Matas, you are authenticated!"},
        )
        self.assertEqual(asyncio.run(routes.health_check()), {"status": "healthy", "database": "postgresql"})

    def test_status_and_metadata_wrap_service_errors(self):
        with patch.object(routes, "read_status", return_value={"status": "done"}):
            self.assertEqual(asyncio.run(routes.status("coarse")), {"status": "done"})

        with patch.object(routes, "get_analysis_metadata", side_effect=RuntimeError("bad")):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(routes.metadata("coarse"))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "bad")

    def test_analyze_fills_defaults_and_calls_process_analysis(self):
        with patch.object(routes, "process_analysis", return_value={"ok": True}) as mocked_process:
            result = asyncio.run(routes.analyze(layer="detail"))

        self.assertEqual(result, {"ok": True})
        self.assertEqual(mocked_process.call_args.kwargs["grid_size"], routes.DEFAULT_DETAIL_GRID_SIZE_M)
        self.assertEqual(mocked_process.call_args.kwargs["tile_size"], routes.DEFAULT_DETAIL_TILE_SIZE_M)

    def test_grid_stats_distribution_and_counties_delegate(self):
        with patch.object(routes, "query_grid", return_value={"features": []}) as mocked_grid:
            self.assertEqual(asyncio.run(routes.grid(layer="coarse", bbox="1,2,3,4")), {"features": []})
        self.assertEqual(mocked_grid.call_args.kwargs["bbox"], "1,2,3,4")

        with patch.object(routes, "query_stats", return_value={"count": 1}) as mocked_stats:
            self.assertEqual(asyncio.run(routes.stats(classes="green, red")), {"count": 1})
        self.assertEqual(mocked_stats.call_args.kwargs["classes"], ["GREEN", "RED"])

        with patch.object(routes, "query_distribution", return_value={"count": 2}):
            self.assertEqual(asyncio.run(routes.distribution("detail")), {"count": 2})

        with patch.object(routes, "get_counties", return_value=["A"]):
            self.assertEqual(asyncio.run(routes.counties()), {"items": ["A"]})

    def test_grid_wraps_service_error(self):
        with patch.object(routes, "query_grid", side_effect=ValueError("bad bbox")):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(routes.grid())

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "bad bbox")


if __name__ == "__main__":
    unittest.main()
