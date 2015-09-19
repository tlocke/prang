import copy
import xml.dom
import binascii
import urllib
import requests
from itertools import chain
import os.path


class PrangElement():
    def __init__(self, name, namespaces, base_uri, attrs):
        self._parent = None
        self.name = name
        self.namespaces = namespaces
        self.base_uri = base_uri
        self.attrs = attrs
        self._children = []

    @property
    def parent(self):
        return self._parent

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
                sorted([(k, v) for k, v in self.attrs.items()]):
            out.append(
                '\n' + wspace + ' ' * 4 + attr_name + '="' + attr_value + '"')
        if sum(1 for c in self.iter_children()) > 0:
            child_wspace = wspace + ' ' * 2
            out.append('>\n')
            for child in self.iter_children():
                if isinstance(child, str):
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

    def __deepcopy__(self, memo):
        cpy = copy.copy(self)
        if 'root' not in memo:
            cpy._parent = None
            memo['root'] = True
        cpy._children = copy.deepcopy(self._children, memo)
        for c in cpy.iter_child_elems():
            c._parent = cpy
        return cpy

    def insert_child(self, idx, child):
        if not isinstance(child, (PrangElement, str)):
            raise Exception("A child must be an element or string.")

        if isinstance(child, PrangElement):
            child.remove()
            if child.contains_element(self):
                raise Exception("Can't create a circular reference.")
            child._parent = self
        self._children.insert(idx, child)

    def contains_element(self, element):
        if self is element:
            return True
        for child in self.iter_child_elems():
            if child.contains_element(element):
                return True
        return False

    def append_child(self, child):
        self.insert_child(sum(1 for c in self.iter_children()), child)

    def remove(self):
        if self.parent is not None:
            return self.parent.remove_child(self)

    def remove_child(self, child):
        for i in range(len(self._children)):
            c = self._children[i]
            if c is child:
                if isinstance(c, PrangElement):
                    c._parent = None
                del self._children[i]
                return i
        raise Exception(
            "This should never happen. The parent's children doesn't "
            "contain the child.")

    def enumerate_child_elements(self):
        return (
            (i, c) for i, c in enumerate(self.children)
            if isinstance(c, PrangElement))

    def iter_child_elems(self, names=None):
        if names is None:
            return (c for c in self._children if isinstance(c, PrangElement))
        else:
            return (
                c for c in self._children
                if isinstance(c, PrangElement) and c.name in names)

    def iter_children(self):
        return self._children

RELAXNG_NS = 'http://relaxng.org/ns/structure/1.0'


def to_prang_elem(parent, elem_dom):
    elem_dom.normalize()

    if parent is None:
        namespaces = {
            '': '', 'xml': 'http://www.w3.org/XML/1998/namespace'}
        base_uri = ''
    elif isinstance(parent, str):
        namespaces = {
            '': '', 'xml': 'http://www.w3.org/XML/1998/namespace'}
        base_uri = parent
        parent = None
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
            if attr_nsuri in (None, RELAXNG_NS):
                # Normalize whitespace for RELAX NG token
                attrs[attr.localName] = ' '.join(attr.value.split())

    elem = PrangElement(elem_dom.localName, namespaces, base_uri, attrs)
    for child in elem_dom.childNodes:
        node_type = child.nodeType
        if node_type == xml.dom.Node.ELEMENT_NODE and \
                child.namespaceURI == RELAXNG_NS:
            elem.append_child(to_prang_elem(elem, child))
        elif node_type == xml.dom.Node.TEXT_NODE:
            elem.append_child(child.data)

    return elem


def simplify_4_2_whitespace(elem):
    if elem.name == 'name':
        for attr_name, attr_value in list(elem.attrs.items()):
            if attr_name in ('name', 'type', 'combine'):
                elem.attrs[attr_name] = attr_value.strip()
        child = list(elem.iter_children())[0]
        elem.remove_child(child)
        elem.append_child(child.strip())

    if elem.name not in ('value', 'param'):
        for child in list(elem.iter_children()):
            if isinstance(child, str) and len(child.split()) == 0:
                elem.remove_child(child)

    for child in elem.iter_child_elems():
        simplify_4_2_whitespace(child)


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


