import prang
import xml.dom.minidom


def compare_simplify(func, input_schema, desired_simplified_schema_str, *args):
    schema_dom = xml.dom.minidom.parseString(input_schema)
    schema_elem = prang.to_prang_elem(None, schema_dom.documentElement)
    func(*([schema_elem] + list(args)))
    simplified_schema_str = str(schema_elem)
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
    prang.simplify(schema_elem)
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
    name="addressBook"
    xmlns="http://relaxng.org/ns/structure/1.0">
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
        prang.simplify_4_12_num_children, schema_str, desired_schema_str, None)


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
    name="addressBook"
    xmlns="http://relaxng.org/ns/structure/1.0">
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
        prang.simplify_4_13_mixed, schema_str, desired_schema_str)


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
    name="addressBook"
    xmlns="http://relaxng.org/ns/structure/1.0">
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
        prang.simplify_4_14_optional, schema_str, desired_schema_str)


def test_4_15_zero_or_more_element():
    schema_str = """<?xml version="1.0"?>
<element name="addressBook" xmlns="http://relaxng.org/ns/structure/1.0">
  <zeroOrMore>
    <element name="email">
      <text/>
    </element>
  </zeroOrMore>
</element>
"""
    desired_schema_str = """<?xml version="1.0"?>
<element
    name="addressBook"
    xmlns="http://relaxng.org/ns/structure/1.0">
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
        prang.simplify_4_15_zero_or_more, schema_str, desired_schema_str)
