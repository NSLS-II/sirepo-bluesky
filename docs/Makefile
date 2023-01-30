# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    = "-W"  # This flag turns warnings into errors.
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = PackagingScientificPython
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

simulations-srw.inc:
	python build-table.py --path=../sirepo_bluesky/tests/SIREPO_SRDB_ROOT/user/testuser/ --sim-type=srw --outfile=source/simulations-srw.inc

simulations-srw-other.inc:
	python build-table.py --path=../sirepo_bluesky/tests/SIREPO_SRDB_ROOT/user/testuser/ --sim-type=srw --outfile=source/simulations-srw-other.inc --pattern="[!00]*"

simulations-shadow.inc:
	python build-table.py --path=../sirepo_bluesky/tests/SIREPO_SRDB_ROOT/user/testuser/ --sim-type=shadow --outfile=source/simulations-shadow.inc

simulations-shadow-other.inc:
	python build-table.py --path=../sirepo_bluesky/tests/SIREPO_SRDB_ROOT/user/testuser/ --sim-type=shadow --outfile=source/simulations-shadow-other.inc --pattern="[!00]*"

simulations-madx.inc:
	python build-table.py --path=../sirepo_bluesky/tests/SIREPO_SRDB_ROOT/user/testuser/ --sim-type=madx --outfile=source/simulations-madx.inc

simulations-madx-other.inc:
	python build-table.py --path=../sirepo_bluesky/tests/SIREPO_SRDB_ROOT/user/testuser/ --sim-type=madx --outfile=source/simulations-madx-other.inc --pattern="[!00]*"

html: simulations-srw.inc simulations-srw-other.inc simulations-shadow.inc simulations-shadow-other.inc simulations-madx.inc simulations-madx-other.inc


show:
	@python -c "import webbrowser; webbrowser.open_new_tab('file://$(shell pwd)/$(BUILDDIR)/html/index.html')"
