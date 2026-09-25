import os
import pickle
import stat
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import json
from gql import Client
from graphql import print_ast
from monarchmoney import MonarchMoney
from monarchmoney.monarchmoney import (
    SESSION_FILE,
    LegacySessionFileException,
    LoginFailedException,
)


class TestMonarchMoney(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """
        Set up any necessary data or variables for the tests here.
        This method will be called before each test method is executed.
        """
        with open("temp_session.json", "w") as fh:
            session_data = {
                "cookies": {"test_cookie": "test_value"},
                "token": "test_token",
            }
            json.dump(session_data, fh)
        self.monarch_money = MonarchMoney()
        self.monarch_money.load_session("temp_session.json")

    @patch.object(Client, "execute_async")
    async def test_get_transaction_rules_includes_complete_rule_fields(
        self, mock_execute_async
    ):
        """Transaction rules include every criterion and action used by the web UI."""
        expected = {
            "transactionRules": [
                {
                    "id": "rule-1",
                    "originalStatementCriteria": [
                        {"operator": "contains", "value": "core account"}
                    ],
                    "merchantNameCriteria": [{"operator": "eq", "value": "fees"}],
                    "criteriaOwnerIsJoint": False,
                    "criteriaOwnerUserIds": ["user-1"],
                    "criteriaOwnerUsers": [{"id": "user-1", "displayName": "Owner"}],
                    "criteriaBusinessEntityIds": ["business-1"],
                    "criteriaBusinessEntityIsUnassigned": False,
                    "criteriaBusinessEntities": [
                        {"id": "business-1", "name": "Business"}
                    ],
                    "linkSavingsGoalAction": {"id": "goal-1", "name": "Reserve"},
                    "setLinkToPaydownBudgetAction": True,
                    "actionSetOwnerIsJoint": False,
                    "actionSetOwner": {"id": "user-1", "displayName": "Owner"},
                    "actionSetBusinessEntity": {
                        "id": "business-1",
                        "name": "Business",
                    },
                    "actionSetBusinessEntityIsUnassigned": False,
                    "splitTransactionsAction": {
                        "splitsInfo": [
                            {
                                "savingsGoalId": "goal-1",
                                "ownerUserId": "user-1",
                                "ownerIsJoint": False,
                                "businessEntityId": "business-1",
                                "businessEntityIsUnassigned": False,
                            }
                        ]
                    },
                }
            ]
        }
        mock_execute_async.return_value = expected

        result = await self.monarch_money.get_transaction_rules()

        self.assertEqual(result, expected)
        request = mock_execute_async.call_args.kwargs["request"]
        query = print_ast(request.document)
        required_fields = (
            "originalStatementCriteria",
            "merchantNameCriteria",
            "criteriaOwnerIsJoint",
            "criteriaOwnerUserIds",
            "criteriaOwnerUsers",
            "criteriaBusinessEntityIds",
            "criteriaBusinessEntityIsUnassigned",
            "criteriaBusinessEntities",
            "linkSavingsGoalAction",
            "setLinkToPaydownBudgetAction",
            "actionSetOwnerIsJoint",
            "actionSetOwner",
            "actionSetBusinessEntity",
            "actionSetBusinessEntityIsUnassigned",
            "savingsGoalId",
            "ownerUserId",
            "ownerIsJoint",
            "businessEntityId",
            "businessEntityIsUnassigned",
        )
        for field in required_fields:
            with self.subTest(field=field):
                self.assertIn(field, query)

    @patch.object(Client, "execute_async")
    async def test_get_accounts(self, mock_execute_async):
        """
        Test the get_accounts method.
        """
        mock_execute_async.return_value = TestMonarchMoney.loadTestData(
            filename="get_accounts.json",
        )
        result = await self.monarch_money.get_accounts()
        mock_execute_async.assert_called_once()
        kwargs = mock_execute_async.call_args.kwargs
        self.assertIn("request", kwargs)
        self.assertNotIn("document", kwargs)
        self.assertIsNotNone(result, "Expected result to not be None")
        self.assertEqual(len(result["accounts"]), 7, "Expected 7 accounts")
        self.assertEqual(
            result["accounts"][0]["displayName"],
            "Brokerage",
            "Expected displayName to be Brokerage",
        )
        self.assertEqual(
            result["accounts"][1]["currentBalance"],
            1000.02,
            "Expected currentBalance to be 1000.02",
        )
        self.assertFalse(
            result["accounts"][2]["isAsset"],
            "Expected isAsset to be False",
        )
        self.assertEqual(
            result["accounts"][3]["subtype"]["display"],
            "Roth IRA",
            "Expected subtype display to be 'Roth IRA'",
        )
        self.assertFalse(
            result["accounts"][4]["isManual"],
            "Expected isManual to be False",
        )
        self.assertEqual(
            result["accounts"][5]["institution"]["name"],
            "Rando Employer Investments",
            "Expected institution name to be 'Rando Employer Investments'",
        )
        self.assertEqual(
            result["accounts"][6]["id"],
            "90000000030",
            "Expected id to be '90000000030'",
        )
        self.assertEqual(
            result["accounts"][6]["type"]["name"],
            "loan",
            "Expected type name to be 'loan'",
        )

    @patch.object(Client, "execute_async")
    async def test_get_transactions_summary(self, mock_execute_async):
        """
        Test the get_transactions_summary method.
        """
        mock_execute_async.return_value = TestMonarchMoney.loadTestData(
            filename="get_transactions_summary.json",
        )
        result = await self.monarch_money.get_transactions_summary()
        mock_execute_async.assert_called_once()
        self.assertIsNotNone(result, "Expected result to not be None")
        self.assertEqual(
            result["aggregates"][0]["summary"]["sumIncome"],
            50000,
            "Expected sumIncome to be 50000",
        )

    @patch.object(Client, "execute_async")
    async def test_delete_account(self, mock_execute_async):
        """
        Test the delete_account method.
        """

        mock_execute_async.return_value = {
            "deleteAccount": {
                "deleted": True,
                "errors": None,
                "__typename": "DeleteAccountMutation",
            }
        }

        result = await self.monarch_money.delete_account("170123456789012345")

        mock_execute_async.assert_called_once()

        kwargs = mock_execute_async.call_args.kwargs
        self.assertIn("request", kwargs)
        self.assertNotIn("document", kwargs)
        self.assertEqual(kwargs["operation_name"], "Common_DeleteAccount")
        self.assertEqual(kwargs["variable_values"], {"id": "170123456789012345"})

        self.assertIsNotNone(result, "Expected result to not be None")
        self.assertEqual(result["deleteAccount"]["deleted"], True)
        self.assertEqual(result["deleteAccount"]["errors"], None)

    @patch.object(Client, "execute_async")
    async def test_delete_merchant_same_id_raises(self, mock_execute_async):
        """
        delete_merchant refuses to merge a merchant into itself.
        """

        with self.assertRaises(ValueError):
            await self.monarch_money.delete_merchant(
                "170000000000000001", move_to_merchant_id="170000000000000001"
            )

        mock_execute_async.assert_not_called()

    @patch.object(Client, "execute_async")
    async def test_get_account_type_options(self, mock_execute_async):
        """
        Test the get_account_type_options method.
        """
        # Mock the execute_async method to return a test result
        mock_execute_async.return_value = TestMonarchMoney.loadTestData(
            filename="get_account_type_options.json",
        )

        # Call the get_account_type_options method
        result = await self.monarch_money.get_account_type_options()

        # Assert that the execute_async method was called once
        mock_execute_async.assert_called_once()

        # Assert that the result is not None
        self.assertIsNotNone(result, "Expected result to not be None")

        # Assert that the result matches the expected output
        self.assertEqual(
            len(result["accountTypeOptions"]), 10, "Expected 10 account type options"
        )
        self.assertEqual(
            result["accountTypeOptions"][0]["type"]["name"],
            "depository",
            "Expected first account type option name to be 'depository'",
        )
        self.assertEqual(
            result["accountTypeOptions"][1]["type"]["name"],
            "brokerage",
            "Expected second account type option name to be 'brokerage'",
        )
        self.assertEqual(
            result["accountTypeOptions"][2]["type"]["name"],
            "real_estate",
            "Expected third account type option name to be 'real_estate'",
        )

    @patch.object(Client, "execute_async")
    async def test_get_account_holdings(self, mock_execute_async):
        """
        Test the get_account_holdings method.
        """
        # Mock the execute_async method to return a test result
        mock_execute_async.return_value = TestMonarchMoney.loadTestData(
            filename="get_account_holdings.json",
        )

        # Call the get_account_holdings method
        result = await self.monarch_money.get_account_holdings(account_id=1234)

        # Assert that the execute_async method was called once
        mock_execute_async.assert_called_once()

        # Assert that the result is not None
        self.assertIsNotNone(result, "Expected result to not be None")

        # Assert that the result matches the expected output
        self.assertEqual(
            len(result["portfolio"]["aggregateHoldings"]["edges"]),
            3,
            "Expected 3 holdings",
        )
        self.assertEqual(
            result["portfolio"]["aggregateHoldings"]["edges"][0]["node"]["quantity"],
            101,
            "Expected first holding to be 101 in quantity",
        )
        self.assertEqual(
            result["portfolio"]["aggregateHoldings"]["edges"][1]["node"]["totalValue"],
            10000,
            "Expected second holding to be 10000 in total value",
        )
        self.assertEqual(
            result["portfolio"]["aggregateHoldings"]["edges"][2]["node"]["holdings"][0][
                "name"
            ],
            "U S Dollar",
            "Expected third holding name to be 'U S Dollar'",
        )

    @patch.object(Client, "execute_async")
    async def test_get_all_holdings(self, mock_execute_async):
        """
        Test the get_all_holdings method.
        """
        # First call returns the account list (3 brokerage accounts among 7),
        # then one holdings result per brokerage account
        mock_execute_async.side_effect = [
            TestMonarchMoney.loadTestData(filename="get_accounts.json"),
            TestMonarchMoney.loadTestData(filename="get_account_holdings.json"),
            TestMonarchMoney.loadTestData(filename="get_account_holdings.json"),
            TestMonarchMoney.loadTestData(filename="get_account_holdings.json"),
        ]

        # Call the get_all_holdings method
        result = await self.monarch_money.get_all_holdings()

        # Assert one accounts query plus one holdings query per brokerage account
        self.assertEqual(
            mock_execute_async.call_count,
            4,
            "Expected 4 calls: 1 for accounts, 3 for holdings",
        )

        # Assert that the result is not None
        self.assertIsNotNone(result, "Expected result to not be None")

        # Assert only the brokerage accounts are included
        self.assertEqual(
            len(result["accounts"]),
            3,
            "Expected holdings for 3 brokerage accounts",
        )
        self.assertEqual(
            result["accounts"][0]["id"],
            "900000000",
            "Expected first brokerage account id to be '900000000'",
        )
        self.assertEqual(
            result["accounts"][0]["displayName"],
            "Brokerage",
            "Expected first brokerage account displayName to be 'Brokerage'",
        )
        self.assertEqual(
            len(
                result["accounts"][0]["holdings"]["portfolio"]["aggregateHoldings"][
                    "edges"
                ]
            ),
            3,
            "Expected 3 holdings in the first brokerage account",
        )
        self.assertEqual(
            result["accounts"][1]["holdings"]["portfolio"]["aggregateHoldings"][
                "edges"
            ][1]["node"]["security"]["ticker"],
            "GOOG",
            "Expected second holding ticker to be 'GOOG'",
        )

    @patch.object(Client, "execute_async")
    async def test_get_budgets(self, mock_execute_async):
        """
        Test the get_accounts method.
        """
        mock_execute_async.return_value = TestMonarchMoney.loadTestData(
            filename="get_budgets.json",
        )
        result = await self.monarch_money.get_budgets(
            start_date="2024-12-01", end_date="2025-2-31"
        )
        mock_execute_async.assert_called_once()
        self.assertIsNotNone(result, "Expected result to not be None")
        self.assertEqual(
            len(result["budgetData"]["monthlyAmountsByCategory"]),
            2,
            "Expected 2 categories",
        )
        self.assertEqual(len(result["categoryGroups"]), 2, "Expected 2 category groups")
        self.assertEqual(len(result["goalsV2"]), 1, "Expected 1 goal")

    @patch.object(Client, "execute_async")
    async def test_get_household_members(self, mock_execute_async):
        """
        Test the get_household_members method.
        """
        mock_execute_async.return_value = {
            "myHousehold": {
                "users": [
                    {
                        "id": "user-1",
                        "name": "Alex",
                        "displayName": "Alex",
                        "householdRole": "OWNER",
                    },
                    {
                        "id": "user-2",
                        "name": "Sam",
                        "displayName": "Sam",
                        "householdRole": "MEMBER",
                    },
                ]
            }
        }
        result = await self.monarch_money.get_household_members()
        mock_execute_async.assert_called_once()
        self.assertIsNotNone(result, "Expected result to not be None")
        users = result["myHousehold"]["users"]
        self.assertEqual(len(users), 2, "Expected 2 household members")
        self.assertEqual(users[0]["id"], "user-1")
        self.assertEqual(users[0]["name"], "Alex")
        self.assertEqual(users[0]["displayName"], "Alex")
        self.assertEqual(users[0]["householdRole"], "OWNER")
        self.assertEqual(users[1]["id"], "user-2")
        self.assertEqual(users[1]["householdRole"], "MEMBER")

    @patch.object(Client, "execute_async")
    async def test_get_household_members_empty(self, mock_execute_async):
        """
        Test the get_household_members method with no members.
        """
        mock_execute_async.return_value = {"myHousehold": {"users": []}}
        result = await self.monarch_money.get_household_members()
        mock_execute_async.assert_called_once()
        self.assertEqual(result["myHousehold"]["users"], [])

    async def test_login(self):
        """
        Test the login method with empty values for email and password.
        """
        with self.assertRaises(LoginFailedException):
            await self.monarch_money.login(use_saved_session=False)
        with self.assertRaises(LoginFailedException):
            await self.monarch_money.login(
                email="", password="", use_saved_session=False
            )

    @patch.object(Client, "execute_async")
    async def test_get_transactions_needs_review_filter(self, mock_execute_async):
        """
        Test that needs_review parameter is passed as needsReview in GraphQL filters.
        """
        mock_execute_async.return_value = {
            "allTransactions": {"results": [], "totalCount": 0},
            "transactionRules": [],
        }

        await self.monarch_money.get_transactions(needs_review=True)

        mock_execute_async.assert_called_once()
        kwargs = mock_execute_async.call_args.kwargs
        self.assertIn("variable_values", kwargs)
        self.assertTrue(
            kwargs["variable_values"]["filters"]["needsReview"],
            "Expected needsReview filter to be True",
        )

    @patch.object(Client, "execute_async")
    async def test_update_transaction_owner(self, mock_execute_async):
        """Assign a household member or explicitly restore Shared ownership."""
        for owner_user_id, expected in (("user-1", "user-1"), ("", None)):
            with self.subTest(owner_user_id=owner_user_id):
                mock_execute_async.reset_mock()
                await self.monarch_money.update_transaction(
                    "txn-1", owner_user_id=owner_user_id
                )
                mock_execute_async.assert_called_once()
                self.assertEqual(
                    mock_execute_async.call_args.kwargs["variable_values"]["input"],
                    {
                        "id": "txn-1",
                        "category": None,
                        "name": None,
                        "ownerUserId": expected,
                    },
                )

    @patch.object(Client, "execute_async")
    async def test_update_transaction_preserves_owner(self, mock_execute_async):
        """Omitted or None ownership must not turn a category edit into Shared."""
        for kwargs in ({}, {"owner_user_id": None}):
            with self.subTest(kwargs=kwargs):
                mock_execute_async.reset_mock()
                await self.monarch_money.update_transaction(
                    "txn-1", category_id="cat-1", **kwargs
                )
                mock_execute_async.assert_called_once()
                self.assertEqual(
                    mock_execute_async.call_args.kwargs["variable_values"]["input"],
                    {"id": "txn-1", "category": "cat-1", "name": None},
                )

    @patch("builtins.input", return_value="")
    @patch("getpass.getpass", return_value="")
    async def test_interactive_login(self, _input_mock, _getpass_mock):
        """
        Test the interactive_login method with empty values for email and password.
        """
        with self.assertRaises(LoginFailedException):
            await self.monarch_money.interactive_login(use_saved_session=False)

    @patch("monarchmoney.monarchmoney.ClientSession")
    async def test_multi_factor_authenticate_bad_code_raises_login_failed(
        self, mock_client_session
    ):
        """
        Bad MFA codes should raise LoginFailedException, not RequireMFAException.
        """
        response = AsyncMock()
        response.status = 400
        response.reason = "Bad Request"
        response.json = AsyncMock(return_value={"detail": "Invalid MFA code"})

        post_context = MagicMock()
        post_context.__aenter__.return_value = response

        session = MagicMock()
        session.post.return_value = post_context

        client_context = MagicMock()
        client_context.__aenter__.return_value = session
        mock_client_session.return_value = client_context

        with self.assertRaises(LoginFailedException) as ctx:
            await self.monarch_money.multi_factor_authenticate(
                "bradley@example.com", "password", "123456"
            )

        self.assertEqual(str(ctx.exception), "Invalid MFA code")

    @classmethod
    def loadTestData(cls, filename) -> dict:
        filename = f"{os.path.dirname(os.path.realpath(__file__))}/{filename}"
        with open(filename, "r") as file:
            return json.load(file)

    def tearDown(self):
        """
        Tear down any necessary data or variables for the tests here.
        This method will be called after each test method is executed.
        """
        self.monarch_money.delete_session("temp_session.json")


class TestDuplicateTransactions(unittest.IsolatedAsyncioTestCase):
    async def test_page_limit_preserves_duplicates_and_default_full_scan(self):
        transactions = [
            {
                "id": str(index),
                "date": "2026-09-20",
                "amount": -10,
                "plaidName": "same reference",
                "account": {"id": "123"},
                "createdAt": str(index),
            }
            for index in range(4)
        ]

        async def page(**kwargs):
            offset = kwargs["offset"]
            return {
                "allTransactions": {
                    "results": transactions[offset : offset + kwargs["limit"]],
                    "totalCount": len(transactions),
                }
            }

        for options, expected_calls, expected_count in (
            ({}, 2, 4),
            ({"max_pages": 1}, 1, 2),
            ({"max_pages": 2}, 2, 4),
        ):
            with self.subTest(options=options):
                client = MonarchMoney()
                client.get_transactions = AsyncMock(side_effect=page)
                result = await client.find_duplicate_transactions(
                    page_size=2, **options
                )
                self.assertEqual(client.get_transactions.await_count, expected_calls)
                self.assertEqual(len(result), 1)
                self.assertEqual(len(result[0]["transactions"]), expected_count)
                self.assertEqual(
                    [
                        call.kwargs["offset"]
                        for call in client.get_transactions.await_args_list
                    ],
                    list(range(0, expected_count, 2)),
                )

    async def test_nonpositive_page_limit_is_rejected_before_requests(self):
        client = MonarchMoney()
        client.get_transactions = AsyncMock()
        for max_pages in (0, -1):
            with self.assertRaisesRegex(ValueError, "max_pages must be positive"):
                await client.find_duplicate_transactions(max_pages=max_pages)
        client.get_transactions.assert_not_awaited()


class _CreatesMarkerOnUnpickle:
    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        return (open, (self.path, "w"))


class TestSessionFile(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.dir = temporary.name
        self.session_file = os.path.join(self.dir, "sub", "session.json")

    def test_default_session_file_is_under_home(self):
        expected = os.path.join(os.path.expanduser("~"), ".mm", "mm_session.json")
        self.assertEqual(SESSION_FILE, expected)
        self.assertEqual(MonarchMoney()._session_file, expected)

    def test_save_session_writes_owner_only_json(self):
        MonarchMoney(session_file=self.session_file, token="tok").save_session()
        self.assertEqual(stat.S_IMODE(os.stat(self.session_file).st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE(os.stat(os.path.dirname(self.session_file)).st_mode), 0o700
        )
        with open(self.session_file) as fh:
            self.assertEqual(json.load(fh), {"token": "tok", "auth_mode": "token"})

        restored = MonarchMoney(session_file=self.session_file)
        restored.load_session()
        self.assertEqual(restored.token, "tok")

    def test_save_session_with_relative_path_in_cwd(self):
        cwd = os.getcwd()
        os.chdir(self.dir)
        self.addCleanup(os.chdir, cwd)
        MonarchMoney(session_file="session.json", token="tok").save_session()
        self.assertEqual(stat.S_IMODE(os.stat("session.json").st_mode), 0o600)

    def test_save_session_tightens_existing_file_mode(self):
        os.makedirs(os.path.dirname(self.session_file))
        with open(self.session_file, "w") as fh:
            fh.write("{}")
        os.chmod(self.session_file, 0o644)
        MonarchMoney(session_file=self.session_file, token="tok").save_session()
        self.assertEqual(stat.S_IMODE(os.stat(self.session_file).st_mode), 0o600)

    async def test_legacy_pickle_session_is_never_unpickled(self):
        marker = os.path.join(self.dir, "pwned")
        os.makedirs(os.path.dirname(self.session_file))
        with open(self.session_file, "wb") as fh:
            pickle.dump(_CreatesMarkerOnUnpickle(marker), fh)
        mm = MonarchMoney(session_file=self.session_file)

        with self.assertRaises(LegacySessionFileException):
            mm.load_session()
        self.assertFalse(os.path.exists(marker))

        with patch.object(mm, "_login_user", new_callable=AsyncMock) as login_user:
            await mm.login("user@example.com", "password", save_session=False)
        login_user.assert_awaited_once_with("user@example.com", "password", None)
        self.assertFalse(os.path.exists(marker))

    async def test_empty_session_file_falls_through_to_credential_login(self):
        os.makedirs(os.path.dirname(self.session_file))
        with open(self.session_file, "w") as fh:
            fh.write("{}")
        mm = MonarchMoney(session_file=self.session_file)

        with patch.object(mm, "_login_user", new_callable=AsyncMock) as login_user:
            await mm.login("user@example.com", "password", save_session=False)
        login_user.assert_awaited_once_with("user@example.com", "password", None)

    @patch("monarchmoney.monarchmoney.ClientSession")
    async def test_upload_sends_cookies_only_to_monarch_hosts(
        self, mock_client_session
    ):
        response = MagicMock(status=200)
        response.json = AsyncMock(return_value={})
        session = MagicMock()
        session.post = AsyncMock(return_value=response)
        mock_client_session.return_value.__aenter__.return_value = session

        mm = MonarchMoney()
        mm.set_cookies({"session_id": "s", "csrftoken": "c"})
        cases = {
            "https://api.monarch.com/upload/": True,
            "https://monarch.com.evil.example/upload/": False,
            "https://notmonarch.com/upload/": False,
        }
        for url, sends_cookies in cases.items():
            await mm._upload_form_data(url, MagicMock())
            cookies = mock_client_session.call_args.kwargs["cookies"]
            self.assertEqual(cookies is not None, sends_cookies, url)

    @patch("monarchmoney.monarchmoney.ClientSession")
    async def test_upload_sends_authorization_only_to_monarch_hosts(
        self, mock_client_session
    ):
        response = MagicMock(status=200)
        response.json = AsyncMock(return_value={})
        session = MagicMock()
        session.post = AsyncMock(return_value=response)
        mock_client_session.return_value.__aenter__.return_value = session

        mm = MonarchMoney(token="tok")
        cases = {
            "https://api.monarch.com/upload/": True,
            "https://monarch.com.evil.example/upload/": False,
            "https://notmonarch.com/upload/": False,
        }
        for url, sends_auth in cases.items():
            await mm._upload_form_data(url, MagicMock())
            headers = mock_client_session.call_args.kwargs["headers"]
            self.assertEqual("Authorization" in headers, sends_auth, url)


if __name__ == "__main__":
    unittest.main()
