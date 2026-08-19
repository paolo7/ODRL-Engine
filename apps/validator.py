import streamlit as st
import os
import tempfile

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import validate
from common.streamlit_style import apply_style


# ---------------------------------------------------------
# Streamlit Configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="ODRL Policy Validator",
    layout="wide"
)

apply_style()

st.markdown("## ODRL Policy Validator")

st.markdown(
    """
    Upload or paste an **ODRL Policy** and validate it.

    The validator checks both whether the input is valid RDF and
    whether the RDF graph conforms to the ODRL specification.
    """
)


# ---------------------------------------------------------
# Session State
# ---------------------------------------------------------

if "policy_text" not in st.session_state:
    st.session_state.policy_text = ""

if "policy_upload_id" not in st.session_state:
    st.session_state.policy_upload_id = None

if "policy_suffix" not in st.session_state:
    st.session_state.policy_suffix = ".ttl"


# ---------------------------------------------------------
# Helper: Display Validation Results
# ---------------------------------------------------------

def display_validation_results(validation_result):
    """
    Display the result returned by validate.validate_ODRL()
    in a structured Streamlit UI.
    """

    is_valid_rdf = validation_result.get(
        "is_valid_RDF",
        False
    )

    is_valid_odrl = validation_result.get(
        "is_valid_ODRL"
    )

    # -----------------------------------------------------
    # Main validation status
    # -----------------------------------------------------

    st.divider()

    st.subheader("Validation Result")

    col1, col2 = st.columns(2)

    with col1:

        if is_valid_rdf:
            st.success("✅ Valid RDF")
        else:
            st.error("❌ Invalid RDF")

    with col2:

        if is_valid_odrl is True:
            st.success("✅ Valid ODRL")
        elif is_valid_odrl is False:
            st.error("❌ Invalid ODRL")
        else:
            st.warning("⚠️ ODRL validation not performed")


    # -----------------------------------------------------
    # Basic information
    # -----------------------------------------------------

    with st.expander("Validation details", expanded=False):

        file_format = validation_result.get("file_format")

        if file_format is not None:
            st.write(
                f"**File format:** `{file_format}`"
            )

        graph_size = validation_result.get(
            "ODRL_graph_size"
        )

        if graph_size is not None:
            st.write(
                f"**RDF graph size:** `{graph_size}` triples"
            )


    # -----------------------------------------------------
    # ODRL statistics
    # -----------------------------------------------------

    if is_valid_odrl:

        st.subheader("ODRL Statistics")

        odrl_stats_text = validation_result.get(
            "odrl_stats_text"
        )

        if odrl_stats_text:
            st.info(odrl_stats_text)

        odrl_stats = validation_result.get(
            "odrl_stats"
        )

        if odrl_stats:

            with st.expander(
                "ODRL Statistics Details",
                expanded=False
            ):
                st.json(odrl_stats)


    # -----------------------------------------------------
    # Errors
    # -----------------------------------------------------

    errors = validation_result.get(
        "errors",
        []
    )

    if errors:

        with st.expander(
            f"Errors ({len(errors)})",
            expanded=False
        ):

            for error in errors:
                st.error(error)


    # -----------------------------------------------------
    # Warnings
    # -----------------------------------------------------

    warnings = validation_result.get(
        "warnings",
        []
    )

    if warnings:

        with st.expander(
            f"Warnings ({len(warnings)})",
            expanded=False
        ):

            for warning in warnings:
                st.warning(warning)


    # -----------------------------------------------------
    # Information
    # -----------------------------------------------------

    info = validation_result.get(
        "info",
        []
    )

    if info:

        with st.expander(
            f"Information ({len(info)})",
            expanded=False
        ):

            for message in info:
                st.info(message)


    # -----------------------------------------------------
    # SHACL validation report
    # -----------------------------------------------------

    shacl_report = validation_result.get(
        "shacl_validation_report"
    )

    if shacl_report:

        with st.expander(
            "SHACL Validation Report",
            expanded=False
        ):

            st.text(
                str(shacl_report)
            )


    # -----------------------------------------------------
    # Other returned fields
    # -----------------------------------------------------

    known_fields = {
        "is_valid_RDF",
        "is_valid_ODRL",
        "file_format",
        "ODRL_graph_size",
        "odrl_stats",
        "odrl_stats_text",
        "errors",
        "warnings",
        "info",
        "shacl_validation_report",
    }

    other_fields = {
        key: value
        for key, value in validation_result.items()
        if key not in known_fields
    }

    if other_fields:

        with st.expander(
            "Other Validation Results",
            expanded=False
        ):

            for key, value in other_fields.items():

                with st.expander(
                    key,
                    expanded=False
                ):

                    if isinstance(
                        value,
                        (dict, list)
                    ):
                        st.json(value)
                    else:
                        st.write(value)


# ---------------------------------------------------------
# Helper: Save Uploaded File
# ---------------------------------------------------------

def save_uploaded_file(uploaded_file):
    """
    Save an uploaded Streamlit file temporarily because
    validate.validate_ODRL_from_file() expects a filename.
    """

    suffix = Path(
        uploaded_file.name
    ).suffix.lower()

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    temp.write(
        uploaded_file.getvalue()
    )

    temp.close()

    return temp.name


# ---------------------------------------------------------
# Upload Policy
# ---------------------------------------------------------

st.subheader("Upload ODRL Policy")

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


# ---------------------------------------------------------
# Automatically process a NEW upload
# ---------------------------------------------------------

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

        # Save the uploaded file and validate it immediately.
        policy_path = None

        try:

            policy_path = save_uploaded_file(
                uploaded_policy
            )

            with st.spinner(
                "Validating uploaded ODRL policy..."
            ):

                validation_result = (
                    validate.validate_ODRL_from_file(
                        policy_path
                    )
                )

            st.success(
                f"Uploaded: {uploaded_policy.name}"
            )

            display_validation_results(
                validation_result
            )

        except Exception as e:

            st.error(
                "Validation of the uploaded policy failed."
            )

            st.exception(e)

        finally:

            if (
                policy_path
                and os.path.exists(policy_path)
            ):
                os.remove(policy_path)


# ---------------------------------------------------------
# Policy Text
# ---------------------------------------------------------

st.subheader("ODRL Policy")

policy_text = st.text_area(
    "Policy Text",
    height=450,
    key="policy_text",
    label_visibility="collapsed"
)


# ---------------------------------------------------------
# Validate Button
# ---------------------------------------------------------

validate_button = st.button(
    "Validate Policy",
    use_container_width=True
)


# ---------------------------------------------------------
# Manual Validation
# ---------------------------------------------------------

if validate_button:

    policy_text = st.session_state.policy_text

    if not policy_text.strip():

        st.warning(
            "⚠️ Please paste or upload an ODRL policy first."
        )

        st.stop()

    try:

        with st.spinner(
            "Validating ODRL policy..."
        ):

            # IMPORTANT:
            # Manual validation uses the string-based validator.
            validation_result = (
                validate.validate_ODRL_from_string(
                    policy_text
                )
            )

        display_validation_results(
            validation_result
        )

    except Exception as e:

        st.error(
            "Validation failed."
        )

        st.exception(e)