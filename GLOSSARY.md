# JapaAI.ng Domain Glossary

Real-time curated immigration and permanent residence intelligence built directly from official national government portals across 12 destination countries.

## Core Concepts

**Destination Hub**:
A country workspace organizing official portals, national requirements, active Live Snapshots, and structured immigration Pathways for one destination country.
_Avoid_: Country page, portal tab, nation card

**Pathway**:
An official national immigration, work, study, or remote-work route leading toward lawful residence or Permanent Residence (PR) with defined thresholds and sequential stages.
_Avoid_: Program track (except for RCIP Pilot vs Permanent 2027), visa scheme

**Toolkit**:
A deep, country-specific interactive rules workspace (such as the Canada RCIP Toolkit covering CLB/NCLC conversion, settlement funds calculation, and 14 participating communities).
_Avoid_: Deep engine, calculator suite

**Live Snapshot**:
A timestamped verbatim HTML excerpt and alert notice fetched directly from an official government portal, hashed for change detection, and cached in SQLite without fabricated prose.
_Avoid_: Scraped cache, AI summary

**Source Registry**:
The combined index of verified official ministry portal URLs and active Live Snapshots used by the UI Sources Index and Copilot search.
_Avoid_: Link bank, knowledge base

**Dossier**:
A print-ready, HTML-escaped report summarizing an applicant's selected Destination Hub, Pathway stages, checklist progress, and personal notes (or Canada RCIP 6-pillar readiness).
_Avoid_: PDF stub, report dump

**Applicant Profile**:
A user's factual background inputs (education, field, paid experience, language levels, budget, remote income, job offer, or RCIP criteria) used strictly for transparent scoring with zero fake score floors.
_Avoid_: Resume persona, score boost

**Readiness Verdict**:
An evidence-based status tier (`STRONG_MATCH`, `VIABLE_WITH_JOB_OFFER`, `PREPARE_GAPS`, or `INCOMPLETE` in global matching; honest `0–100` tiering in Canada RCIP) computed exclusively from stated facts.
_Avoid_: Approval guarantee, eligibility prediction

**Official Citation**:
A clickable government-domain URL attached to every Copilot answer excerpt and tagged `[LIVE]` when backed by a Live Snapshot.
_Avoid_: External link, blog reference

## RCIP Specialization

**Program Track**:
The transition split between Canada's **Rural Community Immigration Pilot** (community recommendations dated `<= 2026-12-31`) and the **Permanent RCIP Program** (`>= 2027-01-01`).
_Avoid_: Visa batch, pathway tier
