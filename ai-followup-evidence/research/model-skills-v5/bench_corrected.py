"""An explicitly separate corrected timestamp variant, without mutating the frozen transfer pack."""
from bench_long import *
import bench as core
original_reader=core.read_case

def read_case(cid):
    if cid!='N05':return original_reader(cid)
    root=HERE/'correction-case';seal=json.loads((root/'CASE_SEAL.json').read_text())
    for name,expected in seal['files'].items():assert sha((root/name).read_bytes())==expected
    case=json.loads((root/'case-private.json').read_text());raw=(root/'evidence.jsonl').read_bytes()
    locators=json.loads((root/'locators.json').read_text())
    return case,raw,locators,prior.groups(raw,locators)

core.read_case=read_case
