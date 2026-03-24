"""
Mock LLM responses for each agent.

Used when USE_MOCK_LLM=true so the pipeline can run end-to-end
without a real Anthropic API key. All content is realistic but fictional,
scoped to the AI Drug Discovery sector.

Structure: MOCK_RESPONSES[AgentClassName] -> JSON string that each agent's
run() method can parse, identical in schema to what the real LLM returns.
"""

# ---------------------------------------------------------------------------
# SourcingAgent  →  JSON array of StartupScreeningResult objects
#                   Each item: startup (StartupProfile) + classification +
#                   evidence + dimension_scores (5 axes) + total_score +
#                   score_rationale + priority_rank
# ---------------------------------------------------------------------------
SOURCING = """
[
  {
    "startup": {
      "name": "Isomorphic Labs",
      "founded_year": 2021,
      "hq": "London, UK",
      "stage": "Late Stage",
      "total_funding_usd_m": 600.0,
      "technology_approach": "Spin-out from DeepMind leveraging AlphaFold2 and proprietary ML models for end-to-end small-molecule drug design and target identification.",
      "technology_category": "generative_chemistry",
      "key_investors": ["Alphabet", "Thrive Capital"],
      "summary": "Isomorphic Labs applies AI to predict protein-ligand binding and accelerate hit-to-lead optimisation. It has partnerships with Eli Lilly and Novartis worth up to $2.9B. The company focuses on oncology and metabolic diseases.",
      "status": "active",
      "source_urls": []
    },
    "classification": "generative_chemistry",
    "evidence": [
      "Isomorphic Labs signed drug discovery partnerships with Eli Lilly and Novartis worth up to $2.9B in milestones — the largest pharma-AI deals of 2023.",
      "The company is an Alphabet spin-out and uses AlphaFold2 as the structural foundation for its small-molecule design pipeline.",
      "Backed by $600M with no disclosed outside VC — wholly owned by Alphabet, de-risking capital availability."
    ],
    "dimension_scores": {
      "tech_frontier":               {"score": 5.0, "rationale": "AlphaFold-native architecture is the global frontier in structure-based drug design; no peer has comparable structural biology IP."},
      "commercialization_potential": {"score": 4.5, "rationale": "$2.9B in pharma partnership milestones provides near-term de-risked revenue with royalty upside from owned pipeline."},
      "data_flywheel":               {"score": 4.5, "rationale": "Wet-lab feedback from Lilly/Novartis programmes continuously retrains in-house models, creating a compounding data moat."},
      "team_credibility":            {"score": 5.0, "rationale": "DeepMind lineage (ex-AlphaFold team) combined with Alphabet financial backing is the strongest team signal in the sector."},
      "information_completeness":    {"score": 4.0, "rationale": "Partnership terms publicly disclosed; financials opaque due to private structure, but overall information density is high."}
    },
    "total_score": 23.0,
    "score_rationale": "Isomorphic Labs combines the most defensible AI architecture in drug design with the deepest pockets and the largest pharma partnerships in the sector. The primary risk is that the Alphabet umbrella limits an independent IPO narrative, and clinical outcomes remain unproven.",
    "priority_rank": 1
  },
  {
    "startup": {
      "name": "Xaira Therapeutics",
      "founded_year": 2024,
      "hq": "San Francisco, USA",
      "stage": "Series A",
      "total_funding_usd_m": 1000.0,
      "technology_approach": "Foundation models for both molecule generation and biological target understanding, with a fully integrated lab-to-clinic platform built from scratch.",
      "technology_category": "generative_chemistry",
      "key_investors": ["ARCH Venture Partners", "Foresite Capital", "GV"],
      "summary": "Xaira launched in 2024 with $1B in Series A funding — one of the largest biotech Series A rounds ever. The company is building proprietary AI models trained on massive wet-lab datasets to dramatically compress drug development timelines.",
      "status": "active",
      "source_urls": []
    },
    "classification": "generative_chemistry",
    "evidence": [
      "Xaira Therapeutics raised $1B Series A in April 2024 from ARCH Venture Partners, Foresite Capital, and GV — the largest biotech Series A on record.",
      "Founded by former Genentech scientists and computational biology leaders from the Broad Institute.",
      "Building integrated wet-lab + AI platform from day one, generating proprietary training data across multiple target classes."
    ],
    "dimension_scores": {
      "tech_frontier":               {"score": 4.5, "rationale": "Building foundation models trained on self-generated wet-lab data — a vertically integrated approach with no direct public comparator at launch scale."},
      "commercialization_potential": {"score": 3.5, "rationale": "Founded in 2024 with no disclosed partnerships yet; $1B runway reduces near-term revenue pressure but commercial track record is zero."},
      "data_flywheel":               {"score": 5.0, "rationale": "Entire strategy is centred on generating proprietary training data through in-house biology labs — the purest data-flywheel play in the sector."},
      "team_credibility":            {"score": 4.5, "rationale": "Ex-Genentech and Broad Institute founders, with top-tier VC syndicate signals elite network and diligence depth."},
      "information_completeness":    {"score": 3.0, "rationale": "Very recently founded; pipeline, targets, and technology details not yet publicly disclosed, limiting analytical depth."}
    },
    "total_score": 20.5,
    "score_rationale": "Xaira is the highest-conviction capital deployment in the sector in 2024 based on investor quality and data-flywheel architecture. The key risk is that it is pre-revenue and pre-pipeline — investors are betting entirely on team and thesis.",
    "priority_rank": 2
  },
  {
    "startup": {
      "name": "Insilico Medicine",
      "founded_year": 2014,
      "hq": "Hong Kong / New York, USA",
      "stage": "Late Stage",
      "total_funding_usd_m": 400.0,
      "technology_approach": "End-to-end generative AI platform (Chemistry42, Biology42, Medicine42) covering target discovery, molecule generation, and clinical trial design.",
      "technology_category": "generative_chemistry",
      "key_investors": ["Sequoia China", "B Capital", "Warburg Pincus"],
      "summary": "Insilico advanced the first fully AI-designed drug (INS018_055 for IPF) into Phase II trials, validating its generative chemistry platform. The company has a pipeline spanning fibrosis, oncology, and immunology.",
      "status": "active",
      "source_urls": []
    },
    "classification": "generative_chemistry",
    "evidence": [
      "INS018_055, designed entirely by Insilico's AI platform, entered Phase II trials for IPF in 2023 — the first fully AI-generated small molecule at this stage.",
      "Raised $95M Series D in 2023; total funding ~$400M across Sequoia China, B Capital, and Warburg Pincus.",
      "The Chemistry42 platform has been licensed to over 30 pharma and biotech partners as a SaaS offering."
    ],
    "dimension_scores": {
      "tech_frontier":               {"score": 4.5, "rationale": "First to advance a fully AI-designed molecule to Phase II, which is a concrete clinical validation no competitor has matched."},
      "commercialization_potential": {"score": 4.5, "rationale": "Dual revenue model (SaaS licensing + proprietary pipeline) is the most mature commercialisation structure among private AI drug design companies."},
      "data_flywheel":               {"score": 4.0, "rationale": "SaaS partnerships provide continuous molecular design feedback, though data ownership terms with partners may limit reuse."},
      "team_credibility":            {"score": 4.0, "rationale": "Alex Zhavoronkov (CEO) is a recognised pioneer in AI drug discovery; team has deep generative modelling expertise spanning biology and chemistry."},
      "information_completeness":    {"score": 4.5, "rationale": "Phase II trial registration, SaaS partnership announcements, and investor disclosures provide unusually high information density for a private company."}
    },
    "total_score": 21.5,
    "score_rationale": "Insilico is the most clinically de-risked private AI drug design company with a Phase II readout imminent for IPF. The primary risk is binary: a failure in INS018_055 would challenge the platform's clinical translation narrative and potentially delay IPO plans.",
    "priority_rank": 3
  },
  {
    "startup": {
      "name": "Generate Biomedicines",
      "founded_year": 2018,
      "hq": "Cambridge, USA",
      "stage": "Series C",
      "total_funding_usd_m": 370.0,
      "technology_approach": "Protein language models and generative AI for designing entirely novel therapeutic proteins, including antibodies, enzymes, and peptide therapeutics.",
      "technology_category": "protein_design",
      "key_investors": ["Flagship Pioneering", "NVIDIA", "Foresite Labs"],
      "summary": "Generate Biomedicines uses its Chroma generative model to design proteins with specified therapeutic properties from scratch. Lead programs target oncology and immunology; the company completed IND-enabling studies for its first candidate in 2024.",
      "status": "active",
      "source_urls": []
    },
    "classification": "protein_design",
    "evidence": [
      "Generate's Chroma model can design novel protein sequences conditioned on structural and functional constraints — published in Nature 2023.",
      "Completed IND-enabling studies for first de-novo designed therapeutic protein candidate in oncology (undisclosed target) in 2024.",
      "Backed by Flagship Pioneering (Moderna's creator) and NVIDIA, providing both strategic and compute infrastructure advantages."
    ],
    "dimension_scores": {
      "tech_frontier":               {"score": 4.5, "rationale": "Chroma's ability to generate fully novel proteins beyond natural sequence space is a genuine frontier capability in therapeutic protein design."},
      "commercialization_potential": {"score": 3.5, "rationale": "IND-stage asset exists but no partnership revenue disclosed; Flagship backing suggests capital availability but slow commercial ramp."},
      "data_flywheel":               {"score": 4.0, "rationale": "In-house wet-lab protein expression and characterisation data continuously retrains generative models — a genuine closed-loop biology flywheel."},
      "team_credibility":            {"score": 4.5, "rationale": "Flagship Pioneering's track record (Moderna, Relay) and NVIDIA strategic investment are among the strongest investor signals in the sector."},
      "information_completeness":    {"score": 3.5, "rationale": "Nature publication provides technology transparency; pipeline targets undisclosed, limiting competitive positioning analysis."}
    },
    "total_score": 20.0,
    "score_rationale": "Generate Biomedicines occupies a differentiated niche in de-novo protein design with credible academic and clinical validation. The main risk is the long lead time to revenue — Flagship Pioneering companies typically take 5-7 years from founding to meaningful clinical stage.",
    "priority_rank": 4
  },
  {
    "startup": {
      "name": "Iktos",
      "founded_year": 2016,
      "hq": "Paris, France",
      "stage": "Series B",
      "total_funding_usd_m": 45.0,
      "technology_approach": "Generative deep learning (Makya platform) for de-novo drug design optimising across multiple parameters including synthesis feasibility and ADMET properties.",
      "technology_category": "generative_chemistry",
      "key_investors": ["Elaia Partners", "Bpifrance", "Servier"],
      "summary": "Iktos specialises in AI-driven de-novo small molecule design with a strong emphasis on synthetic accessibility — molecules that can actually be made in a lab. The company has partnerships with multiple European pharma companies and recently expanded to Japan.",
      "status": "active",
      "source_urls": []
    },
    "classification": "generative_chemistry",
    "evidence": [
      "Iktos partnered with Servier (top-10 European pharma) and multiple undisclosed Japanese pharma companies for AI-assisted lead optimisation.",
      "Makya platform published in peer-reviewed journals demonstrating superiority in synthetic accessibility scores vs. competing generative methods.",
      "Raised €40M Series B in 2023 led by Elaia Partners and supported by Bpifrance deep tech programme."
    ],
    "dimension_scores": {
      "tech_frontier":               {"score": 3.5, "rationale": "Synthesis-feasibility-aware generative chemistry is a meaningful niche differentiator, though the approach is less novel than protein design or phenomics platforms."},
      "commercialization_potential": {"score": 4.0, "rationale": "Active pharma partnerships in Europe and Asia indicate real demand; SaaS-style licensing model provides predictable revenue."},
      "data_flywheel":               {"score": 3.5, "rationale": "Partnership data provides feedback but ownership terms likely limit full reuse; no disclosed in-house wet-lab capability."},
      "team_credibility":            {"score": 3.5, "rationale": "Strong computational chemistry pedigree; Servier strategic investor adds pharma validation, though founding team lacks US/UK Tier-1 VC pedigree."},
      "information_completeness":    {"score": 4.0, "rationale": "Multiple published papers, disclosed partnership names, and funding details provide solid information basis for analysis."}
    },
    "total_score": 18.5,
    "score_rationale": "Iktos is a capital-efficient, commercially validated generative chemistry platform with a clear B2B model and real pharma traction in Europe. The primary risk is scale: limited capital and a European focus may make it difficult to compete for US mega-partnerships against better-funded US/UK peers.",
    "priority_rank": 5
  },
  {
    "startup": {
      "name": "BioMap",
      "founded_year": 2021,
      "hq": "Beijing, China / Palo Alto, USA",
      "stage": "Series B",
      "total_funding_usd_m": 200.0,
      "technology_approach": "Large biological language model (xTrimoPGLM, 100B parameters) trained on protein, genomic, and clinical data for target discovery and antibody design.",
      "technology_category": "multiomics",
      "key_investors": ["Tencent", "Hillhouse Capital", "CPE Yuanfeng"],
      "summary": "BioMap built one of the largest biological foundation models in the world and applies it to antibody engineering, protein function prediction, and multi-omics integration. The company focuses on autoimmune and oncology indications.",
      "status": "active",
      "source_urls": []
    },
    "classification": "multiomics",
    "evidence": [
      "xTrimoPGLM (100B parameter biological language model) published in Nature Machine Intelligence 2024, demonstrating SOTA on protein structure and function benchmarks.",
      "Tencent and Hillhouse Capital led $200M Series B, providing both compute infrastructure (Tencent Cloud) and healthcare ecosystem access.",
      "Dual US/China presence provides access to large Chinese patient cohorts for training data while maintaining US market access."
    ],
    "dimension_scores": {
      "tech_frontier":               {"score": 4.5, "rationale": "100B parameter bio-language model is among the largest in the world; multi-modal training across protein, genomic, and clinical data is genuinely frontier."},
      "commercialization_potential": {"score": 3.5, "rationale": "Strong Chinese market access through Tencent ecosystem; US commercialisation path less clear given regulatory and geopolitical environment."},
      "data_flywheel":               {"score": 4.5, "rationale": "Access to large Chinese patient cohorts through hospital network partnerships creates a data advantage that Western competitors cannot easily replicate."},
      "team_credibility":            {"score": 4.0, "rationale": "Strong computational biology team; Tencent and Hillhouse are Tier-1 Asian investors with deep healthcare networks."},
      "information_completeness":    {"score": 3.5, "rationale": "Nature publication provides model transparency; business model and US partnership pipeline less clearly disclosed."}
    },
    "total_score": 20.0,
    "score_rationale": "BioMap is technically among the most advanced biological foundation model companies globally, with a unique data advantage from Chinese clinical datasets. The primary risk for non-Asian investors is geopolitical: US-China technology tensions may limit cross-border partnerships and complicate an eventual IPO.",
    "priority_rank": 6
  },
  {
    "startup": {
      "name": "Variational AI",
      "founded_year": 2019,
      "hq": "Vancouver, Canada",
      "stage": "Series A",
      "total_funding_usd_m": 35.0,
      "technology_approach": "Proprietary variational autoencoder and diffusion models for multi-parameter molecular optimisation, specialising in CNS and rare disease applications.",
      "technology_category": "generative_chemistry",
      "key_investors": ["Amplitude Ventures", "MaRS Investment Accelerator Fund"],
      "summary": "Variational AI's Entorian platform jointly optimises potency, selectivity, ADMET, and synthetic accessibility in a single model pass. The company has multiple pharma partnerships and a growing CNS pipeline.",
      "status": "active",
      "source_urls": []
    },
    "classification": "generative_chemistry",
    "evidence": [
      "Variational AI announced pharma collaboration with an undisclosed Top-20 pharma company for CNS lead optimisation in Q3 2023.",
      "Entorian platform demonstrated multi-parameter optimisation across 6 ADMET properties simultaneously in a peer-reviewed publication.",
      "Raised CAD $35M Series A from Amplitude Ventures and MaRS IAF — primary Canadian AI drug discovery investment of 2022."
    ],
    "dimension_scores": {
      "tech_frontier":               {"score": 3.5, "rationale": "Multi-parameter optimisation in a single generative pass is technically sound but similar approaches exist at better-funded US competitors."},
      "commercialization_potential": {"score": 3.5, "rationale": "Active pharma partnership and CNS focus (high unmet need, pricing power) indicate commercial validity, but scale is limited."},
      "data_flywheel":               {"score": 3.0, "rationale": "Partnership data provides some feedback loop; no evidence of proprietary wet-lab data generation or systematic closed-loop biology."},
      "team_credibility":            {"score": 3.0, "rationale": "Strong computational chemistry credentials; limited top-tier VC backing and no disclosed ex-Big-Pharma or ex-Big-Tech founding team members."},
      "information_completeness":    {"score": 3.5, "rationale": "Published methods and partnership announcement provide reasonable information basis; financial details limited."}
    },
    "total_score": 16.5,
    "score_rationale": "Variational AI is a technically credible but capital-constrained generative chemistry company with early pharma validation in a high-value CNS niche. The main risk is scale: with $35M raised, it will struggle to compete for large pharma partnerships against Isomorphic or Insilico without a significant Series B.",
    "priority_rank": 7
  },
  {
    "startup": {
      "name": "DP Technology",
      "founded_year": 2018,
      "hq": "Beijing, China",
      "stage": "Series C",
      "total_funding_usd_m": 250.0,
      "technology_approach": "Deep Potential molecular dynamics models enabling accurate, scalable quantum-mechanics-level simulations of molecular systems for drug and material discovery.",
      "technology_category": "generative_chemistry",
      "key_investors": ["Sequoia China", "Source Code Capital", "GGV Capital"],
      "summary": "DP Technology applies deep potential energy models to run molecular dynamics simulations at quantum accuracy but classical computing speed. Its Uni-Mol foundation model enables atom-level property prediction across chemical and biological spaces.",
      "status": "active",
      "source_urls": []
    },
    "classification": "generative_chemistry",
    "evidence": [
      "Uni-Mol, DP Technology's molecular foundation model, published in ICLR 2023 and adopted by over 50 pharma and chemical companies globally.",
      "Raised $250M Series C in 2023 from Sequoia China and Source Code Capital.",
      "Deep Potential MD models used by Shell, BASF, and Pfizer for materials and drug discovery applications — broad adoption signal."
    ],
    "dimension_scores": {
      "tech_frontier":               {"score": 4.0, "rationale": "Quantum-accuracy molecular simulation at classical scale is a genuinely hard technical problem; Uni-Mol's broad adoption validates the approach."},
      "commercialization_potential": {"score": 3.5, "rationale": "Broad industrial adoption across pharma, materials, and energy provides diversified revenue; drug discovery is one of several verticals, limiting focus."},
      "data_flywheel":               {"score": 3.5, "rationale": "Wide academic and industrial adoption generates model improvement feedback, though commercial data ownership structure is unclear."},
      "team_credibility":            {"score": 4.0, "rationale": "Founded by computational physics academics from PKU and Princeton; Sequoia China backing is the strongest VC signal in Chinese deep tech."},
      "information_completeness":    {"score": 4.0, "rationale": "ICLR publication, disclosed funding, and named enterprise customers provide high information quality for a Chinese deep tech company."}
    },
    "total_score": 19.0,
    "score_rationale": "DP Technology is a technically rigorous platform company with proven industrial adoption, but its value proposition spans materials, energy, and pharma — limiting the concentration of investment thesis for a pure AI drug discovery investor. Geopolitical risk (China-based) is an additional consideration.",
    "priority_rank": 8
  }
]
"""

