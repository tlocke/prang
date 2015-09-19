from functools import partial
from collections import namedtuple
import xml.dom


class PrangNode():
    def __init__(self, attrs, children):
        self._attrs = attrs
        self._children = tuple(children)

    @property
    def attrs(self):
        return self._attrs

    @property
    def children(self):
        return self._children


class SchemaElement():
    def __init__(self, atts, *children):
        self.defs = None
        self.ref_name = None
        self.element = None
        self._atts = atts

        # Check that all children are either strings or SchemaElements
        for c in children:
            if not isinstance(c, (str, SchemaElement)):
                raise Exception("The children must be strings or Elements", c)
        self._children = children

    def _resolve(self):
        if self.element is None:
            if self.ref_name is None:
                self.element = self
            else:
                self.element = self.defs[self.ref_name]

    @property
    def atts(self):
        self._resolve()
        return self.element._atts

    @property
    def children(self):
        self._resolve()
        return self.element._children

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.ref_name is None:
            args = [k + '=' + repr(v) for k, v in self._atts.items()]
            args += [repr(a) for a in self._children]
            return self.__class__.__name__ + "(" + ', '.join(args) + ")"
        else:
            return "Ref(" + self.ref_name + ")"


class Element(SchemaElement):
    def __init__(self, *children):
        SchemaElement.__init__(self, {}, *children)


class Choice(SchemaElement):
    def __init__(self, p1, p2):
        SchemaElement.__init__(self, {}, p1, p2)


class Start(SchemaElement):
    def __init__(self, p):
        SchemaElement.__init__(self, {}, p)


class Name(SchemaElement):
    def __init__(self, atts, nc):
        SchemaElement.__init__(self, atts, nc)


class Data(SchemaElement):
    def __init__(self, atts, *children):
        SchemaElement.__init__(self, atts, *children)


class NsName(SchemaElement):
    def __init__(self, atts, *children):
        SchemaElement.__init__(self, atts, *children)


class Except(SchemaElement):
    def __init__(self, *children):
        SchemaElement.__init__(self, {}, *children)


class Empty(SchemaElement):
    def __init__(self):
        SchemaElement.__init__(self, {})


class List(SchemaElement):
    def __init__(self, p):
        SchemaElement.__init__(self, {}, p)


class AnyName(SchemaElement):
    def __init__(self, *children):
        SchemaElement.__init__(self, {}, *children)


class Group(SchemaElement):
    def __init__(self, p1, p2):
        SchemaElement.__init__(self, {}, p1, p2)


class Text(SchemaElement):
    def __init__(self):
        SchemaElement.__init__(self, {})


class Value(SchemaElement):
    def __init__(self, atts, p):
        SchemaElement.__init__(self, atts, p)


class Attribute(SchemaElement):
    def __init__(self, *children):
        SchemaElement.__init__(self, {}, *children)


class OneOrMore(SchemaElement):
    def __init__(self, *children):
        SchemaElement.__init__(self, {}, *children)


class Interleave(SchemaElement):
    def __init__(self, p1, p2):
        SchemaElement.__init__(self, {}, p1, p2)


class Define(SchemaElement):
    def __init__(self, atts, p):
        SchemaElement.__init__(self, atts, p)


class Grammar(SchemaElement):
    def __init__(self, *children):
        SchemaElement.__init__(self, {}, *children)


class NotAllowed(SchemaElement):
    def __init__(self, error_schema=None, error_doc=None, error_message=None):
        SchemaElement.__init__(self, {})
        self.error_schema = error_schema
        self.error_doc = error_doc
        self.error_message = error_message


class After(SchemaElement):
    def __init__(self, p1, p2):
        SchemaElement.__init__(self, {}, p1, p2)


class Ref():
    def __init__(self, defs, ref_name):
        self.defs = defs
        self.ref_name = ref_name
        self.node = None

    def _resolve(self):
        if self.node is None:
            self.node = self.defs[self.ref_name]

    @property
    def name(self):
        self._resolve()
        return self.node.name

    @property
    def atts(self):
        self._resolve()
        return self.node.atts

    @property
    def children(self):
        self._resolve()
        return self.node.children

    def __str__(self):
        return "Ref(" + self.ref_name + ")"

    def __repr__(self):
        return "Ref(" + self.ref_name + ")"

EMPTY = Empty()
TEXT = Text()


