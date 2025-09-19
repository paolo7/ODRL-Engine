import rdflib
import pyshacl

import validate

odrl_incorrect_example_1 = """{
    "permission": [{}{}{
        "target": "http://example.com/asset:9898.movie",
        "action": "use
    }]
}"""

odrl_incorrect_example_2 = """{
    "permission": [{
        "target": "http://example.com/asset:9898.movie",
        "action": "use"
    }]
}"""
odrl_example_1 = """{
    "@context": {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "odrl": "http://www.w3.org/ns/odrl/2/",
        "dpv": "https://w3id.org/dpv/owl#",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "cactus": "https://www.cactusweb.gr/vocab/",
        "id": "https://www.cactusweb.gr/vocab/id/"
      },
    "@type": "odrl:Policy",
    "odrl:uid": { "@id": "http://example.com/policy:1010" },
    "odrl:permission": [{
        "odrl:target": { "@id": "http://example.com/asset:9898.movie" },
        "odrl:action": { "@id": "odrl:use" }
    }]
}"""

validate.generate_ODRL_diagnostic_report(odrl_example_1)
