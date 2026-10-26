# Ontology Guidelines

This guide helps you create an ontology that is understood by the OVAL Policy Evaluator, and related ODRL tools. 

__Important Note__: You do not need to define a domain specific ontology to use the OVAL Policy Evaluator, 
but without it, its reasoning capabilities will be limited to standard ODRL. In general, if you are not limiting yourself
to only standard terms then defining an ontology is good practice, and  tools like the ODRL Editor can provide more UI support if 
a domain specific ontology is defined.

True to the open-world nature of the Semantic Web, your ontology can contain more information than what is listed
below, but those additional pieces of information will not affect the behaviour or OVAL and ODRL Engine tools.

Note: the `dips:` prefix in the examples is just a dummy placeholder for any other prefix.

## Action

To define a new action:
* define it as type `odrl:Action`
* define its human readable label using `rdfs:label`
* __Action hierarchy__: define the more general type of action that this action specialises using `odrl:includedIn`. If its not a specialisation of any specific action, make it a specialisation of one of the more general actions `odrl:use` or `odrl:transfer`. To follow the ODRL specification, define exactly one (no more, no less) such relation for each action.

Minimal example:
```
dips:2d_print a odrl:Action ;
    rdfs:label "2D Print" ;
    odrl:includedIn odrl:print .
```

Example SPARQL query to return the Action hierarchy:
```
SELECT ?action ?action_label ?super_action ?super_action_label
WHERE {
  ?action a odrl:Action ;
          rdfs:label ?action_label .

  OPTIONAL {
    ?action odrl:includedIn ?super_action .
    ?super_action rdfs:label ?super_action_label .
  }
}
```

## Asset

To define a new asset:
* define it as type `odrl:Asset`
* define its human readable label using `rdfs:label`
* __Asset Hierarchy__: optionally, if you want to define a hierarchy of assets, 
define the more general type using the `odrl:partOf` relation.

Minimal example:
```
dips:HR_data a odrl:Asset ;
  rdfs:label "HR Data" .
```

Example with hierarchy information:
```
dips:sick_leave_data a odrl:Asset ;
  rdfs:label "Salary Data" ;
  odrl:partOf dips:HR_data .
```

Example SPARQL query to return the Asset hierarchy:
```
SELECT ?asset ?asset_label ?super_asset ?super_asset_label
WHERE {
  ?asset a odrl:Asset ;
         rdfs:label ?asset_label .

  OPTIONAL {
    ?asset odrl:partOf ?super_asset .
    ?super_asset rdfs:label ?super_asset_label .
  }
}
```
## Party

To define a new party (this follows the same pattern as for Asset):
* define it as type `odrl:Party`
* define its human readable label using `rdfs:label`
* __Party Hierarchy__: optionally, if you want to define a hierarchy of parties, 
define the more general type using the `odrl:partOf` relation.

Minimal example:
```
dips:DIPS_Development_Team a odrl:Party ;
  rdfs:label "DIPS Development Team" .
```

Example with hierarchy information:
```
dips:Anne a odrl:Party ;
  rdfs:label "Anne A" ;
  odrl:partOf dips:DIPS_Development_Team .
```

Example SPARQL query to return the Party hierarchy:
```
SELECT ?party ?party_label ?super_party ?super_party_label
WHERE {
  ?party a odrl:Party ;
         rdfs:label ?party_label .

  OPTIONAL {
    ?party odrl:partOf ?super_party .
    ?super_party rdfs:label ?super_party_label .
  }
}
```

## RDFS Reasoning

Your ontology can define arbitrary [RDFS hierarchies](https://www.w3.org/TR/rdf-schema/) using the `rdf:type` and `rdfs:subClassOf` relations. 
This allows limited RDFS Reasoning that affects the `odrl:isA` operator.

Example defining two classes of purposes (commercial and reseach) and three types of each:
```
dips:CommercialPurpose rdfs:subClassOf dips:AnyPurpose ;
    rdfs:label "Commercial purpose" .

dips:ResearchPurpose rdfs:subClassOf dips:AnyPurpose ;
    rdfs:label "Research purpose" .

# Specific commercial purpose types
dips:TargetedAdvertising rdf:type dips:CommercialPurpose ;
    rdfs:label "Targeted advertising" .

dips:MarketAnalysis rdf:type dips:CommercialPurpose ;
    rdfs:label "Market analysis" .

dips:ProductPersonalization rdf:type dips:CommercialPurpose ;
    rdfs:label "Product personalization" .

# Specific research purpose types
dips:ClinicalResearch rdf:type dips:ResearchPurpose ;
    rdfs:label "Clinical research" .

dips:AcademicResearch rdf:type dips:ResearchPurpose ;
    rdfs:label "Academic research" .

dips:ScientificReproducibility rdf:type dips:ResearchPurpose ;
    rdfs:label "Scientific reproducibility" .
```
Using this ontology, for example, you can define a constraint that prohibits commercial research
using Left Operand `odrl:purpose`, operator `odrl:isA` and Right Operand `dips:ResearchPurpose` on a prohibition.
An access request that specifies `dips:TargetedAdvertising` as its `odrl:purpose` would therefore be rejected, while one
that specifies `dips:ClinicalResearch` instead would be permitted. 
If instead you used the more general class `dips:AnyPurpose` in that constraint, all instances of purposes in this sample
ontology would lead to a rejection.

Example SPARQL query to return all the instances of a class <CLASS_PLACEHOLDER>, accounting for RDFS inferences.
```
SELECT ?instance
WHERE {
  ?instance a / rdfs:subClassOf* <CLASS_PLACEHOLDER> .
}
```

## Left Operand

To can define a new Left Operand:
* define it as type `odrl:Left Operand`
* define its human readable label using `rdfs:label`

Minimal example:
```
dips:credential_issuer a odrl:LeftOperand ;
    rdfs:label "The issuer of the credentials" .
```

Example SPARQL query to return all Left Operands
```
SELECT ?left_operand ?left_operand_label
WHERE {
  ?left_operand a odrl:LeftOperand ;
                rdfs:label ?left_operand_label .
}
```