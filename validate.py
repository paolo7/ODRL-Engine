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


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def save_uploaded_file(uploaded_file):
    """
    Save uploaded Streamlit file temporarily because
    validate expects a filename.
    """
    suffix = os.path.splitext(uploaded_file.name)[1]

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    temp.write(uploaded_file.getvalue())
    temp.close()

    return temp.name


def display_validation_result(validation_result):
    """
    Display the structured validation result in Streamlit.
    """

    is_valid_rdf = validation_result.get("is_valid_RDF", False)
    is_valid_odrl = validation_result.get("is_valid_ODRL")

    # -----------------------------------------------------
    # Main validation status
    # -----------------------------------------------------

    st.subheader("Validation Status")

    col1, col2 = st.columns(2)

    with col1:
        if is_valid_rdf:
            st.success("✓ Valid RDF")
        else:
            st.error("✗ Invalid RDF")

    with col2:
        if is_valid_odrl is True:
            st.success("✓ Valid ODRL")
        elif is_valid_odrl is False:
            st.error("✗ Invalid ODRL")
        else:
            st.warning("— ODRL validation not performed")

    # -----------------------------------------------------
    # Basic information
    # -----------------------------------------------------

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        file_format = validation_result.get("file_format")

        if file_format:
            st.metric(
                "Detected format",
                str(file_format)
            )

    with col2:
        graph_size = validation_result.get("ODRL_graph_size")

        if graph_size is not None:
            st.metric(
                "RDF triples",
                graph_size
            )

    # -----------------------------------------------------
    # ODRL statistics
    # -----------------------------------------------------

    if is_valid_odrl is True:

        st.divider()
        st.subheader("ODRL Statistics")

        stats_text = validation_result.get(
            "odrl_stats_text"
        )

        if stats_text:
            st.text(stats_text)

        stats = validation_result.get("odrl_stats")

        if stats:
            labels = [
                "Policy",
                "Set",
                "Agreement",
                "Offer",
                "Permission",
                "Prohibition",
                "Duty",
                "Constraint"
            ]

            columns = st.columns(len(labels))

            for column, label, value in zip(
                columns,
                labels,
                stats
            ):
                with column:
                    st.metric(label, value)

    # -----------------------------------------------------
    # Detailed validation results
    # -----------------------------------------------------

    st.divider()
    st.subheader("Detailed Results")

    # Errors
    errors = validation_result.get("errors", [])

    with st.expander(
        f"Errors ({len(errors)})",
        expanded=not is_valid_rdf or is_valid_odrl is False
    ):
        if errors:
            for error in errors:
                st.error(error)
        else:
            st.info("No errors.")

    # Warnings
    warnings = validation_result.get("warnings", [])

    with st.expander(
        f"Warnings ({len(warnings)})",
        expanded=False
    ):
        if warnings:
            for warning in warnings:
                st.warning(warning)
        else:
            st.info("No warnings.")

    # Info
    info = validation_result.get("info", [])

    with st.expander(
        f"Information ({len(info)})",
        expanded=False
    ):
        if info:
            for item in info:
                st.info(item)
        else:
            st.info("No additional information.")

    # File format
    with st.expander(
        "File information",
        expanded=False
    ):
        st.json({
            "file_format": validation_result.get("file_format"),
            "ODRL_graph_size": validation_result.get(
                "ODRL_graph_size"
            )
        })

    # SHACL validation report
    shacl_report = validation_result.get(
        "shacl_validation_report"
    )

    if shacl_report:
        with st.expander(
            "SHACL Validation Report",
            expanded=False
        ):
            st.text(shacl_report)

    # Raw result
    with st.expander(
        "Complete validation result",
        expanded=False
    ):
        st.json(validation_result)


# ---------------------------------------------------------
# Main App
# ---------------------------------------------------------

st.title("ODRL Policy Validation")

st.write(
    """
    Upload an ODRL policy file (`.ttl`, `.rdf`, `.jsonld`, etc.).

    The policy will automatically be validated against the
    ODRL SHACL shapes and the validation results will be
    displayed below.
    """
)


# ---------------------------------------------------------
# Upload
# ---------------------------------------------------------

uploaded_policy = st.file_uploader(
    "Upload ODRL Policy",
    type=[
        "ttl",
        "rdf",
        "xml",
        "nt",
        "jsonld",
        "json"
    ]
)


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

if uploaded_policy is not None:

    st.success(
        f"Uploaded: {uploaded_policy.name}"
    )

    policy_path = None

    with st.spinner(
        "Validating ODRL policy..."
    ):

        try:

            # Save uploaded file
            policy_path = save_uploaded_file(
                uploaded_policy
            )

            # Run structured validation
            validation_result = validate.validate_ODRL_from_file(
                policy_path
            )

            st.success(
                "Validation completed successfully."
            )

            st.divider()

            # Display results
            display_validation_result(
                validation_result
            )

        except Exception as e:

            st.error(
                "Validation failed."
            )

            st.exception(e)

        finally:

            # Remove temporary file
            if policy_path is not None:
                try:
                    os.remove(policy_path)
                except OSError:
                    pass