def typify(grammar_el):
    defs = {}

    def freeze(el):
        if isinstance(el, str):
            return el
        else:
            children = tuple(freeze(c) for c in el.iter_children())
            if el.name == 'ref':
                elem = Element()
                elem.defs = defs
                elem.ref_name = el.attrs['name']
                return elem
            elif el.name == 'element':
                return Element(*children)
            elif el.name == 'choice':
                return Choice(*children)
            elif el.name == 'start':
                return Start(*children)
            elif el.name == 'name':
                return Name(el.attrs, *children)
            elif el.name == 'empty':
                return EMPTY
            elif el.name == 'text':
                return TEXT
            elif el.name == 'value':
                return Value(el.attrs, *children)
            elif el.name == 'data':
                return Data(el.attrs, *children)
            elif el.name == 'nsName':
                return NsName(el.attrs, *children)
            elif el.name == 'attribute':
                return Attribute(*children)
            elif el.name == 'group':
                return Group(*children)
            elif el.name == 'except':
                return Except(*children)
            elif el.name == 'anyName':
                return AnyName(*children)
            elif el.name == 'oneOrMore':
                return OneOrMore(*children)
            elif el.name == 'interleave':
                return Interleave(*children)
            elif el.name == 'define':
                return Define(el.attrs, *children)
            elif el.name == 'grammar':
                return Grammar(*children)
            elif el.name == 'list':
                return List(*children)
            else:
                raise Exception("element name not recognized " + el.name)

    grammar_el = freeze(grammar_el)
    for el in grammar_el.children[1:]:
        defs[el.atts['name']] = el.children[0]
    return grammar_el


def contains(nc, n):
    if isinstance(nc, AnyName):
        if len(nc.children) == 0:
            return True
        else:
            return not contains(nc.children[0].children[0], n)
    elif isinstance(nc, NsName):
        if nc.atts['ns'] == n.ns:
            if len(nc.children) == 0:
                return True
            else:
                return not contains(nc.children[0].children[0], n)
        else:
            return False
    elif isinstance(nc, Name):
        print("It's a name in contains")
        print("nc", nc)
        print("n", n)
        return (nc.atts['ns'], nc.children[0]) == n
    elif isinstance(nc, Choice):
        return any(contains(nc, n) for nc in nc.children)
    return False


def nullable(p):
    if isinstance(p, (Group, Interleave)):
        return all(nullable(c) for c in p.children)
    elif isinstance(p, Choice):
        return any(nullable(c) for c in p.children)
    elif isinstance(p, OneOrMore):
        return nullable(p.children[0])
    elif isinstance(p, (Empty, Text)):
        return True
    else:
        return False


def child_deriv(p, s):
    print("in child deriv, pattern ", p)
    print("in child deriv, node ", s)

    if isinstance(s, str):
        return text_deriv(p, s)
    else:
        print("p1 is", p)
        p1 = start_tag_open_deriv(p, s.qn)
        print("p1 is", p1)
        check_choice(p1)
        p2 = atts_deriv(p1, s.atts)
        print("p2 is", p2)
        check_choice(p2)
        p3 = start_tag_close_deriv(p2)
        print("p3 is", p3)
        check_choice(p3)
        p4 = children_deriv(p3, s.children)
        check_choice(p4)
        print("p4 is", p4)
        p5 = end_tag_deriv(p4)
        print("p5 is", p5)
        return p5


def choice(p1, p2):
    if isinstance(p2, NotAllowed):
        return p1
    elif isinstance(p1, NotAllowed):
        return p2
    else:
        return Choice(p1, p2)


class NotAllowedException(Exception):
    pass


def check_choice(el):
    if isinstance(el, Choice):
        for c in el.children:
            check_choice(c)

        if len(el.children) != 2:
            raise Exception("Check choice fail!", el)


def start_tag_open_deriv(p, qn):
    print("in start tag open deriv, pattern", p)
    print("in start tag open deriv, qn", qn)

    if isinstance(p, Choice):
        p1, p2 = p.children
        res = choice(
            start_tag_open_deriv(p1, qn),
            start_tag_open_deriv(p2, qn))
        check_choice(res)
        return res
    elif isinstance(p, Element):
        print("in open deriv, it's an element.")
        nc, top = p.children
        print("nc", nc)
        print("top", top)
        if contains(nc, qn):
            return after(top, EMPTY)
        else:
            return NotAllowed(p, qn)
    elif isinstance(p, Interleave):
        p1, p2 = p.children
        return choice(
            apply_after(
                partial(flip(interleave), p2), start_tag_open_deriv(p1, qn)),
            apply_after(partial(interleave, p1), start_tag_open_deriv(p2, qn)))
    elif isinstance(p, OneOrMore):
        p1 = p.children[0]
        return apply_after(
            partial(flip(group), choice(p1, EMPTY)),
            start_tag_open_deriv(p1, qn))
    elif isinstance(p, Group):
        p1, p2 = p.children
        x = apply_after(
            partial(flip(group), p2), start_tag_open_deriv(p1, qn))
        if nullable(p1):
            return choice(x, start_tag_open_deriv(p2, qn))
        else:
            return x
    elif isinstance(p, After):
        p1, p2 = p.children
        return apply_after(
            partial(flip(after), p2), start_tag_open_deriv(p1, qn))
    else:
        return NotAllowed(p, qn)


