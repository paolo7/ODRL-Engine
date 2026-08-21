from rdflib import Graph, Namespace, RDF, URIRef, Literal


SH = Namespace("http://www.w3.org/ns/shacl#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")


# ------------------------------------------------------------------
# Public function
# ------------------------------------------------------------------

def explain_SHACL_validation_report(report_graph: Graph) -> str:
    """
    Convert a pySHACL validation report RDF graph into a short,
    human-readable explanation.

    The function tries to explain ODRL concepts rather than exposing
    SHACL/RDF implementation details such as blank node identifiers,
    rdf:first, rdf:rest, etc.
    """

    results = list(report_graph.objects(None, SH.result))

    if not results:
        conforms = list(report_graph.objects(None, SH.conforms))

        if conforms and str(conforms[0]).lower() == "true":
            return "SHACL validation passed. No violations were found."

        return (
            "SHACL validation failed, but no detailed "
            "violations were found."
        )

    # --------------------------------------------------------------
    # Detect logical-constraint list problems.
    #
    # A single malformed logical constraint can generate TWO SHACL
    # results: one for rdf:first and one for rdf:rest.
    #
    # We combine those into one human-readable error.
    # --------------------------------------------------------------

    logical_constraint_results = []

    normal_results = []

    for result in results:
        path = report_graph.value(result, SH.resultPath)

        if path in (RDF.first, RDF.rest):
            logical_constraint_results.append(result)
        else:
            normal_results.append(result)

    lines = []

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    total_issues = 0

    if logical_constraint_results:
        total_issues += 1

    total_issues += len(normal_results)

    issue_word = "issue" if total_issues == 1 else "issues"

    lines.append(
        f"SHACL validation failed with "
        f"{total_issues} {issue_word}."
    )
    lines.append("")

    # --------------------------------------------------------------
    # Logical constraint problem
    # --------------------------------------------------------------

    if logical_constraint_results:

        # Use the first result to identify the logical constraint.
        first_result = logical_constraint_results[0]

        focus_node = report_graph.value(
            first_result,
            SH.focusNode
        )

        rule_description = _describe_rule_containing_node(
            report_graph,
            focus_node
        )

        explanation = (
            "The logical constraint is not represented as a valid "
            "RDF list. An ODRL logical constraint such as `and`, "
            "`or`, or `xone` must contain a list of constraints."
        )

        lines.append(
            f"- Logic constraint violation: {explanation}"
        )

        if rule_description:
            lines.append(
                f"  {rule_description}"
            )

        lines.append("")

    # --------------------------------------------------------------
    # Other SHACL violations
    # --------------------------------------------------------------

    for result in normal_results:

        severity = report_graph.value(
            result,
            SH.resultSeverity
        )

        path = report_graph.value(
            result,
            SH.resultPath
        )

        message = report_graph.value(
            result,
            SH.resultMessage
        )

        focus_node = report_graph.value(
            result,
            SH.focusNode
        )

        severity_label = (
            _shacl_term_label(severity)
            if severity
            else "Violation"
        )

        path_label = _shacl_path_label(path)

        explanation = _make_human_shacl_message(
            report_graph,
            result,
            path,
            message
        )

        lines.append(
            f"- {path_label} "
            f"{severity_label.lower()}: "
            f"{explanation}"
        )

        rule_description = _describe_rule_containing_node(
            report_graph,
            focus_node
        )

        if rule_description:
            lines.append(
                f"  {rule_description}"
            )

        lines.append("")

    return "\n".join(lines).strip()


# ------------------------------------------------------------------
# Human-readable SHACL messages
# ------------------------------------------------------------------

