#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Rico Sennrich

# This script implements hybrid compound splitting as described in
# Fritzinger & Fraser 2010: How to Avoid Burning Ducks: Combining Linguistic Analysis and Corpus Statistics for German Compound Processing
# the variant without morphology tool corresponds to Koehn & Knight 2003: Empirical Methods for Compound Splitting

# As SMOR morphology, I recommend the most recent version of Zmorge: zmorge-{version}-smor_newlemma.a at http://kitt.ifi.uzh.ch/kitt/zmorge/
# The script requires SFST in hybrid mode.

# A syntactic representation of split compounds as described in:
#  Rico Sennrich, Philip Williams, Matthias Huck (2014):
#    A tree does not make a well-formed sentence: Improving syntactic string-to-tree statistical machine translation with more linguistic knowledge.
#    In: Computer Speech & Language (in press).
# can be generated (given a corpus in the Moses XML format) with the following commands:
# hybrid_compound_splitter.py -train -syntax -corpus INPUT_FILE -model MODEL_FILE
# hybrid_compound_splitter.py -write-filler -no-truecase -q -syntax -smor zmorge-{version}-smor_newlemma.a -model MODEL_FILE < INPUT_FILE > OUTPUT_FILE

from __future__ import division, unicode_literals
import sys
import os
import re
import pprint
import json
import codecs
import argparse
from collections import defaultdict
from operator import mul

from lxml import etree as ET

try:
  import pexpect
except ImportError:
  sys.stderr.write('Error: this script requires Pexpect >= 3.0\n')
  sys.exit(1)

if pexpect.__version__ < 3:
  sys.stderr.write('Error: this script requires Pexpect >= 3.0. Version {0} found\n'.format(pexpect.__version__))
  sys.exit(1)

if sys.version_info >= (3, 0):
    from functools import reduce

JUNCTURES = ['', 's', 'es', '-'] # only allow  these junctures in unsupervised mode (ignored in hybrid mode)
SMOR_SPLIT = ['NN', 'NE'] # only split these word classes with SMOR
MIN_SIZE = 4
MIN_COUNT = 5
MAX_COUNT = 5
MAX_SPLIT_HYPOTHESES = 1000 # break if there are too many ways to split a word

SMOR_ENCODING = 'UTF-8'


class FstWrapper():
    def __init__(self, smor_binary, smor_model):
        self.child = pexpect.spawnu(smor_binary + ' ' + smor_model)
        self.child.delaybeforesend = 0
        self.child.expect(["analyze> ", pexpect.EOF], timeout=600)
        before = self.child.before
        if self.child.terminated:
            raise RuntimeError(before)

    def analyse(self, word):
        word = word.strip()
        if word == "" or word == "q" or word == "\x7f":
            return []
        self.child.sendline(word)
        try:
            self.child.expect(["analyze> ", pexpect.EOF])
        except pexpect.TIMEOUT:
            sys.stderr.write('Warning: timeout while waiting for fst-mor\n')
            sys.stderr.write('String: {0}'.format(word))
            return []
        result = self.child.before.split("\r\n")[1:-1]
        if len(result) == 1 and re.match("^no result for ", result[0]):
            result = []
        return result


