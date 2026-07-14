import streamlit as st
import os
import tempfile

import io
from contextlib import redirect_stdout

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


# ---------------------------------------------------------
# Main App
# ---------------------------------------------------------

st.title("ODRL Policy Validation")

st.write(
    """
    Upload an ODRL policy file (`.ttl`, `.rdf`, etc.).

    The policy will automatically be validated and a
    diagnostic report will be generated.
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
        "jsonld"
    ]
)

# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

if uploaded_policy is not None:

    st.success(
        f"Uploaded: {uploaded_policy.name}"
    )

    with st.spinner(
            "Validating ODRL policy..."
    ):

        try:

            # Save uploaded file
            policy_path = save_uploaded_file(
                uploaded_policy
            )

            # Run validation
            # Capture printed validation report
            output_buffer = io.StringIO()

            with redirect_stdout(output_buffer):

                validate.generate_ODRL_diagnostic_report(
                    policy_path
                )

            report = output_buffer.getvalue()

            st.success(
                "Validation completed successfully."
            )

            st.divider()

            st.subheader(
                "Validation Report"
            )

            st.text_area(
                "Diagnostic Report",
                report,
                height=700
            )



        except Exception as e:

            st.error(
                "Validation failed."
            )

            st.exception(e)


        finally:

            # Remove temporary file
            try:
                os.remove(policy_path)
            except:
                pass