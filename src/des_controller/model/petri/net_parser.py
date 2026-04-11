"""Tools for parsing a Tina Toolbox textual format file (.net)."""

import dataclasses
from enum import Enum, StrEnum, auto
from typing import Final, cast
import pyparsing as pp


r"""
The grammar of the Tina Toolbox textual format file (.net) is described in:
<https://projects.laas.fr/tina/manuals/formats.html>.
As of 2026-03-29, the page reads:

* The .net format *

    This is the textual description format of Time Petri nets.

    A net is described by a series of declarations of places, transitions and/or notes, and an optional naming
    declaration for the net. The net described is the superposition of these declarations.
    The grammar of .net declarations is the following, in which nonterminals are bracketed by < .. >,
    terminals are in upper case or quoted. Spaces, carriage return and tabs act as separators.

    Optionally, labels may be assigned to places and transitions. This should be preferably done within
    "tr" and "pl" declarations rather than using separate "lb" declarations. The later form ("lb") is kept
    for backward compatibility and might disappear in future releases.

    Grammar:

    .net                    ::= (<trdesc>|<pldesc>|<lbdesc>|<prdesc>|<ntdesc>|<netdesc>)*
    netdesc                 ::= 'net' <net>
    trdesc                  ::= 'tr' <transition> {":" <label>} {<interval>} {<tinput> -> <toutput>}
    pldesc                  ::= 'pl' <place> {":" <label>} {(<marking>)} {<pinput> -> <poutput>}
    ntdesc                  ::= 'nt' <note> ('0'|'1') <annotation>
    lbdesc                  ::= 'lb' [<place>|<transition>] <label>
    prdesc                  ::= 'pr' (<transition>)+ ("<"|">") (<transition>)+
    interval                        ::= ('['|']')INT','INT('['|']') | ('['|']')INT','w['
    tinput                  ::= <place>{<arc>}
    toutput                 ::= <place>{<normal_arc>}
    pinput                  ::= <transition>{<normal_arc>}
    poutput                 ::= <transition>{arc}
    arc                     ::= <normal_arc> | <test_arc> | <inhibitor_arc> |
                                <stopwatch_arc> | <stopwatch-inhibitor_arc>
    normal_arc              ::= '*'<weight>
    test_arc                ::= '?'<weight>
    inhibitor_arc           ::= '?-'<weight>
    stopwatch_arc           ::= '!'<weight>
    stopwatch-inhibitor_arc ::= '!-'<weight>
    weight, marking         ::= INT{'K'|'M'|'G'|'T'|'P'|'E'}
    net, place, transition, label, note, annotation ::= ANAME | '{'QNAME'}'
    INT                     ::= unsigned integer
    ANAME                   ::= alphanumeric name, see Notes below
    QNAME                   ::= arbitrary name, see Notes below

    Notes:

    Two forms are admitted for net, place and transition names:
    - ANAME : any non empty string of letters, digits, primes ' and underscores _
    - '{'QNAME'}' : any chain between braces, and in which characters {, }, and \ are prefixed by \

    Empty lines and lines beginning with '#' are considered comments.

    In any closed temporal interval [eft,lft], one must have eft <= lft.

    The letter 'K' (resp. 'M', 'G', 'T', 'P', 'E') following a weight or marking multiplies it by 10^3
    (resp. 10^6, 10^9, 10^12, 10^15, 10^18).

    Weight is optional for normal arcs, but mandatory for test and inhibitor arcs

    By default:
    - transitions have temporal interval [0,w[
    - normal arcs have weight 1
    - places have marking 0
    - places and transitions have the empty label "{}"

    When several labels are assigned to some node, only the last assigned is kept. 
"""


"""
+--------------------------------------+
|                                      |
| Patterns for parsing a subset of the |
|               grammar.               |
|                                      |
+--------------------------------------+
"""


class Vocabulary(StrEnum):
    MANTISSA = auto()
    SUFFIX = auto()
    PLACE = auto()
    TRANSITION = auto()
    LABEL = auto()
    MARKING = auto()
    WEIGHT = auto()
    NORMAL_ARC = auto()
    TEST_ARC = auto()
    INHIBITOR_ARC = auto()
    ARC = auto()
    LOWER_BRACKET = auto()
    LOWER_LIMIT = auto()
    UPPER_LIMIT = auto()
    UPPER_BRACKET = auto()
    INTERVAL = auto()
    TINPUTS = auto()
    TOUTPUTS = auto()


QNAME: Final = pp.Combine(pp.OneOrMore(pp.CharsNotIn(r"\{}") | (pp.Suppress("\\") + pp.Char(r"\{}"))))
ANAME: Final = pp.Word(pp.alphanums + "_'")
INT: Final = pp.Word(pp.nums)

XNAME: Final = pp.Combine(ANAME | pp.Suppress("{") + QNAME + pp.Suppress("}"))
INTX: Final = pp.Group(INT(Vocabulary.MANTISSA) + pp.Opt(pp.Char("KMGTPE")(Vocabulary.SUFFIX)))

place: Final = XNAME(Vocabulary.PLACE)
transition: Final = XNAME(Vocabulary.TRANSITION)
label: Final = XNAME(Vocabulary.LABEL)

marking: Final = INTX(Vocabulary.MARKING)
weight: Final = INTX(Vocabulary.WEIGHT)

