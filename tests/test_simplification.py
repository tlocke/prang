import prang.simplification
import xml.dom.minidom
import pytest


def compare_simplify(
        func, input_schema_str, desired_simplified_schema_str, *args):
    input_schema_dom = xml.dom.minidom.parseString(input_schema_str)
    input_schema_el = prang.simplification.to_prang_elem(
        None, input_schema_dom.documentElement)
    func(*([input_schema_el] + list(args)))
    simplified_schema_str = str(input_schema_el)
    if simplified_schema_str != desired_simplified_schema_str:
        print(simplified_schema_str)
        print(desired_simplified_schema_str)
    assert simplified_schema_str == desired_simplified_schema_str


'''
def test_simplification():
    schema_str = """<?xml version="1.0"?>
<element name="foo"
         xmlns="http://relaxng.org/ns/structure/1.0"
         xmlns:a="http://relaxng.org/ns/annotation/1.0"
         xmlns:ex1="http://www.example.com/n1"
         xmlns:ex2="http://www.example.com/n2">
  <a:documentation>A foo element.</a:documentation>
  <element name="ex1:bar1">
    <empty/>
  </element>
  <element name="ex2:bar2">
    <empty/>
  </element>
</element>"""

    schema_dom = xml.dom.minidom.parseString(schema_str)
    schema_elem = prang.to_prang_elem(None, schema_dom.documentElement)
    # print('prang out', str(schema_elem))
    prang.simplification.simplify(schema_elem)
    simplified_schema_str = str(schema_elem)
    # print("simplified out", simplified_schema_str)
    desired_simplified_schema_str = """<?xml version="1.0"?>
<grammar
    xmlns="http://relaxng.org/ns/structure/1.0">
  <start>
    <ref
        name="foo.element"/>
  </start>
  <define
      name="foo.element">
    <element>
      <name
          ns="">
        foo
      </name>
      <group>
        <ref
            name="bar1.element"/>
        <ref
            name="bar2.element"/>
      </group>
    </element>
  </define>
  <define
      name="bar1.element">
    <element>
      <name
          ns="http://www.example.com/n1">
        bar1
      </name>
      <empty/>
    </element>
  </define>
  <define
      name="bar2.element">
    <element>
      <name
          ns="http://www.example.com/n2">
        bar2
      </name>
      <empty/>
    </element>
  </define>
</grammar>"""
    if simplified_schema_str != desired_simplified_schema_str:
        print(simplified_schema_str)
        print(desired_simplified_schema_str)
    assert simplified_schema_str == desired_simplified_schema_str
'''


def test_4_11_div():
    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<element name="addressBook" ',
            'xmlns="http://relaxng.org/ns/structure/1.0">',
            '<div>',
            '<element name="email">',
            '<text/>',
            '</element>',
            '<element name="name">',
            '<text/>',
            '</element>',
            '</div>',
            '</element>'])

    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook">
  <element
      name="email">
    <text/>
  </element>
  <element
      name="name">
    <text/>
  </element>
</element>
"""
    compare_simplify(
        prang.simplification.simplify_4_11_div, schema_str, desired_schema_str)


def test_4_12_num_children():
    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<element name="addressBook" ',
            'xmlns="http://relaxng.org/ns/structure/1.0">',
            '<choice>',
            '<element name="email">',
            '<text/>',
            '</element>',
            '<element name="name">',
            '<text/>',
            '</element>',
            '<element name="note">',
            '<text/>',
            '</element>',
            '</choice>',
            '</element>'])

    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook">
  <choice>
    <choice>
      <element
          name="email">
        <text/>
      </element>
      <element
          name="name">
        <text/>
      </element>
    </choice>
    <element
        name="note">
      <text/>
    </element>
  </choice>
</element>
"""
    compare_simplify(
        prang.simplification.simplify_4_12_num_children, schema_str,
        desired_schema_str)

    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<element name="addressBook" ',
            'xmlns="http://relaxng.org/ns/structure/1.0">',
            '<choice>',
            '<element name="email">',
            '<text/>',
            '</element>',
            '</choice>',
            '</element>'])

    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook">
  <element
      name="email">
    <text/>
  </element>
