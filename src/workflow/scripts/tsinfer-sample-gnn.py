#!/usr/bin/env python3
import json

import pandas as pd
import tskit


ts = tskit.load(snakemake.input.trees)  # noqa: F821

samples_listed_by_population = [
    ts.samples(population=pop_id) for pop_id in range(ts.num_populations)
]

# Return an n_ind x n_pop array of gnn values
gnn = ts.genealogical_nearest_neighbours(ts.samples(), samples_listed_by_population)

sample_nodes = [ts.node(n) for n in ts.samples()]
sample_ids = [n.id for n in sample_nodes]

sample_names = [
    json.loads(ts.individual(n.individual).metadata)["name"] for n in sample_nodes
]

sample_pops = [
    json.loads(ts.population(n.population).metadata)["population"] for n in sample_nodes
]

gnn_table = pd.DataFrame(
    data=gnn,
    index=[
        pd.Index(sample_ids, name="Sample node"),
        pd.Index(sample_names, name="Individual"),
        pd.Index(sample_pops, name="Species"),
    ],
    columns=[json.loads(p.metadata)["population"] for p in ts.populations()],
)

# Save gnn table
gnn_table.to_csv(snakemake.output.gnn, header=True)  # noqa: F821


# FIXME: this should be an option; don't know beforehand how we want
# to group data

# Calculate mean overall gnn scores grouped by Species
gnn_mean = gnn_table.groupby(level="Species").mean()
gnn_mean.to_csv(snakemake.output.mean, header=True)  # noqa: F821