def text_deriv(p, s):
    if isinstance(p, Choice):
        p1, p2 = p.children
        return choice(text_deriv(p1, s), text_deriv(p2, s))
    elif isinstance(p, Interleave):
        p1, p2 = p.children
        return choice(
            interleave(text_deriv(p1, s), p2),
            interleave(p1, text_deriv(p2, s)))
    elif isinstance(p, Group):
        p1, p2 = p.children
        pg = group(text_deriv(p1, s), p2)
        if nullable(p1):
            return choice(pg, text_deriv(p2, s))
        else:
            return pg
    elif isinstance(p, After):
        p1, p2 = p.children
        return after(text_deriv(p1, s), p2)
    elif isinstance(p, OneOrMore):
        return group(text_deriv(p.children[0], s), choice(p, EMPTY))
    elif isinstance(p, Text):
        return TEXT
    elif isinstance(p, Value):
        if datatypeEqual(p, s):
            return EMPTY
        else:
            return NotAllowed(p, s)
    elif isinstance(p, Data):
        if datatypeAllows(p, s):
            if len(p.children) == 0:
                nc = None
            else:
                last_child = p.children[-1]
                if isinstance(last_child, Except):
                    nc = last_child.children[0]
                else:
                    nc = None

            if nc is None:
                return EMPTY
            else:
                if nullable(text_deriv(nc, s)):
                    return NotAllowed(p, s)
                else:
                    return EMPTY
        else:
            return NotAllowed(p, s)
    elif isinstance(p, List):
        if nullable(list_deriv(p.children[0], s.split())):
            return EMPTY
        else:
            return NotAllowed(p, s)
    else:
        return NotAllowed(p, s)


def list_deriv(p, string_list):
    if len(string_list) == 0:
        return p
    else:
        return list_deriv(text_deriv(p, string_list[0]), string_list[1:])


def group(p1, p2):
    if isinstance(p1, NotAllowed):
        return NotAllowed()
    elif isinstance(p2, NotAllowed):
        return NotAllowed()
    elif isinstance(p1, Empty):
        return p2
    elif isinstance(p2, Empty):
        return p1
    else:
        return Group(p1, p2)


def interleave(p1, p2):
    if isinstance(p1, NotAllowed):
        return NotAllowed()
    elif isinstance(p2, NotAllowed):
        return NotAllowed()
    elif isinstance(p1, Empty):
        return p2
    elif isinstance(p2, Empty):
        return p1
    else:
        return Interleave(p1, p2)


def after(p1, p2):
    if any(isinstance(p, NotAllowed) for p in (p1, p2)):
        return NotAllowed((p1, p2), None)
    else:
        return After(p1, p2)


def datatypeAllows(p, s):
    return p.atts['datatypeLibrary'] == '' and \
        p.atts['type'] in ('string', 'token')


def normalize_whitespace(s):
    return ' '.join(s.split())


def datatypeEqual(p, s):
    if p.atts['datatypeLibrary'] == '':
        if p.atts['type'] == 'string':
            return p.children[0] == s
        elif p.atts['type'] == 'token':
            return normalize_whitespace(p.children[0]) == \
                normalize_whitespace(s)
        else:
            return False
    else:
        return False


def apply_after(f, p):
    if isinstance(p, After):
        p1, p2 = p.children
        return After(p1, f(p2))
    elif isinstance(p, Choice):
        p1, p2 = p.children
        return choice(apply_after(f, p1), apply_after(f, p2))
    elif isinstance(p, NotAllowed):
        return NotAllowed(p)


def flip(f):
    def g(x, y):
        return f(y, x)
    return g


def att_deriv(p, att_node):
    # print("in att deriv pattern", p)
    # print("in att deriv node", att_node)
    if isinstance(p, After):
        p1, p2 = p.children
        return after(att_deriv(p1, att_node), p2)
    elif isinstance(p, Choice):
        p1, p2 = p.children
        return choice(att_deriv(p1, att_node), att_deriv(p2, att_node))
    elif isinstance(p, Group):
        return choice(
            group(att_deriv(p1, att_node), p2),
            group(p1, att_deriv(p2, att_node)))
    elif isinstance(p, Interleave):
        return choice(
            interleave(att_deriv(p1, att_node), p2),
            interleave(p1, att_deriv(p2, att_node)))
    elif isinstance(p, OneOrMore):
        return group(att_deriv(p.p, att_node), choice(p, EMPTY))
    elif isinstance(p, Attribute):
        nc, p1 = p.children
        if contains(nc, att_node.qn) and value_match(p1, att_node.s):
            return EMPTY
        else:
            return NotAllowed(p, att_node)
    else:
        return NotAllowed(p, att_node)


