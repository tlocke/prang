import prang
import os
import os.path
import pytest
from prang.validation import (
    Name, Interleave, Element, EMPTY, ElementNode, QName, TEXT, After,
    start_tag_close_deriv, after, interleave, children_deriv, text_deriv,
    child_deriv, choice, NotAllowed, whitespace, Choice, OneOrMore,
    start_tag_open_deriv, atts_deriv, one_or_more, strip_children_deriv,
    group, nullable, end_tag_deriv, apply_after, flip)
from prang.simplification import PrangException
from functools import partial


def test_children_deriv_interleave():
    schema = After(
        Interleave(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY),
            TEXT),
        EMPTY)

    doc = tuple()

    deriv = children_deriv(schema, ('',))
    assert str(children_deriv(schema, doc)) == str(deriv)

    x = child_deriv(schema, '')
    print("x is", x)
    deriv = choice(schema, x) if whitespace('') else x
    assert str(children_deriv(schema, '')) == str(deriv)

    deriv = text_deriv(schema, '')
    assert str(child_deriv(schema, '')) == str(deriv)

    p1 = Interleave(
        Element(
            Name({'ns': ''}, 'bar'),
            EMPTY),
        TEXT)
    p2 = EMPTY

    deriv = After(text_deriv(p1, ''), p2)
    assert str(text_deriv(schema, '')) == str(deriv)

    p11 = Element(
        Name({'ns': ''}, 'bar'),
        EMPTY)
    p12 = TEXT

    deriv = choice(
        interleave(text_deriv(p11, ''), p12),
        interleave(p11, text_deriv(p12, '')))
    assert str(text_deriv(p1, '')) == str(deriv)

    deriv = NotAllowed()
    assert str(text_deriv(p11, '')) == str(deriv)

    deriv = NotAllowed()
    assert str(interleave(NotAllowed(), p12)) == str(deriv)

    deriv = TEXT
    assert str(text_deriv(p12, '')) == str(deriv)

    assert whitespace('') is True

    schema = After(
        Interleave(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY),
            TEXT),
        EMPTY)

    deriv = Choice(
        After(
            Interleave(
                Element(
                    Name({'ns': ''}, 'bar'),
                    EMPTY),
                TEXT),
            EMPTY),
        After(
            Interleave(
                Element(
                    Name({'ns': ''}, 'bar'),
                    EMPTY),
                TEXT),
            EMPTY))

    print('is', children_deriv(schema, doc))
    print('should be', deriv)
    assert str(children_deriv(schema, doc)) == str(deriv)


def test_start_tag_close_interleave():
    p1 = Interleave(
        Element(
            Name({'ns': ''}, 'bar'),
            EMPTY),
        TEXT)
    p2 = EMPTY
    schema = After(
        p1,
        p2)

    deriv = after(start_tag_close_deriv(p1), p2)
    assert str(start_tag_close_deriv(schema)) == str(deriv)

    schema = p1
    p11 = Element(
        Name({'ns': ''}, 'bar'),
        EMPTY)
    p12 = TEXT

    deriv = interleave(start_tag_close_deriv(p11), start_tag_close_deriv(p12))
    assert str(start_tag_close_deriv(schema)) == str(deriv)

    schema = p11
    deriv = schema
    assert str(start_tag_close_deriv(schema)) == str(deriv)

    schema = p12
    deriv = schema
    assert str(start_tag_close_deriv(schema)) == str(deriv)

    schema = p2
    deriv = schema
    assert str(start_tag_close_deriv(schema)) == str(deriv)

    schema = After(
        Interleave(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY),
            TEXT),
        EMPTY)

    deriv = schema

    assert str(start_tag_close_deriv(schema)) == str(deriv)


def test_start_tag_close_simple():
    schema = After(
        EMPTY,
        EMPTY)

    deriv = After(EMPTY, EMPTY)
    assert str(start_tag_close_deriv(schema)) == str(deriv)


def test_atts_deriv_interleave():
    schema = After(
        Interleave(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY),
            TEXT),
        EMPTY)

    deriv = schema

    doc = tuple()

    assert str(atts_deriv(schema, doc)) == str(deriv)


def test_atts_deriv():

    schema = After(
        EMPTY,
        EMPTY)

    doc = tuple()

    deriv = schema

    assert str(atts_deriv(schema, doc)) == str(deriv)


def test_contains():
    schema = Name({'ns': ''}, 'foo')

    doc = QName('', 'foo')

    assert prang.validation.contains(schema, doc) is True


def test_start_tag_open_deriv():
    schema = Element(
        Name({'ns': ''}, 'foo'), EMPTY)

    doc = QName('', 'foo')

    deriv = After(
        EMPTY,
        EMPTY)
    assert str(start_tag_open_deriv(schema, doc)) == str(deriv)


