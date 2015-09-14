import prang.simplification
import prang.validation
import pkgutil
import xml.dom
import xml.dom.minidom
from ._version import get_versions
import os.path
__version__ = get_versions()['version']
del get_versions


rng_str = pkgutil.get_data('prang', 'relaxng.rng').decode('utf8')
rng_dom = xml.dom.minidom.parseString(rng_str)
rng_el = prang.simplification.to_prang_elem(None, rng_dom.documentElement)
prang.simplification.simplify(rng_el)
test_el = rng_el
rng_el = prang.validation.typify(rng_el)
rng_start_el = rng_el.children[0]
rng_top_el = rng_start_el.children[0]
rng_defs = dict((c.atts['name'], c.children[0]) for c in rng_el.children[1:])


class Schema():
    def __init__(
            self, schema_string=None, schema_file=None, schema_file_name=None,
            base_uri=None):
        # print("After simplification of rng", test_el)
        if schema_file_name is not None:
            schema_file = open(schema_file_name)
            if base_uri is None:
                base_uri = os.path.dirname(
                    os.path.join(os.getcwd(), schema_file_name)) + os.sep
        if schema_file is not None:
            schema_str = ''.join(schema_file.readlines())
        if schema_str is None:
            raise Exception(
                "A schema_str, schema_file or schema_file_name argument must "
                "be given.")
        schema_dom = xml.dom.minidom.parseString(schema_str)
        self.schema_el = prang.simplification.to_prang_elem(
            base_uri, schema_dom.documentElement)
        # prang.validation.validate(rng_defs, rng_top_el, schema_str)
        print("about to simplify")
        prang.simplification.simplify(self.schema_el)
        print(self.schema_el)
        # print("about to typify")
        self.frozen_schema_el = prang.validation.typify(self.schema_el)
        # print("finished typifying")
        # print(self.frozen_schema_el)
        start_el = self.frozen_schema_el.children[0]
        self.top_el = start_el.children[0]
        self.defs = dict(
            (el.atts['name'], el.children[0])
            for el in self.frozen_schema_el.children[1:])

    def validate(self, doc_str=None, doc_file=None, doc_file_name=None):
        if doc_file_name is not None:
            doc_file = open(doc_file_name)
        if doc_file is not None:
            doc_str = ''.join(doc_file.readlines())
        if doc_str is None:
            raise Exception(
                "A doc_str, doc_file or doc_file_name argument must be given.")
        prang.validation.validate(self.defs, self.top_el, doc_str)
