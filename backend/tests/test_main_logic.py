import asyncio
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app import main


class FakeQuery:
    def __init__(self, result=None, results=None):
        self.result = result
        self.results = results if results is not None else []

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.results


class FakeDB:
    def __init__(self, result=None, results=None):
        self.result = result
        self.results = results if results is not None else []
        self.added = []
        self.commits = 0

    def query(self, *_args, **_kwargs):
        return FakeQuery(self.result, self.results)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1


class MainLogicTests(unittest.TestCase):
    def test_get_current_user_accepts_valid_token(self):
        user = SimpleNamespace(username="a@example.com")
        token_value = main.jwt.encode({"sub": "a@example.com"}, main.SECRET_KEY, algorithm=main.ALGORITHM)

        result = main.get_current_user(SimpleNamespace(credentials=token_value), FakeDB(result=user))

        self.assertIs(result, user)

    def test_get_current_user_rejects_invalid_or_missing_user(self):
        with self.assertRaises(HTTPException) as ctx:
            main.get_current_user(SimpleNamespace(credentials="bad"), FakeDB())
        self.assertEqual(ctx.exception.status_code, 401)

        token_value = main.jwt.encode({"sub": "a@example.com"}, main.SECRET_KEY, algorithm=main.ALGORITHM)
        with self.assertRaises(HTTPException) as ctx:
            main.get_current_user(SimpleNamespace(credentials=token_value), FakeDB(result=None))
        self.assertEqual(ctx.exception.detail, "User not found")

    def test_create_payment_intent_and_status_delegate_to_stripe(self):
        intent = SimpleNamespace(client_secret="secret", id="pi_123")
        with patch.object(main.stripe.PaymentIntent, "create", return_value=intent) as mocked_create:
            result = asyncio.run(main.create_payment_intent(main.PaymentIntentRequest(amount=1000)))

        mocked_create.assert_called_once_with(amount=1000, currency="eur", payment_method_types=["card"])
        self.assertEqual(result, {"clientSecret": "secret", "paymentIntentId": "pi_123"})

        status = SimpleNamespace(status="succeeded", amount=1000, currency="eur")
        with patch.object(main.stripe.PaymentIntent, "retrieve", return_value=status):
            self.assertEqual(
                asyncio.run(main.get_payment_status("pi_123")),
                {"status": "succeeded", "amount": 1000, "currency": "eur"},
            )

    def test_stripe_errors_are_http_400(self):
        with patch.object(main.stripe.PaymentIntent, "create", side_effect=RuntimeError("stripe down")):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(main.create_payment_intent(main.PaymentIntentRequest(amount=1000)))

        self.assertEqual(ctx.exception.status_code, 400)

    def test_record_purchase_creates_new_active_plan_and_disables_existing(self):
        current_user = SimpleNamespace(id=5)
        existing_plan = SimpleNamespace(is_active=True)
        db = FakeDB(result=None, results=[existing_plan])
        request = main.PurchaseRequest(plan_id="lithuania_day", transaction_id="tx")

        result = asyncio.run(main.record_purchase(request, db=db, current_user=current_user))

        self.assertEqual(result, {"success": True})
        self.assertFalse(existing_plan.is_active)
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].user_id, 5)
        self.assertEqual(db.added[0].transaction_id, "tx")
        self.assertEqual(db.commits, 1)

    def test_record_purchase_reactivates_existing_plan(self):
        current_user = SimpleNamespace(id=5)
        existing_plan = SimpleNamespace(is_active=False, transaction_id=None, purchased_at=None, expires_at=None)
        db = FakeDB(result=existing_plan, results=[])
        request = main.PurchaseRequest(plan_id="unknown", transaction_id="tx")

        result = asyncio.run(main.record_purchase(request, db=db, current_user=current_user))

        self.assertEqual(result, {"success": True})
        self.assertTrue(existing_plan.is_active)
        self.assertEqual(existing_plan.transaction_id, "tx")
        self.assertIsNone(existing_plan.expires_at)
        self.assertEqual(db.commits, 1)

    def test_get_user_plans_expires_old_plans_and_returns_active_ids(self):
        expired = SimpleNamespace(plan_id="old", expires_at=datetime.now() - timedelta(days=1), is_active=True)
        active = SimpleNamespace(plan_id="active", expires_at=datetime.now() + timedelta(days=1), is_active=True)
        db = FakeDB(results=[expired, active])

        result = asyncio.run(main.get_user_plans(db=db, current_user=SimpleNamespace(id=1)))

        self.assertEqual(result, {"purchased_plans": ["active"]})
        self.assertFalse(expired.is_active)
        self.assertEqual(db.commits, 1)

    def test_has_active_plan_returns_false_when_only_expired(self):
        expired = SimpleNamespace(expires_at=datetime.now() - timedelta(days=1), is_active=True)
        db = FakeDB(results=[expired])

        result = asyncio.run(main.has_active_plan(db=db, current_user=SimpleNamespace(id=1)))

        self.assertEqual(result, {"has_active_plan": False})
        self.assertFalse(expired.is_active)


if __name__ == "__main__":
    unittest.main()
