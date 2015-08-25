from six import text_type, iteritems
import xml.dom
import binascii
import urllib.parse
import requests
from itertools import chain, islice
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


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
                sorted([(k, v) for k, v in iteritems(self.attrs)]):
            out.append(
                '\n' + wspace + ' ' * 4 + attr_name + '="' + attr_value + '"')
        if sum(1 for c in self.iter_children()) > 0:
            child_wspace = wspace + ' ' * 2
            out.append('>\n')
            for child in self.iter_children():
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
        if not isinstance(child, (PrangElement, text_type)):
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
        for child in self.iter_child_elements():
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

    def iter_child_elements(self, names=None):
        if names is None:
            return (c for c in self._children if isinstance(c, PrangElement))
        else:
            return (
                c for c in self._children
                if isinstance(c, PrangElement) and c.name in names)

    def iter_children(self):
        return self._children

    '''
    def check_integrity(self):
        for
    '''

NATIVE_NAMESPACES = (
    None, 'http://relaxng.org/ns/structure/1.0',
    'http://www.w3.org/2000/xmlns', 'http://www.w3.org/XML/1998/namespace')


def to_prang_elem(parent, elem_dom):
    elem_dom.normalize()

    if parent is None:
        namespaces = {'': '', 'xml': 'http://www.w3.org/XML/1998/namespace'}
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

    elem = PrangElement(elem_dom.localName, namespaces, base_uri, attrs)
    for child in elem_dom.childNodes:
        node_type = child.nodeType
        if node_type == xml.dom.Node.ELEMENT_NODE and \
                child.namespaceURI in NATIVE_NAMESPACES:
            elem.append_child(to_prang_elem(elem, child))
        elif node_type == xml.dom.Node.TEXT_NODE:
            elem.append_child(child.data)

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


def simplify_4_2_whitespace(elem):
    if elem.name == 'name':
        for attr_name, attr_value in list(iteritems(elem.attrs)):
            if attr_name in ('name', 'type', 'combine'):
                elem.attrs[attr_name] = attr_value.strip()

    if elem.name not in ('value', 'param'):
        for child in list(elem.iter_children()):
            if isinstance(child, text_type) and len(child.split()) == 0:
                elem.remove_child(child)

    for child in elem.iter_child_elements():
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
            for name, value in iteritems(parent.attrs):
                if name == 'datatypeLibrary':
                    datatypeLibrary = value
            parent = parent.parent
        if datatypeLibrary is None:
            datatypeLibrary = ''
        attrs['datatypeLibrary'] = datatypeLibrary

    for child in elem.iter_child_elements():
        simplify_datalibrary_4_3_add(child)


def simplify_datalibrary_4_3_remove(elem):
    if elem.name not in ('data', 'value') and 'datatypeLibrary' in elem.attrs:
        del elem.attrs['datatypeLibrary']

    for child in elem.iter_child_elements():
        simplify_datalibrary_4_3_remove(child)


def simplify_type_value(elem):
    if elem.name == 'value' and 'type' not in elem.attrs:
        elem.attrs['type'] = 'token'
        elem.attrs['datatypeLibrary'] = ''

    for child in elem.iter_child_elements():
        simplify_type_value(child)


def simplify_href(elem):
    if elem.name in ('externalRef', 'include'):
        elem.attrs['href'] = urllib.parse.urljoin(
            elem.base_uri, xlink_encode(elem.attrs['href']))

    for child in elem.iter_child_elements():
        simplify_href(child)


def simplify_externalRef(elem):
    if elem.name == 'externalRef':
        href = elem.attrs['href']

        r = requests.get(href)
        ext_dom = xml.dom.minidom.parseString(r.text)
        doc_elem = ext_dom.documentElement

        sub_elem = to_prang_elem(doc_elem)

        if 'ns' in elem.attrs and 'ns' not in sub_elem.attrs:
            sub_elem.attrs['ns'] = elem.attrs['ns']

        simplify_4_2_whitespace(sub_elem)
        simplify_datalibrary_4_3_add(sub_elem)
        simplify_datalibrary_4_3_remove(sub_elem)
        simplify_type_value(sub_elem)
        simplify_href(sub_elem)
        simplify_externalRef(sub_elem)
        idx = elem.remove()
        elem.insert_child(idx, sub_elem)

    else:
        for child in elem.iter_child_elements():
            simplify_externalRef(child)


def simplify_include(elem):
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

        simplify_4_2_whitespace(sub_elem)
        simplify_datalibrary_4_3_add(sub_elem)
        simplify_datalibrary_4_3_remove(sub_elem)
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
            for child in list(element.children):
                if child.name == 'start':
                    child.remove()
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
            for child in list(element.children):
                if child.name == 'define' and child.attrs['name'] in defines:
                    child.remove()
                elif child.name == 'div':
                    remove_define_components(child)

        remove_define_components(sub_elem)

        elem.name = 'div'
        del elem.attrs['href']

        sub_elem.name = 'div'
        elem.children.insert(0, sub_elem)

    else:
        for child in elem.iter_child_elements():
            simplify_include(child)


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

    for child in elem.iter_child_elements():
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

        for child in el.iter_child_elements():
            add_ns_attribute(child)

    add_ns_attribute(elem)

    def remove_ns_attribute(el):
        if (
                el.name.endswith(':name') or
                el.name not in ('name', 'nsName', 'value')) and \
                'ns' in el.attrs:
            del el.attrs['ns']

        for child in el.iter_child_elements():
            remove_ns_attribute(child)

    remove_ns_attribute(elem)


