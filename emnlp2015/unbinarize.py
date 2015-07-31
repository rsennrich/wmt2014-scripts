#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Rico Sennrich


from __future__ import print_function, unicode_literals
import sys
import tree
import re

whitespace = re.compile('\s+')

def get_unbinarized_children(t, children=None):

    if children is None:
        children = []

    for child in t:
        if isinstance(child, tree.Tree) and child.node.startswith('^'):
            get_unbinarized_children(child, children)
        else:
            children.append(child)

    if not isinstance(t, tree.Tree) or t.node.startswith('^'):
        return
    else:
        t[:] = children
        for child in t:
            get_unbinarized_children(child)



if __name__ == '__main__':
  for line in sys.stdin:
      t = tree.Tree(line)
      get_unbinarized_children(t)
      print(whitespace.sub(' ',t.__str__()))