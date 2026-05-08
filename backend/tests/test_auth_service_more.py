import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.schemas_auth import RegisterRequest, ResetPasswordRequest
from app.services import auth_service


class FakeDB:
    def __init__(self, result=None):
        self.result = result
        self.added = []
        self.commits = 0
        self.refreshed = []

    def query(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result

    def add(self, value):
        self.added.append(value)
        value.id = 42

    def commit(self):
        self.commits += 1

    def refresh(self, value):
        self.refreshed.append(value)


class AuthServiceMoreTests(unittest.TestCase):
    def test_build_authenticated_user_payload(self):
        user = SimpleNamespace(id=1, email="a@example.com", full_name="A")

        self.assertEqual(
            auth_service.build_authenticated_user_payload(user),
            {"id": 1, "email": "a@example.com", "name": "A"},
        )

    def test_assign_password_reset_token_sets_token_and_future_expiry(self):
        user = SimpleNamespace(reset_token=None, reset_token_expires=None)

        with patch.object(auth_service, "create_random_token", return_value="tok"):
            token = auth_service.assign_password_reset_token(user)

        self.assertEqual(token, "tok")
        self.assertEqual(user.reset_token, "tok")
        self.assertGreater(user.reset_token_expires, datetime.utcnow() + timedelta(hours=23))

    def test_clear_password_reset_state_hashes_and_clears_token(self):
        user = SimpleNamespace(hashed_password="old", reset_token="tok", reset_token_expires=datetime.utcnow())

        with patch.object(auth_service, "get_password_hash", return_value="new-hash") as mocked_hash:
            auth_service.clear_password_reset_state(user, "new-password")

        mocked_hash.assert_called_once_with("new-password")
        self.assertEqual(user.hashed_password, "new-hash")
        self.assertIsNone(user.reset_token)
        self.assertIsNone(user.reset_token_expires)

    def test_decode_username_from_token_rejects_missing_subject(self):
        token = auth_service.jwt.encode({"anything": "else"}, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM)

        with self.assertRaises(HTTPException) as ctx:
            auth_service.decode_username_from_token(token)

        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_from_token_rejects_missing_user(self):
        token = auth_service.jwt.encode({"sub": "a@example.com"}, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM)

        with self.assertRaises(HTTPException) as ctx:
            auth_service.get_current_user_from_token(FakeDB(result=None), token)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "User not found")

    def test_register_user_rejects_duplicate_email(self):
        request = RegisterRequest(name="A", email="a@example.com", password="secret")

        with patch.object(auth_service, "get_user_by_email", return_value=SimpleNamespace()):
            with self.assertRaises(HTTPException) as ctx:
                auth_service.register_user(FakeDB(), request)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_register_user_creates_and_persists_user(self):
        request = RegisterRequest(name="A", email="a@example.com", password="secret")
        db = FakeDB()

        with patch.object(auth_service, "get_user_by_email", return_value=None), patch.object(
            auth_service,
            "get_password_hash",
            return_value="hashed",
        ):
            response = auth_service.register_user(db, request)

        self.assertEqual(response, {"message": "User created successfully", "user_id": 42})
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.added[0].email, "a@example.com")
        self.assertEqual(db.added[0].hashed_password, "hashed")

    def test_login_user_rejects_missing_or_bad_password(self):
        with patch.object(auth_service, "get_user_by_login", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                auth_service.login_user(FakeDB(), SimpleNamespace(username="a", password="b"))

        self.assertEqual(ctx.exception.status_code, 401)

    def test_build_frontend_url_removes_query_fragment_and_trailing_slash(self):
        self.assertEqual(
            auth_service.build_frontend_url(" https://example.com/app/?x=1#frag "),
            "https://example.com/app",
        )

    def test_reset_user_password_rejects_invalid_token(self):
        with self.assertRaises(HTTPException) as ctx:
            auth_service.reset_user_password(FakeDB(result=None), ResetPasswordRequest(token="bad", new_password="x"))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Invalid or expired token")


if __name__ == "__main__":
    unittest.main()
