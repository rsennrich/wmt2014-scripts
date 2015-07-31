#!/bin/bash

#perform compound splitting and particle verb restructuring

script_dir=$1
shift
smor=$1
shift

$script_dir/hybrid_compound_splitter.py \
  -smor $smor \
  -write-filler -no-truecase -q -syntax -fewest -dependency $@ \
| $script_dir/emnlp2015/hyphen-splitter.py -syntax \
| $script_dir/emnlp2015/separable_prefix.py $smor