import streamlit as st

import tempfile
import os
import multiprocessing
import json
import pandas as pd

from io import StringIO
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.streamlit_style import apply_style
import ODRL_Evaluator as Evaluator
import rdf_utils
from rdf_utils import extract_features_list_from_policy


# ============================================================
# CONFIG
# ============================================================

EVAL_TIMEOUT_SECONDS = int(
    os.environ.get(
        "ODRL_ACCESS_REQUEST_EVAL_TIMEOUT_SECONDS",
        "30"
    )
)

COLUMNS_TIMEOUT_SECONDS = int(
    os.environ.get(
        "ODRL_ACCESS_REQUEST_COLUMNS_TIMEOUT_SECONDS",
        "15"
    )
)

# ============================================================
# HUMAN-READABLE ACCESS REQUEST RESULT HELPERS
# ============================================================

ODRL_NS = "http://www.w3.org/ns/odrl/2/"

OPERATOR_LABELS = {
    f"{ODRL_NS}eq": "equal to",
    f"{ODRL_NS}neq": "not equal to",
    f"{ODRL_NS}lt": "less than",
    f"{ODRL_NS}lteq": "less than or equal to",
    f"{ODRL_NS}gt": "greater than",
    f"{ODRL_NS}gteq": "greater than or equal to",
    f"{ODRL_NS}isAnyOf": "one of",
    f"{ODRL_NS}isNoneOf": "none of",
    f"{ODRL_NS}hasPart": "has part",
    f"{ODRL_NS}isPartOf": "is part of",
    f"{ODRL_NS}isAllOf": "contains all of",
}


# ============================================================
# CSS FOR RULE RESULT CONTAINERS
# ============================================================