def test_start_tag_open_deriv_interleave():
    schema = Element(
        Name({'ns': ''}, 'foo'),
        Interleave(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY),
            TEXT))

    doc = QName('', 'foo')

    deriv = After(
        Interleave(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY),
            TEXT),
        EMPTY)
    assert str(start_tag_open_deriv(schema, doc)) == str(deriv)


def test_interleave():
    schema = Element(
        Name({'ns': ''}, 'foo'),
        Interleave(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY),
            TEXT))

    doc = ElementNode(QName('', 'foo'), tuple(), tuple())

    assert str(child_deriv(schema, doc)) == str(NotAllowed())


def test_start_tag_open_deriv_one_or_more():
    schema = Element(
        Name({'ns': ''}, 'foo'),
        Choice(
            EMPTY,
            OneOrMore(
                Element(
                    Name({'ns': ''}, 'bar'),
                    EMPTY))))

    doc = QName('', 'foo')

    p2 = Choice(
        EMPTY,
        OneOrMore(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY)))

    deriv = After(p2, EMPTY)
    assert str(start_tag_open_deriv(schema, doc)) == str(deriv)


def test_atts_deriv_one_or_more():
    schema = After(
        Choice(
            EMPTY,
            OneOrMore(
                Element(
                    Name({'ns': ''}, 'bar'),
                    EMPTY))),
        EMPTY)
    doc = ()

    deriv = schema
    assert str(atts_deriv(schema, doc)) == str(deriv)


def test_start_tag_close_deriv_one_or_more():
    schema = After(
        Choice(
            EMPTY,
            OneOrMore(
                Element(
                    Name({'ns': ''}, 'bar'),
                    EMPTY))),
        EMPTY)
    p1 = Choice(
        EMPTY,
        OneOrMore(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY)))
    p2 = EMPTY
    deriv = after(start_tag_close_deriv(p1), p2)
    assert str(start_tag_close_deriv(schema)) == str(deriv)

    p11 = EMPTY
    p12 = OneOrMore(
        Element(
            Name({'ns': ''}, 'bar'),
            EMPTY))
    deriv = choice(start_tag_close_deriv(p11), start_tag_close_deriv(p12))
    assert str(start_tag_close_deriv(p1)) == str(deriv)

    deriv = EMPTY
    assert str(start_tag_close_deriv(p11)) == str(deriv)

    p121 = Element(
        Name({'ns': ''}, 'bar'),
        EMPTY)
    deriv = one_or_more(start_tag_close_deriv(p121))
    assert str(start_tag_close_deriv(p12)) == str(deriv)

    deriv = p121
    assert str(start_tag_close_deriv(p121)) == str(deriv)

    deriv = After(
        Choice(
            EMPTY,
            OneOrMore(
                Element(
                    Name({'ns': ''}, 'bar'),
                    EMPTY))),
        EMPTY)
    assert str(start_tag_close_deriv(schema)) == str(deriv)


def test_one_or_more_children_deriv():
    schema = After(
        Choice(
            EMPTY,
            OneOrMore(
                Element(
                    Name({'ns': ''}, 'bar'),
                    EMPTY))),
        EMPTY)

    doc = ('x', ElementNode(QName('', 'bar'), tuple(), ()))

    deriv = strip_children_deriv(schema, doc)
    assert str(children_deriv(schema, doc)) == str(deriv)

    x = child_deriv(schema, 'x')
    y = child_deriv(x, doc[1])
    assert str(strip_children_deriv(schema, doc)) == str(y)

    deriv = text_deriv(schema, 'x')
    assert str(child_deriv(schema, 'x')) == str(deriv)

    p1 = Choice(
        EMPTY,
        OneOrMore(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY)))
    p2 = EMPTY

    deriv = after(text_deriv(p1, 'x'), p2)
    assert str(text_deriv(schema, 'x')) == str(deriv)

    p11 = EMPTY
    p12 = OneOrMore(
        Element(
            Name({'ns': ''}, 'bar'),
            EMPTY))
    deriv = choice(text_deriv(p11, 'x'), text_deriv(p12, 'x'))
    assert str(text_deriv(p1, 'x')) == str(deriv)

    assert str(text_deriv(p11, 'x')) == str(NotAllowed())

    p121 = Element(
        Name({'ns': ''}, 'bar'),
        EMPTY)

    deriv = group(text_deriv(p121, 'x'), choice(OneOrMore(p121), EMPTY))
    assert str(text_deriv(p12, 'x')) == str(deriv)

    assert str(text_deriv(p121, 'x')) == str(NotAllowed())


def test_group():
    assert str(group(NotAllowed(), EMPTY)) == str(NotAllowed())


