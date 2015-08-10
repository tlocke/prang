from six import text_type, iteritems
import xml.dom
import binascii
import urllib.parse
import requests
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


class PrangElement():
    def __init__(self, parent, name, base_uri, attrs, children):
        self.parent = parent
        self.name = name
        self.base_uri = base_uri
        self.attrs = attrs
        self.children = children

    def __str__(self):
        out = []
        if self.parent is None:
            out.append('<?xml version="1.0"?>\n')
        level = 0
        parent = self.parent
        while parent is not None:
            level += 1
            parent = parent.parent
        wspace = '  ' * level

        out.append(wspace + '<' + self.name)
        for attr_name, attr_value in iteritems(self.attrs):
            out.append(
                '\n' + wspace + ' ' * 4 + attr_name + '="' + attr_value + '"')
        if len(self.children) > 0:
            child_wspace = wspace + ' ' * 2
            out.append('>\n')
            for child in self.children:
                if isinstance(child, text_type):
                    length = 0
                    line = []
                    for word in child.split():
                        new_len = length + len(word)
                        if new_len + len(line) > 78:
                            out.append(child_wspace + ' '.join(line) + '\n')
                            length = 0
                            line = []
                        else:
                            length = new_len
                        line.append(word)
                    if len(line) > 0:
                        out.append(child_wspace + ' '.join(line) + '\n')
                else:
                    out.append(str(child))
            out.append(wspace + '</' + self.name + '>\n')
        else:
            out.append('/>\n')
        return ''.join(out)


NATIVE_NAMESPACES = (None, 'http://relaxng.org/ns/structure/1.0')


def to_prang_elem(parent, elem_dom):
    elem_dom.normalize()

    base_uri = None
    attrs = {}
    attrs_dom = elem_dom.attributes
    if attrs_dom is not None:
        for i in range(attrs_dom.length):
            attr = attrs_dom.item(i)
            if attr.name == 'xml:base':
                base_uri = attr.value

            # This is the anotation simplification rule for attributes
            if attr.namespaceURI in NATIVE_NAMESPACES:
                attrs[attr.localName] = attr.value
    if base_uri is None:
        base_uri = '' if parent is None else parent.base_uri

    children = []
    elem = PrangElement(parent, elem_dom.localName, base_uri, attrs, children)
    for child in elem_dom.childNodes:
        node_type = child.nodeType
        if node_type == xml.dom.Node.ELEMENT_NODE and \
                child.namespaceURI in NATIVE_NAMESPACES:
            children.append(to_prang_elem(elem, child))
        elif node_type == xml.dom.Node.TEXT_NODE:
            children.append(child.data)

    return elem


def is_valid(schema, doc):
    if isinstance(schema, text_type):
        schema_dom = xml.dom.minidom.parseString(schema)
    if isinstance(doc, text_type):
        pass
        # doc_dom = xml.dom.minidom.parseString(doc)

    schema_elem = to_prang_elem(
        schema_dom.getDocumentElement())
    schema_dom = simplify(schema_elem)


def simplify_whitespace(elem):
    if elem.name == 'name':
        for attr_name, attr_value in list(iteritems(elem.attrs)):
            if attr_name in ('name', 'type', 'combine'):
                elem.attrs[attr_name] = attr_value.strip()

    if elem.name not in ('value', 'param'):
        children = elem.children
        new_children = []
        for child in children:
            if isinstance(child, text_type):
                if len(child.split()) > 0:
                    new_children.append(child)
            else:
                new_children.append(child)
                simplify_whitespace(child)
        elem.children = new_children


def xlink_encode(href):
    new_value = []
    for char in href:
        code_point = ord(char)
        if 0 <= code_point < 33 or code_point > 126 or \
                char in (
                    '<', '>', '<', '>', '{', '}', '|', '\\', '^', '`'):
            new_value.append("%" + binascii.hexlify(char.encode('utf8')))
        else:
            new_value.append(char)
    return ''.join(new_value)


