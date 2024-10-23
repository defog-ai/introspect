import json
import unittest
from utils_logging import truncate_list, truncate_dict, truncate_obj


class TestUtilsLogging(unittest.TestCase):

    # override the default maxDiff attribute for easy debugging
    def __init__(self, *args, **kwargs):
        super(TestUtilsLogging, self).__init__(*args, **kwargs)
        self.maxDiff = None

    def test_truncate_list_short(self):
        data = [1, 2, 3]
        result_str = truncate_list(data, max_len_list=5, max_len_str=5, to_str=True)
        self.assertEqual(result_str, json.dumps(data, indent=2))
        result_dict = truncate_list(data, max_len_list=5, max_len_str=5, to_str=False)
        self.assertEqual(result_dict, data)

    def test_truncate_list_long(self):
        data = list(range(10))
        result_str = truncate_list(data, max_len_list=5, max_len_str=5, to_str=True)
        self.assertEqual(result_str, "[0, 1, 2, 3, 4...(10 total elements)]")
        result_dict = truncate_list(data, max_len_list=5, max_len_str=5, to_str=False)
        self.assertEqual(result_dict, data[:5])

    def test_truncate_list_obj(self):
        data = [
            {"key1": [1, 2, 3], "key2": "value"},
            {"key1": list(range(10)), "key2": "valuevalue"},
        ]
        result_dict = truncate_list(data, max_len_list=5, max_len_str=4, to_str=False)
        expected_dict = [
            {"key1": [1, 2, 3], "key2": "valu...[5 chars]"},
            {"key1": list(range(5)), "key2": "valu...[10 chars]"},
        ]
        self.assertEqual(result_dict, expected_dict)
        result_str = truncate_list(data, max_len_list=5, max_len_str=4, to_str=True)
        expected_json_str = json.dumps(expected_dict, indent=2)
        self.assertEqual(result_str, expected_json_str)

    def test_truncate_dict_short(self):
        data = {"key1": [1, 2, 3], "key2": "value"}
        result_str = truncate_dict(data, max_len_list=5, max_len_str=5, to_str=True)
        expected_json_str = json.dumps(data, indent=2)
        self.assertEqual(result_str, expected_json_str)
        result_dict = truncate_dict(data, max_len_list=5, max_len_str=5, to_str=False)
        self.assertEqual(result_dict, data)

    def test_truncate_dict_long(self):
        data = {"key1": list(range(10)), "key2": "valuevalue"}
        truncated_dict = {"key1": list(range(5)), "key2": "valu...[10 chars]"}
        result_dict = truncate_dict(data, max_len_list=5, max_len_str=4, to_str=False)
        self.assertDictEqual(result_dict, truncated_dict)
        expected_json_str = json.dumps(truncated_dict, indent=2)
        result_str = truncate_dict(data, max_len_list=5, max_len_str=4, to_str=True)
        self.assertEqual(result_str, expected_json_str)

    def test_truncate_dict_nested(self):
        data = {"key1": {"subkey1": list(range(10))}, "key2": "valuevalue"}
        truncated_dict = {
            "key1": {"subkey1": list(range(5))},
            "key2": "valu...[10 chars]",
        }
        expected_json_str = json.dumps(truncated_dict, indent=2)
        result_str = truncate_dict(data, max_len_list=5, max_len_str=4, to_str=True)
        self.assertEqual(result_str, expected_json_str)
        result_dict = truncate_dict(data, max_len_list=5, max_len_str=4, to_str=False)
        self.assertEqual(result_dict, truncated_dict)

    def test_truncate_dict_nested_twice(self):
        data = {
            "key1": {
                "subkey1": {"subsubkey1": list(range(10))},
                "subkey2": "valuevalue",
            }
        }
        truncated_dict = {
            "key1": {
                "subkey1": {"subsubkey1": list(range(5))},
                "subkey2": "valu...[10 chars]",
            }
        }
        expected_json_str = json.dumps(truncated_dict, indent=2)
        result_str = truncate_dict(data, max_len_list=5, max_len_str=4, to_str=True)
        self.assertEqual(result_str, expected_json_str)
        result_dict = truncate_dict(data, max_len_list=5, max_len_str=4, to_str=False)
        self.assertEqual(result_dict, truncated_dict)

    def test_truncate_obj_string_short(self):
        data = "short"
        result_str = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=True)
        self.assertEqual(result_str, data)
        result_obj = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=False)
        self.assertEqual(result_obj, data)

    def test_truncate_obj_string_exact(self):
        data = "exactlyten"
        result_str = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=True)
        self.assertEqual(result_str, data)
        result_obj = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=False)
        self.assertEqual(result_obj, data)

    def test_truncate_obj_string_long(self):
        data = "this is a very long string"
        truncated_str = "this is a ...[26 chars]"
        result_str = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=True)
        self.assertEqual(result_str, truncated_str)
        result_obj = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=False)
        self.assertEqual(result_obj, truncated_str)


if __name__ == "__main__":
    unittest.main()
