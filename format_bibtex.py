#!/usr/bin/env python3
import sys
import re

_INDENT = "    "
_journal_abbr_dict = {
    "Joint Submission" : "Joint Submission",
    "Journal of Physical Chemistry Letters" : "J. Phys. Chem. Lett.",
    "The Journal of Physical Chemistry Letters" : "J. Phys. Chem. Lett.",
    "The Journal of Chemical Physics" : "J. Chem. Phys.",
    "J. Chem. Phys" : "J. Chem. Phys.",
    "Journal of Chemical Physics" : "J. Chem. Phys.",
    "Nano Letters" : "Nano Lett.",
    "ACS Energy Letters" : "ACS Energy Lett.",
    "Physical Review" : "Phys. Rev.",
    "Physical Review A" : "Phys. Rev. A",
    "Physical Review B" : "Phys. Rev. B",
    "Physical Review C" : "Phys. Rev. C",
    "Physical Review D" : "Phys. Rev. D",
    "Physical Review E" : "Phys. Rev. E",
    "Physical Review X" : "Phys. Rev. X",
    "Physical Review A" : "Phys. Rev. A",
    "Physical Review Applied" : "Phys. Rev. Appl.",
    "Physical Review Research" : "Phys. Rev. Res.",
    "Physical Review Materials" : "Phys. Rev. Mater.",
    "Physical Review Letters" : "Phys. Rev. Lett.",
    "Phys. Rev. Research" : "Phys. Rev. Res.",
    "Reviews of Modern Physics" : "Rev. Mod. Phys.",
    "Reports on Progress in Physics" : "Rep. Prog. Phys.",
    "Advances in Physics" : "Adv. Phys.",
    "Nature Communications" : "Nat. Commun.",
    "Nature communications" : "Nat. Commun.",
    "Nat Commun" : "Nat. Commun.",
    "npj Computational Materials" : "npj Comput. Mater.",
    "npj Comput Mater" : "npj Comput. Mater.",
    "Nat Rev Mater" : "Nat. Rev. Mater.",
    "Nature reviews. Materials" : "Nat. Rev. Mater.",
    "Nature Mater" : "Nat. Mater.",
    "Nature Materials" : "Nat. Mater.",
    "Nature nanotechnology" : "Nat. Nanotechnol.",
    "Annals of Physics" : "Ann. Phys.",
    "New Journal of Physics" : "New J. Phys.",
    "Computer Physics Communications" : "Comput. Phys. Commun.",
    "Journal of Physics: Condensed Matter" : "J. Condens. Matter Phys.",
    "Applied Physics Letters" : "Appl. Phys. Lett.",
    "Journal of Physics C: Solid State Physics" : "J. Phys. Condens. Matter",
    "Computational Materials Science" : "Comput. Mater. Sci.",
    "The Philosophical Magazine: A Journal of Theoretical Experimental and Applied Physics" : "Philos. Mag.-J. Theor. Exp. Appl. Phys.",
    "Proc. Natl. Acad. Sci. U.S.A." : "PNAS",
    "Materials Science and Engineering B" : "Mater. Sci. Eng. B",
    "SIAM Review" : "SIAM Rev.",
    "AIP Conference Proceedings" : "AIP Conf. Proc.",
    "Journal Club for Condensed Matter Physics" : "J. Club Condens. Matter Phys.",
    "Journal of Mathematical Physics." : "J. Math. Phys.",
    "Nanotechnology" : "Nanotechnology",
    "Physical Chemistry Chemical Physics" : "Phys. Chem. Chem. Phys.",
    "SciPost Physics Lecture Notes" : "SciPost Phys. Lect. Notes",
    "Communications Physics" : "Commun. Phys.",
    "Journal of the physical society of Japan" : "J. Phys. Soc. Jpn.",
    "Sov. Phys. JETP" : "Sov. Phys. JETP",
    "Journal of the ACM" : "J. ACM",
    "Zh. Eksp. Teor. Fiz." : "Zh. Eksp. Teor. Fiz.",
    "Canadian Journal of Physics" : "Can. J. Phys.",
    "The London, Edinburgh, and Dublin Philosophical Magazine and Journal of Science" : "Philos. Mag.",
}
values = list(_journal_abbr_dict.values())
for value in values:
    _journal_abbr_dict[value] = value


_words_to_capitalize = [
    "Hall", "ZnO", "Be(0001)", "Mo(110)", "${\\mathrm{TiO}}_{2}$", "Green's",
    "Si", "Holstein", "Fr\\\"ohlich", "GaS", "GaSe", "InSe", "InS",
    "Mexican-hat-like", "Janus",
]
_words_to_convert = {
    "SrTiO3" : "SrTiO$_3$",
    "SrTiO 3" : "SrTiO$_3$",
    "SrTiO 3" : "SrTiO$_3$",
    "GW" : "$GW$"
}

def extract_content(text, keyword):
    match = re.search(keyword + r'\s*=\s*"?\{(.+)\}"?', text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(keyword + r'\s*=\s*"?\{?(.*?)}?"?', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

filename = sys.argv[1]

filename_write = filename + ".new"

fr = open(filename, "r")
fw = open(filename_write, "w")

for line in fr:
    # Skip empty line
    if len(line.strip()) == 0:
        fw.write(line)
        continue

    line_new = line

    # Fix indentation to four spaces
    if line_new.strip()[0].isalpha():
        line_new = _INDENT + line.strip() + "\n"

    data = line.strip().split()
    keyword = data[0].lower()
    keyword = keyword.split("=")[0].lower()

    if keyword == "journal":
        # Journal abbreviation
        if "{" in line:
            journal_name = re.search(r"\{(.+?)\}", line).group(1)
        elif '"' in line:
            journal_name = re.search(r'"(.+?)"', line).group(1)

        if journal_name in _journal_abbr_dict:
            journal_name_new = _journal_abbr_dict[journal_name]
        elif "arxiv" in journal_name.lower():
            journal_name_new = journal_name
        else:
            print(f"Unknown journal {journal_name}")
            journal_name_new = journal_name

        line_new = _INDENT + "journal = {" + journal_name_new + "},\n"

    elif keyword == "title":
        # Capitalization and math formatting of title
        title = extract_content(line, keyword)
        if title is None:
            print("WARNING : Title parsing failed")
            print(line)

        for word in _words_to_capitalize:
            title = title.replace(" " + word + " ", " {" + word + "} ")
            title = title.replace(" " + word + ", ", " {" + word + "}, ")
            if title.endswith(" " + word):
                n = len(word) + 1
                title = title[:-n] + " {" + word + "}"

        for word, word_new in _words_to_convert.items():
            title = title.replace(" " + word + " ", " {" + word_new + "} ")
            title = title.replace(" " + word + ", ", " {" + word_new + "}, ")
            if title.endswith(" " + word):
                n = len(word) + 1
                title = title[:-n] + " {" + word_new + "}"

        line_new = _INDENT + "title = {" + title + "},\n"

    elif keyword == "pages":
        # Replace EN DASH by hyphen
        pages = extract_content(line, keyword)
        if pages is None:
            print("WARNING : pages parsing failed")
            print(line)

        pages = pages.replace("–", "-")
        pages = pages.replace("--", "-")
        line_new = _INDENT + "pages = {" + pages + "},\n"

    elif keyword == "note":
        line_new = ""
    else:
        pass


    fw.write(line_new)

fr.close()
fw.close()