class SMORSplitter(object):

    def __init__(self, smor_model, no_truecase):

        self.smor = FstWrapper('fst-mor', smor_model)
        self.data = defaultdict(set)
        self.re_mainclass = re.compile(r'<\+(.*?)>')
        self.re_any = re.compile(r'<([^#~-]+?)>')
        self.re_nn = re.compile(r'<#>')
        self.re_morph = re.compile(r'<([#~-])>')
        self.re_fugenlaut = re.compile(r'<->')
        self.re_segment = re.compile(r'<([A-Z#~]*?)>')
        self.re_hyphenation = re.compile(r'\{(.+?)\}-(?:<TRUNC>)?')
        self.re_last = re.compile(r'(.+?)<\+',re.UNICODE)
        self.no_truecase = no_truecase


    def convert(self, analyses):
        """convert SMOR output into list of morphemes"""

        for word, lines in analyses:
            cache = []
            for line in lines:

                if line.startswith('no result'):
                    continue

                if not line:
                    continue

                try:
                    pos = self.re_mainclass.search(line).group(1)
                except AttributeError:
                    continue

                if pos == 'V' and '<PPres>' in line:
                    continue
                elif pos == 'PUNCT':
                    continue

                #score number of morphemes; heuristic adopted from SFST
                segments = len(self.re_segment.findall(line))
                if line.startswith('<CAP>'):
                    if self.no_truecase:
                        continue
                    else:
                        segments -= 1

                # convert markup of hyphenated words into markup of compounds (with '-' as juncture element which is lost if we split, but kept if we don't)
                # {ABC}-<TRUNC>Abwehr<+NN><Fem><Nom><Sg> -> ABC<->-<#>Abwehr<+NN><Fem><Nom><Sg>
                line = self.re_hyphenation.sub(r'\1<->-<#>', line)

                main = self.re_last.search(line).group(1)
                parts = self.re_any.sub('',main)

                cache.append((word,segments,parts,pos))

            self.get_best(cache)


    def get_best(self,cache):
        if cache:
            for best in cache: #currently, process all segmentations. possible modification: only use 'best' segmentation, i.e. the one with the fewest morphemes

                #only split nouns
                if best[3] in SMOR_SPLIT:

                    wordform = best[0]
                    lemma = best[2]
                    if not '<#>' in lemma:
                        continue
                    if '<~>' in lemma:
                        continue
                    stem = ''.join(lemma.split('<#>')[:-1])
                    stem = self.re_morph.sub('',stem)

                    # restore inflected ending from analysis
                    try:
                        ending = best[0].split(stem)[1]
                        split = lemma.split('<#>')[:-1] + [ending]
                    except:
                        split = lemma.split('<#>')

                    # keep inflection of ending
                    split[-1] = self.re_morph.sub('',split[-1])

                    for i, item in enumerate(split):
                        root, fuge = item, ''
                        items = item.split('<->')

                        if len(items) == 2:
                            root, fuge = items
                        elif len(items) > 2:
                            root = ''.join(items[:-1])
                            fuge = items[-1]

                        root = self.re_morph.sub('', root)
                        split[i] = (root, fuge)

                    self.data[best[0]].add(tuple(split))


    def analyze(self, words_in):
        """get all new words from input line and send them to SMOR for analysis"""

        todo = []

        for word in words_in:
            if not word in self.data:

                self.data[word] = set([((word,''),)])
                todo.append(word)

        analyses = [(word, self.smor.analyse(word)) for word in todo]
        self.convert(analyses)



def train_model(in_obj, out_path, syntax):

    freq = defaultdict(int)

    re_syntax_splitter = re.compile(r'((?:\s*(?:<[^<>]*>)+\s*)|(?:(?<!>)\s+(?!<)))')

    for line in in_obj:
        if syntax and '<' in line:
            words = [word for word in re_syntax_splitter.split(line) if word and not word == ' ' and not word.startswith('<')]
        else:
            words = line.split()
        for word in words:
            freq[word] += 1

    write_model(freq, out_path)


def write_model(model, file_path):

    if sys.version_info < (3, 0):
        file_obj = codecs.getwriter('UTF-8')(open(args.model, 'w'))
    else:
        file_obj = open(args.model, 'w', encoding='UTF-8')

    file_obj.write('# -*- coding: utf-8 -*-\n\n')
    file_obj.write('from __future__ import unicode_literals\n\n')
    file_obj.write('model = ')
    json.dump(model,file_obj, indent=2)
    file_obj.close()


def generate_decompositions(splits, memory = False, write_juncture = False):

    if not memory:
        memory = []

    for start in splits[-1].keys():
        if start == 0:
            yield [splits[-1][start]] + memory
        else:
            if write_juncture:
                juncture, segment, new_start = splits[-1][start]
                new_memory = [(juncture, -1), (segment, new_start)] + memory
            else:
                new_memory = [splits[-1][start]] + memory
            for decomposition in generate_decompositions(splits[:start+1], new_memory, write_juncture = write_juncture):
                yield decomposition


def get_unsupervised_splits(word, freq, truecase, fst_server=None, write_juncture=False, no_truecase=False):
    reachable = [{} for i in range(len(word)+1)]
    for end in range(MIN_SIZE, len(word)+1):
        for start in range(0, end-MIN_SIZE+1):

            if start and not reachable[start]: # no split ending in this position
                continue

            for juncture in JUNCTURES:

                if start == 0 and juncture:
                    continue

                if word[start:start+len(juncture)] != juncture:
                    continue

                subword_orig = word[start+len(juncture):end]
                subword = subword_orig.lower()
                if subword not in freq or freq[subword] < MIN_COUNT:
                    continue

                if VERBOSE:
                    sys.stderr.write('\tmatching word {0} .. {1} ({2}){3} {4}\n'.format(start, end, juncture, subword, freq[subword]))

                if subword in truecase:
                    subword = truecase[subword]

                if no_truecase:
                    subword_out = subword_orig
                else:
                    subword_out = subword

                if not start in reachable[end] or freq[subword] > reachable[end][start][1]:
                    if write_juncture and not start == 0:
                        juncture_out = '@' + juncture + '@'
                        reachable[end][start] = (juncture_out, subword_out, freq[subword])
                    else:
                        reachable[end][start] = (subword_out, freq[subword])

    #no split found
    if not reachable[-1]:
        return

    for decomposition in generate_decompositions(reachable, write_juncture = write_juncture):
        yield decomposition