def simplify_datalibrary_4_3_add(elem):
    attrs = elem.attrs
    datatypeLibrary = None

    if 'datatypeLibrary' in attrs:
        datatypeLibrary = xlink_encode(attrs['datatypeLibrary'])
        attrs['datatypeLibrary'] = datatypeLibrary

    if elem.name in ('data', 'value') and datatypeLibrary is None:
        parent = elem.parent
        while datatypeLibrary is None and parent is not None:
            for name, value in parent.attrs.items():
                if name == 'datatypeLibrary':
                    datatypeLibrary = value
            parent = parent.parent
        if datatypeLibrary is None:
            datatypeLibrary = ''
        attrs['datatypeLibrary'] = datatypeLibrary

    for child in elem.iter_child_elems():
        simplify_datalibrary_4_3_add(child)


def simplify_datalibrary_4_3_remove(elem):
    if elem.name not in ('data', 'value') and \
            'datatypeLibrary' in elem.attrs:
        del elem.attrs['datatypeLibrary']

    for child in elem.iter_child_elems():
        simplify_datalibrary_4_3_remove(child)


def simplify_type_value(elem):
    if elem.name == 'value' and 'type' not in elem.attrs:
        elem.attrs['type'] = 'token'
        elem.attrs['datatypeLibrary'] = ''

    for child in elem.iter_child_elems():
        simplify_type_value(child)


def simplify_href(elem):
    if elem.name in ('externalRef', 'include'):
        elem.attrs['href'] = urllib.parse.urljoin(
            elem.base_uri, xlink_encode(elem.attrs['href']))

    for child in elem.iter_child_elems():
        simplify_href(child)


def simplify_externalRef(elem):
    if elem.name == 'externalRef':
        href = elem.attrs['href']

        if href.startswith('http://') or href.startswith('https://'):
            ext_str = requests.get(href).text
        else:
            with open(href) as f:
                ext_str = ''.join(f)
        ext_dom = xml.dom.minidom.parseString(ext_str)
        doc_elem = ext_dom.documentElement

        sub_base_uri = os.path.join(elem.base_uri, os.path.dirname(href), '')
        sub_elem = to_prang_elem(sub_base_uri, doc_elem)

        if 'ns' in elem.attrs and 'ns' not in sub_elem.attrs:
            sub_elem.attrs['ns'] = elem.attrs['ns']

        simplify_4_2_whitespace(sub_elem)
        simplify_datalibrary_4_3_add(sub_elem)
        simplify_datalibrary_4_3_remove(sub_elem)
        simplify_type_value(sub_elem)
        simplify_href(sub_elem)
        simplify_externalRef(sub_elem)
        elem.name = sub_elem.name
        elem.attrs.clear()
        elem.attrs.update(sub_elem.attrs)
        for c in list(sub_elem.iter_children()):
            elem.append_child(c)

    else:
        for child in elem.iter_child_elems():
            simplify_externalRef(child)


