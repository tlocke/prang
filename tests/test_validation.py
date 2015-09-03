import prang
import os
import os.path
import pytest


def test_battery():
    TEST_CASES_PATH = os.path.join('tests', 'test_cases')
    for test_dir in os.listdir(TEST_CASES_PATH):
        test_path = os.path.join(TEST_CASES_PATH, test_dir)
        for test_file in os.listdir(test_path):
            test_file_path = os.path.join(test_path, test_file)
            if test_file.endswith('.rng'):
                with open(test_file_path, 'r') as schema_file:
                    schema_str = ''.join(schema_file.readlines())
                if test_file.startswith('i'):
                    with pytest.raises(Exception):
                        prang.Schema(schema_str)
                else:
                    prang.Schema(schema_str)
