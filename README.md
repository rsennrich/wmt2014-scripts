Scripts for Edinburgh English-German syntax system for WMT 2014
===============================================================

This repository contains scripts used for the Edinburgh syntax submission (UEDIN-SYNTAX) for the English-German
shared translation task at the 2014 Workshop on Statistical Machine Translation (http://www.statmt.org/wmt14/).

The scripts will facilitate the reproduction of our results, and may be useful for people who want to use ParZu (or a different parser with the dependency format by Kilian Foth) for SMT,
or *-German string-to-tree systems in general. The hybrid compound splitter can also be used for phrase-based systems, and with German as source language.

CONTENTS
--------

- hybrid_compound_splitter.py

   compound splitter for German (hybrid of finite-state and corpus-based methods as described in Fritzinger & Fraser (2010)),
   with a novel syntactic representation of split compounds for simple compound merging after string-to-tree translation.
   The syntactic representation of split compounds is treebank independent and described in Sennrich, Williams and Huck (2014).

   The system to WMT 2014 used the following commands for training/applying the compound splitter:

   `hybrid_compound_splitter.py -train -syntax -corpus INPUT_FILE -model MODEL_FILE`
   `hybrid_compound_splitter.py -write-filler -no-truecase -q -syntax -smor zmorge-{version}-smor_newlemma.a -model MODEL_FILE < INPUT_FILE > OUTPUT_FILE`

   In a string-to-tree system with a syntactic representation of compounds,
   just apply the following regex substitution to the output for compound merging:

   `s/ \@(.*?)\@ /\1/g;`

- enrich_labelset.py

   modification of ParZu dependency label set for SMT, splitting up overgeneral labels into distinct subtypes.
   This script can be applied to ParZu output in CONLL format (before conversion into moses format
   with the script included in mosesdecoder under `scripts/training/wrappers/conll2mosesxml.py`).

   Use command line option `--wmt14` to activate the modifications used for the submission.
   Assuming you have the (German-side) tokenized corpus as `INPUT_FILE`, the Moses parsed files are generated as follows:

   ```
   /path/to/mosesdecoder/scripts/tokenizer/deescape-special-chars.perl < INPUT_FILE | \
    /path/to/ParZu/parzu -i tokenized_lines --projective | \
    enrich_labelset.py --wmt14 | \
    /path/to/mosesdecoder/scripts/training/wrappers/conll2mosesxml.py
    ```

LICENSE
-------

The scripts are available under the LGPL v2.

PUBLICATIONS
------------

The Edinburgh syntax submission to WMT 2014 is described in:

 Philip Williams, Rico Sennrich, Maria Nadejde, Matthias Huck, Eva Hasler and Philipp Koehn (2014): 
   Edinburgh's Syntax-Based Systems at WMT 2014. In: Proceedings of the Ninth Workshop on Statistical Machine Translation.

More details are provided in:

 Rico Sennrich, Philip Williams, Matthias Huck (2014):
   A tree does not make a well-formed sentence: Improving syntactic string-to-tree statistical machine translation with more linguistic knowledge.
   In: Computer Speech & Language (in press).