</element>
"""
    compare_simplify(
        prang.simplification.simplify_4_12_num_children, schema_str,
        desired_schema_str)

    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<element name="addressBook" ',
            'xmlns="http://relaxng.org/ns/structure/1.0">',
            '<attribute>',
            '<anyName>',
            '<except>',
            '<nsName ns="http://relaxng.org/ns/structure/1.0"/>',
            '<nsName ns=""/>',
            '</except>',
            '</anyName>'
            '</attribute>',
            '</element>'])

    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook">
  <attribute>
    <anyName>
      <except>
        <choice>
          <nsName
              ns="http://relaxng.org/ns/structure/1.0"/>
          <nsName
              ns=""/>
        </choice>
      </except>
    </anyName>
    <text/>
  </attribute>
</element>
"""
    compare_simplify(
        prang.simplification.simplify_4_12_num_children, schema_str,
        desired_schema_str)

    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<element name="addressBook" ',
            'xmlns="http://relaxng.org/ns/structure/1.0">',
            '<choice>',
            '<element name="email">',
            '<text/>',
            '</element>',
            '<element name="name">',
            '<text/>',
            '</element>',
            '<element name="note">',
            '<text/>',
            '</element>',
            '<element name="address">',
            '<text/>',
            '</element>',
            '</choice>',
            '</element>'])

    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook">
  <choice>
    <choice>
      <choice>
        <element
            name="email">
          <text/>
        </element>
        <element
            name="name">
          <text/>
        </element>
      </choice>
      <element
          name="note">
        <text/>
      </element>
    </choice>
    <element
        name="address">
      <text/>
    </element>
  </choice>
</element>
"""
    compare_simplify(
        prang.simplification.simplify_4_12_num_children, schema_str,
        desired_schema_str)


def test_4_13_mixed():
    schema_str = """<?xml version="1.0"?>
<element name="addressBook" xmlns="http://relaxng.org/ns/structure/1.0">
  <mixed>
    <element name="email">
      <text/>
    </element>
  </mixed>
</element>
"""
    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook">
  <interleave>
    <element
        name="email">
      <text/>
    </element>
    <text/>
  </interleave>
</element>
"""
    compare_simplify(
        prang.simplification.simplify_4_13_mixed, schema_str,
        desired_schema_str)


def test_4_14_optional():
    schema_str = """<?xml version="1.0"?>
<element name="addressBook" xmlns="http://relaxng.org/ns/structure/1.0">
  <optional>
    <element name="email">
      <text/>
    </element>
  </optional>
</element>
"""
    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook">
  <choice>
    <element
        name="email">
      <text/>
    </element>
    <empty/>
  </choice>
</element>
"""
    compare_simplify(
        prang.simplification.simplify_4_14_optional, schema_str,
        desired_schema_str)


def test_4_15_zero_or_more_element():
    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<element name="addressBook" ',
            'xmlns="http://relaxng.org/ns/structure/1.0">',
            '<zeroOrMore>',
            '<element name="email">',
            '<text/>',
            '</element>',
            '</zeroOrMore>',
            '</element>'])

    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook">
  <choice>
    <oneOrMore>
      <element
          name="email">
        <text/>
      </element>
    </oneOrMore>
    <empty/>
  </choice>
</element>
"""
    compare_simplify(
        prang.simplification.simplify_4_15_zero_or_more, schema_str,
        desired_schema_str)


def test_4_17_combine():
    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<grammar xmlns="http://relaxng.org/ns/structure/1.0">',
            '<start>',
            '<element name="addressBook">',
            '<zeroOrMore>',
            '<element name="card">',
            '<ref name="card.attlist"/>',
            '</element>',
            '</zeroOrMore>',
            '</element>',
            '</start>',
            '<define name="card.attlist" combine="interleave">',
            '<attribute name="name">',
            '<text/>',
            '</attribute>',
            '</define>',
            '<define name="card.attlist" combine="interleave">',
            '<attribute name="email">',
            '<text/>',
            '</attribute>',
            '</define>',
            '</grammar>'])

    desired_schema_str = """<?xml version="1.0"?>
<grammar>
  <start>
    <element
        name="addressBook">
      <zeroOrMore>
        <element
            name="card">
          <ref
              name="card.attlist"/>
        </element>
      </zeroOrMore>
    </element>
  </start>
  <define
      name="card.attlist">
    <interleave>
      <attribute
          name="name">
        <text/>
      </attribute>
      <attribute
          name="email">
        <text/>
      </attribute>
    </interleave>
  </define>
</grammar>
"""
    compare_simplify(
        prang.simplification.simplify_4_17_combine, schema_str,
        desired_schema_str)


