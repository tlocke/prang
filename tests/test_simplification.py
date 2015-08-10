import prang
import xml.dom.minidom


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
