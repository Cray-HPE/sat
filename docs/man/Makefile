RST_MAN_PAGES = $(wildcard *.8.rst)

all: $(RST_MAN_PAGES:.rst=)

%.8: %.8.rst
	rst2man.py $< $@

clean:
	rm -f *.8

.PHONY: all clean
