# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = source
BUILDDIR      = build
BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
INPUT_MODELS = $(BUILDDIR)/model_tables/input_models.rst

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile model_tables
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	rm -rf build

# TODO: make make_model_tables.py a dependency so that it doesn't always run.
model_tables:
	python make_model_tables.py -o $(BUILDDIR)/model_tables

github: html
	rm -rf source/pydss
	sphinx-apidoc -o source/pydss ../pydss
	-git branch -D gh-pages
	-git push origin --delete gh-pages
	ghp-import -n -b gh-pages -m "Update documentation" ./build/html
	git checkout gh-pages
	git push --set-upstream origin gh-pages
	git checkout ${BRANCH}
