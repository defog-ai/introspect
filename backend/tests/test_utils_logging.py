from datetime import datetime, timedelta
import json
import unittest

import pandas as pd
from utils_logging import truncate_list, truncate_dict, truncate_obj


class TestUtilsLogging(unittest.TestCase):

    # override the default maxDiff attribute for easy debugging
    def __init__(self, *args, **kwargs):
        super(TestUtilsLogging, self).__init__(*args, **kwargs)
        self.maxDiff = None

    def test_truncate_list_short(self):
        data = [1, 2, 3]
        result_dict = truncate_list(data, max_len_list=5, max_len_str=5)
        self.assertEqual(result_dict, data)

    def test_truncate_list_long(self):
        data = list(range(10))
        result_dict = truncate_list(data, max_len_list=5, max_len_str=5)
        self.assertEqual(result_dict, data[:5])

    def test_truncate_list_dates_pd(self):
        date_range = pd.date_range("2021-01-01", periods=10).to_list()
        result_dict = truncate_list(date_range, max_len_list=5, max_len_str=5)
        self.assertEqual(result_dict, date_range[:5])

    def test_truncate_list_dates(self):
        date_range = [
            (datetime.fromisoformat("2021-01-01") + timedelta(days=i),)
            for i in range(10)
        ]
        result_dict = truncate_list(date_range, max_len_list=5, max_len_str=5)
        self.assertEqual(result_dict, date_range[:5])

    def test_truncate_list_nested(self):
        data = [[1, 2, 3], list(range(10))]
        result_dict = truncate_list(data, max_len_list=5, max_len_str=5)
        expected_dict = [[1, 2, 3], list(range(5))]
        self.assertEqual(result_dict, expected_dict)

    def test_truncate_list_mixed(self):
        dt = datetime.now()
        data = [
            {"key1": [1, 2, 3], "key2": "value", "key3": dt},
            {"key1": list(range(10)), "key2": "valuevalue"},
        ]
        result_dict = truncate_list(data, max_len_list=5, max_len_str=4)
        expected_dict = [
            {"key1": [1, 2, 3], "key2": "valu...[5 chars]", "key3": dt},
            {"key1": list(range(5)), "key2": "valu...[10 chars]"},
        ]
        self.assertEqual(result_dict, expected_dict)

    def test_truncate_dict_short(self):
        data = {"key1": [1, 2, 3], "key2": "value"}
        result_dict = truncate_dict(data, max_len_list=5, max_len_str=5)
        self.assertEqual(result_dict, data)

    def test_truncate_dict_long(self):
        data = {"key1": list(range(10)), "key2": "valuevalue"}
        expected_dict = {"key1": list(range(5)), "key2": "valu...[10 chars]"}
        result_dict = truncate_dict(data, max_len_list=5, max_len_str=4)
        self.assertDictEqual(result_dict, expected_dict)

    def test_truncate_dict_nested(self):
        data = {"key1": {"subkey1": list(range(10))}, "key2": "valuevalue"}
        expected_dict = {
            "key1": {"subkey1": list(range(5))},
            "key2": "valu...[10 chars]",
        }
        result_dict = truncate_dict(data, max_len_list=5, max_len_str=4)
        self.assertEqual(result_dict, expected_dict)

    def test_truncate_dict_nested_twice(self):
        data = {
            "key1": {
                "subkey1": {"subsubkey1": list(range(10))},
                "subkey2": "valuevalue",
            }
        }
        expected_dict = {
            "key1": {
                "subkey1": {"subsubkey1": list(range(5))},
                "subkey2": "valu...[10 chars]",
            }
        }
        result_dict = truncate_dict(data, max_len_list=5, max_len_str=4)
        self.assertEqual(result_dict, expected_dict)

    def test_truncate_obj_string_short(self):
        data = "short"
        result = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=True)
        self.assertEqual(result, data)
        result = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=False)
        self.assertEqual(result, data)

    def test_truncate_obj_string_exact(self):
        data = "exactlyten"
        result = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=True)
        self.assertEqual(result, data)
        result = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=False)
        self.assertEqual(result, data)

    def test_truncate_obj_string_long(self):
        data = "this is a very long string"
        truncated_str = "this is a ...[26 chars]"
        result = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=True)
        self.assertEqual(result, truncated_str)
        result = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=False)
        self.assertEqual(result, truncated_str)

    def test_truncate_obj_list_to_str(self):
        data = list(range(10))
        result = truncate_obj(data, max_len_list=5, max_len_str=10, to_str=True)
        expected = json.dumps(data[:5], indent=2)
        self.assertEqual(result, expected)

    def test_truncate_obj_dict_to_str(self):
        dt = datetime.fromisoformat("2021-01-01")
        data = {"key1": list(range(10)), "key2": "valuevalue", "key3": dt}
        result = truncate_obj(data, max_len_list=5, max_len_str=4, to_str=True)
        expected = json.dumps(
            {
                "key1": list(range(5)),
                "key2": "valu...[10 chars]",
                "key3": "2021-01-01 00:00:00",
            },
            indent=2,
        )
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
