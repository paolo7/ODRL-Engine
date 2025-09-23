import rdflib
# import pyshacl

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
        "foaf": "http://xmlns.com/foaf/0.1/"
      },
    "@type": "odrl:Policy",
    "@id": "http://example.com/policy:1010",
    "odrl:permission": [{
        "odrl:target": { "@id": "http://example.com/asset:9898.movie" },
        "odrl:action": { "@id": "odrl:use" }
    }]
}"""


negotiation_odrl_example_1 = """{
  "permission": [
    {
      "action": "http://www.w3.org/ns/odrl/2/digitize",
      "assignee": "https://w3id.org/dpv/dpv-owl#JointDataControllers",
      "target": "http://example.org/datasets/socialMediaAnalytics",
      "constraint": [
        {
          "leftOperand": "purpose",
          "operator": "http://www.w3.org/ns/odrl/2/eq",
          "rightOperand": "https://w3id.org/dpv#CustomerCare"
        }
      ]
    }
  ],
  "prohibition": [
    {
      "action": "http://www.w3.org/ns/odrl/2/derive",
      "assignee": "https://w3id.org/dpv/dpv-owl#DataProtectionAuthority",
      "target": "http://example.org/datasets/socialMediaAnalytics",
      "constraint": [
        {
          "leftOperand": "purpose",
          "operator": "http://www.w3.org/ns/odrl/2/eq",
          "rightOperand": "https://w3id.org/dpv#CommunicationForCustomerCare"
        }
      ]
    }
  ],
  "obligation": [
    {
      "action": {
        "source": "http://www.w3.org/ns/odrl/2/attribute",
        "refinement": [
          {
            "leftOperand": "http://www.w3.org/ns/odrl/2/fileFormat",
            "operator": "http://www.w3.org/ns/odrl/2/isA",
            "rightOperand": "PDF"
          }
        ]
      },
      "assignee": {
        "@type": "PartyCollection",
        "source": "https://w3id.org/dpv/dpv-owl#DataProtectionAuthority",
        "refinement": [
          {
            "leftOperand": "hasRelationWithDataSubject",
            "operator": "http://www.w3.org/ns/odrl/2/isA",
            "rightOperand": "University"
          }
        ]
      },
      "target": {
        "@type": "AssetCollection",
        "source": "http://example.org/datasets/socialMediaAnalytics",
        "refinement": [
          {
            "leftOperand": "Users",
            "operator": "http://www.w3.org/ns/odrl/2/isAllOf",
            "rightOperand": "Students"
          }
        ]
      },
      "constraint": [
        {
          "and": [
            {
              "leftOperand": "purpose",
              "operator": "http://www.w3.org/ns/odrl/2/eq",
              "rightOperand": "https://w3id.org/dpv#AgeVerification"
            },
            {
              "leftOperand": "http://www.w3.org/ns/odrl/2/language",
              "operator": "http://www.w3.org/ns/odrl/2/isA",
              "rightOperand": "English"
            },
            {
              "leftOperand": "http://www.w3.org/ns/odrl/2/event",
              "operator": "http://www.w3.org/ns/odrl/2/isA",
              "rightOperand": "Party"
            }
          ]
        }
      ]
    }
  ],
  "duty": [
    {
      "action": {
        "source": "http://www.w3.org/ns/odrl/2/annotate",
        "refinement": [
          {
            "leftOperand": "http://www.w3.org/ns/odrl/2/dateTime",
            "operator": "http://www.w3.org/ns/odrl/2/gt",
            "rightOperand": "9/9/2025"
          }
        ]
      },
      "assignee": {
        "@type": "PartyCollection",
        "source": "https://w3id.org/dpv/dpv-owl#DataProtectionAuthority",
        "refinement": [
          {
            "leftOperand": "hasAddress",
            "operator": "http://www.w3.org/ns/odrl/2/isAnyOf",
            "rightOperand": "London"
          }
        ]
      },
      "target": {
        "@type": "AssetCollection",
        "source": "http://example.org/datasets/socialMediaAnalytics",
        "refinement": [
          {
            "leftOperand": "Platform",
            "operator": "http://www.w3.org/ns/odrl/2/isA",
            "rightOperand": "Company"
          }
        ]
      },
      "constraint": [
        {
          "and": [
            {
              "leftOperand": "purpose",
              "operator": "http://www.w3.org/ns/odrl/2/eq",
              "rightOperand": "https://w3id.org/dpv#TargetedAdvertising"
            },
            {
              "leftOperand": "http://www.w3.org/ns/odrl/2/event",
              "operator": "http://www.w3.org/ns/odrl/2/isA",
              "rightOperand": "Conference"
            }
          ]
        }
      ]
    },
    {
      "action": "http://www.w3.org/ns/odrl/2/archive",
      "assignee": "https://w3id.org/dpv/dpv-owl#LegalEntity",
      "target": "http://example.org/datasets/socialMediaAnalytics",
      "constraint": [
        {
          "leftOperand": "purpose",
          "operator": "http://www.w3.org/ns/odrl/2/eq",
          "rightOperand": "https://w3id.org/dpv#CommercialPurpose"
        }
      ]
    },
    {
      "action": "http://www.w3.org/ns/odrl/2/anonymize",
      "assignee": "https://w3id.org/dpv/dpv-owl#Authority",
      "target": "http://example.org/datasets/socialMediaAnalytics",
      "constraint": [
        {
          "leftOperand": "purpose",
          "operator": "http://www.w3.org/ns/odrl/2/eq",
          "rightOperand": "https://w3id.org/dpv#PersonalisedAdvertising"
        }
      ]
    }
  ],
  "uid": "http://example.org/policy-a9ef21bf-3bbf-4b15-85d1-2cf0171473bd",
  "@context": [
    "http://www.w3.org/ns/odrl.jsonld",
    {
      "dcat": "http://www.w3.org/ns/dcat#",
      "dpv": "https://w3id.org/dpv/dpv-owl#"
    }
  ],
  "@type": "Policy"
}"""

validate.generate_ODRL_diagnostic_report(odrl_incorrect_example_1)
