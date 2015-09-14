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

SchemaNode = namedtuple('SchemaNode', ['name', 'atts', 'children'])

EMPTY = SchemaNode('empty', {}, tuple())


def typify(node):
    if isinstance(node, str):
        return node
    else:
        children = tuple(typify(c) for c in node.iter_children())
        return SchemaNode(node.name, node.attrs, children)


def contains(nc, n):
    print("In contains ")
    print("nc", nc)
    print("n", n)
    if nc.name == 'anyName':
        if len(nc.children) == 0:
            return True
        else:
            return not contains(nc.children[0], n)
    elif nc.name == 'nsName':
        if nc.atts['ns'] == n.ns:
            if len(nc.children) == 0:
                return True
            else:
                return not contains(nc.children[0], n)
    elif nc.name == 'name':
        return nc.atts['ns'], nc.children[0] == n
    elif nc.name == 'choice':
        return any(contains(nc, n) for nc in nc.children)
    return False


def nullable(p):
    if p.name in ('group', 'interleave'):
        return all(nullable(c) for c in p.children)
    elif p.name in ('choice', 'oneOrMore'):
        return any(nullable(c) for c in p.children)
    elif p.name in (
            'element', 'attribute', 'list', 'value', 'data', 'notAllowed'):
        return False
    elif p.name in ('empty', 'text'):
        return True
    else:
        return False


'''
def child_deriv(p, s):
    if isinstance(s, str):
        return text_deriv(p, s)
    else:
        if p.name == 'choice':
            p1, p2 = p.children
            choice(start_tag_open_deriv(p1, qn), start_tag_open_deriv(p2, qn))

        p1 = start_tag_open_deriv(p, s.qn)
        p2 = atts_deriv(p1, s.atts)
        p3 = start_tag_close_deriv(p2)
        p4 = children_deriv(p3, s.iter_children())
        return end_tag_deriv(p4)
'''

'''
def choice(p1, p2):
    if isinstance(p2, NotAllowed):
        return p1
    elif isinstance(p1, NotAllowed):
        return p2
    else:
        return choice(p1, p2)


'''


class InvalidException(Exception):
    pass


def validate_child(defs, p, s):
    # print("in child deriv")
    # print("defs", defs)
    # print("p", p)
    # print("s", s)
    if p.name == 'ref':
        p = defs[p.atts['name']]
    # print("new p", p)

    if isinstance(s, str):
        print("it's a string", s)
        # return text_deriv(p, s)
        return EMPTY
    elif p.name == 'element':
        print("it's an element", s)
        nc, top = p.children
        if not contains(nc, s.qn):
            raise InvalidException(p, s)
    elif p.name == 'choice':
        p1, p2 = p.children
        try:
            validate_child(defs, p1, s)
        except InvalidException:
            validate_child(defs, p2, s)
    else:
        raise Exception("Don't recognize " + str(p))
