"""
Find all OmniScripts that (directly or transitively) create/update records on
objects with master-detail relationships. Such writes will fail in the new
release per the QA Slack escalation.

Trace path:
  OmniScript -> IntegrationProcedure(s) -> ... -> DataRaptor Load -> SObject(MD-child)

Outputs a markdown report at requirements/vendor/scripts/md_omniscripts_report.md
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "force-app" / "main" / "default"
DT_DIR = ROOT / "omniDataTransforms"
IP_DIR = ROOT / "omniIntegrationProcedures"
OS_DIR = ROOT / "omniScripts"
OUT = Path(__file__).resolve().parent / "md_omniscripts_report.md"

# 1. Master-detail child objects (records of these have MD parents).
MD_CHILD_OBJECTS = {
    "PRM_CaseManagerAssociation__c": "IndividualApplication",
    "PRM_ContactMethod__c": "HealthcareFacility",
    "PRM_ProgramParticipation__c": "PRM_Program__c",
    "PRM_CaseDataManager__c": "IndividualApplication",
    "PRM_AccountContractEntity__c": "Account",
}

NAME_RE = re.compile(r"<name>([^<]+)</name>")
OUTPUT_OBJ_RE = re.compile(r"<outputObjectName>([^<]+)</outputObjectName>")
LANGUAGE_RE = re.compile(r"<language>([^<]+)</language>")
IS_ACTIVE_RE = re.compile(r"<isActive>(true|false)</isActive>")


def file_active(text: str) -> bool:
    """Whether the *top-level* OmniProcess element is active.
    The first <isActive> in the document is the top-level one.
    """
    m = IS_ACTIVE_RE.search(text)
    return m is not None and m.group(1) == "true"


def file_root_name(text: str) -> str | None:
    m = NAME_RE.search(text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Step A: Find DataRaptor Loads (DRLoad) that write to any MD-child object.
# ---------------------------------------------------------------------------
md_writer_drs: dict[str, set[str]] = defaultdict(set)  # dr_name -> {target_obj}
for fp in DT_DIR.glob("*.rpt-meta.xml"):
    txt = fp.read_text(encoding="utf-8", errors="ignore")
    outputs = set(OUTPUT_OBJ_RE.findall(txt))
    md_hits = outputs & MD_CHILD_OBJECTS.keys()
    if md_hits:
        dr_name = file_root_name(txt) or fp.stem
        md_writer_drs[dr_name].update(md_hits)

print(f"[A] MD-writing DataRaptors: {len(md_writer_drs)}")

# ---------------------------------------------------------------------------
# Step B: Build IP catalog + IP -> (DRs called, IPs called) call graph.
# Each IP file has a <name> (Type) and <language> (SubType, usually "Procedure").
# Inside IPs, DRPostAction steps reference DRs by name in a "bundle" property.
# IPs are referenced by other IPs / OmniScripts via integrationProcedureKey
# which is "<Type>_<SubType>".
# ---------------------------------------------------------------------------
import html as _html

# propertySetConfig JSON is XML-escaped (&quot; instead of "). After unescaping
# we can extract bundle (DR ref) and integrationProcedureKey (IP ref) values.
IP_KEY_RE = re.compile(r'"integrationProcedureKey"\s*:\s*"([^"]+)"')
BUNDLE_RE = re.compile(r'"bundle"\s*:\s*"([^"]+)"')


def _refs(text: str, pattern: re.Pattern[str]) -> set[str]:
    return set(pattern.findall(_html.unescape(text)))

# ip_versions[procedure_key] = list of (file_path, isActive, name, language)
ip_versions: dict[str, list[tuple[Path, bool, str, str]]] = defaultdict(list)
ip_dr_calls: dict[Path, set[str]] = defaultdict(set)
ip_ip_calls: dict[Path, set[str]] = defaultdict(set)

def _proc_key_from_filename(fp: Path) -> str:
    """OmniScripts reference IPs by the filename prefix minus the
    "_<SubType>_<version>.oip-meta.xml" tail.

    Example: PRM_PDMRecordsCreationParent_Procedure_1.oip-meta.xml
             -> PRM_PDMRecordsCreationParent
    """
    stem = fp.name.removesuffix(".oip-meta.xml")
    # strip trailing _<version>
    stem = re.sub(r"_\d+$", "", stem)
    # strip trailing _<SubType> (Procedure | English | language token)
    stem = re.sub(r"_(Procedure|English|Spanish|French|German|Italian|Japanese|Chinese|Korean|Portuguese|Dutch|Russian|Turkish|Arabic)$", "", stem)
    return stem


for fp in IP_DIR.glob("*.oip-meta.xml"):
    txt = fp.read_text(encoding="utf-8", errors="ignore")
    name = file_root_name(txt)
    lang_m = LANGUAGE_RE.search(txt)
    if not name or not lang_m:
        continue
    language = lang_m.group(1)
    proc_key = _proc_key_from_filename(fp)
    is_active = file_active(txt)
    ip_versions[proc_key].append((fp, is_active, name, language))
    ip_dr_calls[fp].update(_refs(txt, BUNDLE_RE))
    ip_ip_calls[fp].update(_refs(txt, IP_KEY_RE))

# Pick the "best" version of each IP: prefer active, fall back to highest suffix.
best_ip_file: dict[str, Path] = {}
for proc_key, versions in ip_versions.items():
    active = [v for v in versions if v[1]]
    chosen = (
        active[0] if active
        else max(versions, key=lambda v: int(re.search(r"_(\d+)\.oip", v[0].name).group(1) or 0))
    )
    best_ip_file[proc_key] = chosen[0]

print(f"[B] Unique IPs (procedure keys): {len(best_ip_file)}")

# ---------------------------------------------------------------------------
# Step C: Determine which IPs eventually write to an MD-child object.
# Start with IPs whose chosen version directly calls an MD-writing DR.
# Then expand transitively through ip_ip_calls until fixed point.
# ---------------------------------------------------------------------------
md_writer_dr_names = set(md_writer_drs.keys())
md_writer_ip_keys: set[str] = set()
ip_reason: dict[str, set[str]] = defaultdict(set)  # proc_key -> reasons

for proc_key, fp in best_ip_file.items():
    direct_drs = ip_dr_calls[fp] & md_writer_dr_names
    if direct_drs:
        md_writer_ip_keys.add(proc_key)
        for d in direct_drs:
            for obj in md_writer_drs[d]:
                ip_reason[proc_key].add(f"DR:{d} -> {obj}")

# Also track which MD-child objects each writer IP touches (transitively).
ip_targets: dict[str, set[str]] = defaultdict(set)
for proc_key, fp in best_ip_file.items():
    for d in ip_dr_calls[fp] & md_writer_dr_names:
        ip_targets[proc_key].update(md_writer_drs[d])

# Transitive closure: any IP that calls a writer IP is itself a writer IP.
changed = True
while changed:
    changed = False
    for proc_key, fp in best_ip_file.items():
        called = ip_ip_calls[fp]
        intersect = called & md_writer_ip_keys
        # Track new MD-writer status
        was_writer = proc_key in md_writer_ip_keys
        if intersect:
            if not was_writer:
                md_writer_ip_keys.add(proc_key)
                for child_key in intersect:
                    ip_reason[proc_key].add(f"IP:{child_key}")
                changed = True
            # Always propagate target objects from child IPs
            for child_key in intersect:
                before = len(ip_targets[proc_key])
                ip_targets[proc_key].update(ip_targets.get(child_key, set()))
                if len(ip_targets[proc_key]) > before:
                    changed = True

print(f"[C] IPs that (transitively) write to MD child objects: {len(md_writer_ip_keys)}")

# ---------------------------------------------------------------------------
# Step D: Find OmniScripts (active) that reference any MD-writer IP key.
# Group by OmniScript base name (Type_Language) and keep the active version.
# ---------------------------------------------------------------------------
os_versions: dict[str, list[tuple[Path, bool, str, str]]] = defaultdict(list)
os_ip_refs: dict[Path, set[str]] = defaultdict(set)
os_dr_refs: dict[Path, set[str]] = defaultdict(set)

for fp in OS_DIR.glob("*.os-meta.xml"):
    txt = fp.read_text(encoding="utf-8", errors="ignore")
    name = file_root_name(txt)
    lang_m = LANGUAGE_RE.search(txt)
    if not name or not lang_m:
        continue
    language = lang_m.group(1)
    base_key = f"{name}_{language}"
    is_active = file_active(txt)
    os_versions[base_key].append((fp, is_active, name, language))
    os_ip_refs[fp].update(_refs(txt, IP_KEY_RE))
    os_dr_refs[fp].update(_refs(txt, BUNDLE_RE))

best_os_file: dict[str, tuple[Path, bool]] = {}
for base_key, versions in os_versions.items():
    active = [v for v in versions if v[1]]
    chosen = (
        active[0] if active
        else max(versions, key=lambda v: int(re.search(r"_(\d+)\.os", v[0].name).group(1) or 0))
    )
    best_os_file[base_key] = (chosen[0], chosen[1])

print(f"[D] Unique OmniScripts: {len(best_os_file)}")

# Match OmniScripts that either call an MD-writer IP, or *directly* call an
# MD-writer DataRaptor via a DRPostAction step (no IP indirection).
affected: list[tuple[str, Path, bool, set[str], set[str], set[str]]] = []
for base_key, (fp, active) in best_os_file.items():
    ip_hits = os_ip_refs[fp] & md_writer_ip_keys
    dr_hits = os_dr_refs[fp] & md_writer_dr_names
    if not (ip_hits or dr_hits):
        continue
    target_objs: set[str] = set()
    for k in ip_hits:
        target_objs.update(ip_targets.get(k, set()))
    for d in dr_hits:
        target_objs.update(md_writer_drs.get(d, set()))
    affected.append((base_key, fp, active, ip_hits, dr_hits, target_objs))

affected.sort(key=lambda x: (not x[2], x[0]))  # active first, then by name

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
lines: list[str] = []
lines.append("# OmniScripts at risk: master-detail create/update failures")
lines.append("")
lines.append("**Context:** A new release breaks Create / Update DML on objects that")
lines.append("are children of a master-detail relationship. The following OmniScripts")
lines.append("call (directly or transitively) an Integration Procedure that invokes a")
lines.append("DataRaptor Load writing to one of the MD-child objects below.")
lines.append("")
lines.append("## Master-detail child objects in scope")
lines.append("")
lines.append("| Child Object | Master-Detail Parent |")
lines.append("|---|---|")
for child, parent in MD_CHILD_OBJECTS.items():
    lines.append(f"| `{child}` | `{parent}` |")
lines.append("")
lines.append(f"**MD-writing DataRaptor Loads:** {len(md_writer_drs)}  ")
lines.append(f"**Integration Procedures that (transitively) write to MD-child objects:** {len(md_writer_ip_keys)}  ")
lines.append(f"**Active+latest OmniScripts impacted:** {len(affected)}")
lines.append("")

# Affected OmniScripts table
lines.append("## Affected OmniScripts")
lines.append("")
lines.append("Failure modes:")
lines.append("- **IP**: OmniScript calls an Integration Procedure that (transitively) writes to an MD-child object.")
lines.append("- **DR**: OmniScript has a `DataRaptor Post Action` step that writes directly to an MD-child object.")
lines.append("")
lines.append("| # | OmniScript | Active | File | MD child object(s) written | Called IP(s) | Direct DR Load(s) |")
lines.append("|---|---|---|---|---|---|---|")
for i, (key, fp, active, ip_hits, dr_hits, targets) in enumerate(affected, 1):
    rel = fp.relative_to(ROOT.parents[2])
    target_cell = ", ".join(sorted(f"`{t}`" for t in targets)) or "—"
    ip_cell = ", ".join(sorted(ip_hits)) if ip_hits else "—"
    dr_cell = ", ".join(sorted(dr_hits)) if dr_hits else "—"
    lines.append(
        f"| {i} | `{key}` | {'Yes' if active else 'No'} | `{rel}` | {target_cell} | {ip_cell} | {dr_cell} |"
    )
lines.append("")

# Grouped by target object
lines.append("## Affected OmniScripts grouped by MD-child target object")
lines.append("")
by_target: dict[str, list[str]] = defaultdict(list)
for key, fp, active, ip_hits, dr_hits, targets in affected:
    for t in targets:
        by_target[t].append(key)
for t in sorted(by_target):
    lines.append(f"### `{t}` ({len(by_target[t])} OmniScript(s))")
    lines.append("")
    for k in sorted(set(by_target[t])):
        lines.append(f"- `{k}`")
    lines.append("")

# Underlying writer DRs
lines.append("## DataRaptor Loads writing to MD-child objects")
lines.append("")
lines.append("| DataRaptor | Target object(s) |")
lines.append("|---|---|")
for dr in sorted(md_writer_drs):
    lines.append(f"| `{dr}` | {', '.join(sorted(md_writer_drs[dr]))} |")
lines.append("")

# Writer IPs
lines.append("## Integration Procedures that (transitively) write to MD-child objects")
lines.append("")
lines.append("| IP procedureKey | Reason |")
lines.append("|---|---|")
for k in sorted(md_writer_ip_keys):
    reasons = ", ".join(sorted(ip_reason.get(k, set()))) or "(transitive)"
    lines.append(f"| `{k}` | {reasons} |")
lines.append("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nReport written: {OUT}")
print(f"Affected OmniScripts: {len(affected)}")
