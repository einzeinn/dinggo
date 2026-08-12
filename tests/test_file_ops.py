import os
import tempfile
import unittest
from tools.file_ops import read_file, write_file, list_dir, edit_file, get_unified_diff


class TestFileOps(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_and_read_file(self):
        file_path = os.path.join(self.dir_path, "sample.txt")
        content = "Hello, Dinggo CLI!"
        
        w_res = write_file(file_path, content)
        self.assertTrue(w_res["success"])
        self.assertGreater(w_res["bytes_written"], 0)

        r_res = read_file(file_path)
        self.assertTrue(r_res["success"])
        self.assertEqual(r_res["content"], content)

    def test_list_dir(self):
        os.makedirs(os.path.join(self.dir_path, "subdir"))
        write_file(os.path.join(self.dir_path, "file1.txt"), "abc")

        res = list_dir(self.dir_path)
        self.assertTrue(res["success"])
        names = [item["name"] for item in res["items"]]
        self.assertIn("subdir", names)
        self.assertIn("file1.txt", names)

    def test_edit_file_and_diff(self):
        file_path = os.path.join(self.dir_path, "code.py")
        old_code = "def foo():\n    return 1\n"
        new_code = "def foo():\n    return 2\n"

        write_file(file_path, old_code)

        diff = get_unified_diff(file_path, old_code, new_code)
        self.assertIn("-    return 1", diff)
        self.assertIn("+    return 2", diff)

        edit_res = edit_file(file_path, new_code)
        self.assertTrue(edit_res["success"])
        self.assertIn("+    return 2", edit_res["diff"])

        final_read = read_file(file_path)
        self.assertEqual(final_read["content"], new_code)


if __name__ == "__main__":
    unittest.main()