def simplify_4_7_include(schema_el):
    def transform_includes(elem):
        for child in elem.iter_child_elems():
            simplify_4_7_include(child)

        if elem.name == 'include':
            href = elem.attrs['href']

            if href.startswith('http://') or href.startswith('https://'):
                ext_str = requests.get(href).text
            else:
                with open(href) as f:
                    ext_str = ''.join(f)

            ext_dom = xml.dom.minidom.parseString(ext_str)
            doc_elem = ext_dom.documentElement

            sub_base_uri = os.path.join(
                elem.base_uri, os.path.dirname(href), '')
            sub_elem = to_prang_elem(sub_base_uri, doc_elem)
            if sub_elem.name != 'grammar':
                raise Exception(
                    "The document element referred to by and 'include' must "
                    "be 'grammar'.")

            simplify_4_2_whitespace(sub_elem)
            simplify_datalibrary_4_3_add(sub_elem)
            simplify_datalibrary_4_3_remove(sub_elem)
            simplify_type_value(sub_elem)
            simplify_href(sub_elem)
            simplify_externalRef(sub_elem)
            simplify_4_7_include(sub_elem)

            def has_start_component(element):
                for child in element.iter_child_elems():
                    if child.name == 'start' or (
                            child.name == 'div' and
                            has_start_component(child)):
                        return True
                return False

            def remove_start_components(element):
                for child in list(element.iter_children()):
                    if child.name == 'start':
                        child.remove()
                    elif child.name == 'div':
                        remove_start_components(child)

            if has_start_component(elem):
                remove_start_components(sub_elem)

            defines = set()

            def find_define_components(element):
                for child in element.iter_child_elems():
                    if child.name == 'define':
                        defines.add(child.attrs['name'])
                    elif element.name == 'div':
                        find_define_components(child)

            find_define_components(elem)

            print("defines", defines)

            def remove_define_components(element):
                for child in list(element.iter_child_elems()):
                    if child.name == 'define' and \
                            child.attrs['name'] in defines:
                        child.remove()
                    elif child.name == 'div':
                        remove_define_components(child)

            remove_define_components(sub_elem)

            elem.name = 'div'
            del elem.attrs['href']

            sub_elem.name = 'div'
            elem.insert_child(0, sub_elem)

    transform_includes(schema_el)


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
            name_elem_name, elem.namespaces, elem.base_uri, name_elem_attrs)
        name_elem.append_child(attr_parts[-1])
        elem.insert_child(0, name_elem)
        del elem.attrs['name']

    for child in elem.iter_child_elems():
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

        for child in el.iter_child_elems():
            add_ns_attribute(child)

    add_ns_attribute(elem)

    def remove_ns_attribute(el):
        if (
                el.name.endswith(':name') or
                el.name not in ('name', 'nsName', 'value')) and \
                'ns' in el.attrs:
            del el.attrs['ns']

        for child in el.iter_child_elems():
            remove_ns_attribute(child)

    remove_ns_attribute(elem)


def simplify_qnames(elem):
    if elem.name.endswith(':name'):
        prefix, local_name = elem.name.split(':')
        elem.attrs['ns'] = elem.namespaces[prefix]
        elem.name = local_name

    for child in elem.iter_child_elems():
        simplify_qnames(child)


def simplify_4_11_div(el):
    for child in list(el.iter_child_elems()):
        simplify_4_11_div(child)

    if el.name == 'div':
        el_parent = el.parent
        idx = el.remove()
        for child in reversed(el.iter_children()):
            el_parent.insert_child(idx, child)


def simplify_4_12_num_children(schema_el):

    def first_batch(el):
        for child in list(el.iter_child_elems()):
            first_batch(child)

        if el.name in (
                'define', 'oneOrMore', 'zeroOrMore', 'optional', 'list',
                'mixed') and sum(1 for c in el.iter_children()) > 1:
            group_elem = PrangElement(
                'group', el.namespaces.copy(), el.base_uri, {})

            for child in list(el.iter_children()):
                group_elem.append_child(child)
            el.append_child(group_elem)

        elif el.name == 'element':
            if sum(1 for c in el.iter_children()) > 2:
                group_elem = PrangElement(
                    'group', el.namespaces.copy(), el.base_uri, {})
                for child in list(el.iter_children())[1:]:
                    group_elem.append_child(child)
                el.append_child(group_elem)

        elif el.name == 'except':
            if sum(1 for c in el.iter_children()) > 1:
                choice_elem = PrangElement(
                    'choice', el.namespaces, el.base_uri, {})
                for child in list(el.iter_children()):
                    choice_elem.append_child(child)
                el.append_child(choice_elem)

        elif el.name == 'attribute':
            if sum(1 for c in el.iter_children()) == 1:
                el.append_child(
                    PrangElement('text', el.namespaces, el.base_uri, {}))

    first_batch(schema_el)

    def second_batch(el):
        for child in list(el.iter_child_elems()):
            second_batch(child)

        if el.name in ('choice', 'group', 'interleave'):
            len_children = sum(1 for c in el.iter_children())
            if len_children == 1:
                child = list(el.iter_children())[0]
                el.name = child.name
                el.attrs.clear()
                el.attrs.update(child.attrs)
                child.remove()
                for c in list(child.iter_children()):
                    el.append_child(c)
            elif len_children > 2:
                new_elem = PrangElement(
                    el.name, el.namespaces, el.base_uri, {})
                for child in list(el.iter_children())[:-1]:
                    new_elem.append_child(child)
                el.insert_child(0, new_elem)

    second_batch(schema_el)


