# ODRL Engine Change Log

* __2 September 2026__: New Feature: Stricter ODRL validation, including validation of constraint operands against the ODRL-defined operand list, with support for atomic, compound, and compact policies.
* __28 August 2026__: Extended access-control evaluation with set operators, RDF-list operands and an API endpoint for evaluating access requests.
* __27 August 2026__: Added reasoning support for includedIn and partOf, with expanded unit-test coverage.
* __26 August 2026__: New Feature: Access Control evaluation mode with configurable access-request evaluation semantics, including conflict strategies, treatment of unspecified events, and duties.
* __19 August 2026__: New Feature: Major ODRL validation overhaul, including a validation API, validator application, file-based validation, and comprehensive tests based on the ODRL 2.2 specification.
* __18 August 2026__: Completed support for policy-level assignees, parties, targets, and actions, including support for arbitrary date datatypes in left operands.
* __31 July 2026__: Extended the API with streaming evaluation and policy feature extraction.
* __14 July 2026__: Added a GUI dashboard and Docker-based service deployment for the ODRL Engine 
with a validator, ODRL policy generator, and State-of-the-World generator applications.
* __2 June 2026__: Implemented Docker deployment infrastructure.
* __6 May 2026__: Added full support for ODRL logic constraints, including nested constraints, with dedicated tests.
* __5 May 2026__: Added support for synthetic policy generation: generating consequences of permission duties, remedies, and streaming evaluation, together with expanded automated tests.
* __1 May 2026__: Improvement: Decoupled evaluation functions and expanded scalability testing for larger datasets.
* __29 April 2026__: Added support for synthetic policy generation: added generation and configuration of ODRL duties and remedies.
* __28 April 2026__: Added an initial scalability experiments framework.
* __15 April 2026__: New Feature: Added support in the ODRL Evaluator for obligations, consequences, duties, and remedies, along with automated tests.
* __17 February 2026__: Added initial support for multi-policy evaluation.
* __10 February 2026__: New Feature: Date-aware constraint evaluation in the evaluator.
* __13 November 2025__: New Feature: Introduced the State-of-the-World generator.
* __11 November 2025__: New Feature: Introduced the ODRL policy generator, including configurable generation parameters and downloadable generated policies.
* __3 November 2025__: Added a Google Colab interface.
* __19 September 2025__: Initial ODRL Engine implementation, including example policies and the first validation functionality.