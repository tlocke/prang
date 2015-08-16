from six import text_type, iteritems
import xml.dom
import binascii
import urllib.parse
import requests
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


class PrangElement():
    def __init__(self, parent, name, namespaces, base_uri, attrs, children):
        self.parent = parent
        self.name = name
        self.namespaces = namespaces
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
        for attr_name, attr_value in \
                sorted([(k, v) for k, v in iteritems(self.attrs)]):
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

    def insert_child(self, idx, child):
        if isinstance(child, PrangElement):
            child.parent = self
        self.children.insert(idx, child)

    def append_child(self, child):
        if isinstance(child, PrangElement):
            child.parent = self
        self.children.append(child)

NATIVE_NAMESPACES = (
    None, 'http://relaxng.org/ns/structure/1.0',
    'http://www.w3.org/2000/xmlns')


def to_prang_elem(parent, elem_dom):
    elem_dom.normalize()

    if parent is None:
        namespaces = {'': ''}
        base_uri = ''
    else:
        namespaces = parent.namespaces.copy()
        base_uri = parent.base_uri

    attrs = {}
    attrs_dom = elem_dom.attributes
    if attrs_dom is not None:
        for i in range(attrs_dom.length):
            attr = attrs_dom.item(i)
            attr_nsuri = attr.namespaceURI
            if attr.name == 'xml:base':
                base_uri = attr.value

            if attr.prefix == 'xmlns' or attr.name == 'xmlns':
                namespaces[attr.localName] = attr.value
                attr_nsuri = 'http://www.w3.org/2000/xmlns'

            # This is the anotation simplification rule for attributes
            if attr_nsuri in NATIVE_NAMESPACES:
                attrs[attr.localName] = attr.value

    children = []
    elem = PrangElement(
        parent, elem_dom.localName, namespaces, base_uri, attrs, children)
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


def simplify_name_attribute(elem):
    if elem.name in ('element', 'attribute') and 'name' in elem.attrs:
        attr_parts = elem.attrs['name'].split(':')
        if len(attr_parts) == 1:
            name_elem_name = 'name'
        else:
            name_elem_name = attr_parts[0] + ':name'

        name_elem_attrs = {}
        if elem.name == 'attribute' and 'ns' not in elem.attrs:
            name_elem_attrs['ns'] = ''

        name_elem = PrangElement(
            elem, name_elem_name, elem.namespaces, elem.base_uri,
            name_elem_attrs, [attr_parts[-1]])
        elem.children.insert(0, name_elem)
        del elem.attrs['name']

    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_name_attribute(child)


def simplify_ns_attribute(elem):
    def add_ns_attribute(el):
        if (
                el.name.endswith(':name') or
                el.name in ('name', 'nsName', 'value')) and \
                'ns' not in el.attrs:
            ancestor = el.parent
            ns = None
            while ancestor is not None and ns is None:
                ns = ancestor.attrs.get('ns', None)
                ancestor = ancestor.parent

            el.attrs['ns'] = '' if ns is None else ns

        for child in el.children:
            if not isinstance(child, text_type):
                add_ns_attribute(child)

    add_ns_attribute(elem)

    def remove_ns_attribute(el):
        if (
                el.name.endswith(':name') or
                el.name not in ('name', 'nsName', 'value')) and \
                'ns' in el.attrs:
            del el.attrs['ns']

        for child in el.children:
            if not isinstance(child, text_type):
                remove_ns_attribute(child)

    remove_ns_attribute(elem)


def simplify_qnames(elem):
    if elem.name.endswith(':name'):
        prefix, local_name = elem.name.split(':')
        elem.attrs['ns'] = elem.namespaces[prefix]
        elem.name = local_name

    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_qnames(child)


def simplify_4_11_div(elem, idx):
    if elem.name == 'div':
        for child in elem.children.reverse():
            elem.parent.insert_child(idx, child)
        recurse_children = elem.parent.children
    else:
        recurse_children = elem.children

    for i, child in enumerate(recurse_children):
        if not isinstance(child, text_type):
            simplify_4_11_div(child, i)


