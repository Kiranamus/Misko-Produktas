import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app import auth
from app.schemas_auth import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest
from app.services import auth_service


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeDB:
    def __init__(self, result=None):
        self.result = result
        self.commits = 0

    def query(self, *_args, **_kwargs):
        return FakeQuery(self.result)

    def commit(self):
        self.commits += 1


class AuthModuleTests(unittest.TestCase):
    def test_password_hash_roundtrip(self):
        password = "slaptazodis123"

        hashed = auth.get_password_hash(password)

        self.assertNotEqual(password, hashed)
        self.assertTrue(auth.verify_password(password, hashed))
        self.assertFalse(auth.verify_password("neteisingas", hashed))

    def test_create_access_token_keeps_subject(self):
        token = auth.create_access_token({"sub": "matas@example.com"})

        payload = auth_service.jwt.decode(
            token,
            auth.SECRET_KEY,
            algorithms=[auth.ALGORITHM],
        )

        self.assertEqual(payload["sub"], "matas@example.com")
        self.assertIn("exp", payload)

    def test_create_random_token_returns_non_empty_distinct_values(self):
        token_a = auth.create_random_token()
        token_b = auth.create_random_token()

        self.assertNotEqual(token_a, token_b)
        self.assertGreaterEqual(len(token_a), 20)
        self.assertGreaterEqual(len(token_b), 20)


class AuthServiceTests(unittest.TestCase):
    def test_build_login_response_serializes_user(self):
        user = SimpleNamespace(
            id=7,
            username="matas@example.com",
            email="matas@example.com",
            full_name="Matas",
        )

        with patch.object(auth_service, "create_access_token", return_value="jwt-token") as mocked_token:
            response = auth_service.build_login_response(user)

        mocked_token.assert_called_once_with(data={"sub": "matas@example.com"})
        self.assertEqual(
            response,
            {
                "access_token": "jwt-token",
                "token_type": "bearer",
                "user": {"id": 7, "email": "matas@example.com", "name": "Matas"},
            },
        )

    def test_decode_username_from_token_rejects_invalid_token(self):
        with self.assertRaises(HTTPException) as ctx:
            auth_service.decode_username_from_token("blogas-token")

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Invalid token")

    def test_login_user_returns_bearer_payload(self):
        user = SimpleNamespace(
            id=5,
            username="matas@example.com",
            email="matas@example.com",
            full_name="Matas",
            hashed_password="hashed",
        )
        request = LoginRequest(username="matas@example.com", password="sekretas")

        with patch.object(auth_service, "get_user_by_login", return_value=user) as mocked_get_user, patch.object(
            auth_service, "verify_password", return_value=True
        ) as mocked_verify, patch.object(
            auth_service, "build_login_response", return_value={"access_token": "abc"}
        ) as mocked_build:
            result = auth_service.login_user(FakeDB(), request)

        mocked_get_user.assert_called_once()
        mocked_verify.assert_called_once_with("sekretas", "hashed")
        mocked_build.assert_called_once_with(user)
        self.assertEqual(result, {"access_token": "abc"})

    def test_create_password_reset_token_returns_dummy_for_missing_user(self):
        db = FakeDB()
        request = ForgotPasswordRequest(username="missing@example.com")

        with patch.object(auth_service, "get_user_by_login", return_value=None):
            response = auth_service.create_password_reset_token(db, request)

        self.assertEqual(response.token, "user_not_found_dummy_token")
        self.assertEqual(db.commits, 0)

    def test_create_password_reset_token_updates_user_and_commits(self):
        user = SimpleNamespace(reset_token=None, reset_token_expires=None)
        db = FakeDB()

        with patch.object(auth_service, "get_user_by_login", return_value=user), patch.object(
            auth_service, "assign_password_reset_token", return_value="reset-token"
        ) as mocked_assign:
            response = auth_service.create_password_reset_token(
                db,
                ForgotPasswordRequest(username="matas@example.com"),
            )

        mocked_assign.assert_called_once_with(user)
        self.assertEqual(response.token, "reset-token")
        self.assertEqual(db.commits, 1)

    def test_reset_user_password_clears_reset_state(self):
        user = SimpleNamespace(
            hashed_password="old",
            reset_token="token",
            reset_token_expires="future",
        )
        db = FakeDB(result=user)

        with patch.object(auth_service, "clear_password_reset_state") as mocked_clear:
            response = auth_service.reset_user_password(
                db,
                ResetPasswordRequest(token="token", new_password="naujas"),
            )

        mocked_clear.assert_called_once_with(user, "naujas")
        self.assertEqual(db.commits, 1)
        self.assertEqual(response, {"message": "Password reset successfully"})


if __name__ == "__main__":
    unittest.main()