'''
p1 = start_tag_open_deriv(p, s.qn)
p2 = atts_deriv(p1, s.atts)
p3 = start_tag_close_deriv(p2)
p4 = children_deriv(p3, s.iter_children())
return end_tag_deriv(p4)


def start_tag_open_deriv(p, qn):
    if p.name == 'choice':
        p1, p2 = tuple(p.iter_children())
        choice(start_tag_open_deriv(p1, qn), start_tag_open_deriv(p2, qn))
    elif p.name == 'element':
        if contains(p.nc, qn):
            return after(p.p, Empty())
        else:
            return NotAllowed()
    elif isinstance(p, Interleave):
        p1, p2 = p.children
        return choice(
            apply_after(flip(interleave, p2), start_tag_open_deriv(p1, qn)),
            apply_after(partial(interleave, p1), start_tag_open_deriv(p2, qn)))
    elif isinstance(p, OneOrMore):
        return apply_after(
            flip(group, choice(p.p, Empty())), start_tag_open_deriv(p.p, qn))
    elif isinstance(p, Group):
        p1, p2 = p.children
        x = apply_after(
            flip(group, p2), start_tag_open_deriv(p1, qn))
        if nullable(p1):
            return choice(x, start_tag_open_deriv(p2, qn))
        else:
            return x
    elif isinstance(p, After):
        p1, p2 = p.children
        return apply_after(flip(after, p2), start_tag_open_deriv(p1, qn))
    else:
        return NotAllowed()



def text_deriv(cx, p, s):
    if p.name == 'choice':
        p1, p2 = tuple(p.iter_children())
        return choice(text_deriv(cx, p1, s), text_deriv(cx, p2, s))
    elif p.name == 'interleave':
        p1, p2 = tuple(p.iter_children())
        return choice(
            interleave(text_deriv(cx, p1, s), p2),
            interleave(text_deriv(cx, p2, s)))
    elif p.name == 'group':
        p1, p2 = tuple(p.iter_children())
        pg = group(text_deriv(cx, p1, s), p2)
        if nullable(p1):
            return choice(pg, text_deriv(cx, p2, s))
        else:
            return pg
    elif p.is_after:
        p1, p2 = tuple(p.iter_children())
        return after(text_deriv(cx, p1, s), p2)
    elif p.name == 'oneOrMore':
        p1 = next(p.iter_children())
        return group(text_deriv(cx, p1, s), choice(p, Empty))
    elif p.name == 'text':
        return Text
    elif p.name == 'value':
        if datatypeEqual(p.dt, next(p.iter_children()), p.cx):
            return Empty
        else:
            return NotAllowed
    elif p.name == 'data':
        if datatypeAllows(p.dt, p.params, next(p.iter_children()), s):
            ex = p.ex
            if ex is None:
                return Empty()
            else:
                if nullable(text_deriv(cx, ex, s)):
                    return NotAllowed()
                else:
                    return Empty()
        else:
            return NotAllowed()
    elif p.name == 'list':
        if nullable(list_deriv(cx, next(p.iter_children()), s.split())):
            return Empty()
        else:
            return NotAllowed()
    else:
        return NotAllowed()


def list_deriv(cx, p, string_list):
    if len(string_list) == 0:
        return p
    else:
        return list_deriv(
            cx, text_deriv(cx, p, string_list[0]), string_list[1:])


def group(p1, p2):
    if p1 == NotAllowed():
        return p2
    elif p2 == NotAllowed():
        return p1
    elif p1 == Empty():
        return p2
    elif p2 == Empty():
        return p1
    else:
        return group(p1, p2)


def interleave(p1, p2):
    if p1 == NotAllowed():
        return p2
    elif p2 == NotAllowed():
        return p1
    elif p1 == Empty():
        return p2
    elif p2 == Empty():
        return p1
    else:
        return interleave(p1, p2)


def after(p1, p2):
    if any(isinstance(p, NotAllowed) for p in (p1, p2)):
        return NotAllowed()
    else:
        return after(p1, p2)


def datatypeAllows(dt, params, s, cx):
    return dt.uri == '' and dt.lname in ('string', 'token')


def normalize_whitespace(s):
    return ''.join(s.split())


def datatypeEqual(dt, s1, cx1, s2, cx2):
    if dt.uri == '':
        if dt.ln == 'string':
            return s1 == s2
        elif dt.ln == 'token':
            return normalize_whitespace(s1) == normalize_whitespace(s2)
        else:
            return False
    else:
        return False


def apply_after(f, p):
    if isinstance(p, After):
        p1, p2 = p.children
        return after(p1, f(p2))
    elif isinstance(p, Choice):
        p1, p2 = p.children
        return choice(apply_after(f, p1), apply_after(f, p2))
    elif isinstance(p, NotAllowed):
        return NotAllowed()


def flip(f, x):
    def g(y):
        return f(y, x)
    return g


def att_deriv(cx, p, att_node):
    if isinstance(p, After):
        p1, p2 = p.children
        return after(att_deriv(cx, p1, att_node), p2)
    elif isinstance(p, Choice):
        p1, p2 = p.children
        return choice(att_deriv(cx, p1, att_node), att_deriv(cx, p2, att_node))
    elif isinstance(p, Group):
        return choice(
            group(att_deriv(cx, p1, att_node), p2),
            group(p1, att_deriv(cx, p2, att_node)))
    elif isinstance(p, Interleave):
        return choice(
            interleave(att_deriv(cx, p1, att_node), p2),
            interleave(p1, att_deriv(cx, p2, att_node)))
    elif isinstance(p, OneOrMore):
        return group(att_deriv(cx, p.p, att_node), choice(p, Empty()))
    elif isinstance(p, Attribute):
        if contains(p.nc, att_node.qn) and value_match(cx, p.p, att_node.s):
            return Empty()
        else:
            return NotAllowed()
    else:
        return NotAllowed()


def atts_deriv(cx, p, att_nodes):
    if len(att_nodes) == 0:
        return p
    else:
        return atts_deriv(cx, att_deriv(cx, p, att_nodes[0]), att_nodes[1:])


def value_match(cx, p, s):
    return (nullable(p) and whitespace(s)) or nullable(text_deriv(cx, p, s))


def start_tag_close_deriv(p):
    if isinstance(p, After):
        p1, p2 = p.children
        return after(start_tag_close_deriv(p1), p2)
    elif isinstance(p, Choice):
        p1, p2 = p.children
        return choice(start_tag_close_deriv(p1), start_tag_close_deriv(p2))
    elif isinstance(p, Group):
        p1, p2 = p.children
        return group(start_tag_close_deriv(c) for c in p.iter_children())
    elif isinstance(p, Interleave):
        p1, p2 = p.children
        return interleave(
            start_tag_close_deriv(p1), start_tag_close_deriv(p2))
    elif isinstance(p, OneOrMore):
        return OneOrMore(start_tag_close_deriv(p.p))
    elif isinstance(p, Attribute):
        return NotAllowed()
    else:
        return p


def one_or_more(p):
    if isinstance(p, NotAllowed):
        return NotAllowed
    else:
        return OneOrMore(p)


def children_deriv(cx, p, child_nodes):
    len_child_nodes = len(child_nodes)
    if len_child_nodes == 0:
        return children_deriv(cx, p, [''])
    elif len_child_nodes == 1 and isinstance(child_nodes[0], str):
        s = child_nodes[0]
        p1 = child_deriv(cx, p, s)
        if whitespace(s):
            return choice(p, p1)
        else:
            return p1
    else:
        return strip_children_deriv(cx, p, child_nodes)


def strip_children_deriv(cx, p, child_nodes):
    if len(child_nodes) == 0:
        return p
    else:
        h, t = child_nodes[0], child_nodes[1:]
        return strip_children_deriv(
            cx, p if strip(h) else child_deriv(cx, p, h), t)


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
            return NotAllowed
    else:
        return NotAllowed

'''
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
            atts.append(
                Att(
                    QName(attr_dom.namespaceURI, attr_dom.localName),
                    attr_dom.nodeValue))
    ns = '' if elem_dom.namespaceURI is None else elem_dom.namespaceURI
    qn = QName(ns, elem_dom.localName)

    return ElementNode(qn, tuple(atts), tuple(children))


def validate(defs, top_el, doc_str):
    doc = xml.dom.minidom.parseString(doc_str)
    doc_root = to_doc_elem(doc.documentElement)
    # print("schema el is", grammar_el)
    validate_child(defs, top_el, doc_root)