def simplify_4_13_mixed(elem):
    if elem.name == 'mixed':
        elem.name = 'interleave'
        elem.append_child(
            PrangElement('text', elem.namespaces.copy(), elem.base_uri, {}))
    for child in elem.iter_child_elems():
        simplify_4_13_mixed(child)


def simplify_4_14_optional(elem):
    if elem.name == 'optional':
        elem.name = 'choice'
        elem.append_child(
            PrangElement(
                'empty', elem.namespaces.copy(), elem.base_uri, {}))
    for child in elem.iter_child_elems():
        simplify_4_14_optional(child)


def simplify_4_15_zero_or_more(elem):
    if elem.name == 'zeroOrMore':
        elem.name = 'choice'
        one_or_more_elem = PrangElement(
            'oneOrMore', elem.namespaces.copy(), elem.base_uri, {})
        for child in elem.iter_children():
            one_or_more_elem.append_child(child)
        elem.append_child(one_or_more_elem)
        elem.append_child(
            PrangElement(
                'empty', elem.namespaces.copy(), elem.base_uri, {}))

    for child in elem.iter_child_elems():
        simplify_4_15_zero_or_more(child)


def find_descendent(elem, names):
    for child in elem.iter_child_elems():
        if child.name in names:
            return child
        else:
            desc = find_descendent(child, names)
            if desc is not None:
                return desc
    return None


def simplify_4_16_constraints(elem):
    if elem.name == 'except':
        if elem.parent.name == 'anyName' and \
                find_descendent(elem, ('anyName',)) is not None:
            raise Exception(
                "An except element that is a child of an anyName element "
                "must not have any anyName descendant elements.")
        if elem.parent.name == 'nsName' and \
                find_descendent(elem, ('nsName', 'anyName')) is not None:
            raise Exception(
                "An except element that is a child of an nsName element "
                "must not have any nsName or anyName descendant elements.")

    if elem.name == 'attribute' and \
            sum(1 for c in elem.iter_children()) > 0:
        first_child = list(elem.iter_children())[0]
        if first_child.name == 'name':
            found_elem = first_child
        else:
            found_elem = find_descendent(first_child, ('name', ))

        if found_elem is not None and \
                found_elem.attrs.get('ns', None) == '' and \
                '.'.join(found_elem.iter_children()).strip() == 'xmlns':

            raise Exception(
                "A name element that occurs as the first child of an "
                "attribute element or as the descendant of the first "
                "child of an attribute element and that has an ns "
                "attribute with value equal to the empty string must not "
                "have content equal to xmlns.")

        if first_child.name in ('name', 'nsName'):
            found_elem = first_child
        else:
            found_elem = find_descendent(first_child, ('name', 'nsName'))

        if found_elem is not None and \
                found_elem.attrs.get('ns', None) == \
                'http://www.w3.org/2000/xmlns':

            raise Exception(
                "A name or nsName element that occurs as the first child "
                "of an attribute element or as the descendant of the "
                "first child of an attribute element must not have an ns "
                "attribute with value http://www.w3.org/2000/xmlns.")

    for child in elem.iter_child_elems():
        simplify_4_16_constraints(child)


