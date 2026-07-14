import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


from common.streamlit_style import apply_style

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="ODRL Engine Dashboard",
    layout="wide",
)
apply_style()

APPS_FILE = Path("/tmp/odrl-engine/apps.json")


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def load_apps():
    """
    Load the list of discovered apps written by entrypoint.py.
    """

    if not APPS_FILE.exists():
        return []

    with open(APPS_FILE, "r") as f:
        apps = json.load(f)

    # Remove ourselves
    apps = [
        app
        for app in apps
        if app["route"] != "odrl-engine-dashboard"
    ]

    # Sort alphabetically
    apps.sort(key=lambda a: a["route"].lower())

    return apps


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

apps = load_apps()

if not apps:
    st.warning("No Streamlit applications were discovered.")
    st.stop()

tab_names = [
    app.get("title", app["route"].replace("-", " ").title())
    for app in apps
]

# ---------------------------------------------------------
# Application selector
# ---------------------------------------------------------

selected = st.segmented_control(
    "",
    options=tab_names,
    default=tab_names[0],
)

# Find the selected app
selected_index = tab_names.index(selected)
app = apps[selected_index]

# Display the selected application
components.iframe(
    src=f"../{app['route']}/",
    height=900,
    scrolling=True,
)