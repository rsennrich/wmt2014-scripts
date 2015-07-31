#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Rico Sennrich

# hyphen splitter: splits all hyphenated words, and with option -syntax, creates a hierarchical tree in moses XML format.

from __future__ import division, unicode_literals
import sys
import re
import codecs
import argparse

from lxml import etree as ET

def create_compound_xml(element, wordlist, merge_junctures, dependency, initial=False):

    # separate last segment, then recursively label remainder as compound modifier
    if initial:
        juncture = ''
        dep = ET.Element('tree')
        dep.set('label', 'SEGMENT')
        dep.text = wordlist[-1]
        remainder = wordlist[:-1]
        if remainder:
            create_compound_xml(element, remainder, merge_junctures, dependency)
        element.append(dep)
        return

    juncture = wordlist[-1]
    word = wordlist[-2]
    remainder = wordlist[:-2]

    head = ET.Element('tree')
    head.set('label', 'comp_mod')
    element.append(head)

    dep1 = ET.Element('tree')
    dep1.text = word
    if merge_junctures:
        dep1.set('label', 'SEGMENT+JUNC')
    else:
        dep1.set('label', 'SEGMENT')

    if remainder:
        create_compound_xml(head, remainder, merge_junctures, dependency)

    head.append(dep1)

    dep2 = ET.Element('tree')
    dep2.set('label', 'JUNC')
    dep2.text = juncture
    dep3 = ET.Element('tree')
    dep3.set('label', 'junc')
    dep3.append(dep2)
    head.append(dep3)


def main(file_obj, merge_junctures, syntax, dependency):

    re_syntax_splitter = re.compile(r'((?:\s*(?:<[^<>]*>)+\s*)|(?:(?<!>)\s+(?!<)))')
    re_hyphen_splitter = re.compile(r'(\S+?)\-(?=\S)')

    for line in file_obj:

        # only do syntactic processing if option syntax is used and we see '<' in line
        write_syntax = syntax
        if write_syntax and not '<' in line:
            write_syntax = False

        if write_syntax:
            words_in = re_syntax_splitter.split(line)
            words_in_clean = [word for word in words_in if word and not word.startswith('<') and not word == ' ']
        else:
            words_in = line.split()
            words_in_clean = words_in

        words = []
        for word in words_in:

            if not word:
                continue
            if word == ' ' or (write_syntax and word.startswith('<')) or word == '@-@':
                words.append(word)
                continue

            if merge_junctures:
                word = re_hyphen_splitter.sub(r'\1-@@ ', word)
            else:
                word = re_hyphen_splitter.sub(r'\1 @-@ ', word)

            if write_syntax and len(word.split()) > 1:
                head = ET.Element('x')
                create_compound_xml(head, word.split(), merge_junctures, dependency, initial=True)
                word = ET.tostring(head, encoding="UTF-8")[3:-4].decode("UTF-8")
                word = word.rsplit('<',1)[0]
                words[-1] = words[-1].rsplit('<',1)[0]

            words.append(word)

        if write_syntax:
            sys.stdout.write(''.join(words))
        else:
            sys.stdout.write(' '.join(words) + '\n')


def parse_arguments():

    help_text =  "hyphen splitter\n"

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=help_text)

    general = parser.add_argument_group('general options')

    general.add_argument('-model', metavar='MODEL',
                    help='path to statistical model. Currently ignored.')
    general.add_argument('-corpus', type=argparse.FileType('r'), default=sys.stdin, metavar='PATH',
                    help='input text (default: standard input).')
    general.add_argument('-train', action="store_true",
                    help='train model on input text. Currently ignored.')
    general.add_argument('-syntax', action="store_true",
                    help='input/output is syntactic tree')
    general.add_argument('-q', action="store_true",
                    help='quiet mode.')
    general.add_argument('-dependency', action='store_true',
                    help='dependency-like representation of compounds (ensure that every nonterminal in compound representation has exactly one preterminal)')

    general.add_argument('-merge-filler', action="store_true", dest='merge_junctures',
                    help='concatenate hyphens with preceding word ("Test-@@ Datei" instead of "Test @-@ Datei")')

    args = parser.parse_args()

    return args

if __name__ == '__main__':

    args = parse_arguments()

    VERBOSE = not args.q

    if sys.version_info < (3, 0):
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
        args.corpus = codecs.getreader('UTF-8')(args.corpus)
        sys.stderr = codecs.getwriter('UTF-8')(sys.stderr)

    if args.train:
        sys.exit(0)

    else:
        main(args.corpus, args.merge_junctures, args.syntax, args.dependency)
