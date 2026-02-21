"""Sphinx configuration for Motion In Ocean documentation.

Generates HTML/PDF documentation from Python docstrings (Google-style via napoleon)
and guides in docs/ directory.
"""

import sys
from pathlib import Path


# Add source directory to path for autodoc
sys.path.insert(0, str(Path("..").resolve()))

# --- Project information ---

project = "Motion In Ocean"
copyright = "2024-2026, Cyan Automation"
author = "Cyan Automation"
version = "1.0"
release = "1.0.0"

# --- General configuration ---

extensions = [
    "sphinx.ext.autodoc",  # Auto-document from docstrings
    "sphinx.ext.napoleon",  # Parse Google/NumPy style docstrings
    "sphinx.ext.intersphinx",  # Link to other project docs
    "sphinx.ext.viewcode",  # Link to source code
    "sphinx.ext.todo",  # Support .. todo:: directives
]

# Napoleon configuration (Google-style docstring support)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_method_docstring = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None
napoleon_custom_sections = None

# Autodoc configuration
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True
autodoc_mock_imports = ["picamera2", "libcamera"]  # Mock hardware deps

# Intersphinx mapping (for linking to external docs)
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "flask": ("https://flask.palletsprojects.com/", None),
}

# Templates path
templates_path = ["_templates"]

# Source suffix
source_suffix = {
    ".rst": None,
    ".md": "myst_parser",
}

# Master doc
master_doc = "index"

# Exclude patterns
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Pygments style for code highlighting
pygments_style = "sphinx"

# --- HTML output ---

html_theme = "alabaster"
html_theme_options = {
    "description": "Docker-first Raspberry Pi CSI camera streaming with multi-node management",
    "github_user": "CyanAutomation",
    "github_repo": "motioninocean",
    "github_banner": True,
    "fixed_sidebar": False,
}

html_static_path = ["_static"]
html_title = "Motion In Ocean Documentation"
html_logo = None
html_favicon = None

# --- LaTeX output ---

latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "10pt",
}

latex_documents = [
    ("index", "MotionInOcean.tex", "Motion In Ocean Documentation", author, "manual"),
]

# --- Man page output ---

man_pages = [
    ("index", "motion-in-ocean", "Motion In Ocean Documentation", [author], 1),
]

# --- Texinfo output ---

texinfo_documents = [
    (
        "index",
        "MotionInOcean",
        "Motion In Ocean Documentation",
        author,
        "MotionInOcean",
        "Docker-first Raspberry Pi streaming solution.",
        "Miscellaneous",
    ),
]

# --- Suppress warnings ---
suppress_warnings = [
    "autodoc.import_object_warning",  # Common for mock imports
]

# --- Additional configuration ---

# Enable TODO directives
todo_include_todos = True

# Set documentation root (relative to this file)
doc_root = Path(__file__).parent