st.markdown(
    """
    <style>

    .odrl-rule {
        border-radius: 0.5rem;
        padding: 1rem 1.25rem 1.25rem 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(0, 0, 0, 0.08);
    }

    .odrl-rule-green {
        background-color: rgba(40, 167, 69, 0.12);
        border-left: 5px solid #28a745;
    }

    .odrl-rule-yellow {
        background-color: rgba(255, 193, 7, 0.16);
        border-left: 5px solid #ffc107;
    }

    .odrl-rule-red {
        background-color: rgba(220, 53, 69, 0.12);
        border-left: 5px solid #dc3545;
    }

    .odrl-rule-message {
        font-weight: 500;
        margin-bottom: 0.75rem;
    }

    .odrl-rule-heading {
        font-weight: 600;
        margin-top: 0.75rem;
        margin-bottom: 0.25rem;
    }

    .odrl-rule-list {
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
        padding-left: 1.5rem;
    }

    .odrl-rule-list li {
        margin-bottom: 0.2rem;
    }

    .odrl-original-rule {
        margin-top: 1rem;
        padding-top: 0.75rem;
        border-top: 1px solid rgba(0, 0, 0, 0.12);
    }

    .odrl-original-rule-label {
        font-size: 0.8rem;
        font-weight: 600;
        opacity: 0.7;
        margin-bottom: 0.25rem;
    }

    .odrl-original-rule-text {
        font-size: 0.85rem;
        font-style: italic;
        opacity: 0.75;
        white-space: pre-line;
    }
    
    .odrl-outcome {
        border-radius: 0.5rem;
        padding: 1rem 1.25rem;
        margin: 1rem 0 1.5rem 0;
        border: 1px solid rgba(0, 0, 0, 0.08);
        font-size: 1.15rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .odrl-outcome-granted {
        background-color: rgba(40, 167, 69, 0.12);
        border-left: 5px solid #28a745;
    }

    .odrl-outcome-denied {
        background-color: rgba(220, 53, 69, 0.12);
        border-left: 5px solid #dc3545;
    }

    .odrl-outcome-unknown {
        background-color: rgba(255, 193, 7, 0.16);
        border-left: 5px solid #ffc107;
    }

    .odrl-outcome-icon {
        font-size: 1.5rem;
        line-height: 1;
    }

    .odrl-outcome-explanation {
        margin-top: 0.5rem;
        margin-bottom: 1.5rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


def humanise_iri(iri):
    """
    Convert an IRI into a readable label.

    Important:
    Literal values such as ISO date/time strings are preserved.
    """

    if iri is None:
        return ""

    # --------------------------------------------------------
    # RDFLib values
    # --------------------------------------------------------

    try:
        from rdflib import URIRef, Literal

        if isinstance(iri, Literal):
            return str(iri)

        if isinstance(iri, URIRef):
            iri = str(iri)

        else:
            iri = str(iri)

    except ImportError:
        iri = str(iri)

    # --------------------------------------------------------
    # ODRL namespace
    # --------------------------------------------------------

    if iri.startswith(ODRL_NS):
        return iri[len(ODRL_NS):]

    # --------------------------------------------------------
    # Only process something as an IRI if it actually starts
    # with an IRI scheme.
    #
    # This is important because:
    #
    #   2027-01-11T11:13:10.665638
    #
    # contains ":" but is NOT an IRI.
    # --------------------------------------------------------

    if not iri.startswith(
        (
            "http://",
            "https://",
            "urn:"
        )
    ):
        return iri

    # --------------------------------------------------------
    # HTTP/HTTPS/URN IRI
    # --------------------------------------------------------

    if "/" in iri:
        iri = iri.rstrip("/").rsplit("/", 1)[-1]

    # Only split ':' after we know this is an IRI.
    if ":" in iri:
        iri = iri.rsplit(":", 1)[-1]

    return iri


def humanise_value(value):
    """
    Convert an ODRL value into readable text.

    Crucially, date/time literals are returned unchanged.
    """

    if isinstance(value, list):
        return ", ".join(
            humanise_value(item)
            for item in value
        )

    try:
        from rdflib import Literal, URIRef

        # ----------------------------------------------------
        # RDF Literal:
        #
        # Preserve lexical representation.
        #
        # Example:
        # 2027-01-11T11:13:10.665638
        #
        # must remain exactly that.
        # ----------------------------------------------------

        if isinstance(value, Literal):
            return str(value)

        # ----------------------------------------------------
        # RDF URI:
        #
        # Humanise it.
        # ----------------------------------------------------

        if isinstance(value, URIRef):
            return humanise_iri(value)

    except ImportError:
        pass

    # --------------------------------------------------------
    # Plain Python strings.
    #
    # IMPORTANT:
    # Do not treat every string containing ':' as an IRI.
    # --------------------------------------------------------

    if isinstance(value, str):

        if value.startswith(
            (
                "http://",
                "https://",
                "urn:"
            )
        ):
            return humanise_iri(value)

        return value

    return str(value)


def humanise_condition(condition):
    """
    Convert one ODRL condition into a human-readable sentence.
    """

    # --------------------------------------------------------
    # Logical condition
    # --------------------------------------------------------

    if (
        isinstance(condition, list)
        and len(condition) == 2
        and isinstance(condition[0], str)
        and isinstance(condition[1], list)
    ):

        logic_op = humanise_iri(
            condition[0]
        )

        subconditions = condition[1]

        readable = [
            humanise_condition(subcondition)
            for subcondition in subconditions
        ]

        if logic_op.endswith("andSequence"):
            return " and then ".join(readable)

        if logic_op.endswith("and"):
            return " and ".join(readable)

        if logic_op.endswith("or"):
            return " or ".join(readable)

        if logic_op.endswith("xone"):
            return (
                "exactly one of "
                + ", ".join(readable)
            )

        return ", ".join(readable)

    # --------------------------------------------------------
    # Normal condition
    # --------------------------------------------------------

    if (
        not isinstance(condition, list)
        or len(condition) != 3
    ):
        return str(condition)

    left, operator, right = condition

    left_text = humanise_iri(left)

    operator_text = OPERATOR_LABELS.get(
        operator,
        humanise_iri(operator)
    )

    right_text = humanise_value(right)

    if operator_text == "equal to":
        return (
            f"{left_text} is equal to "
            f"{right_text}"
        )

    if operator_text == "not equal to":
        return (
            f"{left_text} is not equal to "
            f"{right_text}"
        )

    if operator_text == "less than":
        return (
            f"{left_text} is less than "
            f"{right_text}"
        )

    if operator_text == "less than or equal to":
        return (
            f"{left_text} is less than or equal to "
            f"{right_text}"
        )

    if operator_text == "greater than":
        return (
            f"{left_text} is greater than "
            f"{right_text}"
        )

    if operator_text == "greater than or equal to":
        return (
            f"{left_text} is greater than or equal to "
            f"{right_text}"
        )

    if operator_text == "one of":
        return (
            f"{left_text} is one of "
            f"{right_text}"
        )

    if operator_text == "none of":
        return (
            f"{left_text} is none of "
            f"{right_text}"
        )

    if operator_text == "has part":
        return (
            f"{left_text} has part "
            f"{right_text}"
        )

    if operator_text == "is part of":
        return (
            f"{left_text} is part of "
            f"{right_text}"
        )

    if operator_text == "contains all of":
        return (
            f"{left_text} contains all of "
            f"{right_text}"
        )

    return (
        f"{left_text} must be {operator_text} "
        f"{right_text}"
    )


def humanise_conditions(conditions):
    """
    Convert conditions into human-readable strings.
    """

    if not conditions:
        return []

    return [
        humanise_condition(condition)
        for condition in conditions
    ]


def humanise_duty(duty):
    """
    Convert a duty into a human-readable description.
    """

    if not isinstance(duty, dict):
        return str(duty)

    description = duty.get("description")

    if description:
        return str(description)

    conditions = duty.get(
        "conditions",
        []
    )

    if conditions:
        return " and ".join(
            humanise_conditions(conditions)
        )

    rule_id = (
        duty.get("id")
        or duty.get("rule_id")
    )

    if rule_id:
        return humanise_iri(rule_id)

    return "unspecified duty"


def humanise_duties(duties):
    """
    Convert duties into human-readable strings.
    """

    if not duties:
        return []

    return [
        humanise_duty(duty)
        for duty in duties
    ]

def humanise_rule(rule, rule_type="rule"):
    """
    Generate a human-readable description of an evaluator rule.

    Party eq <party>  -> assignee
    Action eq <action> -> action
    Asset eq <asset>  -> target

    All other conditions are retained as additional conditions.
    """

    if not isinstance(rule, dict):
        return str(rule)

    description = rule.get("description")

    if description:
        return str(description)

    conditions = rule.get("conditions", [])

    PARTY_IRI = f"{ODRL_NS}Party"
    ACTION_IRI = f"{ODRL_NS}Action"
    ASSET_IRI = f"{ODRL_NS}Asset"
    EQ_IRI = f"{ODRL_NS}eq"

    assignee = None
    action = None
    target = None

    additional_conditions = []

    for condition in conditions:

        if (
            not isinstance(condition, list)
            or len(condition) != 3
        ):
            additional_conditions.append(condition)
            continue

        left, operator, right = condition

        left = str(left)
        operator = str(operator)

        if left == PARTY_IRI and operator == EQ_IRI:
            assignee = right
            continue

        if left == ACTION_IRI and operator == EQ_IRI:
            action = right
            continue

        if left == ASSET_IRI and operator == EQ_IRI:
            target = right
            continue

        additional_conditions.append(condition)

    party_text = (
        humanise_value(assignee)
        if assignee is not None
        else "any party"
    )

    action_text = (
        humanise_value(action)
        if action is not None
        else "unspecified action"
    )

    target_text = (
        humanise_value(target)
        if target is not None
        else "any target"
    )

    rule_description = (
        f"{rule_type} for {party_text} "
        f"to perform action {action_text} "
        f"on {target_text}"
    )

    if additional_conditions:

        readable_conditions = humanise_conditions(
            additional_conditions
        )

        rule_description += (
            "\n\nSubject to the following conditions:"
        )

        for condition in readable_conditions:
            rule_description += f"\n- {condition}"

    return rule_description


# ============================================================
# RULE CONTENT RENDERING
# ============================================================

def render_condition_bullets(conditions):
    """
    Render conditions as Markdown bullets.
    """

    readable_conditions = humanise_conditions(
        conditions
    )

    if not readable_conditions:
        return

    for condition in readable_conditions:
        st.markdown(
            f"- {condition}"
        )


def render_duty_bullets(duties):
    """
    Render duties as Markdown bullets.
    """

    readable_duties = humanise_duties(
        duties
    )

    if not readable_duties:
        return

    for duty in readable_duties:
        st.markdown(
            f"- {duty}"
        )


# ============================================================
# EVALUATION NOTIFICATIONS
# ============================================================

def render_evaluation_notifications(payload):
    """
    Render all matched permissions and prohibitions.

    Each complete result is rendered as a single HTML block so
    that the message, conditions and original rule all appear
    inside the same coloured background.
    """

    permissions = payload.get(
        "permissions_matched",
        []
    )

    prohibitions = payload.get(
        "prohibitions_matched",
        []
    )

    displayed = False

    # ========================================================
    # Helper for safely inserting text into HTML
    # ========================================================

    def escape_html(value):
        import html
        return html.escape(str(value))

    # ========================================================
    # PERMISSIONS
    # ========================================================

    for permission_match in permissions:

        rule = permission_match.get(
            "rule",
            {}
        )

        conditions = permission_match.get(
            "conditions",
            []
        )

        duties = permission_match.get(
            "duties",
            []
        )

        # ----------------------------------------------------
        # Determine colour / message
        # ----------------------------------------------------

        if not conditions and not duties:

            css_class = "odrl-rule-green"

            message = (
                "Your access request is explicitly "
                "granted by a rule."
            )

        else:

            css_class = "odrl-rule-yellow"

            message = (
                "Your access request can be granted "
                "by a permission rule if the following "
                "conditions hold:"
            )

        # ----------------------------------------------------
        # Build HTML
        # ----------------------------------------------------

        html_parts = []

        html_parts.append(
            f'<div class="odrl-rule {css_class}">'
        )

        # Main message

        html_parts.append(
            f'<div class="odrl-rule-message">'
            f'{escape_html(message)}'
            f'</div>'
        )

        # ----------------------------------------------------
        # Conditions
        # ----------------------------------------------------

        if conditions:

            html_parts.append(
                '<ul class="odrl-rule-list">'
            )

            for condition in humanise_conditions(
                conditions
            ):

                html_parts.append(
                    f'<li>{escape_html(condition)}</li>'
                )

            html_parts.append(
                '</ul>'
            )

        # ----------------------------------------------------
        # Duties
        # ----------------------------------------------------

        if duties:

            html_parts.append(
                '<div class="odrl-rule-heading">'
                'Subject to fulfillment of duties:'
                '</div>'
            )

            html_parts.append(
                '<ul class="odrl-rule-list">'
            )

            for duty in humanise_duties(duties):

                html_parts.append(
                    f'<li>{escape_html(duty)}</li>'
                )

            html_parts.append(
                '</ul>'
            )

        # ----------------------------------------------------
        # Original rule
        # ----------------------------------------------------

        rule_description = humanise_rule(
            rule,
            rule_type="permission"
        )

        html_parts.append(
            '<div class="odrl-original-rule">'
            '<div class="odrl-original-rule-label">'
            'Original Permission'
            '</div>'
            '<div class="odrl-original-rule-text">'
            + escape_html(rule_description)
            + '</div>'
              '</div>'
        )

        html_parts.append(
            '</div>'
        )

        st.markdown(
            "".join(html_parts),
            unsafe_allow_html=True
        )

        displayed = True

    # ========================================================
    # PROHIBITIONS
    # ========================================================

    for prohibition_match in prohibitions:

        rule = prohibition_match.get(
            "rule",
            {}
        )

        conditions = prohibition_match.get(
            "conditions",
            []
        )

        # ----------------------------------------------------
        # Determine colour / message
        # ----------------------------------------------------

        if conditions:

            css_class = "odrl-rule-yellow"

            message = (
                "Your access request might be prohibited "
                "by a rule if the following conditions hold:"
            )

        else:

            css_class = "odrl-rule-red"

            message = (
                "Your access request is explicitly "
                "prohibited by a rule."
            )

        # ----------------------------------------------------
        # Build HTML
        # ----------------------------------------------------

        html_parts = []

        html_parts.append(
            f'<div class="odrl-rule {css_class}">'
        )

        html_parts.append(
            f'<div class="odrl-rule-message">'
            f'{escape_html(message)}'
            f'</div>'
        )

        # ----------------------------------------------------
        # Conditions
        # ----------------------------------------------------

        if conditions:

            html_parts.append(
                '<ul class="odrl-rule-list">'
            )

            for condition in humanise_conditions(
                conditions
            ):

                html_parts.append(
                    f'<li>{escape_html(condition)}</li>'
                )

            html_parts.append(
                '</ul>'
            )

        # ----------------------------------------------------
        # Original prohibition
        # ----------------------------------------------------

        rule_description = humanise_rule(
            rule,
            rule_type="prohibition"
        )

        html_parts.append(
            '<div class="odrl-original-rule">'
            '<div class="odrl-original-rule-label">'
            'Original Prohibition'
            '</div>'
            '<div class="odrl-original-rule-text">'
            + escape_html(rule_description)
            + '</div>'
              '</div>'
        )

        html_parts.append(
            '</div>'
        )

        st.markdown(
            "".join(html_parts),
            unsafe_allow_html=True
        )

        displayed = True

    return displayed



# ============================================================
# WORKER FUNCTIONS
# ============================================================

def _run_extract_columns(policy_path, result_queue):
    """
    Extract the feature IRIs from an ODRL policy.
    """
    try:
        graph = rdf_utils.load(policy_path)[0]

        features = extract_features_list_from_policy(graph)

        column_names = [
            feature["iri"]
            for feature in features
        ]

        result_queue.put(("ok", column_names))

    except Exception as e:
        result_queue.put(("error", str(e)))


def _run_extract_policy_info(policy_path, result_queue):
    """
    Extract both features and actions from an ODRL policy.

    The feature extraction is the same mechanism used by the existing
    evaluator. Actions are extracted directly from the policy graph.
    """
    try:
        graph = rdf_utils.load(policy_path)[0]

        features = extract_features_list_from_policy(graph)

        column_names = [
            feature["iri"]
            for feature in features
        ]

        # ----------------------------------------------------
        # Extract actions from the policy.
        #
        # We use the RDF graph directly rather than depending
        # on the internal representation returned by
        # extract_rule_list_from_policy().
        # ----------------------------------------------------

        ODrl_ACTION = rdf_utils.ODRL_NS["action"] \
            if hasattr(rdf_utils, "ODRL_NS") else None

        # More robustly use the explicit IRI.
        ACTION_PREDICATE = (
            "http://www.w3.org/ns/odrl/2/action"
        )

        RDF_VALUE = (
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#value"
        )

        actions = set()

        for subject, predicate, obj in graph:

            if str(predicate) != ACTION_PREDICATE:
                continue

            # ODRL actions are normally represented as a blank node
            # containing rdf:value.
            action_node = obj

            for _, value_predicate, value in graph:
                if (
                    _ == action_node
                    and str(value_predicate) == RDF_VALUE
                ):
                    actions.add(str(value))

        # ----------------------------------------------------
        # Fallback:
        #
        # If actions were represented directly as IRIs rather
        # than rdf:value blank nodes, retain them as well.
        # ----------------------------------------------------

        for subject, predicate, obj in graph:
            if str(predicate) == ACTION_PREDICATE:
                if str(obj).startswith(
                    "http://www.w3.org/ns/odrl/2/"
                ):
                    actions.add(str(obj))

        result_queue.put(
            (
                "ok",
                {
                    "columns": column_names,
                    "actions": sorted(actions)
                }
            )
        )

    except Exception as e:
        result_queue.put(("error", str(e)))


def _run_access_request_evaluation(
    access_request_string,
    policy_string,
    state_of_the_world_string,
    result_queue
):
    """
    Evaluate the prospective access request.
    """
    try:

        result = Evaluator.evaluate_ODRL_access_request_from_string(
            access_request_string,
            policy_string,
            state_of_the_world_string=state_of_the_world_string
        )

        result_queue.put(("ok", result))

    except Exception as e:
        result_queue.put(("error", str(e)))


def _run_with_timeout(target, args, timeout_seconds):
    """
    Runs target in a separate process and hard-kills it if it
    exceeds timeout_seconds.

    Returns:
        ("ok", value)
        ("error", message)
        ("timeout", None)
    """

    result_queue = multiprocessing.Queue()

    proc = multiprocessing.Process(
        target=target,
        args=(*args, result_queue)
    )

    proc.start()

    proc.join(timeout=timeout_seconds)

    if proc.is_alive():
        proc.terminate()
        proc.join()

        return ("timeout", None)

    if result_queue.empty():
        return (
            "error",
            "Evaluation process terminated unexpectedly."
        )

    return result_queue.get()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

ACTION_IRI = "http://www.w3.org/ns/odrl/2/Action"


def make_access_request_json(form_values):
    """
    Convert the generated form into the JSON representation
    expected by evaluate_ODRL_access_request_from_string().
    """

    request = {}

    for key, value in form_values.items():

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        request[key] = value

    return json.dumps(
        request,
        indent=2
    )


def display_action_name(action_iri):
    """
    Display a friendlier action name while retaining the full
    IRI as the actual selectbox value.
    """

    if action_iri.startswith(
        "http://www.w3.org/ns/odrl/2/"
    ):
        return action_iri[
            len("http://www.w3.org/ns/odrl/2/"):
        ]

    return action_iri


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="ODRL Access Request Evaluator",
    layout="wide"
)

apply_style()

st.markdown("## ODRL Access Request Evaluator")

st.markdown(
    "Create an access request from an ODRL policy and evaluate "
    "whether the request matches the policy's permissions and "
    "prohibitions."
)

st.markdown(
    """
    Instructions:
    1) Upload an ODRL Policy
    2) Optionally, upload a State of the World object if you want to factor in previously executed duties.
    3) Fill in the `Access Request Form`, to specify the action you want permission for.
    4) As an alternative to 3), you can upload an access request as a JSON file.
    5) Press the `Evaluate Access Request` button
    6) The result of the evaluation of the access request will be shown below. Green and Red reports signify permissions
    or prohibitions that directly affect your request. Yellow reports signify permissions and prohibitions that might
    affect your access request, depending on certain conditions. For example, a prohibition might only apply if the value
    of a feature you left blank has a value sufficiently low, or a permission might apply only if you are going to fulfill
    a certain duty.
    """
)

st.markdown(
    """
    Depending on the use case, an access request can be granted depending on different interpretations of the policy. 
    This evaluator does not mandate specific semantics (such as only accept requests if there is an explicit permission, 
    or only accept requests if there is no explicit prohibition, or etc.) but provides the necessary information to make
    a decision based on domain specific requirements.
    """
)


# ============================================================
# SESSION STATE
# ============================================================

if "policy_text" not in st.session_state:
    st.session_state.policy_text = ""

if "sotw_text" not in st.session_state:
    st.session_state.sotw_text = ""

if "access_request_text" not in st.session_state:
    st.session_state.access_request_text = "{}"

if "policy_upload_id" not in st.session_state:
    st.session_state.policy_upload_id = None

if "sotw_upload_id" not in st.session_state:
    st.session_state.sotw_upload_id = None

if "access_request_upload_id" not in st.session_state:
    st.session_state.access_request_upload_id = None

if "policy_suffix" not in st.session_state:
    st.session_state.policy_suffix = ".ttl"

if "access_request_form_generated" not in st.session_state:
    st.session_state.access_request_form_generated = False

if "access_request_features" not in st.session_state:
    st.session_state.access_request_features = []

if "access_request_actions" not in st.session_state:
    st.session_state.access_request_actions = []

if "access_request_form_values" not in st.session_state:
    st.session_state.access_request_form_values = {}

if "evaluation_result_text" not in st.session_state:
    st.session_state.evaluation_result_text = ""

if "evaluation_accept_decision" not in st.session_state:
    st.session_state.evaluation_accept_decision = None

if "evaluation_accept_explanation" not in st.session_state:
    st.session_state.evaluation_accept_explanation = []

# ============================================================
# ABCD LAYOUT
# ============================================================

col_left, col_right = st.columns(2)


# ============================================================
# A — POLICY
# ============================================================

with col_left:

    st.subheader("ODRL Policy")

    uploaded_policy = st.file_uploader(
        "Upload Policy File",
        type=[
            "ttl",
            "json",
            "jsonld",
            "rdf",
            "xml",
            "nt",
            "nq",
            "trig",
            "trix",
        ],
        label_visibility="collapsed",
        key="policy_upload"
    )

    if uploaded_policy is not None:

        if (
            uploaded_policy.file_id
            != st.session_state.policy_upload_id
        ):

            st.session_state.policy_upload_id = (
                uploaded_policy.file_id
            )

            st.session_state.policy_text = (
                uploaded_policy
                .getvalue()
                .decode("utf-8")
            )

            st.session_state.policy_suffix = (
                Path(uploaded_policy.name)
                .suffix
                .lower()
            )

            # A new policy means the old generated form is no
            # longer necessarily valid.
            st.session_state.access_request_form_generated = False
            st.session_state.access_request_features = []
            st.session_state.access_request_actions = []
            st.session_state.access_request_form_values = {}

            st.rerun()

    st.text_area(
        "Policy Text",
        height=400,
        key="policy_text"
    )


# ============================================================
# C — STATE OF THE WORLD
# ============================================================

with col_left:

    st.subheader("State of the World")

    uploaded_sotw = st.file_uploader(
        "Upload SotW CSV",
        type=["csv"],
        label_visibility="collapsed",
        key="sotw_upload"
    )

    if uploaded_sotw is not None:

        if (
            uploaded_sotw.file_id
            != st.session_state.sotw_upload_id
        ):

            st.session_state.sotw_upload_id = (
                uploaded_sotw.file_id
            )

            st.session_state.sotw_text = (
                uploaded_sotw
                .getvalue()
                .decode("utf-8")
            )

            st.rerun()

    st.text_area(
        "CSV Text",
        height=400,
        key="sotw_text"
    )


# ============================================================
# B — ACCESS REQUEST FORM
# ============================================================

with col_right:

    st.subheader("Access Request Form")

    generate_form = st.button(
        "Generate Access Request Form",
        use_container_width=True
    )

    # --------------------------------------------------------
    # Generate the form.
    #
    # This also happens automatically when a policy has just
    # been uploaded.
    # --------------------------------------------------------

    if (
        generate_form
        or (
            st.session_state.policy_upload_id is not None
            and not st.session_state.access_request_form_generated
            and st.session_state.policy_text.strip()
        )
    ):

        policy_path = None

        try:

            policy_suffix = (
                st.session_state.policy_suffix
            )

            with tempfile.NamedTemporaryFile(
                suffix=policy_suffix,
                delete=False,
                mode="w",
                encoding="utf-8"
            ) as policy_file:

                policy_file.write(
                    st.session_state.policy_text
                )

                policy_path = policy_file.name

            with st.spinner(
                "Reading policy features and actions..."
            ):

                status, payload = _run_with_timeout(
                    _run_extract_policy_info,
                    (policy_path,),
                    COLUMNS_TIMEOUT_SECONDS
                )

            if status == "timeout":

                st.error(
                    f"⚠️ Timed out after "
                    f"{COLUMNS_TIMEOUT_SECONDS} seconds "
                    "while reading the policy."
                )

            elif status == "error":

                st.error(
                    "Error, the policy input field does not "
                    "contain a valid ODRL policy."
                )

            else:

                features = payload["columns"]
                actions = payload["actions"]

                # ------------------------------------------------
                # Put Action first.
                #
                # Remove it from the normal feature list so that
                # it isn't displayed twice.
                # ------------------------------------------------

                other_features = [
                    feature
                    for feature in features
                    if feature != ACTION_IRI
                ]

                ordered_features = [
                    ACTION_IRI
                ] + other_features

                st.session_state.access_request_features = (
                    ordered_features
                )

                st.session_state.access_request_actions = (
                    actions
                )

                # ------------------------------------------------
                # Initialise form values.
                #
                # Preserve values already entered if possible.
                # ------------------------------------------------

                old_values = (
                    st.session_state
                    .access_request_form_values
                )

                new_values = {}

                for feature in ordered_features:

                    if feature in old_values:
                        new_values[feature] = (
                            old_values[feature]
                        )

                    elif feature == ACTION_IRI:

                        if actions:
                            new_values[feature] = actions[0]
                        else:
                            new_values[feature] = ""

                    else:
                        new_values[feature] = ""

                st.session_state.access_request_form_values = (
                    new_values
                )

                st.session_state.access_request_form_generated = True

                # ------------------------------------------------
                # Immediately generate JSON from the form.
                # ------------------------------------------------

                st.session_state.access_request_text = (
                    make_access_request_json(
                        new_values
                    )
                )

        except Exception as e:

            st.error(
                f"⚠️ Error generating access request form: {e}"
            )

        finally:

            if (
                policy_path
                and os.path.exists(policy_path)
            ):
                os.remove(policy_path)

    # --------------------------------------------------------
    # Render generated form
    # --------------------------------------------------------

    if st.session_state.access_request_form_generated:

        st.markdown("#### Request fields")

        features = (
            st.session_state
            .access_request_features
        )

        actions = (
            st.session_state
            .access_request_actions
        )

        for feature in features:

            # --------------------------------------------
            # Action gets a dropdown.
            # --------------------------------------------

            if feature == ACTION_IRI:

                current_value = (
                    st.session_state
                    .access_request_form_values
                    .get(feature, "")
                )

                if actions:

                    if current_value not in actions:
                        current_value = actions[0]

                    selected_action = st.selectbox(
                        "Action",
                        options=actions,
                        index=actions.index(
                            current_value
                        ),
                        format_func=display_action_name,
                        key="access_request_action_select"
                    )

                    st.session_state \
                        .access_request_form_values[
                            feature
                        ] = selected_action

                else:

                    st.warning(
                        "No actions were found in the policy."
                    )

            # --------------------------------------------
            # All other features are normal text inputs.
            # --------------------------------------------

            else:

                current_value = (
                    st.session_state
                    .access_request_form_values
                    .get(feature, "")
                )

                value = st.text_input(
                    feature,
                    value=current_value,
                    key=f"access_request_feature_{feature}"
                )

                st.session_state \
                    .access_request_form_values[
                        feature
                    ] = value

        # ----------------------------------------------------
        # Every rerun caused by a form-field change reaches
        # here. Rebuild D from the current form values.
        # ----------------------------------------------------

        st.session_state.access_request_text = (
            make_access_request_json(
                st.session_state
                .access_request_form_values
            )
        )


# ============================================================
# D — ACCESS REQUEST JSON
# ============================================================

with col_right:

    st.subheader("Access Request JSON")

    uploaded_access_request = st.file_uploader(
        "Upload Access Request JSON",
        type=["json"],
        label_visibility="collapsed",
        key="access_request_upload"
    )

    if uploaded_access_request is not None:

        if (
            uploaded_access_request.file_id
            != st.session_state.access_request_upload_id
        ):

            st.session_state.access_request_upload_id = (
                uploaded_access_request.file_id
            )

            uploaded_text = (
                uploaded_access_request
                .getvalue()
                .decode("utf-8")
            )

            st.session_state.access_request_text = (
                uploaded_text
            )

            # ------------------------------------------------
            # A manually uploaded JSON request should become
            # the source of truth until the form is generated
            # or changed.
            # ------------------------------------------------

            st.session_state.access_request_form_generated = (
                False
            )

            st.rerun()

    st.text_area(
        "Access Request JSON",
        height=400,
        key="access_request_text"
    )


# ============================================================
# EVALUATION AREA
# ============================================================

st.divider()

evaluate_button = st.button(
    "Evaluate Access Request",
    use_container_width=True
)


# ============================================================
# EVALUATE
# ============================================================

if evaluate_button:

    policy_text = (
        st.session_state.policy_text
    )

    sotw_text = (
        st.session_state.sotw_text
    )

    access_request_text = (
        st.session_state.access_request_text
    )

    # --------------------------------------------------------
    # Validate inputs
    # --------------------------------------------------------

    if not policy_text.strip():

        st.error(
            "⚠️ Please paste or upload an ODRL policy."
        )

        st.stop()

    if not access_request_text.strip():

        st.error(
            "⚠️ Please provide an access request."
        )

        st.stop()

    # Validate JSON before starting the worker.
    try:

        parsed_request = json.loads(
            access_request_text
        )

        if not isinstance(parsed_request, dict):
            raise ValueError(
                "Access request must contain a JSON object."
            )

    except Exception as e:

        st.error(
            f"⚠️ Invalid access request JSON: {e}"
        )

        st.stop()

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    with st.spinner(
        "Evaluating access request..."
    ):

        result_queue = multiprocessing.Queue()

        proc = multiprocessing.Process(
            target=_run_access_request_evaluation,
            args=(
                access_request_text,
                policy_text,
                sotw_text if sotw_text.strip() else None,
                result_queue
            )
        )

        proc.start()

        proc.join(
            timeout=EVAL_TIMEOUT_SECONDS
        )

        if proc.is_alive():

            proc.terminate()
            proc.join()

            status = "timeout"
            payload = None

        elif result_queue.empty():

            status = "error"
            payload = (
                "Evaluation process terminated unexpectedly."
            )

        else:

            status, payload = (
                result_queue.get()
            )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    if status == "timeout":

        st.error(
            f"⚠️ Evaluation timed out after "
            f"{EVAL_TIMEOUT_SECONDS} seconds."
        )

    elif status == "error":

        st.error(
            f"⚠️ Evaluation error: {payload}"
        )

    else:

        result_text = json.dumps(
            payload,
            indent=2,
            default=str
        )

        st.session_state.evaluation_result_text = (
            result_text
        )

        # ----------------------------------------------------
        # Store the evaluator's access decision and explanation
        #
        # Expected evaluator return structure:
        #
        # {
        #     "permissions_matched": ...,
        #     "prohibitions_matched": ...,
        #     "accept_decision": True / False / None,
        #     "accept_explanation": [...]
        # }
        # ----------------------------------------------------

        st.session_state.evaluation_accept_decision = (
            payload.get("accept_decision")
        )

        accept_explanation = payload.get(
            "accept_explanation",
            []
        )

        # Normalise the explanation so the UI can safely render
        # it as a bullet-point list.
        if accept_explanation is None:
            accept_explanation = []

        elif isinstance(accept_explanation, str):
            accept_explanation = [accept_explanation]

        else:
            accept_explanation = list(
                accept_explanation
            )

        st.session_state.evaluation_accept_explanation = (
            accept_explanation
        )


# ============================================================
# EVALUATION OUTCOME
# ============================================================

st.subheader("Evaluation Outcome")

if st.session_state.evaluation_result_text:

    accept_decision = (
        st.session_state.evaluation_accept_decision
    )

    accept_explanation = (
        st.session_state.evaluation_accept_explanation
    )

    # --------------------------------------------------------
    # Determine outcome presentation
    # --------------------------------------------------------

    if accept_decision is True:

        outcome_css_class = (
            "odrl-outcome odrl-outcome-granted"
        )

        outcome_icon = "✅"
        outcome_text = "Request Granted"

    elif accept_decision is False:

        outcome_css_class = (
            "odrl-outcome odrl-outcome-denied"
        )

        outcome_icon = "⛔"
        outcome_text = "Request Denied"

    else:

        outcome_css_class = (
            "odrl-outcome odrl-outcome-unknown"
        )

        outcome_icon = "⚠️"
        outcome_text = "Request Could Not be Computed"

    # --------------------------------------------------------
    # Prominent outcome banner
    # --------------------------------------------------------

    st.markdown(
        f"""
        <div class="{outcome_css_class}">
            <span class="odrl-outcome-icon">
                {outcome_icon}
            </span>
            <span>
                {outcome_text}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # Outcome explanation
    # --------------------------------------------------------

    st.markdown(
        "#### Outcome Explanation"
    )

    if accept_explanation:

        st.markdown(
            '<div class="odrl-outcome-explanation">',
            unsafe_allow_html=True
        )

        for explanation in accept_explanation:
            st.markdown(
                f"- {explanation}"
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )

    else:

        st.info(
            "No outcome explanation was provided."
        )


# ============================================================
# EVALUATION DETAILS
# ============================================================

st.subheader("Evaluation Details")

if st.session_state.evaluation_result_text:

    try:

        result_payload = json.loads(
            st.session_state.evaluation_result_text
        )

        # ----------------------------------------------------
        # Human-readable permission/prohibition details
        # ----------------------------------------------------

        displayed = render_evaluation_notifications(
            result_payload
        )

        if not displayed:
            st.info(
                "No matching permissions or prohibitions "
                "were found for this access request."
            )

        # ----------------------------------------------------
        # Raw result is hidden by default.
        # ----------------------------------------------------

        with st.expander(
            "Show raw evaluation result"
        ):
            st.code(
                st.session_state.evaluation_result_text,
                language="json"
            )

    except Exception as e:

        st.error(
            f"Unable to display evaluation result: {e}"
        )

        with st.expander(
            "Show raw evaluation result"
        ):
            st.code(
                st.session_state.evaluation_result_text,
                language="text"
            )

else:

    st.info(
        "No evaluation has been performed yet."
    )