def simplify_4_17_combine(elem):
    if elem.name == 'grammar':
        combs = {'define': {}, 'start': {}}
        for child in list(elem.iter_children()):
            if child.name in combs:
                comb_names = combs[child.name]
                if child.name == 'define':
                    comb_name = child.attrs['name']
                else:
                    comb_name = ''
                if comb_name in comb_names:
                    comb_child = comb_names[comb_name]
                    if 'combine' in comb_child.attrs:
                        comb_elem_name = comb_child.attrs['combine']
                    else:
                        comb_elem_name = child.attrs['combine']
                    comb_elem = PrangElement(
                        comb_elem_name, elem.namespaces.copy(),
                        elem.base_uri, {})

                    for c in list(
                            chain(
                                comb_child.iter_children(),
                                child.iter_children())):
                        comb_elem.append_child(c)

                    comb_child.append_child(comb_elem)
                    child.remove()
                else:
                    comb_names[comb_name] = child

        for cat in combs.keys():
            for comb_child in combs[cat].values():
                if 'combine' in comb_child.attrs:
                    del comb_child.attrs['combine']

    for child in elem.iter_child_elems():
        simplify_4_17_combine(child)


def simplify_4_18_grammar(schema_el):
    if schema_el.name != 'grammar':
        pattern_el = PrangElement(
            schema_el.name, schema_el.namespaces.copy(), schema_el.base_uri,
            schema_el.attrs.copy())
        for child in list(schema_el.iter_children()):
            pattern_el.append_child(child)

        schema_el.name = 'grammar'
        schema_el.attrs.clear()
        for k, v in list(pattern_el.attrs.items()):
            if k == 'xmlns' or k.startswith('xmlns:'):
                schema_el.attrs[k] = v
                del pattern_el.attrs[k]

        start_el = PrangElement(
            'start', pattern_el.namespaces.copy(), pattern_el.base_uri, {})
        schema_el.append_child(start_el)
        start_el.append_child(pattern_el)

    names = set()
    dup_map = {}

    def find_defs(el, grammar_count):
        if el.name == 'grammar':
            grammar_count += 1
        elif el.name == 'define':
            def_name = el.attrs['name']
            if def_name in names:
                new_name = def_name + '_g'
                while new_name in names:
                    new_name += '_g'
                names.add(new_name)
                dup_map[(def_name, grammar_count)] = new_name
                el.attrs['name'] = new_name
            else:
                names.add(def_name)
        for c in list(el.iter_child_elems()):
            find_defs(c, grammar_count)

    find_defs(schema_el, 0)

    def rename_refs(el, grammar_count):
        if el.name == 'grammar':
            grammar_count += 1
        elif el.name == 'ref':
            key = (el.attrs['name'], grammar_count)
            if key in dup_map:
                el.attrs['name'] = dup_map[key]
        elif el.name == 'parentRef':
            key = (el.attrs['name'], grammar_count - 1)
            if key in dup_map:
                el.attrs['name'] = dup_map[key]

        for c in list(el.iter_child_elems()):
            rename_refs(c, grammar_count)

    rename_refs(schema_el, 0)

    def handle_refs(el):
        for c in list(el.iter_child_elems()):
            handle_refs(c)

        if el.name == 'parentRef':
            el.name = 'ref'
        elif el.name == 'grammar' and el.parent is not None:
            el_parent = el.parent
            grammar_children = list(el.iter_children())
            grammar_pattern = list(grammar_children[0].iter_children())[0]
            grammar_defines = grammar_children[1:]
            i = el.remove()
            el_parent.insert_child(i, grammar_pattern)
            top_grammar = el_parent
            while top_grammar.parent is not None:
                top_grammar = top_grammar.parent
            for c in grammar_defines:
                top_grammar.append_child(c)

    handle_refs(schema_el)
    schema_el.attrs['xmlns'] = RELAXNG_NS

    # Make sure start element is first
    for i, c in enumerate(list(schema_el.iter_children())):
        if c.name == 'start' and i != 0:
            c.remove()
            schema_el.insert_child(0, c)


