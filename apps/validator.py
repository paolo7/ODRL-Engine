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
    validate.validate_ODRL_from_file() expects a filename.
    """
    suffix = os.path.splitext(uploaded_file.name)[1]

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    temp.write(uploaded_file.getvalue())
    temp.close()

    return temp.name


# ---------------------------------------------------------
# Main App
# ---------------------------------------------------------

st.title("ODRL Policy Validation")

st.write(
    """
    Upload an ODRL policy file (`.ttl`, `.rdf`, `.jsonld`, etc.).

    The policy will be validated for both RDF and ODRL compliance.
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
    ],
    key="odrl_policy_uploader"
)

# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

if uploaded_policy is not None:

    st.success(
        f"Uploaded: {uploaded_policy.name}"
    )

    policy_path = None

    with st.spinner("Validating ODRL policy..."):

        try:

            # Save uploaded file
            policy_path = save_uploaded_file(
                uploaded_policy
            )

            # Run structured validation
            validation_result = validate.validate_ODRL_from_file(
                policy_path
            )

            # -------------------------------------------------
            # Main validation status
            # -------------------------------------------------

            st.divider()

            st.subheader("Validation Result")

            is_valid_rdf = validation_result.get(
                "is_valid_RDF",
                False
            )

            is_valid_odrl = validation_result.get(
                "is_valid_ODRL"
            )

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

            # -------------------------------------------------
            # ODRL statistics
            # -------------------------------------------------

            if is_valid_odrl is True:

                st.divider()

                st.subheader("ODRL Statistics")

                stats_text = validation_result.get(
                    "odrl_stats_text"
                )

                if stats_text:
                    st.text(stats_text)

                # Optional structured statistics
                stats = validation_result.get("odrl_stats")

                if stats:
                    with st.expander("View ODRL statistics data"):
                        st.json(stats)

            # -------------------------------------------------
            # Additional validation information
            # -------------------------------------------------

            st.divider()

            st.subheader("Validation Details")

            # Fields already displayed prominently above
            displayed_fields = {
                "is_valid_RDF",
                "is_valid_ODRL",
                "odrl_stats",
                "odrl_stats_text"
            }

            # Display every remaining returned field
            for key, value in validation_result.items():

                if key in displayed_fields:
                    continue

                # Make the field name more readable
                title = key.replace("_", " ").title()

                with st.expander(title):

                    if isinstance(value, (dict, list)):
                        st.json(value)
                    else:
                        st.write(value)

            st.success(
                "Validation completed successfully."
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