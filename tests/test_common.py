import unittest

from tests.common import make_temp_project_root


class TestCommonTest(unittest.TestCase):
    def test_make_temp_project_root_returns_existing_directory(self):
        temp_ctx, root = make_temp_project_root()
        try:
            self.assertTrue(root.exists())
            self.assertTrue(root.is_dir())
        finally:
            temp_ctx.cleanup()


if __name__ == "__main__":
    unittest.main()
