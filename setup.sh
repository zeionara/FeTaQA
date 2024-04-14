#!/bin/bash

set -e

if test -z "$CONDA_ROOT"; then
  for dir in anaconda anaconda3 miniconda miniconda3 conda conda3; do
    candidate="$HOME/$dir"
    if test -d "$candidate"; then
      CONDA_ROOT="$candidate"
      break
    fi

    candidate="/opt/$dir"
    if test -d "$candidate"; then
      CONDA_ROOT="$candidate"
      break
    fi
  done
fi

if test -z "$CONDA_ROOT"; then
  echo "Can't find conda installation root at $HOME. Please install conda first"
  exit 1
fi

echo "Using conda at $CONDA_ROOT"

source "$CONDA_ROOT/etc/profile.d/conda.sh"

conda create --name tables python=3.12 -y
conda activate tables

conda install python-lsp-server -y
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia

pip install transformers nltk numpy datasets chardet transformers accelerate sacrebleu bert_score 'camelot-py[cv]' python-docx
pip install git+https://github.com/google-research/bleurt.git

# To install ghostscript see: https://ghostscript.readthedocs.io/en/gs10.03.0/Install.html and https://ghostscript.com/docs/9.55.0/Install.htm. Basically:
#
# wget https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10030/ghostscript-10.03.0.tar.xz /tmp
# tar -C /tmp -xJvf /tmp/ghostscript-10.03.0.tar.xz
# cd ghostscript-10.03.0
#
# ./configure
# make
# sudo make soinstall