# ---------------------------------------------------------------------------
# DiligenceAgent  →  full investment memo JSON (no "startup" field —
#                    injected by the agent after parsing)
# Note: same template is returned for every company in the diligence loop.
# ---------------------------------------------------------------------------
DILIGENCE = """
{
  "classification": "generative_chemistry",

  "team": {
    "founder_backgrounds": "Co-founded by ex-DeepMind ML researchers (AlphaFold-adjacent projects) and seasoned drug-discovery scientists from GSK and AstraZeneca. The CEO has one prior biotech exit; the CSO has 15+ peer-reviewed publications in computational chemistry.",
    "pharma_ai_academia_signal": "strong",
    "key_strength": "Rare combination of frontier AI capability and hands-on wet-lab biology in the founding team — most AI drug discovery companies are strong in one but not both.",
    "key_gap": "Commercial and business development capacity is still being built out; the company is transitioning from platform provider to pipeline owner and lacks a seasoned pharma BD leader with large-deal experience."
  },

  "technology": {
    "pathway": "Structure-based generative chemistry",
    "foundation_model_relationship": "Platform is built on top of AlphaFold2-derived structure prediction, extended with proprietary generative chemistry models for hit-to-lead optimisation. The company trains additional layers on its own wet-lab-generated binding and selectivity data, which it claims outperforms open AlphaFold on drug-relevant conformations.",
    "differentiation": "Unlike pure in-silico generative chemistry platforms, this company operates a closed-loop wet-lab synthesis and assay cycle that generates proprietary training data unavailable to competitors — a compounding data moat that is particularly hard to replicate because it requires both wet-lab infrastructure and ML expertise simultaneously."
  },

  "moat": {
    "data_flywheel_description": "In-house biology labs run continuous synthesis-assay-retrain cycles: compounds designed by the generative model are synthesised, tested in cellular and biochemical assays, and the binding/selectivity results are fed back to retrain the models weekly. This flywheel runs 24/7 and compounds over time — competitors starting today would need 3-5 years of similar cycles to reach parity.",
    "proprietary_data_scale": "A large proprietary library of annotated compound-activity data points spanning multiple target classes, accumulated over years of in-house experiments and pharma partnership data (per company disclosures; precise scale not independently verified).",
    "compute_platform_advantage": "Strategic relationship with a major hyperscaler provides preferential access to GPU/TPU clusters at reserved pricing; the company claims significantly larger model training runs than publicly disclosed peers (per company presentations; not independently verified)."
  },

  "pipeline": {
    "is_clinical_stage": false,
    "clinical_stage_label": null,
    "key_assets": [
      "Programme A — undisclosed oncology target, IND-enabling studies complete, Phase I expected H2 2025",
      "Programme B — undisclosed CNS target, lead optimisation stage, co-development with Top-10 pharma partner",
      "Programme C — rare disease indication, target identification phase, fully internally funded"
    ],
    "latest_milestone": "Completed IND-enabling studies for Programme A (Q4 2024); first proprietary asset expected to enter Phase I in H2 2025, which would be a significant clinical validation milestone for the platform."
  },

  "business_model": {
    "primary_model": "hybrid",
    "revenue_sources": [
      "Pharma partnership research fees and milestone payments",
      "Co-development royalties on partnered programmes (back-end weighted)",
      "Platform access licensing to smaller biotechs (emerging, <10% of revenue today)"
    ],
    "partnership_details": "Two active pharma partnerships: one undisclosed Top-10 global pharma (deal signed 2022, estimated $300M+ milestone potential), one mid-cap European pharma (2023, $120M milestone potential). A third platform licensing agreement with an Asian biotech signed Q4 2024. Total disclosed milestone potential: $420M+; total potential including undisclosed back-end royalties estimated at $600-800M."
  },

  "competitive_landscape": "The AI drug discovery sector is bifurcating between platform-and-pipeline hybrids (where this company sits) and pure SaaS/tool providers. Direct competitors in the hybrid model include Isomorphic Labs (Alphabet-backed, AlphaFold heritage, $600M raised — outgunned on capital and brand), Insilico Medicine (generative chemistry, most clinical-stage private peer with Phase II data expected 2025), and Xaira Therapeutics ($1B Series A, 2024 — most recent entrant with deepest pockets). Public comps include Recursion Pharmaceuticals (phenomics approach, listed NASDAQ) and Schrödinger (physics-based ML, SaaS-heavy). The company's specific differentiation — closed-loop wet-lab + generative chemistry — is most directly comparable to Exscientia's former approach (now merged into Recursion), suggesting the market has validated this model. The primary competitive risk is that Isomorphic Labs or Xaira use their capital advantages to outbuild the data flywheel.",

  "bull_case": "If Programme A (Phase I, H2 2025) shows clean safety and early pharmacokinetic signals consistent with the platform's AI-derived predictions, it would provide the first independent clinical validation of the closed-loop generative chemistry approach. A positive signal in 2026 could trigger a 3-5x re-rating and open a 2026-2027 IPO window at $2-4B valuation — comparable to Insilico Medicine's pre-IPO range. The pharma partnership milestones ($420M+ contracted) provide a non-dilutive funding floor that reduces near-term binary risk significantly.",

  "bear_case": "The primary bear case is clinical translation failure: in-silico performance on standard benchmarks (CASF-2016, TDC) has repeatedly failed to predict human outcomes. The first proprietary Phase I candidate may show unexpected toxicity or poor PK, which would impair the platform narrative even if the failure is indication-specific rather than platform-wide. With Isomorphic Labs (Alphabet) and Xaira ($1B) competing for the same pharma partnerships, a clinical setback could result in partner attrition that cascades into a funding shortfall before the next catalyst.",

  "key_risks": [
    "Clinical translation risk: Programme A (Phase I, 2025) is the first proprietary clinical test of the AI platform — a safety or PK failure would impair the platform narrative for 12-18 months.",
    "Partnership concentration: two pharma partners account for ~70% of near-term revenue; renegotiation or termination of either deal (e.g. on target deprioritisation) would be material to the business.",
    "Competitive capital disadvantage: Isomorphic Labs (Alphabet-backed, unlimited capital) and Xaira ($1B warchest) can outspend this company on wet-lab infrastructure, compute, and talent to replicate the data flywheel faster.",
    "Regulatory uncertainty: FDA has not issued final guidance on AI-designed molecules; novel modalities in oncology may face additional safety data requirements that extend Phase I timelines.",
    "Talent concentration risk: the data flywheel is dependent on a small team of ML-biology hybrid researchers — losing 2-3 key scientists to big tech or better-capitalised startups could disrupt the retraining cycle."
  ],

  "overall_conviction": "medium",
  "conviction_rationale": "Strong technical and investor validation, but conviction is capped at medium because no molecule has yet entered human trials — we are pricing platform promises rather than demonstrated clinical outcomes. Conviction would upgrade to high on a clean Phase I readout for Programme A.",

  "evidence": [
    {
      "claim": "The company has raised $400-600M from Tier-1 investors including a strategic from the hyperscaler/big tech ecosystem.",
      "source": "Sourcing evidence: funding round announcement referenced in search results"
    },
    {
      "claim": "The company has executed pharma partnerships with total disclosed milestone potential exceeding $420M.",
      "source": "Sourcing evidence: partnership announcements referenced in company profile source_urls"
    },
    {
      "claim": "The company operates in-house wet-lab synthesis and assay capabilities integrated with its AI platform.",
      "source": "Company profile: technology_approach field describes closed-loop wet-lab + AI design cycle"
    },
    {
      "claim": "IND-enabling studies for Programme A were completed in Q4 2024, with Phase I entry targeted H2 2025.",
      "source": "Sourcing evidence: pipeline milestone announcement in search results"
    }
  ],

  "inferences": [
    {
      "claim": "The closed-loop wet-lab data flywheel creates a compounding moat that will widen relative to pure in-silico competitors over the next 2-3 years.",
      "basis": "Inferred from the platform architecture: continuous assay feedback implies exponentially growing proprietary data, while pure-software competitors are limited to public datasets or slower partnership data flows."
    },
    {
      "claim": "The company is likely targeting a 2026-2027 IPO window, contingent on Phase I data for Programme A.",
      "basis": "Inferred from funding stage (Late Stage), clinical timeline (Phase I 2025, data 2026), and the typical 12-18 month IPO preparation period for AI biotech companies."
    },
    {
      "claim": "The pharma partnership concentration (~70% of revenue from two partners) creates a contingent liability that is not fully reflected in reported milestone potential.",
      "basis": "Inferred from the business model structure: milestone-heavy deals with one or two partners imply that partner deprioritisation risk is the single most material financial risk beyond clinical outcomes."
    }
  ],

  "technology_moat": "The company has built a differentiated closed-loop AI platform combining proprietary wet-lab data generation with continuous model retraining. Its generative chemistry models are trained on a substantial proprietary library of annotated compound-activity data accumulated over years of in-house experiments (per company disclosures), creating a compounding data moat. A substantial patent portfolio covers key architectural innovations and specific chemical scaffolds; the wet-lab infrastructure itself is a barrier that pure-software competitors cannot quickly replicate.",
  "team_assessment": "The founding team combines ex-DeepMind ML expertise with drug-discovery veterans from GSK and AstraZeneca. The CEO has a prior biotech exit. A Chief Medical Officer and VP Chemistry were hired from large-cap pharma in 2023-2024. Key gap: BD/commercial leadership for large pharma deal execution is still being built.",
  "ip_and_partnerships": "A substantial patent portfolio covering model architectures, training methods, and specific chemical scaffolds (per company disclosures; specific count not independently verified). Two active pharma partnerships with $420M+ total disclosed milestone potential. An exclusive data-sharing agreement with a major academic medical centre provides ongoing real-world biological feedback.",
  "investment_thesis": "This company represents a compelling early-stage bet on AI-native drug discovery with a defensible data flywheel. The pharma partnership portfolio provides a non-dilutive funding floor while the company builds its owned pipeline. A Phase I readout in 2025-2026 would be the defining catalyst for a re-rating and potential 2026-2027 IPO at $2-4B."
}
"""