def simplify_4_12_num_children(elem, idx):
    recurse_elem = elem
    if elem.name in (
            'define', 'oneOrMore', 'zeroOrMore', 'optional', 'list',
            'mixed') and len(elem.children) > 1:
        group_elem = PrangElement(
            elem, 'group', elem.namespaces.copy(), elem.base_uri, {}, [])

        for child in elem.children:
            group_elem.append_child(child)

        elem.children[:] = [group_elem]

    elif elem.name == 'element':
        if len(elem.children) > 2:
            group_elem = PrangElement(
                elem, 'group', elem.namespaces, elem.base_uri, {}, [])
            for child in elem.children[2:]:
                group_elem.append_child(child)
            elem.children[2:] = [group_elem]

    elif elem.name == 'except':
        if len(elem.children) > 1:
            choice_elem = PrangElement(
                elem, 'choice', elem.namespaces, elem.base_uri, {}, [])
            for child in elem.children[1:]:
                choice_elem.append_child(child)
            elem.children[1:] = [choice_elem]

    elif elem.name == 'attribute':
        if len(elem.children) == 1:
            elem.children.append(
                PrangElement(
                    elem, 'text', elem.namespaces, elem.base_uri, {}, []))

    if elem.name in ('choice', 'group', 'interleave'):
        len_children = len(elem.children)
        print('elem name', elem.name)
        print('len children', len_children)
        if len_children == 1:
            del elem.parent.children[idx]
            elem.parent.insert_child(idx, elem.children[0])
            recurse_elem = elem.parent
        elif len_children > 2:
            new_elem = PrangElement(
                elem, elem.name, elem.namespaces, elem.base_uri, {}, [])
            for child in elem.children[:-1]:
                new_elem.append_child(child)
            elem.children[:-1] = [new_elem]

    for i, child in enumerate(recurse_elem.children):
        if isinstance(child, PrangElement):
            simplify_4_12_num_children(child, i)


def simplify_4_13_mixed(elem):
    if elem.name == 'mixed':
        elem.name = 'interleave'
        elem.children.append(
            PrangElement(
                elem, 'text', elem.namespaces.copy(), elem.base_uri, {}, []))
    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_4_13_mixed(child)


def simplify_4_14_optional(elem):
    if elem.name == 'optional':
        elem.name = 'choice'
        elem.children.append(
            PrangElement(
                elem, 'empty', elem.namespaces.copy(), elem.base_uri, {}, []))
    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_4_14_optional(child)


def simplify_4_15_zero_or_more(elem):
    if elem.name == 'zeroOrMore':
        elem.name = 'choice'
        one_or_more_elem = PrangElement(
            elem, 'oneOrMore', elem.namespaces.copy(), elem.base_uri, {}, [])
        for child in elem.children:
            one_or_more_elem.append_child(child)
        elem.children[:] = [
            one_or_more_elem, PrangElement(
                elem, 'empty', elem.namespaces.copy(), elem.base_uri, {}, [])]

    for child in elem.children:
        if not isinstance(child, text_type):
            simplify_4_15_zero_or_more(child)


def find_descendent(elem, names):
    for child in elem.children:
        if child.name in names:
            return child
        else:
            desc = find_descendent(child, names)
            if desc is not None:
                return desc
    return None


def simplify_4_16_constraints(elem, i):
    if elem.name == 'except':
        if elem.parent.name == 'anyName' and \
                find_descendent(elem, ('anyName',)) is not None:
            raise Exception(
                "An except element that is a child of an anyName element must "
                "not have any anyName descendant elements.")
        if elem.parent.name == 'nsName' and \
                find_descendent(elem, ('nsName', 'anyName')) is not None:
            raise Exception(
                "An except element that is a child of an nsName element must "
                "not have any nsName or anyName descendant elements.")

    if elem.name == 'attribute' and len(elem.children) > 0:
        first_child = elem.children[0]
        if first_child.name == 'name':
            found_elem = first_child
        else:
            found_elem = find_descendent(first_child, ('name', ))

        if found_elem is not None and \
                found_elem.attrs.get('ns', None) == '' and \
                '.'.join(found_elem.children).strip() == 'xmlns':

            raise Exception(
                "A name element that occurs as the first child of an "
                "attribute element or as the descendant of the first child of "
                "an attribute element and that has an ns attribute with value "
                "equal to the empty string must not have content equal to "
                "xmlns.")

        if first_child.name in ('name', 'nsName'):
            found_elem = first_child
        else:
            found_elem = find_descendent(first_child, ('name', 'nsName'))

        if found_elem is not None and \
                found_elem.attrs.get('ns', None) == \
                'http://www.w3.org/2000/xmlns':

            raise Exception(
                "A name or nsName element that occurs as the first child of "
                "an attribute element or as the descendant of the first child "
                "of an attribute element must not have an ns attribute with "
                "value http://www.w3.org/2000/xmlns.")

    for i, child in enumerate(elem.children):
        if not isinstance(child, text_type):
            simplify_4_16_constraints(child, i)