normal_arc: Final = pp.Group(pp.Suppress("*") + weight)(Vocabulary.NORMAL_ARC)
test_arc: Final = pp.Group(pp.Suppress("?") + weight)(Vocabulary.TEST_ARC)
inhibitor_arc: Final = pp.Group(pp.Suppress("?-") + weight)(Vocabulary.INHIBITOR_ARC)
arc: Final = pp.Group(normal_arc | test_arc | inhibitor_arc)(Vocabulary.ARC)

tinput: Final = pp.Group(place + pp.Opt(arc))
toutput: Final = pp.Group(place + pp.Opt(normal_arc))

interval: Final = pp.Group(
    pp.Char("[]")(Vocabulary.LOWER_BRACKET)
    + INT(Vocabulary.LOWER_LIMIT)
    + pp.Suppress(",")
    + (
        INT(Vocabulary.UPPER_LIMIT) + pp.Char("[]")(Vocabulary.UPPER_BRACKET)
        | pp.Literal("w")(Vocabulary.UPPER_LIMIT) + pp.Literal("[")(Vocabulary.UPPER_BRACKET)
    )
)(Vocabulary.INTERVAL)

trdesc: Final = (
    "tr"
    + transition
    + pp.Opt(pp.Suppress(":") + label)
    + interval
    + pp.ZeroOrMore(tinput.set_results_name(Vocabulary.TINPUTS, list_all_matches=True))
    + pp.Suppress("->")
    + pp.ZeroOrMore(toutput.set_results_name(Vocabulary.TOUTPUTS, list_all_matches=True))
)

pldesc: Final = "pl" + place + pp.Opt(pp.Suppress(":") + label) + pp.Opt(pp.Suppress("(") + marking + pp.Suppress(")"))


"""
+--------------------------------------+
|                                      |
|   Tools for turning parsed grammar   |
|   into structured representation.    |
|                                      |
+--------------------------------------+
"""


class ArcType(Enum):
    NORMAL_ARC = auto()
    TEST_ARC = auto()
    INHIBITOR_ARC = auto()


@dataclasses.dataclass(frozen=True)
class Arc:
    place: str
    arc_type: ArcType
    weight: int


@dataclasses.dataclass(frozen=True)
class TransitionDescription:
    transition: str
    label: str | None
    inputs: list[Arc]
    outputs: list[Arc]


@dataclasses.dataclass(frozen=True)
class PlaceDescription:
    place: str
    label: str | None
    markings: int


def parse_weight(weight) -> int:
    mantissa = int(weight[Vocabulary.MANTISSA])
    suffix = weight.get(Vocabulary.SUFFIX)
    exponent = {"K": 3, "M": 6, "G": 9, "T": 12, "P": 15, "E": 18}.get(suffix, 0)
    return mantissa * pow(10, exponent)


def try_parse_trdesc(desc: str) -> TransitionDescription | None:
    """Try to parse desc as a 'trdesc' string. Return None if it can't be done.
    See grammar description for the definition of 'trdesc'."""
    try:
        parsed = trdesc.parse_string(desc, parse_all=True)
    except pp.ParseException:
        return None

    name = cast(str, parsed[Vocabulary.TRANSITION])
    label = cast(str | None, parsed.get(Vocabulary.LABEL))

    inputs = []
    for t in parsed.get(Vocabulary.TINPUTS) or []:
        if arc := t.get(Vocabulary.ARC):
            if arc_inner := arc.get(Vocabulary.NORMAL_ARC):
                arc_type = ArcType.NORMAL_ARC
            elif arc_inner := arc.get(Vocabulary.TEST_ARC):
                arc_type = ArcType.TEST_ARC
            elif arc_inner := arc.get(Vocabulary.INHIBITOR_ARC):
                arc_type = ArcType.INHIBITOR_ARC
            else:
                assert False, "Unexpected arc type"
            weight = parse_weight(arc_inner[Vocabulary.WEIGHT])
        else:
            arc_type = ArcType.NORMAL_ARC
            weight = 1

        inputs.append(Arc(place=t[Vocabulary.PLACE], arc_type=arc_type, weight=weight))

    outputs = []
    for t in parsed.get(Vocabulary.TOUTPUTS) or []:
        if arc := t.get(Vocabulary.NORMAL_ARC):
            weight = parse_weight(arc[Vocabulary.WEIGHT])
        else:
            weight = 1

        outputs.append(Arc(place=t[Vocabulary.PLACE], arc_type=ArcType.NORMAL_ARC, weight=weight))

    return TransitionDescription(transition=name, label=label, inputs=inputs, outputs=outputs)


def try_parse_pldesc(desc: str) -> PlaceDescription | None:
    """Try to parse 'desc' as a 'pldesc' string. Return None if it can't be done.
    See grammar description for the definition of 'pldesc'."""
    try:
        parsed = pldesc.parse_string(desc, parse_all=True)
    except pp.ParseException:
        return None

    name = cast(str, parsed[Vocabulary.PLACE])
    label = cast(str | None, parsed.get(Vocabulary.LABEL))

    if m := parsed.get(Vocabulary.MARKING):
        markings = parse_weight(m)
    else:
        markings = 0

    return PlaceDescription(place=name, label=label, markings=markings)
