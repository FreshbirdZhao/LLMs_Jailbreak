MAIN := main
IMAGE := a-paper-latex
TEXBIN := $(firstword $(wildcard ./.TinyTeX/bin/* ./.TinyTeX/.TinyTeX/bin/*))
LATEXMK := $(if $(TEXBIN),$(TEXBIN)/latexmk,latexmk)
PATH_PREFIX := $(if $(TEXBIN),PATH="$(abspath $(TEXBIN)):$$PATH",)
FONT_ENV := FONTCONFIG_FILE="$(CURDIR)/fonts.conf" XDG_CACHE_HOME=/tmp/fontcache

.PHONY: bootstrap pdf clean distclean docker-build docker-pdf docker-shell

bootstrap:
	bash ./scripts/bootstrap_tinytex.sh

pdf:
	$(FONT_ENV) $(PATH_PREFIX) $(LATEXMK) -xelatex $(MAIN).tex

clean:
	$(FONT_ENV) $(PATH_PREFIX) $(LATEXMK) -c $(MAIN).tex
	rm -f pages/*.aux

distclean:
	$(FONT_ENV) $(PATH_PREFIX) $(LATEXMK) -C $(MAIN).tex
	rm -f pages/*.aux pages/*.toc pages/*.out pages/*.bbl pages/*.blg
	rm -f $(MAIN).pdf

docker-build:
	docker build -t $(IMAGE) .

docker-pdf:
	docker build -t $(IMAGE) .
	docker run --rm -v "$(CURDIR):/work" -w /work $(IMAGE) latexmk -xelatex $(MAIN).tex

docker-shell:
	docker build -t $(IMAGE) .
	docker run --rm -it -v "$(CURDIR):/work" -w /work $(IMAGE) bash
