#  !git clone https://github.com/paolo7/ODRL-Engine.git
#  %cd ODRL-Engine
#  from setup_colab import setup, show_interface
#  setup()
#  show_interface()

import os
import sys
import subprocess
from google.colab import files
import ipywidgets as widgets
from IPython.display import display, clear_output

def run_cmd(cmd):
    print(f"\n[RUNNING] {cmd}")
    result = subprocess.run(cmd, shell=True, check=False, text=True)
    if result.returncode != 0:
        print(f"⚠️ Command failed: {cmd}")
    return result

def setup():
    print("🚀 Setting up ODRL-Engine environment in Google Colab...\n")

    # install dependencies
    run_cmd("pip install -r requirements.txt")
    run_cmd("pip install ipywidgets")

    # add repo to path
    sys.path.append(os.getcwd())

    # test imports
    print("\n✅ Testing imports...")
    import validate
    import rdflib
    from rdflib.namespace import RDF, RDFS, SKOS
    global colab_functions
    import ipywidgets
    from IPython.display import display, HTML, clear_output

    print("✅ ODRL-Engine setup complete and all imports successful!")
    clear_output(wait=True)

class UploadState:
    filename = None
    content = None

def upload_file():
    uploaded = files.upload()
    # Enforce single file upload
    if len(uploaded) != 1:
        raise ValueError("Please upload exactly one file.")
    # Extract filename and content
    UploadState.filename = list(uploaded.keys())[0]
    UploadState.content = uploaded[UploadState.filename]
    print(f"✅ Uploaded: {UploadState.filename}")

def show_interface():
    import validate
    from colab_functions import visualise
    from colab_functions import graph_equality_comparison
    # --- DROPDOWN MENU ---
    dropdown = widgets.Dropdown(
        options=[
            ('Upload ODRL File', 'upload'),
            ('File Info', 'fileinfo'),
            ('Visualise Policy', 'visualise'),
            ('Full ODRL Validation', 'validate'),
            ('Compare two graph for triple equality', 'comparetriplebytriple'),
        ],
        description='Select:',
    )

    # --- RUN BUTTON ---
    run_button = widgets.Button(description="Run", button_style='success')
    output_run = widgets.Output()

    def on_run_clicked(b):
        with output_run:
            clear_output()
            selected = dropdown.value
            if selected == "upload":
                upload_file()
            elif selected == "visualise":
                if UploadState.filename and UploadState.content:
                    visualise.explore_policies_html()
                else:
                    print("⚠️ No ODRL file uploaded yet.")
            elif selected == "fileinfo":
                if UploadState.filename and UploadState.content:
                    print(f'User uploaded file "{UploadState.filename}" with length {len(UploadState.content)} bytes')
                else:
                    print("⚠️ No ODRL file uploaded yet.")
            elif selected == "validate":
                if UploadState.filename:
                    validate.generate_ODRL_diagnostic_report(UploadState.filename)
                else:
                    print("⚠️ No ODRL file uploaded yet.")
            elif selected == "comparetriplebytriple":
                graph_equality_comparison.compare_rdf_files()
    run_button.on_click(on_run_clicked)

    # --- DISPLAY EVERYTHING ---
    display(dropdown, run_button, output_run)

if __name__ == "__main__":
    setup()
    show_interface()