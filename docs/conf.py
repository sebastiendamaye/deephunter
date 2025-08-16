# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DeepHunter'
copyright = '2025, Sébastien Damaye'
author = 'Sébastien Damaye'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    'sphinx_togglebutton',
    "sphinx_copybutton",
    "sphinx_design",
]

source_suffix = {
    ".rst": "restructuredtext",
}

master_doc = 'index'

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = "pydata_sphinx_theme"
#html_theme = 'sphinx_book_theme'
html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']
html_css_files = [
    'custom.css',
]
html_title = "DeepHunter"
html_copy_source = True
"""
html_theme_options = {
    "repository_url": "https://github.com/sebastiendamaye/deephunter",
    "use_repository_button": True,
}
"""