def simplify_4_19_define_ref(grammar_el):
    refs = set()
    defs = set(c for c in grammar_el.iter_children() if c.name == 'define')

    def find_refs(elem):
        if elem.name == 'ref':
            refs.add(elem)
            elem.reachable_elem = None
            elem.reachable_name = None
            parent = elem.parent
            while parent is not None:
                if parent.name == 'start':
                    elem.reachable_elem = 'start'
                elif parent.name == 'define':
                    elem.reachable_elem = 'define'
                    elem.reachable_name = parent.attrs['name']
                parent = parent.parent

        for child in reversed(list(elem.iter_child_elems())):
            find_refs(child)

    find_refs(grammar_el)

    # Find names of reachable defines
    reachable = set()

    reachable_found = True
    while reachable_found:
        reachable_found = False
        for elem in list(refs):
            if elem.reachable_elem == 'start' or (
                    elem.reachable_elem == 'define' and
                    elem.reachable_name in reachable) and \
                    elem.attrs['name'] not in reachable:
                reachable.add(elem.attrs['name'])
                refs.remove(elem)
                reachable_found = True

    # Remove unreachable defines
    for elem in set(defs):
        if elem.attrs['name'] not in reachable:
            elem.remove()
            defs.remove(elem)

    def find_elements(el):
        if el.name == 'element' and el.parent.name != 'define':
            def_name = 'c'
            while def_name in reachable:
                def_name += '_c'
            reachable.add(def_name)
            ref_el = PrangElement(
                'ref', el.parent.base_uri, el.parent.namespaces.copy(),
                {'name': def_name})
            el_parent = el.parent
            idx = el.remove()
            el_parent.insert_child(idx, ref_el)
            def_el = PrangElement(
                'define', grammar_el.base_uri,
                grammar_el.namespaces.copy(), {'name': def_name})
            grammar_el.append_child(def_el)
            def_el.append_child(el)

        for child in el.iter_child_elems():
            find_elements(child)

    find_elements(grammar_el)

    # Expandable refs
    defs = {}
    for child in grammar_el.iter_children():
        if child.name == 'define':
            if sum(1 for c in child.iter_child_elems('element')) == 0:
                defs[child.attrs['name']] = child

    def find_expandable_refs(subs, el):
        to_recurse = None
        if el.name == 'ref':
            has_anc = False
            parent = el.parent
            while parent is not None and not has_anc:
                if parent.name in ('start', 'element'):
                    has_anc = True
                parent = parent.parent
            ref_name = el.attrs['name']
            if has_anc and ref_name in defs and ref_name not in subs:
                subs = subs.copy()
                subs.add(ref_name)
                el_parent = el.parent
                idx = el.remove()
                to_recurse = []
                for c in defs[ref_name].iter_children():
                    new_c = copy.deepcopy(c)
                    el_parent.insert_child(idx, new_c)
                    to_recurse.append(new_c)

        if to_recurse is None:
            to_recurse = list(el.iter_child_elems())

        for child in to_recurse:
            find_expandable_refs(subs, child)

    find_expandable_refs(set(), grammar_el)

    # Remove expandable defs
    for el in defs.values():
        el.remove()