def atts_deriv(p, att_nodes):
    if len(att_nodes) == 0:
        return p
    else:
        return atts_deriv(att_deriv(p, att_nodes[0]), att_nodes[1:])


def value_match(p, s):
    return (nullable(p) and whitespace(s)) or nullable(text_deriv(p, s))


def start_tag_close_deriv(p):
    if isinstance(p, After):
        p1, p2 = p.children
        return after(start_tag_close_deriv(p1), p2)
    elif isinstance(p, Choice):
        p1, p2 = p.children
        return choice(start_tag_close_deriv(p1), start_tag_close_deriv(p2))
    elif isinstance(p, Group):
        p1, p2 = p.children
        return group(start_tag_close_deriv(p1), start_tag_close_deriv(p2))
    elif isinstance(p, Interleave):
        p1, p2 = p.children
        return interleave(
            start_tag_close_deriv(p1), start_tag_close_deriv(p2))
    elif isinstance(p, OneOrMore):
        return one_or_more(start_tag_close_deriv(p.children[0]))
    elif isinstance(p, Attribute):
        return NotAllowed(p)
    else:
        return p


def one_or_more(p):
    if isinstance(p, NotAllowed):
        return NotAllowed(p)
    else:
        return OneOrMore(p)


def children_deriv(p, child_nodes):
    len_child_nodes = len(child_nodes)
    if len_child_nodes == 0:
        return children_deriv(p, [''])
    elif len_child_nodes == 1 and isinstance(child_nodes[0], str):
        s = child_nodes[0]
        p1 = child_deriv(p, s)
        if whitespace(s):
            return choice(p, p1)
        else:
            return p1
    else:
        return strip_children_deriv(p, child_nodes)


def strip_children_deriv(p, child_nodes):
    if len(child_nodes) == 0:
        return p
    else:
        h, t = child_nodes[0], child_nodes[1:]
        return strip_children_deriv(p if strip(h) else child_deriv(p, h), t)


def strip(child_node):
    if isinstance(child_node, str):
        return whitespace(child_node)
    else:
        return False


def whitespace(s):
    return len(s.strip()) == 0


def end_tag_deriv(p):
    if isinstance(p, Choice):
        p1, p2 = p.children
        return choice(end_tag_deriv(p1), end_tag_deriv(p2))
    elif isinstance(p, After):
        p1, p2 = p.children
        if nullable(p1):
            return p2
        else:
            return NotAllowed(p)
    else:
        return NotAllowed(p)

QName = namedtuple('QName', ['ns', 'lname'])
Att = namedtuple('Att', ['qn', 's'])
ElementNode = namedtuple('ElementNode', ['qn', 'atts', 'children'])


def to_doc_elem(elem_dom):
    children = []
    for child in elem_dom.childNodes:
        node_type = child.nodeType
        if node_type == xml.dom.Node.ELEMENT_NODE:
            children.append(to_doc_elem(child))
        elif node_type == xml.dom.Node.TEXT_NODE:
            children.append(child.data)

    atts = []
    attrs_dom = elem_dom.attributes
    if attrs_dom is not None:
        for i in range(attrs_dom.length):
            attr_dom = attrs_dom.item(i)
            if attr_dom.prefix == 'xmlns' or attr_dom.name == 'xmlns':
                continue
            ns = '' if attr_dom.namespaceURI is None else attr_dom.namespaceURI
            atts.append(Att(QName(ns, attr_dom.localName), attr_dom.nodeValue))
    ns = '' if elem_dom.namespaceURI is None else elem_dom.namespaceURI
    qn = QName(ns, elem_dom.localName)

    return ElementNode(qn, tuple(atts), tuple(children))


def validate(schema_el, doc_str):
    start_el = schema_el.children[0]
    top_el = start_el.children[0]
    doc = xml.dom.minidom.parseString(doc_str)
    doc_root = to_doc_elem(doc.documentElement)
    # print("schema el is", grammar_el)
    deriv = child_deriv(top_el, doc_root)
    # print("deriv is ", deriv)
    if not nullable(deriv):
        raise NotAllowedException(*deriv.children)
