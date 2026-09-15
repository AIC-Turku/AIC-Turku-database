from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"expected block not found: {label}")
    return text.replace(old, new, 1)


template = Path("scripts/templates/plan_experiments.md.j2")
text = template.read_text(encoding="utf-8")

top = r'''    const basePromptTop = `You are an experienced microscopy facility scientist helping me plan an experiment using the attached ${facilityShortName} inventory.

Use the JSON as the only source for facility-specific facts. Use general microscopy knowledge to interpret the biology, infer imaging requirements, explain trade-offs and recommend evidence-weighted candidates.

Core principle: reason aggressively about the experiment; be conservative about undocumented facility facts.

Rules:
- Read planning_contract first.
- A component missing from a complete route hardware list is not on that route; other missing or null values are unknown.
- Treat llm_context.authoritative_route_contract as route truth. Never combine components from different routes.
- Objectives are instrument-level unless explicit route compatibility is recorded.
- Preserve branches, splitters and endpoints. Read selection_mode before inferring simultaneous detection.
- Use capability_route_reconciliation and route_family_coverage to relate capabilities such as TIRF, STED or SIM to recorded route families.
- The inventory records no booking, access or training availability. Operational/QC status is not booking availability.
- You may infer experimental fit from recorded features and general microscopy principles, but do not invent facility-specific performance, configuration or compatibility. If speed, depth, phototoxicity, sample compatibility or fluorophore compatibility is not established, treat it as unknown.
- Surface contradictory records rather than silently resolving them.
- Distinguish recorded fact, deduction, expert inference and unknown when it matters. A recommendation does not require proof that an instrument is objectively best.

Procedure:
1. Translate the request into the imaging constraints that matter.
2. Use microscopy principles to identify plausible strategies and trade-offs.
3. Map them onto recorded routes and verify relevant route membership, detectors/endpoints and branch architecture.
4. Rank candidates by fit. When justified, say which system you would investigate first and why.
5. Mention only one or two unknowns that could change the choice and what to confirm with ${facilityShortName} staff.
6. Ask at most one clarifying question if it could materially change the strategy or shortlist.

My request:
`;'''

bottom = r'''    const basePromptBottom = `

Return a concise, decision-oriented answer: recommendation or short ordered shortlist; why it fits; a useful alternative when relevant; and one or two important unknowns.

Do not dump every matching microscope or default to "ask staff" because some performance data are missing. Do not force a definitive best microscope when evidence cannot support one. Do not invent facility specifications.`;'''

text, n1 = re.subn(r"    const basePromptTop = `.*?`;", lambda _: top, text, count=1, flags=re.S)
text, n2 = re.subn(r"    const basePromptBottom = `.*?`;", lambda _: bottom, text, count=1, flags=re.S)
if (n1, n2) != (1, 1):
    raise RuntimeError(f"prompt blocks not found: {(n1, n2)}")
template.write_text(text, encoding="utf-8")


docs = Path("docs/planning_grounding.md")
d = docs.read_text(encoding="utf-8")
old_docs = '''The planning prompt is intentionally conservative. It asks the LLM to identify
recorded candidate instruments/routes and the unknowns that still matter. It does
**not** require a best microscope, a backup, a performance ranking or an
acquisition plan when the inventory cannot support those conclusions.

Users can describe their need in ordinary language. The prompt should not turn a
vague requirement such as "fast", "deep", "low phototoxicity" or "thick cleared
sample" into a facility-specific modality recommendation unless the inventory and
the user's explicit request justify that step.
'''
new_docs = '''The planning prompt now separates two kinds of inference deliberately. It asks the
LLM to reason actively about the biology and microscopy problem — infer relevant
imaging constraints, explain general modality trade-offs, and rank recorded
candidates by experimental fit — while remaining conservative about undocumented
facility-specific facts.

This means the assistant may recommend a microscope because its recorded route
features align with the inferred needs of an experiment. It may also explain, for
example, why optical sectioning, simultaneous detection or surface-selective
imaging could matter. What it must not do is turn general microscopy knowledge
into an unrecorded facility claim such as a specific system being faster, more
sensitive, deeper or less phototoxic than another.

A recommendation is therefore an evidence-weighted judgement, not a claim that an
instrument is objectively best. Missing performance data should become focused
uncertainties that could overturn the recommendation, rather than forcing every
answer to collapse into "ask staff".
'''
docs.write_text(replace_once(d, old_docs, new_docs, "planning docs"), encoding="utf-8")


tests = Path("tests/test_planning_grounding.py")
t = tests.read_text(encoding="utf-8")
old_test = '''    def test_prompt_does_not_force_best_or_backup(self) -> None:
        prompt = self._prompt().lower()
        self.assertNotIn("the best-fit microscope and one backup", prompt)
        self.assertNotIn("choose one best route on the top instrument and one backup route/instrument", prompt)
        self.assertNotIn("legacy instruction", prompt)
        self.assertIn("do not force a best microscope or backup", prompt)
'''
new_test = '''    def test_prompt_allows_evidence_weighted_recommendations_without_forcing_best(self) -> None:
        prompt = self._prompt().lower()
        self.assertIn("recommend evidence-weighted candidates", prompt)
        self.assertIn("rank candidates by fit", prompt)
        self.assertIn("does not require proof that an instrument is objectively best", prompt)
        self.assertIn("do not force a definitive best microscope", prompt)
        self.assertNotIn("choose one best route on the top instrument and one backup route/instrument", prompt)
'''
t = replace_once(t, old_test, new_test, "best-fit prompt test")
old_perf = '''    def test_prompt_warns_against_unrecorded_performance_inference(self) -> None:
        prompt = self._prompt().lower()
        for term in ("speed", "depth", "phototoxicity", "sample compatibility"):
            with self.subTest(term=term):
                self.assertIn(term, prompt)
'''
new_perf = '''    def test_prompt_separates_scientific_inference_from_facility_claims(self) -> None:
        prompt = self._prompt().lower()
        self.assertIn("infer imaging requirements", prompt)
        self.assertIn("general microscopy knowledge", prompt)
        self.assertIn("infer experimental fit", prompt)
        self.assertIn("do not invent facility-specific performance", prompt)
        for term in ("speed", "depth", "phototoxicity", "sample compatibility"):
            with self.subTest(term=term):
                self.assertIn(term, prompt)
'''
tests.write_text(replace_once(t, old_perf, new_perf, "inference boundary test"), encoding="utf-8")
