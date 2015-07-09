#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Rico Sennrich

# this script modifies the ParZu grammar output to a representation that is more suitable for SMT:
# ambiguous labels are split, and optionally enriched with morphological information. The script also restructures coordinations.
# The modifications (the subset used for the WMT 2014 shared translation task EN-DE) are described in:
#  Rico Sennrich, Philip Williams, Matthias Huck (2015):
#    A tree does not make a well-formed sentence: Improving syntactic string-to-tree statistical machine translation with more linguistic knowledge.
#    In: Computer Speech & Language 32(1), 27-45.

from __future__ import print_function, unicode_literals
import sys
import codecs
from collections import defaultdict

#at which point in the morphological output is case information stored
CASE_POSITION = {b'ADJA':2
                    ,b'PPER':3
                    ,b'ART':2
                    ,b'APPRART':0
                    ,b'APPR':0
                    ,b'APPO':0
                    ,b'PRF':2
                    ,b'NN':1
                    ,b'FM':1
                    ,b'NE':1
                    ,b'PIS':1
                    ,b'PIAT':1
                    ,b'PDS':1
                    ,b'PIDAT':1
                    ,b'PPOSS':1
                    ,b'PPOSAT':1
                    ,b'PRELS':1
                    ,b'PRELAT':1
                    ,b'PWS':1
                    ,b'PWAT':1
                    }



GENDER_POSITION = {b'ADJA':1
                    ,b'PPER':2
                    ,b'ART':1
                    ,b'NN':0
                    ,b'FM':0
                    ,b'NE':0
                    ,b'PIS':0
                    ,b'PIAT':0
                    ,b'PDS':0
                    ,b'PIDAT':0
                    ,b'PPOSS':0
                    ,b'PRELS':0
                    ,b'PPOSAT':0
                    ,b'PRELAT':0
                    ,b'PWS':0
                    ,b'PWAT':0
                    }


NUMBER_POSITION = {b'ADJA':3
                    ,b'PPER':1
                    ,b'ART':3
                    ,b'PRF':1
                    ,b'NN':2
                    ,b'FM':2
                    ,b'NE':2
                    ,b'PIS':2
                    ,b'PIAT':2
                    ,b'PDS':2
                    ,b'PIDAT':2
                    ,b'PPOSS':2
                    ,b'PPOSAT':2
                    ,b'PRELS':2
                    ,b'PRELAT':2
                    ,b'PWS':2
                    ,b'PWAT':2
                    ,b'VVFIN':1
                    ,b'VAFIN':1
                    ,b'VMFIN':1
                    }


PERSON_POSITION = {b'PPER':0
                    ,b'VVFIN':0
                    ,b'VAFIN':0
                    ,b'VMFIN':0
                    }


KEYWORDS = ['pos','word','lemma','tag','tag2','morph','head','func', 'proj_head', 'proj_func']
def create_named_dict(values):
    return dict(zip(KEYWORDS,values))

def sorted_values(named_dict):
    return [named_dict[keyword] for keyword in KEYWORDS]

def write(sentence):
    for word in sentence:
        sys.stdout.write(b'\t'.join(sorted_values(word)) + b'\n')
    sys.stdout.write(b'\n')

def main(fobj_in):
    sentence = []
    for line in fobj_in:

        if line == b"\n":
            convert(sentence)
            write(sentence)
            sentence = []
            continue

        word = create_named_dict(line.split())
        sentence.append(word)


def convert(sentence):

    spans = get_spans(sentence)
    for word in sentence:

        if word['func'] != word['proj_func']:
            sys.stderr.write('Whoops, better check why label and projective label are different\n')
            sys.stderr.write(b'\t'.join(sorted_values(word)) + b'\n')
            sys.exit(1)

        if word['func'] in CONVERSIONS:
            CONVERSIONS[word['func']](word, sentence, spans)

def get_head(word, sentence):
    head_position = int(word['proj_head'])
    if head_position:
        return sentence[head_position-1]

def comma_is_kon(word, sentence, spans):
    '''if comma joins two coordinated elements, mark this with a new function,
    then make it the head of the element to the right, and the dependent of the element to the left.
    this allows for recursive addition of new coordinated elements.

    '''

    if not 'kon' in CONVERSIONS:
        return

    head = get_head(word, sentence)
    if head and head['func'] == b'kon' and int(word['proj_head']) > int(word['pos']) and head['tag'] != b'KON':
        # make sure projectivity isn't violated
        if not any(int(w['proj_head']) > int(word['pos']) or int(w['proj_head']) < int(head['proj_head']) for w in sentence[int(head['proj_head']):int(word['pos'])-1]):
            word['proj_head'] = head['proj_head']
            head['proj_head'] = word['pos']
            word['proj_func'] = b'kon'
            word['func'] = b'kon'
            kon_conversion(word, sentence, spans)
            return word['func']

