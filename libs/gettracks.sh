#!/bin/bash
cdparanoia -sQ |& grep -P "^\s+\d+\." | wc -l