def _make_human_shacl_message(
    report_graph: Graph,
    result,
    path,
    message
) -> str:
    """
    Convert common SHACL constraint violations into human-readable
    messages.
    """

    raw_message = str(message) if message else ""

    source_constraint = report_graph.value(
        result,
        SH.sourceConstraintComponent
    )

    # --------------------------------------------------------------
    # Max count
    # --------------------------------------------------------------

    if source_constraint == SH.MaxCountConstraintComponent:

        source_shape = report_graph.value(
            result,
            SH.sourceShape
        )

        max_count = None

        if source_shape:
            max_count = report_graph.value(
                source_shape,
                SH.maxCount
            )

        if max_count is not None:

            values = _get_path_values(
                report_graph,
                result,
                path
            )

            value_text = _format_values(values)

            property_name = _shacl_path_label(
                path
            ).lower()

            if value_text:
                return (
                    f"This rule has more than "
                    f"{max_count} {property_name} "
                    f"({value_text}). "
                    f"Only {max_count} is allowed."
                )

            return (
                f"This rule has more than "
                f"{max_count} {property_name}. "
                f"Only {max_count} is allowed."
            )

    # --------------------------------------------------------------
    # Min count
    # --------------------------------------------------------------

    if source_constraint == SH.MinCountConstraintComponent:

        source_shape = report_graph.value(
            result,
            SH.sourceShape
        )

        min_count = None

        if source_shape:
            min_count = report_graph.value(
                source_shape,
                SH.minCount
            )

        if min_count is not None:

            # Special case: rdf:first / rdf:rest.
            # These should not normally be exposed to the user.
            if path in (RDF.first, RDF.rest):
                return (
                    "The logical constraint is not represented "
                    "as a valid RDF list."
                )

            return (
                f"This rule is missing its required "
                f"{_shacl_path_label(path).lower()}. "
                f"At least {min_count} is required."
            )

    # --------------------------------------------------------------
    # Class
    # --------------------------------------------------------------

    if source_constraint == SH.ClassConstraintComponent:

        return (
            f"The value of "
            f"{_shacl_path_label(path).lower()} "
            f"does not have the required type."
        )

    # --------------------------------------------------------------
    # Datatype
    # --------------------------------------------------------------

    if source_constraint == SH.DatatypeConstraintComponent:

        return (
            f"The value of "
            f"{_shacl_path_label(path).lower()} "
            f"has an invalid datatype."
        )

    # --------------------------------------------------------------
    # Node kind
    # --------------------------------------------------------------

    if source_constraint == SH.NodeKindConstraintComponent:

        return (
            f"The value of "
            f"{_shacl_path_label(path).lower()} "
            f"has an invalid RDF node type."
        )

    # --------------------------------------------------------------
    # Fallback
    # --------------------------------------------------------------

    if raw_message:
        return _clean_shacl_message(raw_message)

    return (
        "This rule does not satisfy the required constraint."
    )


# ------------------------------------------------------------------
# Find the ODRL rule containing a node
# ------------------------------------------------------------------

def _describe_rule_containing_node(
    graph: Graph,
    node
) -> str:
    """
    Given a focus node, try to find the ODRL Permission,
    Prohibition, or Duty that contains it.

    This is particularly useful for blank nodes representing
    constraints or logical constraints.
    """

    if node is None:
        return ""

    rule_types = [
        (ODRL.Permission, "Permission"),
        (ODRL.Prohibition, "Prohibition"),
        (ODRL.Duty, "Duty"),
    ]

    # --------------------------------------------------------------
    # First: is the focus node itself an ODRL rule?
    # --------------------------------------------------------------

    for rule_type, rule_label in rule_types:

        if (node, RDF.type, rule_type) in graph:

            return _format_rule_description(
                graph,
                node,
                rule_label
            )

    # --------------------------------------------------------------
    # Second: find a rule that points to this node as a constraint.
    # --------------------------------------------------------------

    for rule_type, rule_label in rule_types:

        for rule in graph.subjects(
            RDF.type,
            rule_type
        ):

            # Direct odrl:constraint
            if (rule, ODRL.constraint, node) in graph:

                return _format_rule_description(
                    graph,
                    rule,
                    rule_label
                )

            # The node might be nested inside another logical
            # constraint which is attached to the rule.
            if _node_is_reachable_from_constraint(
                graph,
                rule,
                node
            ):

                return _format_rule_description(
                    graph,
                    rule,
                    rule_label
                )

    return ""


def _node_is_reachable_from_constraint(
    graph: Graph,
    rule,
    target_node
) -> bool:
    """
    Check whether target_node is somewhere inside an ODRL
    constraint attached to rule.

    This follows the common ODRL logical constraint predicates.
    """

    logical_properties = [
        ODRL.and_,
        ODRL.or_,
        ODRL.xone,
        ODRL.andSequence,
    ]

    visited = set()
    stack = list(
        graph.objects(rule, ODRL.constraint)
    )

    while stack:

        current = stack.pop()

        if current in visited:
            continue

        visited.add(current)

        if current == target_node:
            return True

        # Follow logical constraint properties.
        for predicate in logical_properties:

            stack.extend(
                graph.objects(
                    current,
                    predicate
                )
            )

        # Follow RDF list structure.
        stack.extend(
            graph.objects(
                current,
                RDF.first
            )
        )

        stack.extend(
            graph.objects(
                current,
                RDF.rest
            )
        )

    return False


# ------------------------------------------------------------------
# Describe an ODRL rule
# ------------------------------------------------------------------