def aux_conversion(word, sentence, spans):
    '''distinguish between past participle and infinitive auxiliary verbs to avoid overgeneralization.'''
    morph_info = b''
    if word['tag2'].endswith(b'PP'):
        morph_info = b'_pp'
    elif word['tag2'].endswith(b'INF'):
        if any(w['tag'] == b'PTKZU' and w['head'] == word['pos'] for w in sentence):
            morph_info = b'_izu'
        else:
            morph_info = b'_inf'
    elif word['tag2'].endswith(b'IZU'):
        morph_info = b'_izu'

    word['func'] += morph_info
    word['proj_func'] += morph_info


def root_conversion(word, sentence, spans):
    '''distinguish between five types of structures that receive label 'root':
    punct: full stops, question marks etc.
    comma: commas
    bracket: quotation marks, hyphens, and brackets
    vroot: full verb; root of a successful parse
    root: everything else; typically root of partial trees.

    '''
    morph_info = word['func']
    if word['tag2'] == b'$.':
        morph_info = b'punct'
    elif word['tag2'] == b'$(':
        morph_info = b'bracket'
    elif word['tag2'] in [b'VVFIN',b'VMFIN',b'VAFIN']:
      # try to only give label 'vroot' to main clause roots, not to verb-last structures that remain unattached in parse
      midfield_labels = set(['subj','obja','subjc','adv','pred','pp','objp'])
      aux_labels = set(['aux','aux_pp','aux_inf','aux_vvizu'])
      direct_dependents_left = [w for w in sentence[:int(word['pos'])] if w['proj_head'] == word['pos'] and w['tag2'] not in ['$,','$(']]
      direct_dependents_right = [w for w in sentence[int(word['pos']):] if w['proj_head'] == word['pos']]
      if (len(direct_dependents_left) < 2 and not any(w['proj_func'] in aux_labels for w in direct_dependents_left)) or any(w['proj_func'] in midfield_labels for w in direct_dependents_right):
          morph_info = b'vroot'
    elif word['tag2'] == b'$,':
        morph_info = comma_is_kon(word, sentence, spans)
        if not morph_info:
            morph_info = b'comma'

    # mark remaining roots that cover the full sentence (or anything between two punctuation marks) with 'sroot'
    if morph_info  == b'root':
        dependents = sorted(get_dependents_for_word(word, spans))
        if dependents[0] == 0 or sentence[dependents[0]-1]['tag2'] == b'$.' or (sentence[dependents[0]-1]['tag2'] == b'$(' and (dependents[0]-1 == 0 or sentence[dependents[0]-2]['tag2'] == b'$.')):
            if dependents[-1]+1 == len(sentence) or sentence[dependents[-1]+1]['tag2'] == b'$.' or (sentence[dependents[-1]+1]['tag2'] == b'$(' and (dependents[-1]+2 == len(sentence) or sentence[dependents[-1]+2]['tag2'] == b'$.')):
                morph_info = b'sroot'

    word['func'] = morph_info
    word['proj_func'] = morph_info


def obji_conversion(word, sentence, spans):
    '''distinguish between infinitive with 'zu' and bare infinitive
    examples: 
    ich lasse ihn schlafen/obji_bare
    ich bitte ihn, zu schlafen/obji_zu
    '''
    morph_info = b''
    if word['tag2'] == b'VVIZU':
        morph_info = b'_zu'
    elif any(w['tag'] == b'PTKZU' and w['head'] == word['pos'] for w in sentence):
        morph_info = b'_zu'
    else:
        morph_info = b'_bare'

    word['func'] += morph_info
    word['proj_func'] += morph_info

    dependents = sorted(get_dependents_for_word(word, spans))
    if sentence[dependents[0]]['proj_func'] == b'comma':
        word['func'] += b'_comma'
        word['proj_func'] += b'_comma'

def pn_conversion(word, sentence, spans):
    '''add grammatical case to prepositional noun'''
    head = get_head(word, sentence)
    case = get_morphology(head)['case']

    if case != b'_':
        word['func'] += b'_'+ case
        word['proj_func'] += b'_'+ case


def np_conversion(word, sentence, spans):
    '''enforce agreement within NP (case, number, gender)'''
    morph_dict = get_morphology(word)

    # gender doesn't matter for plural agreement
    if morph_dict['number'] == 'pl':
        morph_dict['gender'] = b'_'

    morph_info = morph_dict['gender'] + b'-' + morph_dict['case'] + b'-' + morph_dict['number']

    if morph_info != b'_-_-_':
        word['func'] += b'_'+ morph_info
        word['proj_func'] += b'_'+ morph_info


def subj_coord_conversion(word, sentence, spans):
    '''mark coordinated subjects (which do not need to agree with verb in number)'''
    if any(w['proj_func'] == 'kon' and w['proj_head'] == word['pos'] for w in sentence):
        word['func'] = b'csubj'
        word['proj_func'] = b'csubj'

def subj_conversion(word, sentence, spans):
    '''enforce agreement between subject and verb (person/number)'''

    head = get_head(word, sentence)
    morph_dict = get_morphology(head)

    morph_info = morph_dict['person'] + b'-' + morph_dict['number']

    if morph_info != b'_-_':
        word['func'] += b'_'+ morph_info
        word['proj_func'] += b'_'+ morph_info


