#!/bin/bash

# EMS hack: do post-processing of particle verbs in detruecase step;
# instead of string translation output, we need tree output that we take from -Ttree file.

script_dir=$1
shift

grep "Full Tree" $1 | cut -f 2- -d ":" | cut -f "2-" -d " " | \
python3 $script_dir/emnlp2015/unbinarize.py | \
python $script_dir/emnlp2015/separable_prefix_postprocessing.py