def simplify_datalibrary_add(elem):
    attrs = elem.attrs
    datatypeLibrary = None

    if 'datatypeLibrary' in attrs:
        datatypeLibrary = xlink_encode(attrs['datatypeLibrary'])
        attrs['datatypeLibrary'] = datatypeLibrary

    if elem.name in ('data', 'value') and datatypeLibrary is None:
        parent = elem.parent
        while datatypeLibrary is None and parent is not None:
            for name, value in parent.attrs:
                if name == 'datatypeLibrary':
                    datatypeLibrary = value
            parent = elem.parent
        if datatypeLibrary is None:
            datatypeLibrary = ''
        attrs['datatypeLibrary'] = datatypeLibrary

    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_datalibrary_add(child)


def simplify_datalibrary_remove(elem):
    if elem.name not in ('data', 'value') and 'datatypeLibrary' in elem.attrs:
        del elem.attrs['datatypeLibrary']

    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_datalibrary_remove(child)


def simplify_type_value(elem):
    if elem.name == 'value' and 'type' not in elem.attrs:
        elem.attrs['type'] = 'token'
        elem.attrs['datatypeLibrary'] = ''

    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_type_value(child)


def simplify_href(elem):
    if elem.name in ('externalRef', 'include'):
        elem.attrs['href'] = urllib.parse.urljoin(
            elem.base_uri, xlink_encode(elem.attrs['href']))

    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_href(child)


def simplify_externalRef(elem, idx):
    if elem.name == 'externalRef':
        href = elem.attrs['href']

        r = requests.get(href)
        ext_dom = xml.dom.minidom.parseString(r.text)
        doc_elem = ext_dom.documentElement

        sub_elem = to_prang_elem(doc_elem)

        if 'ns' in elem.attrs and 'ns' not in sub_elem.attrs:
            sub_elem.attrs['ns'] = elem.attrs['ns']

        simplify_whitespace(sub_elem)
        simplify_datalibrary_add(sub_elem)
        simplify_datalibrary_remove(sub_elem)
        simplify_type_value(sub_elem)
        simplify_href(sub_elem)
        simplify_externalRef(sub_elem, None)

        elem.children[idx] = sub_elem

    else:
        for i, child in enumerate(elem.children):
            if not isinstance(child, text_type):
                simplify_externalRef(child, i)


def simplify_include(elem, idx):
    if elem.name == 'include':
        href = elem.attrs['href']

        r = requests.get(href)
        ext_dom = xml.dom.minidom.parseString(r.text)
        doc_elem = ext_dom.documentElement

        sub_elem = to_prang_elem(doc_elem)
        if sub_elem.name != 'grammar':
            raise Exception(
                "The document element referred to by and 'include' must be "
                "'grammar'.")

        simplify_whitespace(sub_elem)
        simplify_datalibrary_add(sub_elem)
        simplify_datalibrary_remove(sub_elem)
        simplify_type_value(sub_elem)
        simplify_href(sub_elem)
        simplify_externalRef(sub_elem, None)
        simplify_include(sub_elem, None)

        def has_start_component(element):
            for child in element.children:
                if child.name == 'start' or (
                        child.name == 'div' and has_start_component(child)):
                    return True
            return False

        def remove_start_components(element):
            children = element.children
            for i in range(len(children)):
                child = children[i]
                if child.name == 'start':
                    del children[i]
                elif child.name == 'div':
                    remove_start_components(child)

        if has_start_component(elem):
            remove_start_components(sub_elem)

        def find_define_components(element, defines):
            if element.name == 'define':
                defines.add(element.attrs['name'])
            elif element.name == 'div':
                for child in element.children:
                    find_define_components(child, defines)
            return defines

        defines = find_define_components(elem, set())

        def remove_define_components(element):
            children = element.children
            for i in range(len(children)):
                child = children[i]
                if child.name == 'define' and child.attrs['name'] in defines:
                    del children[i]
                elif child.name == 'div':
                    remove_define_components(child)

        remove_define_components(sub_elem)

        elem.name = 'div'
        del elem.attrs['href']

        sub_elem.name = 'div'
        elem.children.insert(0, sub_elem)

    else:
        for i, child in enumerate(elem.children):
            if not isinstance(child, text_type):
                simplify_include(child, i)


def simplify(schema_elem):
    simplify_whitespace(schema_elem)
    simplify_datalibrary_add(schema_elem)
    simplify_datalibrary_remove(schema_elem)
    simplify_type_value(schema_elem)
    simplify_href(schema_elem)
    simplify_externalRef(schema_elem, None)
    simplify_include(schema_elem, None)