def test_4_18_grammar():
    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<grammar xmlns="http://relaxng.org/ns/structure/1.0">',
            '<start>',
            '<grammar>',
            '<start>',
            '<ref name="foo"/>',
            '</start>',
            '<define name="foo">',
            '<element name="innerFoo">',
            '<parentRef name="foo"/>',
            '</element>',
            '</define>',
            '</grammar>'
            '</start>',
            '<define name="foo">',
            '<element name="outerFoo">',
            '<empty/>',
            '</element>',
            '</define>',
            '</grammar>'])

    desired_schema_str = """<?xml version="1.0"?>
<grammar
    xmlns="http://relaxng.org/ns/structure/1.0">
  <start>
    <ref
        name="foo"/>
  </start>
  <define
      name="foo_g">
    <element
        name="outerFoo">
      <empty/>
    </element>
  </define>
  <define
      name="foo">
    <element
        name="innerFoo">
      <ref
          name="foo_g"/>
    </element>
  </define>
</grammar>
"""
    compare_simplify(
        prang.simplification.simplify_4_18_grammar, schema_str,
        desired_schema_str)


def test_4_19_define_ref():
    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<grammar xmlns="http://relaxng.org/ns/structure/1.0">',
            '<start>',
            '<ref name="foo"/>',
            '</start>',
            '<define name="foo">',
            '<choice>',
            '<element>',
            '<name ns="">',
            'foo',
            '</name>',
            '<empty/>',
            '</element>',
            '<ref name="foo"/>',
            '</choice>',
            '</define>',
            '</grammar>'])

    with pytest.raises(prang.simplification.PrangException):
        schema_dom = xml.dom.minidom.parseString(schema_str)
        schema_elem = prang.simplification.to_prang_elem(
            None, schema_dom.documentElement)
        prang.simplification.simplify_4_19_define_ref(schema_elem)

    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<grammar xmlns="http://relaxng.org/ns/structure/1.0">',
            '<start>',
            '<element name="name">',
            '<text/>'
            '</element>',
            '</start>',
            '</grammar>'])

    desired_schema_str = """<?xml version="1.0"?>
<grammar>
  <start>
    <ref
        name="c"/>
  </start>
  <define
      name="c">
    <element
        name="name">
      <text/>
    </element>
  </define>
</grammar>
"""
    compare_simplify(
        prang.simplification.simplify_4_19_define_ref, schema_str,
        desired_schema_str)

    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<grammar xmlns="http://relaxng.org/ns/structure/1.0">',
            '<start>',
            '<ref name="c"/>',
            '</start>',
            '<define name="c">',
            '<choice>',
            '<element name="first_name">',
            '<text/>'
            '</element>',
            '<element name="last_name">',
            '<text/>'
            '</element>',
            '</choice>',
            '</define>',
            '</grammar>'])

    desired_schema_str = """<?xml version="1.0"?>
<grammar>
  <start>
    <choice>
      <ref
          name="c_c"/>
      <ref
          name="c_c_c"/>
    </choice>
  </start>
  <define
      name="c_c">
    <element
        name="first_name">
      <text/>
    </element>
  </define>
  <define
      name="c_c_c">
    <element
        name="last_name">
      <text/>
    </element>
  </define>
</grammar>
"""
    compare_simplify(
        prang.simplification.simplify_4_19_define_ref, schema_str,
        desired_schema_str)

    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<grammar xmlns="http://relaxng.org/ns/structure/1.0">',
            '<start>',
            '<element name="first_name">',
            '<ref name="zathustra"/>',
            '</element>',
            '</start>',
            '<define name="zathustra">',
            '<choice>'
            '<ref name="c"/>'
            '<text/>',
            '</choice>',
            '</define>',
            '<define name="c">',
            '<choice>',
            '<empty/>',
            '<text/>',
            '</choice>',
            '</define>',
            '</grammar>'])

    desired_schema_str = """<?xml version="1.0"?>
<grammar>
  <start>
    <ref
        name="c_c"/>
  </start>
  <define
      name="c_c">
    <element
        name="first_name">
      <choice>
        <choice>
          <empty/>
          <text/>
        </choice>
        <text/>
      </choice>
    </element>
  </define>
</grammar>
"""
    compare_simplify(
        prang.simplification.simplify_4_19_define_ref, schema_str,
        desired_schema_str)
    '''
    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<grammar>',
            '<start>',
            '<ref name="styleNameRef"/>',
            '<ref name="text-list"/>',
            '</start>',
            '<define name="text-list">',
            '<element>',
            '<ref name="text-list-attr"/>',
            '<choice>',
            '<oneOrMore>',
            '<ref name="text-list-item"/>',
            '</oneOrMore>',
            '<empty/>',
            '</choice>',
            '<group>',
            '<name ns="urn:oasis:names:tc:opendocument:xmlns:text:1.0">',
            'list',
            '</name>',
            '<choice>',
            '<ref name="text-list-header"/>',
            '<empty/>',
            '</choice>',
            '</group>',
            '</element>',
            '</define>',
            '<define name="text-list-attr">',
            '<interleave>',
            '<interleave>'
            '<choice>',
            '<attribute>',
            '<name ns="urn:oasis:names:tc:opendocument:xmlns:text:1.0">',
            'style-name',
            '</name>'
            '<ref name="styleNameRef"/>',
            '</attribute>',
            '<empty/>',
            '</choice>',
            '<choice>',
            '<attribute>',
            '<name ns="urn:oasis:names:tc:opendocument:xmlns:text:1.0">',
            'continue-numbering',
            '</name>',
            '<ref name="boolean"/>',
            '</attribute>',
            '<empty/>',
            '</choice>',
            '<choice>',
            '<attribute>',
            '<name ns="urn:oasis:names:tc:opendocument:xmlns:text:1.0">',
            'continue-list',
            '</name>',
            '<ref name="IDREF"/>',
            '</attribute>',
            '<empty/>',
            '</choice>',
            '</interleave>',
            '<choice>'
            '<ref name="xml-id"/>'
            '<empty/>',
            '</choice>',
            '</interleave>',
            '</define>',
            '<define name="styleNameRef">',
            '<choice>',
            '<data ',
            'datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes" ',
            'type="NCName"/>',
            '<empty/>',
            '</choice>',
            '</define>',
            '</grammar>'])

    desired_schema_str = """<?xml version="1.0"?>
<grammar>
  <start>
    <element name="first_name">
      <choice>
        <choice>
          <empty/>
          <text/>
        </choice>
        <text/>
      </choice>
    </element>
  </start>
</grammar>
"""
    '''
    schema_str = ''.join(
        [
            '<?xml version="1.0"?>',
            '<grammar xmlns="http://relaxng.org/ns/structure/1.0">',
            '<start>',
            '<ref name="styleNameRef"/>',
            '<ref name="text-list"/>',
            '</start>',
            '<define name="text-list">',
            '<element name="eagle">',
            '<ref name="styleNameRef"/>',
            '</element>',
            '</define>',
            '<define name="styleNameRef">',
            '<data ',
            'datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes" ',
            'type="NCName"/>',
            '</define>',
            '</grammar>'])

    desired_schema_str = """<?xml version="1.0"?>
<grammar>
  <start>
    <data
        datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes"
        type="NCName"/>
    <ref
        name="text-list"/>
  </start>
  <define
      name="text-list">
    <element
        name="eagle">
      <data
          datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes"
          type="NCName"/>
    </element>
  </define>
</grammar>
"""
    compare_simplify(
        prang.simplification.simplify_4_19_define_ref, schema_str,
        desired_schema_str)


def test_odf_1_2():
    schema_str = ''.join(
        open('/home/tlocke/prang/tests/odf_1_2.rng').readlines())
    schema_dom = xml.dom.minidom.parseString(schema_str)
    schema_elem = prang.simplification.to_prang_elem(
        None, schema_dom.documentElement)
    prang.simplification.simplify(schema_elem)