def test_one_or_more():
    schema = Element(
        Name({'ns': ''}, 'foo'),
        Choice(
            EMPTY,
            OneOrMore(
                Element(
                    Name({'ns': ''}, 'bar'),
                    EMPTY))))

    doc = ElementNode(
        QName('', 'foo'), tuple(), (
            'x', ElementNode(QName('', 'bar'), tuple(), ())))

    assert str(child_deriv(schema, doc)) == str(NotAllowed())


def test_one_or_more_multiple():
    schema = Element(
        Name({'ns': ''}, 'foo'),
        OneOrMore(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY)))

    doc = ElementNode(
        QName('', 'foo'), (), (
            ElementNode(QName('', 'bar'), (), ()),
            ElementNode(QName('', 'bar'), (), ()),
            ElementNode(QName('', 'bar'), (), ())))

    qn = QName('', 'foo')
    d1 = start_tag_open_deriv(schema, qn)

    m1 = After(
        OneOrMore(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY)),
        EMPTY)
    assert str(d1) == str(m1)

    atts = ()
    d2 = atts_deriv(d1, atts)

    m2 = m1
    assert str(d2) == str(m2)

    d3 = start_tag_close_deriv(d2)
    m21 = OneOrMore(
        Element(
            Name({'ns': ''}, 'bar'),
            EMPTY))
    m211 = Element(
        Name({'ns': ''}, 'bar'),
        EMPTY)
    m22 = EMPTY
    m3_1 = after(start_tag_close_deriv(m21), m22)
    assert str(m3_1) == str(d3)
    m3_2 = after(start_tag_close_deriv(m21), EMPTY)
    assert str(m3_2) == str(d3)
    m3_3 = after(one_or_more(start_tag_close_deriv(m211)), EMPTY)
    assert str(m3_3) == str(d3)
    m3_4 = after(one_or_more(m211), EMPTY)
    m3_4 = After(OneOrMore(m211), EMPTY)
    m3_4 = After(
        OneOrMore(
            Element(
                Name({'ns': ''}, 'bar'),
                EMPTY)),
        EMPTY)

    assert str(d3) == str(m3_4)

    children = (
        ElementNode(QName('', 'bar'), (), ()),
        ElementNode(QName('', 'bar'), (), ()),
        ElementNode(QName('', 'bar'), (), ()))

    d4 = children_deriv(d3, children)

    m4_1 = children_deriv(m3_4, children)
    assert str(d4) == str(m4_1)
    m4_2 = strip_children_deriv(m3_4, children)
    assert str(d4) == str(m4_2)
    child_0 = ElementNode(QName('', 'bar'), (), ())
    m4_3 = child_deriv(m3_4, child_0)
    child_0_qn = QName('', 'bar')
    m41_1 = start_tag_open_deriv(m3_4, child_0_qn)
    m31 = OneOrMore(
        Element(
            Name({'ns': ''}, 'bar'),
            EMPTY))
    m32 = EMPTY
    m41_2 = apply_after(
        partial(flip(after), m32), start_tag_open_deriv(m31, child_0_qn))
    assert str(m41_1) == str(m41_2)
    m5_1 = start_tag_open_deriv(m31, child_0_qn)
    m311 = Element(
        Name({'ns': ''}, 'bar'),
        EMPTY)
    m5_2 = apply_after(
        partial(flip(group), choice(OneOrMore(m311), EMPTY)),
        start_tag_open_deriv(m311, child_0_qn))
    assert str(m5_1) == str(m5_2)

    assert str(d4) == str(m4_3)

    assert str(child_deriv(schema, doc)) == str(end_tag_deriv(d4))

    assert nullable(child_deriv(schema, doc)) is True


TEST_CASES_PATH = os.path.join(os.getcwd(), 'tests', 'test_cases')


@pytest.mark.parametrize("test_dir", sorted(os.listdir(TEST_CASES_PATH)))
def test_jing(test_dir):
    if test_dir in ('334', '337'):
        return
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
            except Exception as e:
                with open(valid_xml, 'r') as valid_xml_file:
                    valid_xml_str = ''.join(valid_xml_file.readlines())
                print(valid_xml_str)
                print("The exception is ", e)
                raise e
        for invalid_xml in invalid_xmls:
            print("Doing " + invalid_xml)
            with pytest.raises(PrangException) as excinfo:
                schema.validate(doc_file_name=invalid_xml)
                with open(invalid_xml, 'r') as invalid_xml_file:
                    invalid_xml_str = ''.join(invalid_xml_file.readlines())
                print(invalid_xml_str)
            print(excinfo.value)
            if invalid_xml in error_messages:
                assert error_messages[invalid_xml] == str(excinfo.value)

    for invalid_schema in invalid_schemas:
        print("Doing " + invalid_schema)
        with pytest.raises(PrangException):
            prang.Schema(schema_file_name=invalid_schema)
            with open(invalid_schema, 'r') as invalid_schema_file:
                invalid_schema_str = ''.join(invalid_schema_file.readlines())
            print(invalid_schema_str)