# ---------------------------------------------------------------------------
# PublicMarketAgent  →  {"companies": [...], "catalysts": [...]}
# 5 companies: RXRX, SDGR, RLAY, ABCL, ABSI
# 8 catalysts using standardised category + timing + evidence schema
# ---------------------------------------------------------------------------
PUBLIC_MARKET = """
{
  "companies": [
    {
      "name": "Recursion Pharmaceuticals",
      "ticker": "RXRX",
      "exchange": "NASDAQ",
      "market_cap_usd_b": 2.8,
      "business_type": "hybrid",
      "value_chain_position": "Target identification via phenomics imaging + lead optimisation via generative chemistry (Exscientia merger); own clinical pipeline (REC-994, REC-3964)",
      "technology_approach": "Recursion OS combines high-content phenomics imaging with Phenom-Beta biological foundation model for target ID, integrated with Exscientia's generative chemistry and automated synthesis capabilities post-January 2025 merger.",
      "valuation_metrics": {
        "ev_revenue_ratio": 7.8,
        "price_to_sales": 7.2,
        "pe_ratio": null,
        "cash_usd_b": 0.52,
        "week_52_high": 11.20,
        "week_52_low": 3.42,
        "ytd_change_pct": -0.42
      },
      "valuation_commentary": "Trades at 7.8x EV/Revenue — a premium to ABCL (4.2x) but below SDGR (14.8x). The post-merger platform is the most integrated in the sector but cash runway (~18 months at current burn) is the primary discount factor vs. peers with stronger balance sheets.",
      "recent_developments": "Completed merger with Exscientia (Jan 2025), creating the most integrated public AI drug-discovery platform. NVIDIA expanded the DGX Cloud agreement for Phenom-Beta model training. REC-994 Phase II trial in cerebral cavernous malformation (CCM) confirmed on schedule for H2 2025 readout.",
      "bull_cases": [
        "REC-994 Phase II CCM readout (H2 2025): a statistically significant reduction in lesion burden would be the first clinical proof-of-concept for phenomics-derived target selection, triggering multiple expansion from 7.8x to 12-15x EV/Rev.",
        "NVIDIA relationship provides preferential Blackwell GPU access for Phenom-Beta v2 training — a compute moat competitors cannot easily replicate at equivalent cost.",
        "Post-merger chemistry capabilities (Exscientia's automated synthesis) accelerate hit-to-IND timelines across all Roche collaboration programmes, increasing probability of near-term partnership expansion."
      ],
      "bear_cases": [
        "Cash runway of ~18 months ($520M cash vs. ~$300M annual burn) requires a dilutive equity offering in 2026 if REC-994 fails or partnership revenue disappoints — at current depressed stock price, dilution would be severe.",
        "Integration risk from the Exscientia merger: combining two large AI drug discovery organisations with different cultures, platforms, and workflows creates execution risk that may delay pipeline timelines by 6-12 months.",
        "REC-994 CCM is a rare disease with a small patient population (~3,000 US patients); even a positive readout may not move the revenue needle enough to justify the current valuation multiple without a broader pipeline readout."
      ],
      "analyst_conviction": "medium",
      "conviction_rationale": "Conviction is medium because the platform thesis is compelling but the cash cliff creates a near-term binary: REC-994 success or dilutive financing within 18 months.",
      "source_urls": []
    },
    {
      "name": "Schrödinger",
      "ticker": "SDGR",
      "exchange": "NASDAQ",
      "market_cap_usd_b": 3.1,
      "business_type": "hybrid",
      "value_chain_position": "Lead optimisation and hit identification via physics-based FEP+ simulation + ML; SaaS licensing to pharma/biotech + own proprietary pipeline (SGR-1505, SGR-3515)",
      "technology_approach": "Physics-based free energy perturbation (FEP+) engine is the gold standard for predicting small-molecule binding affinity; layered with ML models for ADMET prediction and scaffold hopping. Recurring SaaS revenue from 15 of the top 20 global pharma companies.",
      "valuation_metrics": {
        "ev_revenue_ratio": 14.8,
        "price_to_sales": 14.2,
        "pe_ratio": null,
        "cash_usd_b": 0.85,
        "week_52_high": 26.80,
        "week_52_low": 16.50,
        "ytd_change_pct": 0.08
      },
      "valuation_commentary": "Trades at 14.8x EV/Revenue — the highest multiple in the sector. Justified by the uniqueness of the physics engine (no direct pure-ML substitute for FEP+ in certain selectivity optimisation tasks) and >90% software revenue retention rate. Richly valued vs. RXRX (7.8x) and ABSI (11.5x), but recurring SaaS provides durability that pipeline companies cannot match.",
      "recent_developments": "FY2024 software revenue $160M (+18% YoY), ahead of consensus. SGR-1505 (MCL-1 inhibitor, haematologic malignancies) Phase I dose escalation complete; RP2D announcement expected Q2 2025. New enterprise agreements signed with Lilly and Merck for FEP+ suite expansion.",
      "bull_cases": [
        "SGR-1505 Phase I clean safety profile confirmation (Q2 2025) validates MCL-1 as an FEP+-designed target and unlocks partnership conversations for co-development, potentially adding $50-100M in near-term milestone revenue.",
        "Software revenue growth acceleration above 20% YoY (FY2025 guidance) would confirm market share gains from competitors' pure-ML tools and justify expanding the 14.8x multiple toward 18-20x, providing 20-35% upside.",
        "FEP+ is structurally differentiated from ML-only platforms because physics simulations are required for selectivity optimisation against closely related targets — this use case is not addressable by foundation models, insulating SDGR from pure-ML competitive pressure."
      ],
      "bear_cases": [
        "ML foundation models (AlphaFold3, Isomorphic Labs) may commoditise structure-based design for standard binding affinity prediction, reducing the marginal value of FEP+ for the majority of lead optimisation tasks and slowing SaaS renewal rates below the current >90%.",
        "SGR-1505 dose-limiting toxicity or safety signal would impair the pipeline credibility narrative and trigger a 15-25% multiple compression for the proprietary drug component of the valuation.",
        "Enterprise software spending freeze at top-10 pharma accounts (>60% of SaaS revenue) during cost-reduction cycles could reduce FY2025 renewal rates, which at 14.8x EV/Rev would have an outsized stock impact."
      ],
      "analyst_conviction": "high",
      "conviction_rationale": "High conviction because recurring SaaS revenue (>90% retention, 15 of top 20 pharma) provides downside protection that no other company in the sector can match, while SGR-1505 provides free optionality.",
      "source_urls": []
    },
    {
      "name": "Relay Therapeutics",
      "ticker": "RLAY",
      "exchange": "NASDAQ",
      "market_cap_usd_b": 0.9,
      "business_type": "pipeline",
      "value_chain_position": "Clinical-stage pipeline targeting dynamic protein conformations (PI3Ka, CDK, FGFR) via Dynamo platform combining MD simulations, cryo-EM, and ML",
      "technology_approach": "Dynamo platform integrates protein motion modelling (molecular dynamics + cryo-EM structural data) with ML to identify and drug dynamic protein conformations that are undruggable in their static crystal structures — particularly relevant for mutant-selective kinase inhibitors.",
      "valuation_metrics": {
        "ev_revenue_ratio": null,
        "price_to_sales": null,
        "pe_ratio": null,
        "cash_usd_b": 0.60,
        "week_52_high": 14.60,
        "week_52_low": 5.80,
        "ytd_change_pct": -0.35
      },
      "valuation_commentary": "No revenue multiples applicable (pure-pipeline company). Current market cap of $900M vs. $600M cash implies the market assigns $300M of value to RLY-2608 and the rest of the pipeline. A successful OPERA Phase II readout for RLY-2608 (PI3Ka breast cancer) would likely trigger a 2-3x re-rating; failure would compress toward cash value ($600M = ~$5.50/share).",
      "recent_developments": "RLY-2608 (PI3Ka mutant-selective inhibitor) Phase II OPERA trial interim analysis expected Q3 2025; primary endpoint is ORR vs. alpelisib in PIK3CA-mutant breast cancer patients. Roche partnership for RLY-5836 (CDK2 inhibitor) initiated IND-enabling studies. YTD -35% on broader biotech risk-off.",
      "bull_cases": [
        "RLY-2608 OPERA interim ORR >35% with superior tolerability vs. alpelisib (a hyperglycaemia-prone comparator) would establish RLY-2608 as potential best-in-class in a $2B+ annual addressable market for PI3Ka-mutant breast cancer.",
        "Roche partnership for RLY-5836 provides non-dilutive validation of the Dynamo platform for CDK2 targeting — a second asset potentially entering Phase I in 2026 provides pipeline diversification beyond the OPERA binary.",
        "Current $300M net enterprise value for RLY-2608 implies ~30% probability of approval is priced in; objective probability of RP2D + ORR >30% in a well-selected population is arguably 40-50%, suggesting the stock is mispriced."
      ],
      "bear_cases": [
        "OPERA interim misses primary ORR endpoint (ORR <25%) or shows non-inferiority tolerability vs. alpelisib — stock would compress -50-60% toward cash value of ~$5.50/share, with de-risking pressure on the broader pipeline.",
        "Cash runway of ~18 months at current burn rate (estimated $35-40M/quarter) is insufficient to reach Phase III without additional financing; a negative OPERA interim would force a dilutive offering at depressed prices.",
        "PI3Ka mutant-selective inhibition is a binary oncology bet in a crowded space (Inavolisib, Alpelisib, Capivasertib); even a positive OPERA result may face commercialisation headwinds if payers require head-to-head data vs. approved agents."
      ],
      "analyst_conviction": "medium",
      "conviction_rationale": "Medium conviction because OPERA ORR endpoint vs. alpelisib is mechanistically well-supported but binary — the sole near-term catalyst determines whether this is a 3x or near-zero outcome.",
      "source_urls": []
    },
    {
      "name": "AbCellera Biologics",
      "ticker": "ABCL",
      "exchange": "NASDAQ",
      "market_cap_usd_b": 1.4,
      "business_type": "platform",
      "value_chain_position": "Antibody discovery and early-stage optimisation via AI-assisted microfluidics B-cell screening; serves as CRO/platform for pharma partners — does not advance own clinical pipeline",
      "technology_approach": "AI-powered antibody discovery using proprietary microfluidics for ultra-high-throughput single B-cell screening, combined with ML models for sequence optimisation, affinity prediction, and developability scoring. Platform has discovered >$6B in partnered programmes.",
      "valuation_metrics": {
        "ev_revenue_ratio": 4.2,
        "price_to_sales": 5.8,
        "pe_ratio": null,
        "cash_usd_b": 0.72,
        "week_52_high": 5.10,
        "week_52_low": 2.30,
        "ytd_change_pct": -0.22
      },
      "valuation_commentary": "Trades at 4.2x EV/Revenue — cheapest in the sector on this metric — with cash of $720M vs. $1.4B market cap, implying the market assigns only $680M to the platform and pipeline. This near-cash valuation reflects the COVID antibody revenue cliff and the lack of a visible near-term catalyst. Deep value if management can demonstrate new large-pharma deal flow in 2025.",
      "recent_developments": "COVID-derived antibody royalties (Bebtelovimab) declining toward zero by end-2025 as the asset is no longer recommended. Partnerships with AstraZeneca and Pfizer for next-generation antibody programmes initiated. New oncology-focused subsidiary (Kineta acquisition integration) established. Cash position: $720M — comfortably above the 24-month runway threshold.",
      "bull_cases": [
        "Announcement of 1-2 new top-10 pharma antibody discovery partnerships with >$50M upfront payment would reset the market narrative from COVID-royalty rundown to platform growth, potentially lifting EV/Rev from 4.2x toward 8-10x peers.",
        "Cash-rich balance sheet ($720M) and near-cash valuation create an activist or strategic M&A case — the platform is worth substantially more to a pharma acquirer than the current $680M EV assigned to the business.",
        "Generative antibody design (partnership with Absci and others) represents an emerging capability upgrade that could increase discovery throughput 10x and justify premium pricing for next-gen partnership deals."
      ],
      "bear_cases": [
        "Bebtelovimab royalties declining to near zero by end-2025 removes the primary current revenue contributor without near-term replacement, risking >50% revenue decline in FY2025 if new partnerships do not ramp quickly enough.",
        "Platform differentiation is being eroded by AI-native antibody design companies (Absci zero-shot design, Generate Biomedicines de-novo protein design) that do not require the microfluidics infrastructure — limiting ABCL's addressable partnership market.",
        "Management has not demonstrated capital allocation discipline; significant cash deployment into subsidiaries (Kineta) and internal pipeline without clear ROI creates uncertainty about the optimal use of the $720M balance sheet."
      ],
      "analyst_conviction": "low",
      "conviction_rationale": "Low conviction near-term because revenue visibility is poor while COVID royalties decline and new partnership ramp timing is uncertain; strong cash position limits downside but lacks near-term catalyst for re-rating.",
      "source_urls": []
    },
    {
      "name": "Absci Corporation",
      "ticker": "ABSI",
      "exchange": "NASDAQ",
      "market_cap_usd_b": 0.7,
      "business_type": "hybrid",
      "value_chain_position": "De-novo antibody and protein design via generative AI; integrated cell-free expression system for rapid construct-to-functional-molecule cycles; emerging own pipeline",
      "technology_approach": "Integrated drug creation platform combining generative AI antibody design (zero-shot de-novo design beyond natural sequence space) with cell-free synthetic biology for rapid expression and screening. First AI-de-novo-designed antibody entered IND-enabling studies in 2024.",
      "valuation_metrics": {
        "ev_revenue_ratio": 11.5,
        "price_to_sales": 10.8,
        "pe_ratio": null,
        "cash_usd_b": 0.18,
        "week_52_high": 5.20,
        "week_52_low": 2.90,
        "ytd_change_pct": 0.03
      },
      "valuation_commentary": "Trades at 11.5x EV/Revenue — mid-range for the sector. Cash position of only $180M is the primary constraint; at current burn (~$15M/quarter) runway is ~12 months, making a capital raise probable in H2 2025 regardless of pipeline outcomes. AstraZeneca partnership (Dec 2024) provides partial validation but milestone payments are back-end weighted.",
      "recent_developments": "First fully AI-de-novo-designed antibody entered IND-enabling studies in 2024 — a sector first for zero-shot generative antibody design. Partnership with AstraZeneca for bispecific antibody programme signed December 2024 with undisclosed upfront. YTD near flat after strong 2H 2024 performance driven by milestone announcements.",
      "bull_cases": [
        "IND clearance for the first AI-de-novo antibody (H2 2025) would position Absci as the proof-of-concept company for zero-shot generative antibody design — a milestone with sector-wide signalling value, likely driving +50-80% stock appreciation.",
        "AstraZeneca bispecific partnership could expand to additional targets in 2025-2026 given successful demonstration of cell-free expression speed advantage; each new indication adds $10-30M in milestone optionality.",
        "The combination of zero-shot design (no need for immunisation or natural sequence templates) + cell-free expression (days vs. months for candidate generation) creates a structurally faster discovery cycle vs. microfluidics-based platforms like ABCL."
      ],
      "bear_cases": [
        "Cash runway of ~12 months requires a capital raise in H2 2025; if the IND filing is delayed or the AstraZeneca partnership does not generate near-term milestone cash, Absci will face a dilutive financing at a potentially depressed price.",
        "First de-novo antibody IND hold or significant safety flag in preclinical package would undermine the platform narrative and trigger -30-40% compression; the company has no other clinical-stage asset to de-risk with.",
        "Zero-shot antibody design has not been clinically validated in humans; investors are pricing technology promises — the gap between benchmark performance and clinical efficacy may be larger than anticipated, as has historically been the case in AI drug discovery."
      ],
      "analyst_conviction": "medium",
      "conviction_rationale": "Medium conviction because the de-novo design milestone is technically compelling but cash constraints create a parallel fundraising risk that could dilute the upside; IND clearance + capital raise together determine the 12-month outcome.",
      "source_urls": []
    }
  ],
  "catalysts": [
    {
      "company_name": "Recursion Pharmaceuticals",
      "ticker": "RXRX",
      "category": "clinical",
      "catalyst_type": "Clinical Trial Readout",
      "timing": "H2 2025",
      "expected_date": "H2 2025",
      "description": "REC-994 Phase II top-line data in cerebral cavernous malformation (CCM): primary endpoint is reduction in CCM lesion volume at 6 months vs. placebo in a 60-patient trial (NCT04893174). First fully AI-phenomics-selected clinical candidate at Recursion to reach Phase II readout.",
      "probability": "medium",
      "expected_impact": "+40-60% bull",
      "bull_case": "+40-60% if the trial demonstrates statistically significant lesion burden reduction — validates the Phenom-Beta phenomics selection methodology and supports the platform valuation premium. Could trigger upgrade from 7.8x to 12x EV/Revenue.",
      "bear_case": "-30-40% on failure or statistical non-significance — re-rates phenomics platform credibility downward and raises questions about the Exscientia merger rationale; puts cash runway in focus as dilution becomes necessary.",
      "evidence": "Recursion confirmed on 2025-02-20 investor relations update that REC-994 Phase II remains on schedule for H2 2025 readout; primary endpoint defined as reduction in CCM lesion burden at 6 months vs. placebo."
    },
    {
      "company_name": "Relay Therapeutics",
      "ticker": "RLAY",
      "category": "clinical",
      "catalyst_type": "Clinical Trial Readout",
      "timing": "Q3 2025",
      "expected_date": "Q3 2025",
      "description": "RLY-2608 Phase II OPERA trial interim analysis: primary endpoint is objective response rate (ORR) in PIK3CA-mutant, hormone receptor-positive, HER2-negative breast cancer patients, compared against alpelisib (standard of care). RLY-2608 is a mutant-selective PI3Ka inhibitor designed to reduce the hyperglycaemia toxicity of current-generation alpelisib.",
      "probability": "medium",
      "expected_impact": "+100-150% bull",
      "bull_case": "+100-150% if OPERA demonstrates ORR >35% with materially lower Grade 3+ hyperglycaemia vs. alpelisib comparator — establishes RLY-2608 as potential best-in-class PI3Ka inhibitor and validates the Dynamo platform for mutant-selective targeting; current $300M net enterprise value would reprice to $1.5-2B.",
      "bear_case": "-50-60% on interim failure (ORR <25%) or non-inferiority tolerability — stock compresses toward cash value (~$5.50/share), Roche RLY-5836 partnership optionality partially preserved but primary catalyst narrative broken.",
      "evidence": "OPERA trial registration NCT05348876; Relay confirmed Q3 2025 interim analysis timing in Q4 2024 earnings call with primary ORR endpoint vs. alpelisib."
    },
    {
      "company_name": "Schrödinger",
      "ticker": "SDGR",
      "category": "clinical",
      "catalyst_type": "Clinical Trial Readout",
      "timing": "Q2 2025",
      "expected_date": "Q2 2025",
      "description": "SGR-1505 (MCL-1 inhibitor) Phase I dose escalation completion and recommended Phase II dose (RP2D) announcement for treatment of haematologic malignancies (relapsed/refractory AML, diffuse large B-cell lymphoma). First proprietary FEP+-designed molecule to complete Phase I.",
      "probability": "medium",
      "expected_impact": "+20-30% bull",
      "bull_case": "+20-30% on clean safety profile and early ORR signals — validates that FEP+-designed selectivity (MCL-1 vs. BCL-2 differentiation) translates to human pharmacology; supports RP2D announcement and Phase II initiation, unlocking $50-100M partnership conversation.",
      "bear_case": "-15-25% on dose-limiting cardiac toxicity (MCL-1 is expressed in cardiomyocytes — class-specific risk) or lack of any efficacy signal at tolerable doses, impairing the pipeline valuation component of the SDGR investment case.",
      "evidence": "Schrödinger Q4 2024 earnings call confirmed RP2D announcement timeline for Q2 2025; Phase I safety data disclosed at ASH 2024 showed manageable toxicity profile at dose levels below RP2D."
    },
    {
      "company_name": "Schrödinger",
      "ticker": "SDGR",
      "category": "financial",
      "catalyst_type": "Earnings",
      "timing": "Q1 2025 (February)",
      "expected_date": "Q1 2025",
      "description": "Q4 2024 / FY2024 full-year earnings and FY2025 guidance: market focus on (1) software revenue growth rate vs. +18% FY2024 pace, (2) enterprise licence renewal rate and any churn disclosures, and (3) FY2025 total revenue and software revenue guidance.",
      "probability": "high",
      "expected_impact": "+10-15% bull on guidance beat",
      "bull_case": "+10-15% if FY2025 software revenue guidance implies >20% growth and renewal rate >90% is confirmed — validates software stickiness and justifies the 14.8x EV/Revenue premium vs. sector peers.",
      "bear_case": "-15-20% if FY2025 guidance implies software growth deceleration below 15% or management discloses churn from one of the top-10 pharma accounts that collectively account for >60% of revenue.",
      "evidence": "Q3 2024 earnings: FY2024 software revenue $160M at +18% YoY, ahead of consensus $155M; Q4 2024 earnings date scheduled for February 2025 per SDGR investor relations calendar."
    },
    {
      "company_name": "AbCellera Biologics",
      "ticker": "ABCL",
      "category": "partnership",
      "catalyst_type": "Partnership Announcement",
      "timing": "H1 2025",
      "expected_date": "H1 2025",
      "description": "Expected announcement of 1-2 new large-pharma antibody discovery partnerships to replace declining COVID antibody royalties (Bebtelovimab). Management guided on Q3 2024 earnings call that 'multiple advanced partnership conversations' were in progress with undisclosed top-10 pharma partners.",
      "probability": "medium",
      "expected_impact": "+20-30% bull",
      "bull_case": "+20-30% on a top-10 pharma deal with >$50M upfront payment and multi-year research collaboration — resets the market narrative from COVID-royalty rundown to platform growth; re-rates EV/Revenue from 4.2x toward peer median of 8-10x.",
      "bear_case": "Minimal direct downside if the announcement does not materialise in H1 2025; however, continued silence on new partnerships into H2 2025 would accelerate the revenue cliff narrative as Bebtelovimab royalties decline to zero.",
      "evidence": "AbCellera Q3 2024 earnings call (November 2024): CEO Andrew Booth stated 'we are in advanced discussions with multiple large pharmaceutical partners' and guided for partnership announcements in the first half of 2025."
    },
    {
      "company_name": "Absci Corporation",
      "ticker": "ABSI",
      "category": "platform_validation",
      "catalyst_type": "IND Filing",
      "timing": "H2 2025",
      "expected_date": "H2 2025",
      "description": "IND submission and clearance for the first fully AI-de-novo-designed antibody (undisclosed oncology target, designed by Absci's zero-shot generative model without any natural sequence template). Would be the first IND filed for a de-novo AI-generated antibody globally.",
      "probability": "medium",
      "expected_impact": "+50-80% bull",
      "bull_case": "+50-80% on IND clearance — positions Absci as the proof-of-concept company for zero-shot generative antibody design; likely triggers sector-wide discussion of AI-generated biologics and accelerates partner interest; AstraZeneca may exercise expansion options.",
      "bear_case": "-20-30% on IND hold or significant safety flag in preclinical immunogenicity or toxicology package — de-novo antibodies carry higher unpredictability risk than optimised natural antibodies; would raise questions about the platform's clinical applicability.",
      "evidence": "Absci disclosed in Q3 2024 earnings (November 2024) that the first AI-de-novo-designed antibody had entered IND-enabling studies; management guided for IND submission timing in H2 2025 subject to preclinical package completion."
    },
    {
      "company_name": "Recursion Pharmaceuticals",
      "ticker": "RXRX",
      "category": "partnership",
      "catalyst_type": "Partnership Announcement",
      "timing": "H1 2025",
      "expected_date": "H1 2025",
      "description": "Expected expansion of the Roche collaboration to add new oncology phenomics screening campaigns following successful initiation of 3 existing joint programmes. Management has guided for partnership revenue growth in 2025 driven primarily by milestones from the Roche collaboration.",
      "probability": "medium",
      "expected_impact": "+15-20% bull",
      "bull_case": "+15-20% on a new Roche programme announcement with a meaningful upfront payment ($20M+) — demonstrates that the post-merger Recursion OS platform is commercially validated by the highest-quality pharma partner in the sector.",
      "bear_case": "Minimal stock impact if Roche expansion is delayed, as it is not the primary near-term binary; but failure to grow Roche revenue in FY2025 would increase the probability of a dilutive financing before REC-994 data.",
      "evidence": "Recursion Q4 2024 investor presentation: three active Roche oncology collaboration programmes initiated; Roche has rights to expand collaboration to additional programmes under the existing framework agreement."
    },
    {
      "company_name": "Absci Corporation",
      "ticker": "ABSI",
      "category": "partnership",
      "catalyst_type": "Partnership Announcement",
      "timing": "H1 2025",
      "expected_date": "H1 2025",
      "description": "AstraZeneca bispecific antibody programme (signed December 2024): first programme milestone payment expected on IND-enabling study completion in H1 2025. Milestone amount undisclosed but estimated $5-15M based on similar-stage AZ deals.",
      "probability": "medium",
      "expected_impact": "+10-15% bull",
      "bull_case": "+10-15% on milestone receipt — provides near-term cash relief to the tight $180M balance sheet and demonstrates AstraZeneca's confidence in the bispecific design capability; could catalyse additional indication discussions.",
      "bear_case": "-5-10% if milestone is delayed past H1 2025 due to IND-enabling study setback — heightens capital raise concerns as the 12-month runway becomes more pressing.",
      "evidence": "Absci press release (December 2024): AstraZeneca bispecific antibody collaboration agreement signed; first milestone tied to IND-enabling study completion for the lead programme."
    }
  ]
}
"""

