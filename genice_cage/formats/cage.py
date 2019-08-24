#!/usr/bin/env python
# coding: utf-8
"""
A GenIce format plugin to detect cage-like topologies.

Usage: 
    % genice CS1 -r 2 2 2 -f cage[12,14-16:maxring=6] 
    % genice CRN1 -f cage[3-10:json] 
    % genice CRN1 -f cage[3-10:yaplot] 

It may not work with a small structure. (In the example above, the unit cell of CS1 is extended to 2x2x2 so as to avoid detecting cell-spanning wierd cages.)

Options:
    Cage sizes to be listed, separated by commas and ranged with hyphens. (default is 3 to 8)
    maxring=x  Specify the maximum ring size (default=8).
    json       Output in [JSON](https://www.json.org/) format.
    yaplot     Visualize with [Yaplot](https://github.com/vitroid/Yaplot/). Cages are drawn in different layers according to the number of faces, and faces are colored according to the number of vertices.
"""

import networkx as nx
from countrings import countrings_nx as cr
from genice_cage.polyhed import Polyhed
import json
import numpy as np
from logging import getLogger
import yaplotlib as yp

def centerOfMass(members, rpos):
    logger = getLogger()
    dsum = np.zeros(3)
    for member in members:
        d = rpos[member] - rpos[members[0]]
        d -= np.floor(d+0.5)
        dsum += d
    com = rpos[members[0]] + dsum / len(members)
    com -= np.floor(com)
    return com


def hook2(lattice):
    global options

    logger = getLogger()
    logger.info("Hook2: Cages and vitrites")

    cell = lattice.repcell.mat
    positions = lattice.reppositions
    graph = nx.Graph(lattice.graph) #undirected
    maxringsize = options["maxring"]
    ringlist = [[int(x) for x in ring] for ring in cr.CountRings(graph).rings_iter(maxringsize)]
    ringpos = [centerOfMass(ringnodes, positions) for ringnodes in ringlist]
    logger.info("  Rings: {0}".format(len(ringlist)))
    maxcagesize = max(options["sizes"])
    cages = []
    for cage in Polyhed(ringlist, maxcagesize):
        if len(cage) in options["sizes"]:
            cages.append(list(cage))
    logger.info("  Cages: {0}".format(len(cages)))
    cagepos = np.array([centerOfMass(cage, ringpos) for cage in cages])
    if options["json"]:
        output = dict()
        output["rings"] = ringlist
        output["cages"] = cages
        output["ringpos"] = [[x,y,z] for x,y,z in ringpos]
        output["cagepos"] = [[x,y,z] for x,y,z in cagepos]
        print(json.dumps(output, indent=2, sort_keys=True))
    elif options["yaplot"]:
        s = ""
        for c, cage in enumerate(cages):
            nodes = dict()
            cagesize = len(cage)
            for ringid in cage:
                ns = ringlist[ringid]
                for node in ns:
                    if node not in nodes:
                        # relative pos of the node
                        nodepos = positions[node] - cagepos[c]
                        nodepos -= np.floor( nodepos + 0.5 )
                        # shrink a little
                        nodes[node] = nodepos * 0.9
                s += yp.Color(len(ns))
                s += yp.Layer(cagesize)
                polygon = (np.array([nodes[node] for node in ns]) + cagepos[c]) @ cell
                s += yp.Polygon(polygon)
        print(s + "\n")
    else:
        # human-friendly redundant format
        for cageid, cage in enumerate(cages):
            print("Cage {0}: ({1}, {2}, {3}) {4} hedron".format(cageid, *cagepos[cageid], len(cage)))
            for ringid in sorted(cage):
                print("  Ring {0}: ({1}, {2}, {3}) {4} gon".format(ringid, *ringpos[ringid], len(ringlist[ringid])))
                print("    Nodes: {0}".format(ringlist[ringid]))

    logger.info("Hook2: end.")


def argparser(lattice, arg):
    global options

    logger = getLogger()
    logger.info("Hook0: Parse options for cage plugin.")

    options={"sizes":set(), "maxring":8, "json":False, "yaplot":False}

    if arg != "":
        for a in arg.split(":"):
            decl = a.split("=")
            if len(decl) == 2:
                if decl[0] == "maxring":
                    options["maxring"] = int(decl[1])
                else:
                    assert False, "Wrong declaration."
            elif a in ("json", "JSON"):
                options["json"] = True
            elif a in ("yaplot",):
                options["yaplot"] = True
            else:
                # value list for cage sizes
                for v in a.split(","):
                    w = v.split("-")
                    if len(w) == 2:
                        if w[0] == "":
                            w[0] = "1"
                        if w[1] == "":
                            w[1] = "20"
                        for x in range(int(w[0]), int(w[1])+1):
                            options["sizes"].add(x)
                    else:
                        options["sizes"].add(int(v))

    if len(options["sizes"]) == 0:
        options["sizes"] = {3,4,5,6,7,8}

    logger.info("  Max ring size: {0}".format(options["maxring"]))
    logger.info("  Cage sizes:    {0}".format(options["sizes"]))

    logger.info("Hook0: end.")

hooks = {0:argparser, 2:hook2}
