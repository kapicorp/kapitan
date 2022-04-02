from unittest import mock

import pyfakefs.fake_filesystem_unittest as fakefs

import kapitan.errors
import kapitan.targets


class TestMergeTreeStyleOutput(fakefs.TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def test_merge_tree_style_output(self):
        self.fs.create_file("/src/file1", contents="file1")
        self.fs.create_dir("/src/dir")
        self.fs.create_file("/src/dir/file2", contents="file2")
        kapitan.targets.merge_tree_style_output("/src", "/dst")
        with open("/dst/file1") as f:
            self.assertEqual("file1", f.read())
        with open("/dst/dir/file2") as f:
            self.assertEqual("file2", f.read())

    def test_merge_tree_style_output_file_exists(self):
        self.fs.create_file("/src/file1")
        self.fs.create_file("/src2/file1")
        kapitan.targets.merge_tree_style_output("/src", "/dst")
        with self.assertRaises(kapitan.errors.CompileError):
            kapitan.targets.merge_tree_style_output("/src2", "/dst")

    def test_merge_targets(self):
        m_listdir = mock.patch("os.listdir").start()
        m_listdir.return_value = ["target1", "target2"]
        m_merge_tree = mock.patch("kapitan.targets.merge_tree_style_output").start()
        kapitan.targets.merge_targets(
            tree_style_output=True,
            updated_targets=[],
            compile_path="/dst",
            temp_compile_path="/src",
        )
        m_merge_tree.assert_has_calls([mock.call("/src/target1", "/dst"), mock.call("/src/target2", "/dst")])

    def test_merge_targets_no_targets(self):
        m_listdir = mock.patch("os.listdir").start()
        m_listdir.return_value = []
        m_merge_tree = mock.patch("kapitan.targets.merge_tree_style_output").start()
        kapitan.targets.merge_targets(
            tree_style_output=True,
            updated_targets=[],
            compile_path="/dst",
            temp_compile_path="/src",
        )
        m_merge_tree.assert_not_called()

    def test_merge_targets_target_specified(self):
        m_merge_tree = mock.patch("kapitan.targets.merge_tree_style_output").start()
        kapitan.targets.merge_targets(
            tree_style_output=True,
            updated_targets=["target3", "target4"],
            compile_path="/dst",
            temp_compile_path="/src",
        )
        m_merge_tree.assert_has_calls([mock.call("/src/target3", "/dst"), mock.call("/src/target4", "/dst")])