def simplify_qnames(elem):
    if elem.name.endswith(':name'):
        prefix, local_name = elem.name.split(':')
        elem.attrs['ns'] = elem.namespaces[prefix]
        elem.name = local_name

    for child in elem.iter_child_elements():
        simplify_qnames(child)


def simplify_4_11_div(el):
    if el.name == 'div':
        el_parent = el.parent
        idx = el.remove()
        for child in reversed(el.iter_children()):
            el_parent.insert_child(idx, child)
        recurse_elem = el_parent
    else:
        recurse_elem = el

    for child in list(recurse_elem.iter_child_elements()):
        simplify_4_11_div(child)


def simplify_4_12_num_children(root_el):
    def alter(el):
        if el.name in (
                'define', 'oneOrMore', 'zeroOrMore', 'optional', 'list',
                'mixed') and sum(1 for c in el.iter_children()) > 1:
            group_elem = PrangElement(
                'group', el.namespaces.copy(), el.base_uri, {})

            for child in list(el.iter_children()):
                group_elem.append_child(child)
            el.append_child(group_elem)
            return True

        elif el.name == 'element':
            if sum(1 for c in el.iter_children()) > 2:
                group_elem = PrangElement(
                    'group', el.namespaces, el.base_uri, {})
                for child in islice(el.iter_children(), 2):
                    group_elem.append_child(child)
                el.append_child(group_elem)
                return True

        elif el.name == 'except':
            if sum(1 for c in el.iter_children()) > 1:
                choice_elem = PrangElement(
                    'choice', el.namespaces, el.base_uri, {})
                for child in islice(el.iter_children(), 1):
                    choice_elem.append_child(child)
                el.append_child(choice_elem)
                return True

        elif el.name == 'attribute':
            if sum(1 for c in el.iter_children()) == 1:
                el.append_child(
                    PrangElement('text', el.namespaces, el.base_uri, {}))
                return True

        elif el.name in ('choice', 'group', 'interleave'):
            len_children = sum(1 for c in el.iter_children())
            if len_children == 1:
                elem_parent = el.parent
                idx = el.remove()
                elem_parent.insert_child(idx, list(el.iter_children())[0])
                return True
            elif len_children > 2:
                new_elem = PrangElement(
                    el.name, el.namespaces, el.base_uri, {})
                for child in list(el.iter_children())[:-1]:
                    new_elem.append_child(child)
                el.insert_child(0, new_elem)
                return True

        for child in list(el.iter_child_elements()):
            alter(child)

        return False

    while alter(root_el):
        pass


def simplify_4_13_mixed(elem):
    if elem.name == 'mixed':
        elem.name = 'interleave'
        elem.append_child(
            PrangElement('text', elem.namespaces.copy(), elem.base_uri, {}))
    for child in elem.iter_child_elements():
        simplify_4_13_mixed(child)


def simplify_4_14_optional(elem):
    if elem.name == 'optional':
        elem.name = 'choice'
        elem.append_child(
            PrangElement('empty', elem.namespaces.copy(), elem.base_uri, {}))
    for child in elem.iter_child_elements():
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
            PrangElement('empty', elem.namespaces.copy(), elem.base_uri, {}))

    for child in elem.iter_child_elements():
        simplify_4_15_zero_or_more(child)


def find_descendent(elem, names):
    for child in elem.iter_child_elements():
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
                "An except element that is a child of an anyName element must "
                "not have any anyName descendant elements.")
        if elem.parent.name == 'nsName' and \
                find_descendent(elem, ('nsName', 'anyName')) is not None:
            raise Exception(
                "An except element that is a child of an nsName element must "
                "not have any nsName or anyName descendant elements.")

    if elem.name == 'attribute' and sum(1 for c in elem.iter_children()) > 0:
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

    for child in elem.iter_child_elements():
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
                        comb_elem_name, elem.namespaces.copy(), elem.base_uri,
                        {})

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

    for child in elem.iter_child_elements():
        simplify_4_17_combine(child)


def simplify_4_18_grammar(elem):
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

        def find_defs(el):
            if el.name == 'define':
                def_name = el.attrs['name']
                if def_name in names:
                    dups.append(el)
                else:
                    names.add(def_name)
            for c in el.iter_child_elements():
                find_defs(c)

        find_defs(elem)

        for dup_el in dups:
            dup_name = dup_el.name
            new_name = dup_name
            while new_name in names:
                new_name += '_'
            names.add(new_name)
            dup_el.name = new_name

            grammar_count = 0

            def find_refs(el):
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

                for c in el.iter_child_elements():
                    find_refs(c)
            find_refs(dup_el)
            elem.append_child(dup_el)

        def handle_refs(el):
            if el.name == 'parentRef':
                el.name = 'ref'
            elif el.name == 'grammar' and el.parent is not None:
                i = el.remove()
                el.parent.insert_child(i, el.children[0])

            for c in [el.iter_child_elements()]:
                handle_refs(c)

    for c in elem.iter_child_elements():
        simplify_4_18_grammar(c)