# ---------------------------------------------------------------------------
# ValidatorAgent  →  {"issues": [...], "overall_confidence": "...", "summary": "..."}
# ---------------------------------------------------------------------------
VALIDATOR = """
{
  "issues": [
    {
      "severity": "low",
      "check_type": "overconfident_inference",
      "section": "DiligenceAgent",
      "description": "The moat section references 'a large proprietary library of annotated compound-activity data points' with the attribution '(per company disclosures)'. While correctly attributed, the claim would benefit from a cross-reference to a specific public filing or press release to allow independent verification.",
      "suggested_correction": "Link the data-scale claim to a specific source (e.g. company investor day presentation, 10-K equivalent, or published paper) where the methodology for counting data points is described."
    },
    {
      "severity": "low",
      "check_type": "conflict",
      "section": "DiligenceAgent",
      "description": "The competitive landscape section references Exscientia's former approach as a direct comparable but does not note that Exscientia is no longer an independent entity following the January 2025 merger with Recursion. A reader unfamiliar with the merger may assume Exscientia is still a standalone competitor.",
      "suggested_correction": "Clarify inline: 'Exscientia (now merged into Recursion Pharmaceuticals, January 2025) previously operated a comparable closed-loop generative chemistry model.'"
    }
  ],
  "overall_confidence": "high",
  "summary": "The research is well-structured and the factual claims are appropriately qualified. Two prior issues have been resolved: (1) the private company sourcing list no longer includes publicly traded companies, and (2) specific quantitative claims in the diligence section are now attributed to company disclosures rather than presented as independently verified facts. Two low-severity issues remain: a data-scale claim that would benefit from a more specific source citation, and an Exscientia reference in the competitive landscape that does not acknowledge the company's merger into Recursion. Neither issue impairs the investment conclusions. The report is suitable for an institutional audience with the standard caveat that AI-generated research requires independent verification before investment decisions.",
  "corrected_claims": [
    "Proprietary data scale is described as 'a large proprietary library of annotated compound-activity data points (per company disclosures)' — correctly attributed but specific source citation would strengthen the claim.",
    "Exscientia reference in competitive landscape should note the January 2025 merger with Recursion Pharmaceuticals to avoid reader confusion."
  ]
}
"""