def simplify_4_20_not_allowed(grammar_el):

    def not_allowed_elems(el):
        if el.name in (
                'attribute', 'list', 'group', 'interleave',
                'oneOrMore') and sum(
                    1 for c in el.iter_child_elems()
                    if c.name == 'notAllowed') > 0:

            for c in list(el.iter_children()):
                c.remove()

            el.name = 'notAllowed'
            el.attrs.clear()
        elif el.name == 'choice':
            num_not_alloweds = sum(
                1 for c in el.iter_child_elems() if c.name == 'notAllowed')
            if num_not_alloweds == 2:
                for c in list(el.iter_children()):
                    c.remove()
                el.name = 'notAllowed'
                el.attrs.clear()
            elif num_not_alloweds == 1:
                allowed = None
                for c in list(el.iter_children()):
                    c.remove()
                    if c.name != 'notAllowed':
                        allowed = c
                el.name = allowed.name
                el.attrs.clear()
                el.attrs.update(allowed.attrs)
                for c in allowed.iter_children():
                    el.append_child(c)
        elif el.name == 'except' and sum(
                1 for c in el.iter_child_elems()
                if c.name == 'notAllowed') > 0:
            for c in list(el.iter_children()):
                c.remove()

            el.name = 'notAllowed'
            el.attrs.clear()

        for child in el.iter_child_elems():
            not_allowed_elems(child)

    not_allowed_elems(grammar_el)

    refs = set()
    defs = set()

    def find_defs_refs(elem):
        if elem.name == 'ref':
            refs.add(elem)
            elem.reachable_elem = None
            elem.reachable_name = None
            parent = elem.parent
            while parent is not None:
                if parent.name == 'start':
                    elem.reachable_elem = 'start'
                elif parent.name == 'define':
                    elem.reachable_elem = 'define'
                    elem.reachable_name = parent.attrs['name']
                parent = parent.parent
        elif elem.name == 'define':
            defs.add(elem)
        for child in elem.iter_child_elems():
            find_defs_refs(child)

    find_defs_refs(grammar_el)

    # Find names of reachable defines
    reachable = set()

    reachable_found = True
    while reachable_found:
        reachable_found = False
        for elem in list(refs):
            if elem.reachable_elem == 'start' or (
                    elem.reachable_elem == 'define' and
                    elem.reachable_name in reachable) and \
                    elem.attrs['name'] not in reachable:
                reachable.add(elem.attrs['name'])
                refs.remove(elem)
                reachable_found = True

    # Remove unreachable defines
    for elem in defs:
        if elem.attrs['name'] not in reachable:
            elem.remove()


def simplify_4_21_empty(el):
    for c in list(el.iter_child_elems()):
        simplify_4_21_empty(c)

    num_empties = sum(1 for e in el.iter_child_elems('empty'))

    if el.name in ('group', 'interleave', 'choice') and num_empties == 2:
        el.name = 'empty'
        el.attrs.clear()
        for e in list(el.iter_children()):
            e.remove()
    elif el.name in ('group', 'interleave') and num_empties == 1:
        for child in el.iter_child_elems():
            if child.name != 'empty':
                break
        parent = el.parent
        idx = el.remove()
        parent.insert_child(idx, child)
    elif el.name == 'choice' and list(
            el.iter_child_elems())[1].name == 'empty':
        first_child = next(el.iter_child_elems())
        first_child.remove()
        el.append_child(first_child)
    elif el.name == 'oneOrMore' and num_empties > 0:
        el.name = 'empty'
        el.attrs.clear()
        for e in list(el.iter_children()):
            e.remove()


def simplify(schema_el):
    # print("before 4.2", schema_el)
    simplify_4_2_whitespace(schema_el)
    # print("before 4.3 add", schema_el)
    simplify_datalibrary_4_3_add(schema_el)
    # print("before 4.3 remove", schema_el)
    simplify_datalibrary_4_3_remove(schema_el)
    # print("before value", schema_el)
    simplify_type_value(schema_el)
    simplify_href(schema_el)
    simplify_externalRef(schema_el)
    simplify_4_7_include(schema_el)
    # print("after include", schema_el)
    simplify_name_attribute(schema_el)
    # print("before ns attribute", schema_el)
    simplify_ns_attribute(schema_el)
    # print("before qnames attribute", schema_el)
    simplify_qnames(schema_el)
    # print("before 4.11", schema_el)
    simplify_4_11_div(schema_el)
    # print("after 4.11", schema_el)
    simplify_4_12_num_children(schema_el)
    # print("after 4.12", schema_el)
    simplify_4_13_mixed(schema_el)
    simplify_4_14_optional(schema_el)
    simplify_4_15_zero_or_more(schema_el)
    simplify_4_16_constraints(schema_el)
    simplify_4_17_combine(schema_el)
    # print("after 4.17", schema_el)
    simplify_4_18_grammar(schema_el)
    # print("after 4.18", schema_el)
    simplify_4_19_define_ref(schema_el)
    # print("after 4.19 def ref", schema_el)
    simplify_4_20_not_allowed(schema_el)
    # print("before simplifying empty", schema_el)
    simplify_4_21_empty(schema_el)