def find_nameless_elements(el):
    if el.name == 'element' and 'name' not in el.attrs:
        print(el)
        raise Exception("Nameless element!")
    for child in el.iter_child_elements():
        find_nameless_elements(child)


def simplify_4_19_define_ref(grammar_el):
    refs = set()
    defs = set()

    def find_defs_refs(elem):
        if elem.name == 'ref':
            refs.add(elem)
        elif elem.name == 'define':
            defs.add(elem)
        for child in reversed(list(elem.iter_child_elements())):
            find_defs_refs(child)

    find_defs_refs(grammar_el)

    # Find names of reachable defines
    reachable = set()

    reachable_found = True
    while reachable_found:
        reachable_found = False
        for elem in list(refs):
            parent = elem.parent
            while parent is not None and not reachable_found:
                if parent.name == 'start' or (
                        parent.name == 'define' and
                        parent.attrs['name'] in reachable) and \
                        elem.attrs['name'] not in reachable:
                    reachable.add(elem.attrs['name'])
                    refs.remove(elem)
                    reachable_found = True
                parent = parent.parent

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
                'define', grammar_el.base_uri, grammar_el.namespaces.copy(),
                {'name': def_name})
            grammar_el.append_child(def_el)
            def_el.append_child(el)

        for child in el.iter_child_elements():
            find_elements(child)

    find_elements(grammar_el)

    # Expandable refs
    defs = {}
    for child in grammar_el.iter_children():
        if child.name == 'define':
            if sum(1 for c in child.iter_child_elements('element')) == 0:
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
                    el_parent.insert_child(idx, c)
                    to_recurse.append(c)

        if to_recurse is None:
            to_recurse = list(el.iter_child_elements())

        for child in to_recurse:
            find_expandable_refs(subs, child)

    find_expandable_refs(set(), grammar_el)

    # Remove expandable defs
    for el in defs.values():
        el.remove()


def simplify_4_20_not_allowed(grammar_el):

    def not_allowed_elems(el):
        if el.name in (
                'attribute', 'list', 'group', 'interleave', 'oneOrMore') and \
                sum(
                    1 for c in el.iter_child_elements()
                    if c.name == 'notAllowed') > 0:

            for c in list(el.iter_children()):
                c.remove()

            el.name = 'notAllowed'
            el.attrs.clear()
        elif el.name == 'choice':
            num_not_alloweds = sum(
                1 for c in el.iter_child_elements() if c.name == 'notAllowed')
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
                1 for c in el.iter_child_elements()
                if c.name == 'notAllowed') > 0:
            for c in list(el.iter_children()):
                c.remove()

            el.name = 'notAllowed'
            el.attrs.clear()

        for child in el.iter_child_elements():
            not_allowed_elems(child)

    not_allowed_elems(grammar_el)

    refs = set()
    defs = set()

    def find_defs_refs(elem):
        if elem.name == 'ref':
            refs.add(elem)
        elif elem.name == 'define':
            defs.add(elem)
        for child in elem.iter_child_elements():
            find_defs_refs(child)

    find_defs_refs(grammar_el)

    # Find names of reachable defines
    reachable = set()

    reachable_found = True
    while reachable_found:
        reachable_found = False
        for elem in list(refs):
            parent = elem.parent
            parents = set()
            while parent is not None and not reachable_found:
                if parent in parents:
                    print(parent.name)
                    raise Exception("parent in parents!")
                else:
                    parents.add(parent)
                if parent.name == 'start' or (
                        parent.name == 'define' and
                        parent.attrs['name'] in reachable):
                    reachable.add(elem.attrs['name'])
                    refs.remove(elem)
                    reachable_found = True
                parent = parent.parent

    # Remove unreachable defines
    for elem in defs:
        if elem.attrs['name'] not in reachable:
            elem.remove()


def simplify(schema_elem):
    simplify_4_2_whitespace(schema_elem)
    simplify_datalibrary_4_3_add(schema_elem)
    simplify_datalibrary_4_3_remove(schema_elem)
    simplify_type_value(schema_elem)
    simplify_href(schema_elem)
    simplify_externalRef(schema_elem)
    simplify_include(schema_elem)
    simplify_name_attribute(schema_elem)
    simplify_ns_attribute(schema_elem)
    simplify_qnames(schema_elem)
    simplify_4_11_div(schema_elem)
    simplify_4_12_num_children(schema_elem)
    simplify_4_13_mixed(schema_elem)
    simplify_4_14_optional(schema_elem)
    simplify_4_15_zero_or_more(schema_elem)
    simplify_4_16_constraints(schema_elem)
    simplify_4_17_combine(schema_elem)
    simplify_4_18_grammar(schema_elem)
    simplify_4_19_define_ref(schema_elem)
    simplify_4_20_not_allowed(schema_elem)
