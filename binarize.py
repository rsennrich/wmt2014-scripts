#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Rico Sennrich

# perform deterministic head binarization of trees that were converted from dependency format (with mosesdecoder/scripts/training/wrappers/conll2mosesxml.py):
# right-binarization of the head and its pre-modifiers, followed by left-binarization of all post-modifiers

from __future__ import print_function, unicode_literals
import sys
import codecs
from collections import defaultdict

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import cElementTree as ET

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

# assume dependency structure where each nonterminal has exactly one pre-terminal child, which is the head of the structure.
def find_head(xml):
    for i, child in enumerate(xml):
        if len(child) == 0:
            return i
    # if no head found, we pick the last child (which results in right-binarization of tree)
    return len(xml)-1

def binarize(xml, mode):

    for child in xml:
        binarize(child, mode)

    if len(xml) > 2 and mode == 'head':
        head_position = find_head(xml)
        # right-binarize head position and everything before it
        while head_position > 0 and len(xml) > 2:
            head_position -= 1
            virtual_node = ET.Element('tree')
            if head_position > 0:
                # prefix '^i' marks that we expect more siblings on the left (and possibly on the right)
                virtual_node.set('label', '^i' + xml.get('label'))
            else:
                # prefix '^l' marks that we reached beginning of structure and have more siblings on the right
                virtual_node.set('label', '^l' + xml.get('label'))
            virtual_node.append(xml[head_position])
            virtual_node.append(xml[head_position])
            xml.insert(head_position, virtual_node)
        # left-binarize the rest
        while len(xml) > 2:
            virtual_node = ET.Element('tree')
            virtual_node.set('label', '^l' + xml.get('label'))
            virtual_node.append(xml[0])
            virtual_node.append(xml[0])
            xml.insert(0, virtual_node)

    else:
        while len(xml) > 2:
            virtual_node = ET.Element('tree')
            virtual_node.set('label', '^' + xml.get('label'))
            if mode == 'left':
                virtual_node.append(xml[0])
                virtual_node.append(xml[0])
                xml.insert(0, virtual_node)
            elif mode == 'right':
                virtual_node.append(xml[-2])
                virtual_node.append(xml[-1])
                xml.append(virtual_node)

if __name__ == '__main__':

    if sys.version_info < (3, 0):
        sys.stderr = codecs.getwriter('UTF-8')(sys.stderr)
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
        sys.stdin = codecs.getreader('UTF-8')(sys.stdin)

    mode = sys.argv[1]

    for line in sys.stdin:
        if line == '\n':
            sys.stdout.write(line)
            continue
        xml = ET.fromstring(line)
        binarize(xml, mode)
        escape_xml(xml)
        sys.stdout.write(escape_text(ET.tostring(xml, encoding="UTF-8").decode("UTF-8") + '\n'))