# ---------------------------------------------------------------------------
# ReportWriterAgent  →  8 report section fields
# ---------------------------------------------------------------------------
REPORT_WRITER = """
{
  "executive_summary": "The AI Drug Discovery sector has entered a pivotal inflection phase in 2024-2025, transitioning from proof-of-concept demonstrations to clinical validation. The central question — can AI-designed molecules outperform traditionally discovered drugs in human trials — is now being answered in real time, with three Phase II readouts expected in H2 2025 that will define sector sentiment for the next 24 months.\\n\\nPrivate market activity remains robust despite broader biotech headwinds. The landmark $1B Series A for Xaira Therapeutics signals continued conviction from top-tier life sciences investors in integrated AI-native drug design platforms. Deal structures are evolving: early-stage companies now routinely secure multi-hundred-million-dollar pharma partnerships that fund platform development while preserving equity upside on owned pipelines.\\n\\nIn the public markets, the sector is bifurcating between platform-and-pipeline hybrids (RXRX, SDGR) and pure-play clinical-stage bets (RLAY, ABSI). Valuations have compressed from 2021 peaks but remain elevated relative to traditional biotech. The near-term alpha opportunity lies in correctly pricing the probability of the upcoming Phase II catalysts — particularly REC-994 (RXRX), RLY-2608 (RLAY), and INS018_055 (Insilico). A positive readout on any of these would likely trigger sector-wide multiple expansion.",

  "private_market_overview": "Private investment in AI drug discovery totalled an estimated $4.5B globally in 2024, representing a 30% increase over 2023 despite a broader biotech funding contraction. The concentration of capital has increased: the top 10 deals accounted for ~70% of total funding, with mega-rounds (>$100M) becoming the norm for platform-stage companies that can demonstrate wet-lab validation of their AI outputs.\\n\\nGeographically, the US (San Francisco Bay Area and Boston/Cambridge) accounts for ~65% of deal volume, with the UK (Isomorphic Labs, Exscientia heritage) and Asia (Insilico, BioMap) representing the most active non-US clusters. Corporate venture arms — particularly from NVIDIA, Google Ventures, and large-cap pharma — are increasingly active as strategic co-investors, providing both capital and compute infrastructure.\\n\\nStage distribution has shifted later: Series B and C deals now dominate by value as investors concentrate on companies with at least one clinical-stage asset or a validated pharma partnership. Pure-software AI companies without wet-lab capabilities are finding it progressively harder to raise at premium valuations. The eight companies identified in our sourcing screen represent a cross-section from early (Variational AI, Series A) to late-stage pre-IPO (Isomorphic Labs, Insilico Medicine), with Xaira's $1B Series A as the outlier that reset sector benchmarks.",

  "diligence_highlights": "We conducted deep-dive analysis on three shortlisted companies: Isomorphic Labs, Insilico Medicine, and Generate Biomedicines. Across all three, we observe a common structural advantage: the integration of proprietary wet-lab data generation with model training creates compounding moats that pure-software AI companies cannot easily replicate.\\n\\nIsomorphic Labs stands out for the quality of its pharma partnerships — $2.9B in potential milestone payments from Eli Lilly and Novartis provides substantial non-dilutive runway while the company builds its owned pipeline. The AlphaFold heritage provides a unique starting point for structure-based design, though the company must demonstrate that its generative chemistry capabilities are truly differentiated from the broader AlphaFold ecosystem.\\n\\nInsilico Medicine is the most clinical-stage of the three, with INS018_055 in Phase II for IPF — a disease with high unmet need and a well-understood clinical endpoint. A positive readout would validate the entire generative-AI drug-design paradigm and dramatically increase the company's IPO prospects. Key risk: IPF is a historically difficult indication with multiple prior failures; the bar for 'positive' data is high.\\n\\nAcross all three companies, the primary shared risk is the gap between in-silico performance metrics and clinical outcomes. The field's history includes numerous preclinical successes that did not translate to patients. Investors should weight clinical milestone derisking heavily in any valuation framework.",

  "public_market_analysis": "The AI drug discovery public equity universe comprises six investable companies, with a combined market capitalisation of approximately $9B — down ~60% from the 2021 peak but up 25% from the 2023 trough. The sector trades at a wide valuation dispersion reflecting the heterogeneity of business models, from Schrödinger's recurring SaaS revenue to AbCellera's near-cash valuation.\\n\\nSchrödinger (SDGR) remains the most de-risked investment in the sector, with 18% software revenue growth in FY2024 and a high-quality customer base of 15 of the top 20 pharma companies. Its physics-based FEP+ platform provides a durable competitive advantage in cases where ML alone is insufficient (e.g., selectivity optimisation, ADMET prediction for novel scaffolds). The main risk is that pure-ML competitors improve to the point of commoditising the physics layer.\\n\\nRecursion Pharmaceuticals (RXRX) is the highest-optionality name in the sector. The Exscientia merger creates a genuinely integrated platform that no single competitor can match in scope. However, at 8x EV/Revenue with an 18-month cash runway, it requires a meaningful clinical or partnership catalyst to avoid a dilutive financing round. NVIDIA's ongoing support (both financial and through preferential GPU access) provides a partial backstop.\\n\\nRelay Therapeutics (RLAY) is the clearest near-term binary catalyst trade. The stock trades near cash value, effectively pricing zero probability on RLY-2608 success. Given the mechanistic rationale for PI3Ka mutant-selective inhibition and the tolerability advantages over alpelisib, we believe the market is underpricing a positive outcome.",

  "catalysts_section": "The H2 2025 clinical readout window represents the most concentrated set of AI drug discovery catalysts since the sector's emergence. Three Phase II datasets — REC-994 (RXRX, CCM), RLY-2608 (RLAY, breast cancer), and INS018_055 (Insilico, IPF) — will collectively answer the foundational question of whether AI-assisted drug design produces clinically superior molecules.\\n\\nWe assign the following probability-weighted impact assessments: RLY-2608 carries the highest individual stock impact potential (potential 2x on success, -50% on failure), making it the most attractive asymmetric trade for risk-tolerant investors. INS018_055 carries the highest sector-wide signalling value — a positive result in IPF would likely trigger re-ratings across all AI drug discovery equities. REC-994 in CCM (a rare disease) has a higher probability of success due to the smaller, well-characterised patient population and clear mechanistic rationale.\\n\\nBeyond clinical catalysts, partnership announcements remain a near-term catalyst for ABCL and ABSI, both of which need new large-pharma deal flow to reset negative revenue trajectories. Any top-10 pharma partnership with >$50M upfront would likely drive 20-30% appreciation in these names.",

  "risk_factors": "Sector-level risks are dominated by clinical translation uncertainty. The AI drug discovery field has yet to produce a single FDA-approved drug designed end-to-end by AI systems. While multiple Phase II trials are underway, the historical success rate of Phase II oncology trials is ~40% and rare disease trials ~50%. Investors pricing in high probabilities of AI-platform validation may be extrapolating too aggressively from in-silico performance metrics.\\n\\nRegulatory risk is an emerging concern. The FDA's 2024 AI/ML action plan and ongoing discussions around 'AI-generated evidence' in drug applications create uncertainty about review timelines and data requirements for AI-designed molecules. A restrictive guidance document could materially increase the cost and time of clinical development for all companies in the sector.\\n\\nAt the company level, the most material risks are: (1) cash runway for RXRX (~18 months) and ABSI (~12 months) requiring dilutive equity financing if catalysts disappoint; (2) partnership concentration for most private companies (2-3 pharma partners typically represent >60% of revenue); (3) compute cost inflation affecting margins as model sizes scale; and (4) talent attrition, as compensation benchmarks set by well-funded startups (Xaira's $1B warchest) and big tech continue to pull ML/biology talent from listed companies.",

  "conclusion": "The AI drug discovery sector is at a genuine inflection point. The next 12 months will provide the first definitive clinical evidence — positive or negative — on whether AI-designed molecules work in humans. Our analysis identifies Relay Therapeutics (RLAY) as the most attractive near-term catalyst trade, Schrödinger (SDGR) as the most de-risked hold, and Insilico Medicine (private, pre-IPO) as the highest-conviction private market opportunity given its imminent Phase II readout and clear IPO pathway.\\n\\nFor portfolio construction, we recommend a barbell approach: pair the high-optionality clinical-stage names (RLAY, RXRX) with the more stable SaaS-model exposure (SDGR) and selective private market exposure through fund vehicles with access to late-stage rounds. The sector warrants a meaningful allocation for any life sciences portfolio with a 3-5 year horizon, with position sizing calibrated to individual catalyst risk tolerance.",

  "validation_notes": "The validator identified 2 low-severity issues (down from 5 in the prior iteration). Both previously flagged medium issues have been resolved: (1) the sourcing list no longer contains publicly traded companies such as Recursion Pharmaceuticals; (2) specific quantitative claims in the diligence section (data scale, compute advantage) are now attributed to company disclosures with appropriate caveats. Remaining low-severity notes: a proprietary data-scale claim would benefit from a more specific source citation, and an Exscientia reference in the competitive landscape should acknowledge the January 2025 merger with Recursion. All market data carries a reference date footnote. Overall validator confidence: HIGH."
}
"""

# ---------------------------------------------------------------------------
# Registry — looked up by agent class name in BaseAgent._call_llm()
# ---------------------------------------------------------------------------
MOCK_RESPONSES = {
    "SourcingAgent": SOURCING.strip(),
    "DiligenceAgent": DILIGENCE.strip(),
    "PublicMarketAgent": PUBLIC_MARKET.strip(),
    "ValidatorAgent": VALIDATOR.strip(),
    "ReportWriterAgent": REPORT_WRITER.strip(),
}
