#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Simple script to infer ancestral alleles from outgroups based on
# majority vote
#
import os
import sys
import re
import argparse
import logging
import cyvcf2
from tqdm import tqdm

try:
    inputfile = snakemake.input.vcf
    outputfile = snakemake.output.vcf
    outgroup = snakemake.params.outgroup
    options = snakemake.params.options
except NameError as e:
    inputfile = None
    outputfile = None
    outgroup = None
    options = {'n': 1, 'ploidy': 2}

parser = argparse.ArgumentParser(description="""
Infer ancestral alleles in vcf based on majority vote in outgroups.
""")
parser.add_argument("--outgroup", metavar="outgroup", type=str,
                    help="outgroup name", action="append", default=outgroup)
parser.add_argument("--ploidy", metavar="ploidy", type=int, default=options.get('ploidy', 2),
                    help="set the ploidy")
parser.add_argument("-n", metavar="n", type=int, default=options.get('n', 1),
                    help="number of haplotypes that need to agree on ancestral state")
parser.add_argument("vcf", type=str, nargs="?",
                    help="Input vcf file", default=inputfile)
parser.add_argument("outfile", type=str, nargs="?",
                    help="Output vcf file", default=outputfile)

args = parser.parse_args()

if args.outgroup is None:
    logging.error("Need at least one outgroup")
    sys.exit(1)

nvote = max(args.n, 1)
if (args.n < 1):
    pass
elif (args.n > len(args.outgroup)):
    nvote = len(args.outgroup) * args.ploidy


vcf = cyvcf2.VCF(args.vcf)
# Make sure outgroups in samples
if not set(args.outgroup) <= set(vcf.samples):
    logging.error("not all outgroup names found in vcf sample header")
    sys.exit(1)



n_pass = 0
n_skip = 0
indices = [i for i in range(len(vcf.samples)) if vcf.samples[i] in args.outgroup]
outext = re.compile(r"(.vcf|.vcf.gz|.bcf)$").search(args.outfile)
if outext is None:
    logging.error("please use file extension .vcf, .vcf.gz, or .bcf")
    sys.exit(1)
outext = outext.group(1)
mode = {'.vcf': "w", '.vcf.gz': "wz", '.bcf': "wb"}[outext]


vcf.add_info_to_header({"ID": "AA",
                        "Number": 1,
                        "Type": "Character",
                        "Description": "Ancestral Allele"})
vcfwriter = cyvcf2.cyvcf2.Writer(args.outfile, vcf, mode)
for variant in tqdm(vcf):
    alleles = [variant.REF] + variant.ALT
    ancestral = variant.INFO.get("AA", variant.REF)
    ordered_alleles = [ancestral] + list(set(alleles) - {ancestral})
    if len(ordered_alleles) > 2:
        continue
    alleles = []
    anc = None
    for i in indices:
        alleles.extend([variant.genotypes[i][0], variant.genotypes[i][1]])
    if sum(alleles) >= nvote:
        anc = variant.ALT
    elif len(alleles) - sum(alleles) >= nvote:
        anc = variant.REF
    if isinstance(anc, list):
        anc = anc[0]
    if anc is not None:
        n_pass = n_pass + 1
        try:
            variant.INFO["AA"] = anc
        except AttributeError as e:
            print(e)
            print(variant, anc)
            raise
        vcfwriter.write_record(variant)
    else:
        n_skip = n_skip + 1
vcfwriter.close()

print("get_ancestral_allel.py summary")
print("------------------------------")
print(f"N pass: {n_pass}")
print(f"N skip: {n_skip}")