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
    import ODRL_generator
    from colab_functions import visualise
    from colab_functions import graph_equality_comparison
    # --- DROPDOWN MENU ---
    dropdown = widgets.Dropdown(
        options=[
            ('Upload ODRL File', 'upload'),
            ('File Info', 'fileinfo'),
            ('Visualise Policy', 'visualise'),
            ('Full ODRL Validation', 'validate'),
            ('Graph Diff', 'comparetriplebytriple'),
            ('Generate ODRL Policies', 'ODRLgeneration'),
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
            elif selected == "ODRLgeneration":
                clear_output()  # clear output before showing new widgets

                # --- Helper function for labeled input ---
                def labeled_widget(label_text, widget):
                    return widgets.HBox([widgets.Label(value=label_text, layout=widgets.Layout(width='220px')), widget])

                # --- Input widgets ---
                policy_number_widget = widgets.IntText(value=1)
                p_rule_n_widget = widgets.IntText(value=2)
                f_rule_n_widget = widgets.IntText(value=2)
                o_rule_n_widget = widgets.IntText(value=1)
                constants_per_feature_widget = widgets.IntText(value=4)
                constraint_number_min_widget = widgets.IntText(value=0)
                constraint_number_max_widget = widgets.IntText(value=4)
                chance_feature_null_widget = widgets.FloatText(value=0.5)
                constraint_right_operand_min_widget = widgets.IntText(value=0)
                constraint_right_operand_max_widget = widgets.IntText(value=100)
                ontology_path_widget = widgets.Text(value="sample_ontologies/ODRL_DPV.ttl")

                # Wrap with labels
                widgets_list = [
                    labeled_widget("Number of Policies:", policy_number_widget),
                    labeled_widget("Number of Permission Rules:", p_rule_n_widget),
                    labeled_widget("Number of Prohibition Rules:", f_rule_n_widget),
                    labeled_widget("Number of Obligation Rules:", o_rule_n_widget),
                    labeled_widget("Constants per Feature (Actions/Parties/Targets):", constants_per_feature_widget),
                    labeled_widget("Minimum Constraints per Rule:", constraint_number_min_widget),
                    labeled_widget("Maximum Constraints per Rule:", constraint_number_max_widget),
                    labeled_widget("Chance Feature is Null (0-1):", chance_feature_null_widget),
                    labeled_widget("Constraint Right Operand Min:", constraint_right_operand_min_widget),
                    labeled_widget("Constraint Right Operand Max:", constraint_right_operand_max_widget),
                    labeled_widget("Ontology Path:", ontology_path_widget)
                ]

                # --- Buttons and output ---
                generate_button = widgets.Button(description="Generate", button_style='success')
                download_button = widgets.Button(description="Download TTL", button_style='info')
                download_button.disabled = True  # initially greyed out
                download_button.layout.opacity = '0.5'  # visually greyed out
                output_generate = widgets.Output()

                display(widgets.VBox(widgets_list + [generate_button, download_button, output_generate]))

                policies_graph = None

                # --- Generate button ---
                def on_generate_clicked(b):
                    nonlocal policies_graph
                    with output_generate:
                        clear_output()
                        try:
                            policies_graph = ODRL_generator.generate_ODRL(
                                policy_number=policy_number_widget.value,
                                p_rule_n=p_rule_n_widget.value,
                                f_rule_n=f_rule_n_widget.value,
                                o_rule_n=o_rule_n_widget.value,
                                constants_per_feature=constants_per_feature_widget.value,
                                constraint_number_min=constraint_number_min_widget.value,
                                constraint_number_max=constraint_number_max_widget.value,
                                chance_feature_null=chance_feature_null_widget.value,
                                constraint_right_operand_min=constraint_right_operand_min_widget.value,
                                constraint_right_operand_max=constraint_right_operand_max_widget.value,
                                ontology_path=ontology_path_widget.value
                            )
                            # Print Turtle serialization
                            turtle_output = policies_graph.serialize(format="turtle")
                            print(turtle_output.decode("utf-8") if isinstance(turtle_output, bytes) else turtle_output)

                            # Enable download button visually
                            download_button.disabled = False
                            download_button.layout.opacity = '1.0'
                        except Exception as e:
                            print(f"⚠️ Error during generation: {e}")
                            download_button.disabled = True
                            download_button.layout.opacity = '0.5'

                generate_button.on_click(on_generate_clicked)

                # --- Download button ---
                def on_download_clicked(b):
                    if policies_graph is not None:
                        import tempfile
                        from google.colab import files
                        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as tmp_file:
                            policies_graph.serialize(destination=tmp_file.name, format="turtle")
                            tmp_file.flush()
                            files.download(tmp_file.name)

                download_button.on_click(on_download_clicked)

    run_button.on_click(on_run_clicked)

    # --- DISPLAY EVERYTHING ---
    display(dropdown, run_button, output_run)

if __name__ == "__main__":
    setup()
    show_interface()