def simplify_4_17_combine(elem, i):
    if elem.name == 'grammar':
        combs = {'define': {}, 'start': {}}
        to_delete = []
        for i, child in enumerate(elem.children):
            if child.name in combs:
                comb_names = combs[child.name]
                if child.name == 'define':
                    comb_name = child.attrs['name']
                else:
                    comb_name = ''
                if comb_name in comb_names:
                    comb_idx, comb_child = comb_names[comb_name]
                    if 'combine' in comb_child.attrs:
                        comb_elem_name = comb_child.attrs['combine']
                    else:
                        comb_elem_name = child.attrs['combine']
                    comb_elem = PrangElement(
                        comb_child, comb_elem_name, elem.namespaces.copy(),
                        elem.base_uri, {}, [])

                    for j in range(len(comb_child.children)):
                        comb_elem.append_child(comb_child.children[j])
                        del comb_child.children[j]

                    for j in range(len(child.children)):
                        comb_elem.append_child(child.children[j])

                    comb_child.append_child(comb_elem)
                    to_delete.append(i)
                else:
                    comb_names[comb_name] = (i, child)

        for cat in combs.keys():
            for comb_idx, comb_child in combs[cat].values():
                if 'combine' in comb_child.attrs:
                    del comb_child.attrs['combine']

        for idx in sorted(to_delete, reverse=True):
            del elem.children[idx]

    for i, child in enumerate(elem.children):
        if not isinstance(child, text_type):
            simplify_4_17_combine(child, i)


def simplify_4_18_grammar(elem, i):
    if elem.parent is None and elem.name != 'grammar':
        pattern_name = elem.name
        pattern_namespaces = elem.namespaces
        pattern_base_uri = elem.base_uri
        pattern_attrs = elem.attrs
        pattern_children = elem.children

        elem.name = 'grammar'
        elem.attrs = {}
        for k in [pattern_attrs.keys()]:
            if k.name == 'xmlns' or k.startswith('xmlns:'):
                elem.attrs[k] = pattern_attrs[k]
                del pattern_attrs[k]

        start_el = PrangElement(
            elem, 'start', pattern_namespaces.copy(), pattern_base_uri, {}, [])
        elem.children = [start_el]

        pattern_el = PrangElement(
            start_el, pattern_name, pattern_namespaces.copy(),
            pattern_base_uri, pattern_attrs, [])
        for child in pattern_children:
            pattern_el.append_child(child)

    if elem.parent is None:
        names = set()
        dups = []

        def find_defs(el, i):
            if el.name == 'define':
                def_name = el.attrs['name']
                if def_name in names:
                    dups.append(el, i)
                else:
                    names.add(def_name)
            for j, c in enumerate(el.children):
                if isinstance(c, PrangElement):
                    find_defs(c, j)

        find_defs(elem, None)

        for dup_el, dup_idx in dups:
            dup_name = dup_el.name
            new_name = dup_name
            while new_name in names:
                new_name += '_'
            names.add(new_name)
            dup_el.name = new_name

            grammar_count = 0

            def find_refs(el, i):
                global grammar_count
                if grammar_count == 0:
                    if el.name == 'ref' and el.attr['name'] == dup_name:
                        el.attr['name'] = new_name
                elif grammar_count == 1:
                    if el.name == 'parentRef' and el.attr['name'] == dup_name:
                        el.attr['name'] = new_name
                else:
                    return
                if el.name == 'grammar':
                    grammar_count += 1

                for j, c in enumerate(el.children):
                    if isinstance(c, PrangElement):
                        find_refs(c, j)
            find_refs(dup_el, dup_idx)
            elem.append_child(dup_el)

        def handle_refs(el, i):
            if el.name == 'parentRef':
                el.name = 'ref'
            elif el.name == 'grammar' and el.parent is not None:
                del el.parent.children[i]
                el.parent.insert_child(i, el.children[0])

            for j, c in enumerate(el.children):
                if isinstance(c, PrangElement):
                    handle_refs(c, j)

    for i, child in enumerate(elem.children):
        if not isinstance(child, text_type):
            simplify_4_18_grammar(child, i)


def simplify(schema_elem):
    simplify_whitespace(schema_elem)
    simplify_datalibrary_add(schema_elem)
    simplify_datalibrary_remove(schema_elem)
    simplify_type_value(schema_elem)
    simplify_href(schema_elem)
    simplify_externalRef(schema_elem, None)
    simplify_include(schema_elem, None)
    simplify_name_attribute(schema_elem)
    simplify_ns_attribute(schema_elem)
    simplify_qnames(schema_elem)
    simplify_4_11_div(schema_elem, None)
    simplify_4_12_num_children(schema_elem, None)
    simplify_4_13_mixed(schema_elem)
    simplify_4_14_optional(schema_elem)
    simplify_4_15_zero_or_more(schema_elem)
    simplify_4_16_constraints(schema_elem, None)
    simplify_4_17_combine(schema_elem, None)
    simplify_4_18_grammar(schema_elem, None)
