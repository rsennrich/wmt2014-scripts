#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Rico Sennrich

# restore original representation of particle verbs.
# described in Rico Sennrich and Barry Haddow (2015). A Joint Dependency Model of Morphological and Syntactic Structure for Statistical Machine Translation. Proceedings of EMNLP.

from __future__ import unicode_literals
import sys
import codecs
import tree

def first_leaf(node):
    if isinstance(node, tree.Tree) and len(node):
        return first_leaf(node[0])
    else:
        return node

def last_leaf(node):
    if isinstance(node, tree.Tree) and len(node):
        return last_leaf(node[-1])
    else:
        return node

def comma_enclosure(node):
    comma = False
    if len(node):
        if first_leaf(node).strip() == b',' and not node.node.startswith('kon'):
            comma = True
            if comma and len(node) > 1 and last_leaf(node).strip() != b',':
                node.append(tree.Tree(b'[comma [$, ,]]'))
                return
        elif isinstance(node, tree.Tree) and len(node):
            comma_enclosure(node[-1])

def convert_ptkvz(node):

    part = None
    avz = None
    v_pos = None

    for i,child in list(enumerate(node)):
        if isinstance(child, tree.Tree):
            convert_ptkvz(child)

            if child.node == b'avz':
                for grandchild in child:
                    if grandchild.node == b'PTKVZ':
                        avz = grandchild
                        avz_pos = i

            elif child.node == b'part':
                for grandchild in child:
                    if grandchild.node == b'PTKZU':
                        part = grandchild
                        part_pos = i

            elif child.node.startswith(b'V'):
                v_pos = i
                if avz is not None:
                    # infinitive with zu-prefix and 
                    if child.node == b'VVINF' and part is not None and avz is not None and part_pos == i-2 and avz_pos == i-1:
                        child[0] = avz[0] + part[0] + child[0]
                        del node[part_pos]
                        del node[part_pos]
                        avz = None
                        child.node = b'VVIZU'
                    
                    elif child.node in [b'VVINF', b'VVPP'] and avz is not None and avz_pos == i-1:
                        child[0] = avz[0] + child[0]
                        del node[avz_pos]
                        avz = None

                    # we are not in main clause, so we should concatenate prefix and verb
                    elif avz is not None and (node.node in [b'objc', b'subjc', b'neb', b'rel', b'aux', b'root', b'vkon_sub'] or node.node.startswith(b'obji') or node.node.startswith(b'kon')) and avz_pos == i-1:
                        child[0] = avz[0] + child[0]
                        avz = None
                        del node[avz_pos]

            # identify end field by fact that subordinated clause follows
            elif avz is not None and v_pos is not None and (child.node in [b'objc', b'obji', b'subjc', b'rel', b'neb', b'vroot', b'comma', b'aux'] or child.node.startswith(b'kon') or child.node.startswith(b'obji')):
                node.insert(i, avz)
                del node[avz_pos]
                avz = None
                comma_enclosure(node[i-1])

    # we insert avz as last dependent if we haven't already
    if v_pos is not None and avz is not None:
        node.append(avz)
        del node[avz_pos]
        comma_enclosure(node[-2])
        


if __name__ == '__main__':

    for line in sys.stdin:
        my_tree = tree.Tree(line)
        convert_ptkvz(my_tree)
        if '--tree' in sys.argv:
            sys.stdout.write(my_tree._pprint_flat(nodesep=b'', parens=b'[]', quotes=False) + b'\n')
        else:
            sys.stdout.write(b' '.join([leaf for leaf in my_tree.leaves() if leaf not in [b'<s>', b'</s>']]) + b'\n')