def join_compounds(compounds, freq, truecase, write_junctures, no_truecase, memory = False):

    if not memory:
        memory = []

    for j in range(1, len(compounds)+1):

        if j == 1:
            subword_orig = compounds[0][0]
            subword = subword_orig.lower()
        else:
            prefix = ''.join([''.join(f) for f in compounds[:j-1]])
            suffix = compounds[j-1][0]
            subword_orig = prefix + suffix
            subword = subword_orig.lower()

        if subword not in freq or freq[subword] < MIN_COUNT:
            continue

        if VERBOSE:
            sys.stderr.write('\tmatching word {0} {1}\n'.format(subword, freq[subword]))

        if no_truecase:
            subword_out = subword_orig
        else:
            if subword in truecase:
                subword = truecase[subword]
            subword_out = subword

        new_element = [(subword_out, freq[subword])]

        if j == len(compounds):
            yield memory + new_element
        else:
            if write_junctures:
                new_element.append(('@' + compounds[j-1][1] + '@', -1))
            for compound in join_compounds(compounds[j:], freq, truecase, write_junctures, no_truecase, memory + new_element):
                yield compound


def get_FST_splits(word, freq, truecase, fst_server, write_junctures, no_truecase):

    for split in fst_server.data[word]:
        for compound in join_compounds(split, freq, truecase, write_junctures, no_truecase):
            yield compound


def create_compound_xml(element, wordlist, write_junctures, merge_junctures, dependency, initial=False):

    # separate last segment, then recursively label remainder as compound modifier
    if initial:
        juncture = ''
        dep = ET.Element('tree')
        dep.set('label', 'SEGMENT')
        dep.text = wordlist[-1]
        remainder = wordlist[:-1]
        if remainder:
            create_compound_xml(element, remainder, write_junctures, merge_junctures, dependency)
        element.append(dep)
        return

    if write_junctures or merge_junctures:
        juncture = wordlist[-1]
        word = wordlist[-2]
        remainder = wordlist[:-2]
    else:
        word = wordlist[-1]
        remainder = wordlist[:-1]

    head = ET.Element('tree')
    head.set('label', 'comp_mod')
    element.append(head)

    if merge_junctures:
        dep1 = ET.Element('tree')
        dep1.set('label', 'SEGMENT+JUNC')
        dep1.text = word + juncture[1:-1] + '@@'
    else:
        dep1 = ET.Element('tree')
        dep1.set('label', 'SEGMENT')
        dep1.text = word

    if remainder:
        create_compound_xml(head, remainder, write_junctures, merge_junctures, dependency)

    head.append(dep1)

    if write_junctures:
        dep2 = ET.Element('tree')
        dep2.set('label', 'JUNC')
        dep2.text = juncture
        if dependency:
            dep3 = ET.Element('tree')
            dep3.set('label', 'junc')
            dep3.append(dep2)
            head.append(dep3)
        else:
            head.append(dep2)


def apply_model(file_obj, freq, fst_server, split_function, write_junctures, merge_junctures, syntax, no_truecase, dependency):

    re_syntax_splitter = re.compile(r'((?:\s*(?:<[^<>]*>)+\s*)|(?:(?<!>)\s+(?!<)))')
    truecase = {}

    for word in list(freq):
        word_lc = word.lower()
        if word_lc in freq and freq[word_lc] > freq[word]:
            continue

        freq[word_lc] = freq[word]
        if word_lc != word and not no_truecase:
            truecase[word_lc] = word

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

        if fst_server:
            fst_server.analyze(words_in_clean)

        words = []
        for word in words_in:

            if write_syntax:
                if not word:
                    continue
                if word == ' ' or word.startswith('<'):
                    words.append(word)
                    continue

            word_lc = word.lower()
            if VERBOSE:
                sys.stderr.write('considering {0} ({1})...\n'.format(word, word_lc))

            if word_lc in freq and freq[word_lc] >= MAX_COUNT:
                words.append(word)
                if VERBOSE:
                    sys.stderr.write('\tfrequent word ({0}>{1}), skipping\n'.format(freq[word_lc], MAX_COUNT))
                continue

            best_split = word
            best_score = 1

            for i, decomposition in enumerate(split_function(word, freq, truecase, fst_server, write_junctures or merge_junctures, no_truecase)):

                if i >= MAX_SPLIT_HYPOTHESES:
                    break

                split_list, scores = zip(*decomposition)
                scores = [score for score in scores if score != -1] #ignoring
                total = reduce(mul, scores)
                score = total ** (1/len(scores))
                if FEWEST:
                    score = (-len(scores),score)
                split = ' '.join(split_list)

                if VERBOSE:
                    sys.stderr.write('\t split: {0} ({1} ** 1/{2}) = {3}\n'.format(split, total, len(scores), score))

                if score > best_score:
                    best_split = split
                    best_score = score

            if write_syntax and len(best_split.split()) > 1:
                head = ET.Element('x')
                create_compound_xml(head, best_split.split(), write_junctures, merge_junctures, dependency, initial=True)
                best_split = ET.tostring(head, encoding="UTF-8")[3:-4].decode("UTF-8")
                if dependency:
                    words[-1] = words[-1].rsplit('<',1)[0]
                    best_split = best_split.rsplit('<',1)[0]

            if merge_junctures:
                merged_best_split = []
                for item in best_split.split():
                    if merged_best_split and len(item) > 1 and item[0] == item[-1] == "@":
                        merged_best_split[-1] += item[1:-1] + "@@"
                    else:
                        merged_best_split.append(item)
                best_split = ' '.join(merged_best_split)

            words.append(best_split)

        if write_syntax:
            sys.stdout.write(''.join(words))
        else:
            sys.stdout.write(' '.join(words) + '\n')