def _format_rule_description(
    graph: Graph,
    rule,
    rule_type: str
) -> str:
    """
    Produce a compact description such as:

    Rule: Permission for acme, subject to refinements,
    to do use on 59d1ddcb-f22f-4fc8-a665-2fbf4517c1ff
    """

    parts = [
        f"Rule: {rule_type}"
    ]

    # --------------------------------------------------------------
    # Assignee
    # --------------------------------------------------------------

    assignees = list(
        graph.objects(
            rule,
            ODRL.assignee
        )
    )

    if assignees:

        assignee_text = _format_values(
            assignees
        )

        parts.append(
            f"for {assignee_text}"
        )

    # --------------------------------------------------------------
    # Constraints / refinements
    # --------------------------------------------------------------

    constraints = list(
        graph.objects(
            rule,
            ODRL.constraint
        )
    )

    if constraints:

        parts.append(
            "subject to refinements"
        )

    # --------------------------------------------------------------
    # Action
    # --------------------------------------------------------------

    actions = list(
        graph.objects(
            rule,
            ODRL.action
        )
    )

    if actions:

        action_text = _format_values(
            actions
        )

        parts.append(
            f"to do {action_text}"
        )

    # --------------------------------------------------------------
    # Target
    # --------------------------------------------------------------

    targets = list(
        graph.objects(
            rule,
            ODRL.target
        )
    )

    if targets:

        target_text = _format_values(
            targets
        )

        parts.append(
            f"on {target_text}"
        )

    return ", ".join(parts)


# ------------------------------------------------------------------
# Get values for a SHACL path
# ------------------------------------------------------------------

def _get_path_values(
    report_graph: Graph,
    result,
    path
):
    """
    Find the actual values responsible for a violation.
    """

    focus_node = report_graph.value(
        result,
        SH.focusNode
    )

    if not focus_node or not path:
        return []

    if isinstance(path, URIRef):

        return list(
            report_graph.objects(
                focus_node,
                path
            )
        )

    return []


# ------------------------------------------------------------------
# Format RDF values
# ------------------------------------------------------------------

def _format_values(values):
    """
    Convert RDF values into a compact human-readable list.
    """

    labels = []

    for value in values:

        label = _simple_node_label(
            value
        )

        if label:
            labels.append(label)

    # Remove duplicates while preserving order.
    labels = list(
        dict.fromkeys(labels)
    )

    if not labels:
        return ""

    if len(labels) == 1:
        return labels[0]

    if len(labels) == 2:
        return (
            f"{labels[0]} and {labels[1]}"
        )

    return (
        ", ".join(labels[:-1])
        + f", and {labels[-1]}"
    )


# ------------------------------------------------------------------
# Short RDF node labels
# ------------------------------------------------------------------

def _simple_node_label(node):
    """
    Produce a short readable representation of an RDF node.

    Examples:

        http://www.w3.org/ns/odrl/2/use
            -> use

        did:web:example.com:acme
            -> acme

        http://example.com/music/song.mp3
            -> song.mp3

        blank node
            -> ""
    """

    if node is None:
        return ""

    # --------------------------------------------------------------
    # Blank nodes
    #
    # Never expose internal RDF blank-node identifiers.
    # --------------------------------------------------------------

    if not isinstance(node, (URIRef, Literal)):
        return ""

    if isinstance(node, Literal):
        return str(node)

    uri = str(node)

    # --------------------------------------------------------------
    # ODRL vocabulary
    # --------------------------------------------------------------

    if uri.startswith(str(ODRL)):
        return uri[len(str(ODRL)):]

    # --------------------------------------------------------------
    # did:web / DID-style identifiers
    #
    # did:web:example.com:acme
    # -> acme
    # --------------------------------------------------------------

    if uri.startswith("did:web:"):

        parts = uri.split(":")

        if len(parts) > 2:
            return parts[-1]

    # --------------------------------------------------------------
    # Fragment identifiers
    # --------------------------------------------------------------

    if "#" in uri:
        return uri.rsplit("#", 1)[1]

    # --------------------------------------------------------------
    # Normal HTTP URI
    # --------------------------------------------------------------

    if "/" in uri:
        return uri.rstrip("/").rsplit("/", 1)[1]

    return uri


# ------------------------------------------------------------------
# SHACL vocabulary labels
# ------------------------------------------------------------------

def _shacl_term_label(term):
    """
    Convert SHACL vocabulary terms into readable names.
    """

    if term is None:
        return ""

    text = str(term)

    if text.startswith(str(SH)):
        text = text[len(str(SH)):]

    return (
        text
        .replace("ConstraintComponent", "")
        .replace("_", " ")
    )


# ------------------------------------------------------------------
# SHACL property labels
# ------------------------------------------------------------------

def _shacl_path_label(path):
    """
    Convert an RDF predicate/path into a readable property name.
    """

    if path is None:
        return "Constraint"

    if path == RDF.first:
        return "List"

    if path == RDF.rest:
        return "List"

    label = _simple_node_label(path)

    if not label:
        return "Constraint"

    return (
        label
        .replace("_", " ")
        .capitalize()
    )


# ------------------------------------------------------------------
# Fallback pySHACL message cleanup
# ------------------------------------------------------------------

def _clean_shacl_message(message):
    """
    Clean up common pySHACL wording.
    """

    message = message.strip()

    if (
        message.startswith("More than ")
        and " values on " in message
    ):

        return (
            message
            .replace(
                "More than ",
                "This rule has more than ",
                1
            )
            .replace(
                " values on ",
                " value(s) for ",
                1
            )
            + "."
        )

    return message