def kon_conversion(word, sentence, spans):
    '''
    let elements in coordination copy the label of the first element,
    and mark commas and conjunctions with label that specifies what type of structure is coordinated.

    '''
    head = get_head(word, sentence)
    while head and (head['func'].startswith(b'kon') or head['func'].startswith(b'app') or head['func'].startswith(b'cj')):
        head = get_head(head, sentence)

    if head:
        headfunc = head['func']
    else:
        headfunc = b'root'

    # ignore comparative clause
    if headfunc.startswith(b'kom'):
        return

    elif headfunc.startswith(b'rel') or headfunc.startswith(b'objc') or headfunc.startswith(b'subjc') or headfunc.startswith(b'neb'):
        headfunc = b'vkon_sub'

    # ignore number/person information
    elif headfunc.startswith(b'subj'):
        headfunc = b'subj'

    if word['func'] == b'cj' and headfunc == b'csubj':
        headfunc = b'subj'

    if word['func'] == b'kon' and word['tag'] == b'KON' or word['tag'] == b'$,':
        word['func'] += b'_'+ headfunc
        word['proj_func'] += b'_'+ headfunc
    else:
        word['func'] = headfunc
        word['proj_func'] = headfunc


def gmod_conversion(word, sentence, spans):
    '''distinguish between premodifying and postmodifying genitive modifiers
    premodifying are typically named entities without articles (Peters X)
    postmodifying are typically noun phrases with articles (X der Firma)

    '''
    if int(word['pos']) > int(word['proj_head']):
        info = b'post'
    else:
        info = b'pre'

    word['func'] += b'_'+ info
    word['proj_func'] += b'_'+ info

def pred_conversion(word, sentence, spans):
    '''distinguish between adverbial and nominal predicates'''

    info = b''
    if word['tag2'] in [b'ADJD',b'ADV',b'PWAV']:
        info = b'_adv'
    elif word['tag2'] in [b'NE', b'NN', b'FM', b'PIS', b'PPER', b'PWS', b'ADJA']:
        info = b'_nn'

    word['func'] += info
    word['proj_func'] += info

def get_morphology(word):
    morph_info = word['morph'].split(b'|')
    morph_dict = {}

    tag = word['tag2']

    try:
        morph_dict['case'] = morph_info[CASE_POSITION[tag]].lower()
    except (IndexError, KeyError):
        morph_dict['case'] = b'_'

    try:
        morph_dict['gender'] = morph_info[GENDER_POSITION[tag]].lower()
    except (IndexError, KeyError):
        morph_dict['gender'] = b'_'

    try:
        morph_dict['number'] = morph_info[NUMBER_POSITION[tag]].lower()
    except (IndexError, KeyError):
        morph_dict['number'] = b'_'

    try:
        morph_dict['person'] = morph_info[PERSON_POSITION[tag]].lower()
    except (IndexError, KeyError):
        morph_dict['person'] = b'_'

    return morph_dict


def get_spans(sentence):
    spans = {}
    dominates = defaultdict(set)
    for i,w in enumerate(sentence):
        dominates[i].add(i)
        head = int(w['proj_head'])-1
        while head != -1:
            if i in dominates[head]:
                break
            dominates[head].add(i)
            head = int(sentence[head]['proj_head'])-1

    return dominates

def get_dependents_for_word(word, dependents):
    return dependents[int(word['pos'])-1]

CONVERSIONS = {b'aux':aux_conversion
                ,b'root':root_conversion
                ,b'obji':obji_conversion
                ,b'pn':pn_conversion
                ,b'det':np_conversion
                ,b'attr':np_conversion
                ,b'subj':subj_conversion
                ,b'kon':kon_conversion
                ,b'cj':kon_conversion
                ,b'gmod':gmod_conversion
                ,b'pred':pred_conversion
                }

if __name__ == '__main__':
    if sys.version_info >= (3,0,0):
        sys.stdin = sys.stdin.buffer
        sys.stdout = sys.stdout.buffer
        sys.stderr = sys.stderr.buffer

    # conversions used for WMT 14
    if '--wmt14' in sys.argv:
      CONVERSIONS = {b'root':root_conversion
                ,b'kon':kon_conversion
                ,b'cj':kon_conversion
                ,b'gmod':gmod_conversion}

    if '--wmt15' in sys.argv:
      CONVERSIONS = {b'root':root_conversion
                ,b'kon':kon_conversion
                ,b'cj':kon_conversion
                ,b'gmod':gmod_conversion
                ,b'subj':subj_coord_conversion
                ,b'obji':obji_conversion}

    if '--coord-subj' in sys.argv:
        CONVERSIONS[b'subj'] = subj_coord_conversion

    if '--obji' in sys.argv:
        CONVERSIONS[b'obji'] = obji_conversion

    for arg in sys.argv[1:]:
        if arg.startswith('--disable_'):
            disabled_class = arg.split('_',1)[1].encode('UTF-8')
            del CONVERSIONS[disabled_class]

    main(sys.stdin)
