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
# Page Header
# ---------------------------------------------------------

st.markdown("## ODRL Policy Validator")

st.markdown(
    """
    Upload or paste an **ODRL Policy** and validate it.

    The validator checks both whether the input is valid RDF and
    whether the RDF graph conforms to the ODRL specification.
    
    This validator verifies whether ODRL policies are in a correct *atomic*
    format. ODRL policies in the [compound or compact](https://www.w3.org/TR/odrl-model/#composition)
    formats will be detected as invalid.
    
    Warning, this is an experimental feature. The validator will detect 
    common ODRL data model violations, but it is not guaranteed to do so 
    in all cases. 
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

if "validation_result" not in st.session_state:
    st.session_state.validation_result = None

if "validation_source" not in st.session_state:
    st.session_state.validation_source = None

if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None


# ---------------------------------------------------------
# Helper: Display Validation Results
# ---------------------------------------------------------

def display_validation_results(validation_result):
    """
    Display the result returned by validate.validate_ODRL()
    in a structured Streamlit UI.
    """

    if not validation_result:
        return

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
            st.warning(
                "⚠️ ODRL validation not performed"
            )


    # -----------------------------------------------------
    # Basic information
    # -----------------------------------------------------

    with st.expander(
        "Validation details",
        expanded=False
    ):

        file_format = validation_result.get(
            "file_format"
        )

        if file_format is not None:

            st.write(
                f"**File format:** `{file_format}`"
            )

        graph_size = validation_result.get(
            "ODRL_graph_size"
        )

        if graph_size is not None:

            st.write(
                f"**RDF graph size:** "
                f"`{graph_size}` triples"
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

            st.info(
                odrl_stats_text
            )

        odrl_stats = validation_result.get(
            "odrl_stats"
        )

        if odrl_stats:

            with st.expander(
                "ODRL Statistics Details",
                expanded=False
            ):

                st.json(
                    odrl_stats
                )


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

                st.error(
                    error
                )


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

                st.warning(
                    warning
                )


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

                st.info(
                    message
                )


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
                    str(key),
                    expanded=False
                ):

                    if isinstance(
                        value,
                        (dict, list)
                    ):

                        st.json(
                            value
                        )

                    else:

                        st.write(
                            value
                        )


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

    try:

        temp.write(
            uploaded_file.getvalue()
        )

        temp.flush()

    finally:

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

    # Streamlit provides file_id for UploadedFile objects.
    # Only process the file when it is actually a new upload.
    if (
        uploaded_policy.file_id
        != st.session_state.policy_upload_id
    ):

        st.session_state.policy_upload_id = (
            uploaded_policy.file_id
        )

        # ---------------------------------------------
        # Populate the text area
        # ---------------------------------------------

        try:

            uploaded_content = (
                uploaded_policy
                .getvalue()
                .decode("utf-8")
            )

        except UnicodeDecodeError:

            uploaded_content = (
                uploaded_policy
                .getvalue()
                .decode(
                    "utf-8",
                    errors="replace"
                )
            )

        st.session_state.policy_text = (
            uploaded_content
        )

        st.session_state.policy_suffix = (
            Path(uploaded_policy.name)
            .suffix
            .lower()
        )

        st.session_state.uploaded_filename = (
            uploaded_policy.name
        )

        # ---------------------------------------------
        # Validate uploaded policy
        # ---------------------------------------------

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

            st.session_state.validation_result = (
                validation_result
            )

            st.session_state.validation_source = (
                "upload"
            )

        except Exception as e:

            st.session_state.validation_result = None

            st.session_state.validation_source = (
                "upload_error"
            )

            st.session_state.uploaded_filename = (
                uploaded_policy.name
            )

            st.error(
                "Validation of the uploaded policy failed."
            )

            st.exception(e)

        finally:

            if (
                policy_path
                and os.path.exists(policy_path)
            ):

                try:

                    os.remove(
                        policy_path
                    )

                except OSError:

                    pass


# ---------------------------------------------------------
# Policy Text
# ---------------------------------------------------------

st.subheader("ODRL Policy")

policy_text = st.text_area(
    "Policy Text",
    height=250,
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

    policy_text = (
        st.session_state.policy_text
    )

    if not policy_text.strip():

        st.session_state.validation_result = None

        st.session_state.validation_source = (
            "empty"
        )

    else:

        try:

            with st.spinner(
                "Validating ODRL policy..."
            ):

                validation_result = (
                    validate.validate_ODRL_from_string(
                        policy_text
                    )
                )

            st.session_state.validation_result = (
                validation_result
            )

            st.session_state.validation_source = (
                "manual"
            )

        except Exception as e:

            st.session_state.validation_result = None

            st.session_state.validation_source = (
                "manual_error"
            )

            st.error(
                "Validation failed."
            )

            st.exception(e)


# ---------------------------------------------------------
# Validation Result Area
# ---------------------------------------------------------

if (
    st.session_state.validation_source
    == "upload"
):

    if st.session_state.uploaded_filename:

        st.success(
            f"Uploaded: "
            f"{st.session_state.uploaded_filename}"
        )

    display_validation_results(
        st.session_state.validation_result
    )


elif (
    st.session_state.validation_source
    == "manual"
):

    display_validation_results(
        st.session_state.validation_result
    )


elif (
    st.session_state.validation_source
    == "empty"
):

    st.warning(
        "⚠️ Please paste or upload an ODRL policy first."
    )


elif (
    st.session_state.validation_source
    == "upload_error"
):

    st.error(
        "The uploaded ODRL policy could not be validated."
    )


elif (
    st.session_state.validation_source
    == "manual_error"
):

    st.error(
        "The ODRL policy could not be validated."
    )