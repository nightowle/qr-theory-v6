all: main_tex_con.pdf

Makefile: main_tex_con.tex
    latexmk -pdf -interactive -quiet -file $ <

ean:
    rm main_tex_con.aux main_tex_con.log main_tex_con.out

phd: main_tex_con.pdf

view: phd
    open main_tex_con.pdf