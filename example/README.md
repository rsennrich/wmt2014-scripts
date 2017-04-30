Toy EMS Config for String-to-Tree SMT System 
============================================

The EMS configuration file `toy_example.config` documents the settings used to 
build a string-to-tree SMT system like our submission to WMT 2014.

The configuration only uses some toy data that is provided with this repository, 
but a full-scale system can be implemented by replacing references to 
`parallelA`, `parallelB` and `monolingualA` with real data sets, and changing 
the tuning and evaluation sets.

Main differences from the WMT 2014 submission:

  - this config does not include syntactic constraints
  - this config does not filter the tuning set to short sentences

The file `toy_example_2015.config` shows the base configuration of the WMT 2015 submissions.
It includes tuning on the head-word chain metric (HWCM), and some updated settings.

  - `toy_example_2015_2.config` adds head binarization
  - `toy_example_2015_3.config` adds a relational dependency language model
  - `toy_example_2015_4.config` adds source-syntactic constraints
  - `toy_example_2015_5.config` adds a 5-gram neural language model
  - `toy_example_2015_6.config` slighly modifies compound splitting, and adds particle verb restructuring

[on real-sized data, some steps (such as parsing and training neural networks on all monolingual data)
may take a long time, and you may want to consider to manually distribute the workload over many machines,
and/or to only parse the parallel data and train neural networks on a subset of data, and/or for fewer epochs.]

`toy_example_2015_5.config` contains all models of our official WMT 2015 submission (uedin-syntax); our submission contains two manual "hacks" not automated by EMS:
  - we remove all virtual nodes from the tree binarization (those starting in "^") from `model/unknown-word-soft-matches.*`
    [this means that unknown words are not allowed to match those nodes; RDLM produces lots of warnings if these matches are allowed]
  - we remove all rule table entries from `model/phrase-table.*` whose target side contains words that are not in the vocabulary of RDLM and NPLM.
    [this avoids problems with poor probability estimates for those translations]
    (see `emnlp2015/oov_filter.py`)



Instructions
------------

1. download and install all required software

  - mosesdecoder (http://statmt.org/moses/)
  - ParZu (https://github.com/rsennrich/ParZu)
  - mgiza (https://github.com/moses-smt/mgiza)
  - SRILM (http://www.speech.sri.com/projects/srilm/) [LM training could also be done with other tools, but SRILM is still used for interpolation]

for some configs, also install the following:
  - NPLM (https://github.com/rsennrich/nplm/) for RDLM and NPLM toy_example_2015_{3,5}
    if you use NPLM, (re-)compile Moses with the option "--with-nplm=<root dir of the NPLM toolkit>"
  - Stanford CoreNLP (http://nlp.stanford.edu/software/corenlp.shtml) for English parsing for toy_example_2015_4
  - Maltparser (http://www.maltparser.org/) for projectivization of English parse trees for toy_example_2015_4

2. set the paths in the first 20 lines of `toy_example.config`

3. run EMS with the example configuration. Models etc. are written to `working-dir`

  /path/to/mosesdecoder/scripts/ems/experiment.perl --config toy_example.config --exec


Common issues
-------------

these configs were tested with moses commit 5d8af9c (29 May 2015), and 89d16a4 (31 July 2015).
