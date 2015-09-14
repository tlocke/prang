import prang
import os
import os.path
import pytest


TEST_CASES_PATH = os.path.join(os.getcwd(), 'tests', 'test_cases')


@pytest.mark.parametrize("test_dir", sorted(os.listdir(TEST_CASES_PATH)))
def test_jing(test_dir):
    test_path = os.path.join(TEST_CASES_PATH, test_dir)
    os.chdir(test_path)
    correct_schemas = []
    invalid_schemas = []
    valid_xmls = []
    invalid_xmls = []
    error_messages = {}
    for test_file in os.listdir(test_path):
        test_file_path = os.path.join(test_path, test_file)
        root, ext = os.path.splitext(test_file)
        if ext == '.rng':
            if root.endswith('i'):
                invalid_schemas.append(test_file_path)
            elif root.endswith('c'):
                correct_schemas.append(test_file_path)
        elif ext == '.xml':
            if root.endswith('i'):
                invalid_xmls.append(test_file_path)
            elif root.endswith('v'):
                valid_xmls.append(test_file_path)

    for correct_schema in correct_schemas:
        with open(correct_schema, 'r') as schema_file:
            schema_str = ''.join(schema_file.readlines())
        print(schema_str)
        schema = prang.Schema(schema_file_name=correct_schema)
        for valid_xml in valid_xmls:
            try:
                schema.validate(doc_file_name=valid_xml)
            except:
                with open(valid_xml, 'r') as valid_xml_file:
                    valid_xml_str = ''.join(valid_xml_file.readlines())
                print(valid_xml_str)
                raise
        for invalid_xml in invalid_xmls:
            with pytest.raises(prang.validation.InvalidException) as excinfo:
                schema.validate(doc_file_name=invalid_xml)
                with open(invalid_xml, 'r') as invalid_xml_file:
                    invalid_xml_str = ''.join(invalid_xml_file.readlines())
                print(invalid_xml_str)
            if invalid_xml in error_messages:
                assert error_messages[invalid_xml] == str(excinfo.value)

    for invalid_schema in invalid_schemas:
        continue
        with pytest.raises(Exception):
            prang.Schema(schema_file_name=invalid_schema)
