import os
import tempfile
import unittest

from auth import (
    authenticate_user,
    delete_account,
    load_user_store,
    register_user,
    reset_password,
    save_user_store,
    use_cloud_backend,
    validate_password_strength,
)


class AuthFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store_path = os.path.join(self.temp_dir.name, "users.json")

    def test_register_and_authenticate_user(self):
        store = load_user_store(self.store_path)
        self.assertEqual(store, {})

        created = register_user("demo@example.com", "Secret123!", store_path=self.store_path)
        self.assertTrue(created)

        authenticated = authenticate_user("demo@example.com", "Secret123!", store_path=self.store_path)
        self.assertTrue(authenticated)

        wrong_password = authenticate_user("demo@example.com", "wrong", store_path=self.store_path)
        self.assertFalse(wrong_password)

        duplicate = register_user("demo@example.com", "Another123!", store_path=self.store_path)
        self.assertFalse(duplicate)

    def test_cloud_backend_detection(self):
        original_url = os.environ.get("SUPABASE_URL")
        original_key = os.environ.get("SUPABASE_ANON_KEY")
        self.addCleanup(lambda: os.environ.pop("SUPABASE_URL", None) if original_url is None else os.environ.__setitem__("SUPABASE_URL", original_url))
        self.addCleanup(lambda: os.environ.pop("SUPABASE_ANON_KEY", None) if original_key is None else os.environ.__setitem__("SUPABASE_ANON_KEY", original_key))

        os.environ["SUPABASE_URL"] = "https://example.supabase.co"
        os.environ["SUPABASE_ANON_KEY"] = "test-key"
        self.assertTrue(use_cloud_backend())

        os.environ["SUPABASE_URL"] = "https://your-project.supabase.co"
        os.environ["SUPABASE_ANON_KEY"] = "your-anon-key-here"
        self.assertFalse(use_cloud_backend())

    def test_structured_profile_and_account_deletion(self):
        created = register_user("profile@example.com", "Secret123!", store_path=self.store_path)
        self.assertTrue(created)

        store = load_user_store(self.store_path)
        entry = store.get("profile@example.com", {})
        self.assertIn("profile", entry)
        self.assertIn("investigations", entry)
        self.assertIn("follow_up_chats", entry)

        deleted = delete_account("profile@example.com", "Secret123!", store_path=self.store_path)
        self.assertTrue(deleted)

        store_after = load_user_store(self.store_path)
        self.assertNotIn("profile@example.com", store_after)

    def test_password_strength_and_reset(self):
        created = register_user("reset@example.com", "Secret123!", store_path=self.store_path)
        self.assertTrue(created)

        self.assertFalse(validate_password_strength("weak"))
        self.assertTrue(validate_password_strength("Str0ng!Pass"))

        reset = reset_password("reset@example.com", "NewPass!123", store_path=self.store_path)
        self.assertTrue(reset)
        self.assertTrue(authenticate_user("reset@example.com", "NewPass!123", store_path=self.store_path))


if __name__ == "__main__":
    unittest.main()
