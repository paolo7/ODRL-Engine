from datetime import datetime


def merge_key_multisets(multiset1, multiset2):
    keys = multiset1.keys() | multiset2.keys()
    for key in keys:
        if key in multiset2:
            if key in multiset1:
                multiset1[key] = sorted(list(set(multiset1[key] + multiset2[key])))
            else:
                multiset1[key] = multiset2[key]
    return multiset1

def string_to_element(value):
    if value.isnumeric():
        if "." in value:
            return float(value)
        else:
            return int(value)
    else:
        try:
            return str(datetime.fromisoformat(value))
        except ValueError:
            return value
        
def string_to_rdflib_node(value):
    from rdflib import URIRef, Literal
    if isinstance(value, str):
        import re
        #TODO: Implement datatypes maybe.
        uri_pattern = re.compile(r'\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s<>"\'()]+')
        if uri_pattern.match(value):
            return URIRef(value)
        else:
            return Literal(value)
    else:
        return Literal(str(value))
