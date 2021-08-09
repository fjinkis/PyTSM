# Overview PyTSM

## Requirements

- Python 3.8+ & pip
- dsmadmc client

## Install

1. Run `virtualenv env`
1. Enter to the environment
   1.1. Windows
   `cmd env\Scripts\activate `
   1.2. Linux
   `shell source env/bin/activate `
1. Run `pip install -r requirements.txt`
1. Setup the /config/tsmConfig.yaml

## Gotchas

- Every script built in /src uses the library /src/lib/tsm.py
- Global or commmon functions are defined in /src/common
- All the YAML files are in /config
