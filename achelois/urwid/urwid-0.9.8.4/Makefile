
RELEASE:=$(shell python -c 'import urwid; print urwid.__version__')
SOURCE:= bigtext.py browse.py calc.py dialog.py docgen_reference.py \
    docgen_tutorial.py edit.py fib.py graph.py input_test.py Makefile \
    setup.py test_urwid.py tmpl_tutorial.html tour.py \
    urwid/canvas.py urwid/curses_display.py urwid/escape.py urwid/font.py \
    urwid/graphics.py urwid/html_fragment.py urwid/__init__.py \
    urwid/listbox.py urwid/old_str_util.py urwid/raw_display.py \
    urwid/util.py urwid/web_display.py urwid/widget.py \
    source/str_util.c
DOCS:= reference.html tutorial.html

dist: urwid-$(RELEASE).tar.gz

.PHONY: dist

urwid-$(RELEASE).tar.gz: $(SOURCE) $(DOCS) CHANGELOG
	tar czvf $@ --transform "s{{urwid-$(RELEASE)/{" $(SOURCE) $(DOCS) \
            CHANGELOG

reference.html: $(SOURCE)
	# make sure it runs properly before touching target
	python docgen_reference.py > $@.incoming
	mv $@.incoming $@

tutorial.html: $(SOURCE)
	# make sure it runs properly before touching target
	python docgen_tutorial.py -H > $@.incoming
	mv $@.incoming $@

clean:
	for fn in *.pyc urwid/*.pyc urwid-*.tar.gz $(DOCS); do \
		if [ -e "$$fn" ]; then rm -r "$$fn"; fi \
	done

.PHONY: clean