def parse_arguments():

    help_text =  "compound splitter\n"
    help_text += "  train: python decompounding.py -train -corpus txt-file -model new-model\n"
    help_text += "  apply: python decompounding.py -model trained-model < in > out\n"

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=help_text)

    general = parser.add_argument_group('general options')

    general.add_argument('-model', metavar='MODEL', required=True,
                    help='path to statistical decompounding model. Will be overwritten if -train is active.')
    general.add_argument('-corpus', type=argparse.FileType('r'), default=sys.stdin, metavar='PATH',
                    help='input text (default: standard input).')
    general.add_argument('-train', action="store_true",
                    help='train model on input text. MODEL will be overwritten.')
    general.add_argument('-syntax', action="store_true",
                    help='input/output is syntactic tree')
    general.add_argument('-q', action="store_true",
                    help='quiet mode.')

    application = parser.add_argument_group('application options')

    application.add_argument('-min-size', type=int,
                    help='minimum word size [don\'t split into short words] (default {0})'.format(MIN_SIZE), default=MIN_SIZE)
    application.add_argument('-min-count', type=int,
                    help='minimum word count [don\'t split into rare words] (default {0})'.format(MIN_COUNT), default=MIN_COUNT)
    application.add_argument('-max-count', type=int,
                    help='maximum word count [don\'t split up frequent words] (default {0})'.format(MAX_COUNT), default=MAX_COUNT)
    application.add_argument('-fewest', action="store_true",
                    help='prefer option with fewest splits (that meets all other constraints)')
    application.add_argument('-module', action="store_true",
                    help='load model as Python module - quicker, but model file needs to end in *.py and be in same folder as script.')
    application.add_argument('-smor', metavar='PATH',
                    help='perform hybrid compound splitting (with SMOR morphology). Default: purely corpus-based compound splitting.')
    application.add_argument('-no-truecase', action='store_true',
                    help='leave segments in original case')
    application.add_argument('-dependency', action='store_true',
                    help='dependency-like representation of compounds (ensure that every nonterminal in compound representation has exactly one preterminal)')

    filler = application.add_mutually_exclusive_group()

    filler.add_argument('-write-filler', action="store_true", dest='write_junctures',
                    help='write filler elements (surrounded by @@)')
    filler.add_argument('-merge-filler', action="store_true", dest='merge_junctures',
                    help='write filler elements (concatenated with preceding segment, ending in @@)')

    args = parser.parse_args()

    return args

if __name__ == '__main__':

    args = parse_arguments()

    VERBOSE = not args.q
    MIN_SIZE = args.min_size
    MIN_COUNT = args.min_count
    MAX_COUNT = args.max_count
    FEWEST = args.fewest

    if sys.version_info < (3, 0):
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
        args.corpus = codecs.getreader('UTF-8')(args.corpus)
        sys.stderr = codecs.getwriter('UTF-8')(sys.stderr)

    if args.train:
        train_model(args.corpus, args.model, args.syntax)

    else:
        if args.module:
            if args.model.endswith('.py'):
                args.model = args.model[:-3]
            model = __import__(args.model)

        else:
            if sys.version_info < (3, 0):
                file_obj = codecs.getreader('UTF-8')(open(args.model, 'r'))
            else:
                file_obj = open(args.model, 'r', encoding='UTF-8')
            start = file_obj.read(100)
            offset = start.find('{')
            file_obj.seek(offset)
            model = {}
            model['model'] = json.load(file_obj)
            model = argparse.Namespace(**model)

        if args.smor:
            smor_server = SMORSplitter(args.smor, args.no_truecase)
            split_function = get_FST_splits
        else:
            smor_server = None
            split_function = get_unsupervised_splits


        apply_model(args.corpus, model.model, smor_server, split_function, args.write_junctures, args.merge_junctures, args.syntax, args.no_truecase, args.dependency)
