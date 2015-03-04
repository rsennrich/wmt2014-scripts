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


Instructions
------------

1. download and install all required software

  - mosesdecoder (http://statmt.org/moses/)
  - ParZu (https://github.com/rsennrich/ParZu)
  - mgiza (https://github.com/moses-smt/mgiza)
  - SRILM (http://www.speech.sri.com/projects/srilm/) [LM training could also be done with other tools, but SRILM is still used for interpolation]

2. set the paths in the first 20 lines of `toy_example.config`

3. run EMS with the example configuration. Models etc. are written to `working-dir`

  /path/to/mosesdecoder/scripts/ems/experiment.perl --config toy_example.config --exec


Common issues
-------------

this config was tested with moses commit dca8dd (4 March 2015). On older 
versions, it may run, but will not give good results, even with real data.