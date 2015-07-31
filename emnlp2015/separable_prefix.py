#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Rico Sennrich

# normalize representation of German particle verbs to common representation
# described in Rico Sennrich and Barry Haddow (2015). A Joint Dependency Model of Morphological and Syntactic Structure for Statistical Machine Translation. Proceedings of EMNLP.

from __future__ import print_function, unicode_literals
import sys
import codecs
from collections import defaultdict

import fst_wrapper

from lxml import etree as ET

def get_text(element, text):
    if element.text:
        text.append(element.text)
    for child in element:
        get_text(child, text)
    if element.tail:
        text.append(element.tail)

def strip_xml(xml):
    text_list = []
    get_text(xml, text_list)
    text = ' '.join([t.strip() for t in text_list])
    return text

def escape_xml(element):

    if element.text:
        element.text = element.text.replace('\'','&apos;')
        element.text = element.text.replace('"','&quot;')

    for child in element:
        escape_xml(child)

def escape_text(s):

    s = s.replace('|','&#124;') # factor separator
    s = s.replace('[','&#91;') # syntax non-terminal
    s = s.replace(']','&#93;') # syntax non-terminal

    s = s.replace('&amp;apos;','&apos;') # lxml is buggy if input is escaped
    s = s.replace('&amp;quot;','&quot;') # lxml is buggy if input is escaped

    return s

def convert_ptkvz(xml):

    vvfin = None
    avz = None

    offset = 0
    for i, child in list(enumerate(xml)):
        # separate prefix from verbs
        if child.get('label').startswith('VV') and child.text:
            split = has_vpart(child.text.strip())
            if split:
                avz = ET.Element('tree')
                avz.set('label', 'avz')
                ptkvz = ET.Element('tree')
                ptkvz.set('label', 'PTKVZ')
                ptkvz.text = split[0]
                avz.append(ptkvz)
                xml.insert(i+offset,avz)
                child.text = split[1]
                if split[1].startswith('zu') and split[2]:
                    part = ET.Element('tree')
                    part.set('label', 'part')
                    ptkzu = ET.Element('tree')
                    ptkzu.set('label', 'PTKZU')
                    ptkzu.text = 'zu'
                    part.append(ptkzu)
                    xml.insert(i+offset,part)
                    offset += 1
                    child.text = split[1][2:]
                    child.set('label', 'VVINF')
                offset += 1

        if child.get('label') == 'VVFIN':
            vvfin = child
            vvfin_pos = i+offset
        elif child.get('label') == 'avz':
            avz = child
            break

    # verb has separated prefix: reorder
    if vvfin is not None and avz is not None:
        xml.insert(vvfin_pos, avz)

    # recursion
    for child in xml:
        convert_ptkvz(child)


def has_vpart(word):
    if word in smor_cache:
        return smor_cache[word]
    else:
        analyses = sorted(smor.analyse(word), key=lambda x: x.count('<'))
        analyses = [x for x in analyses if '<+V>' in x]
        if analyses and all('<#>' in line for line in analyses):
            prefix_len = analyses[0].index('<#>')
            if analyses[0].startswith('<CAP>'):
                prefix_len -= 5
            has_zu = "<zu>" in analyses[0]
            smor_cache[word] = word[:prefix_len], word[prefix_len:], has_zu
            return word[:prefix_len], word[prefix_len:], has_zu
        else:
            smor_cache[word] = False
            return False


if __name__ == '__main__':

    if '-train' in sys.argv:
        sys.exit(0)

    smor = fst_wrapper.FstWrapper('fst-mor', sys.argv[1])
    smor_cache = {}

    if sys.version_info < (3, 0):
        sys.stderr = codecs.getwriter('UTF-8')(sys.stderr)
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
        sys.stdin = codecs.getreader('UTF-8')(sys.stdin)

    for line in sys.stdin:
        if line == '\n':
            sys.stdout.write(line)
            continue
        xml = ET.fromstring(line)
        convert_ptkvz(xml)
        escape_xml(xml)
        sys.stdout.write(escape_text(ET.tostring(xml, encoding="UTF-8").decode("UTF-8") + '\n'))