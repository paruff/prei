# Changelog

## [0.4.2](https://github.com/paruff/prei/compare/v0.4.1...v0.4.2) (2026-09-02)


### Fixed

* **ci:** run apt-get update in doc-freshness workflow ([#408](https://github.com/paruff/prei/issues/408)) ([1dc55bd](https://github.com/paruff/prei/commit/1dc55bd7b7b3694858831b0f556ff3fd581feff8))

## [0.4.1](https://github.com/paruff/prei/compare/v0.4.0...v0.4.1) (2026-09-02)


### Added

* add BLS QCEW county-level employment for GACS (GACS-QCEW-1) ([#277](https://github.com/paruff/prei/issues/277)) ([f169ea5](https://github.com/paruff/prei/commit/f169ea50775b62f9eecd71629928bb98a010b571))
* add branch name to footer — identify which code built the image ([a593cb7](https://github.com/paruff/prei/commit/a593cb75bbd4a0984ee6e1005f388386f0f48461))
* add county_fips to GrowthArea + county FIPS map (GACS-QCEW-0) ([#276](https://github.com/paruff/prei/issues/276)) ([a567c1c](https://github.com/paruff/prei/commit/a567c1ce175c84e588820d0d0a2655c082e6bfe6))
* add Docker workflow Makefile targets; local build_date fallback ([61b3b44](https://github.com/paruff/prei/commit/61b3b44756457e951bc9f20207efe9c7c1ef2eef))
* add GACS v2 county employment, school quality, updated weights ([#265](https://github.com/paruff/prei/issues/265)) ([972d83f](https://github.com/paruff/prei/commit/972d83f509f3a9c78e3b7b17b87c6813951905e5))
* add GACS v2 rebalance — rent growth 15%, adjusted weights (GACS-SCORE-1) ([#279](https://github.com/paruff/prei/issues/279)) ([ecbf6be](https://github.com/paruff/prei/commit/ecbf6befd0786ad904a2f6365dfa4fe552b02731))
* add HUD FMR rent benchmark adapter for GACS (GACS-FMR-1) ([#278](https://github.com/paruff/prei/issues/278)) ([ddf3233](https://github.com/paruff/prei/commit/ddf3233e347182954912e6d9599fe46a928dcee0))
* add HUD FMR rent estimates and BLS LAUS county unemployment adapters ([#261](https://github.com/paruff/prei/issues/261)) ([820ecc2](https://github.com/paruff/prei/commit/820ecc2f9b9c8b47c37581f604a859d352e0b579))
* add HUD Income Limits API adapter ([c22929a](https://github.com/paruff/prei/commit/c22929a0f3b3572372b2be9bdd6b4710b0a8fd29))
* add pipeline kanban backend + data health dashboard + screening UX ([#357](https://github.com/paruff/prei/issues/357)) ([fdc1e48](https://github.com/paruff/prei/commit/fdc1e485201446c78e4d675a613b3d0cadba9556))
* **analysis:** add CapEx reserve schedule with defaults ([#381](https://github.com/paruff/prei/issues/381)) ([467cdf0](https://github.com/paruff/prei/commit/467cdf0047a91f19fc52c14be22bd4e6e921a639))
* **analysis:** add exit strategy and fix sensitivity rate axis ([#380](https://github.com/paruff/prei/issues/380)) ([98d0eab](https://github.com/paruff/prei/commit/98d0eab3b6e46e57398b9fd513ffacedda45065c))
* **analysis:** add financing scenario comparison — conventional vs DSCR vs seller financing ([#382](https://github.com/paruff/prei/issues/382)) ([0897277](https://github.com/paruff/prei/commit/089727756d47ecf8ff52a78d92c0a81c62be95ce))
* **build:** add build_date to version display; fix pre-commit inline styles ([ca61638](https://github.com/paruff/prei/commit/ca61638c73683640d040b97dd9e537534a5f60c0))
* **ci:** add GitOps deploy gates, live acceptance tests, rollback + test coverage ([#301](https://github.com/paruff/prei/issues/301)) ([789313c](https://github.com/paruff/prei/commit/789313c7039d0d902b19485b719d8af1620f89bd))
* **ci:** add opencode GitHub Action, ported from fawkes ([232ba56](https://github.com/paruff/prei/commit/232ba5600a420230194dc112aae05115796b175e))
* **ci:** Phase 3 — post-deployment acceptance pipeline with content-aware tests ([b039c9c](https://github.com/paruff/prei/commit/b039c9c844a3c2f191c12444a85b3d2a99e01552))
* **ci:** phase A — CI guard, Pydantic validators, 22 acceptance tests ([#303](https://github.com/paruff/prei/issues/303)) ([54f4132](https://github.com/paruff/prei/commit/54f4132f3965b054703dee62ea7b77e2ff72b800))
* **ci:** phase C — authenticated ZAP scan + flaky test quarantine ([#325](https://github.com/paruff/prei/issues/325)) ([67a2de8](https://github.com/paruff/prei/commit/67a2de8898b98cb5d0aa6396a5f56b57eb32705e))
* **ci:** phase C — flaky test detection, ZAP full scan, SLO dashboard ([#305](https://github.com/paruff/prei/issues/305)) ([9e62f4b](https://github.com/paruff/prei/commit/9e62f4b2bc05eacf6381b163556f84081848dc5c))
* **ci:** Phase D — structured logging, request timing, alerting, API surface validation ([#306](https://github.com/paruff/prei/issues/306)) ([966af39](https://github.com/paruff/prei/commit/966af39aa9182754e7255e189ae0cda5df02ae07))
* **ci:** replace python-semantic-release with release-please ([#405](https://github.com/paruff/prei/issues/405)) ([c9eec56](https://github.com/paruff/prei/commit/c9eec569f1a6f663c365ea8f5459088ad355a0bf))
* **ci:** run 19 BDD acceptance tests against live container after smoke tests ([b424a6a](https://github.com/paruff/prei/commit/b424a6abe4a84191326978ed1122cdf8a5ceff49))
* **county:** wire all 11 TX county foreclosure scrapers into system page ([8a2d0d6](https://github.com/paruff/prei/commit/8a2d0d6031d9997f6e66e7f32eef62de0e27d14f))
* **data:** add Rentometer API adapter for real rent comps ([#376](https://github.com/paruff/prei/issues/376)) ([8849d12](https://github.com/paruff/prei/commit/8849d12a2cf136c38f005c87107b821829f0c9c4))
* **data:** comprehensive US city→county lookup (29,727 cities) ([9e1e9bc](https://github.com/paruff/prei/commit/9e1e9bc48b9d44936e702c56a39444b03d1fc0d8))
* **data:** reso web api + tax strategy + saved searches notifications ([#360](https://github.com/paruff/prei/issues/360), [#373](https://github.com/paruff/prei/issues/373), [#374](https://github.com/paruff/prei/issues/374)) ([#385](https://github.com/paruff/prei/issues/385)) ([1c244a8](https://github.com/paruff/prei/commit/1c244a829316dd172c708ba6ac216bcc6e3633a9))
* **data:** unified US lookup replaces hardcoded county FIPS map ([7f1ce2d](https://github.com/paruff/prei/commit/7f1ce2dd920fa42cb5cc97cc91576be459ad33fc))
* **discovery:** auto-trigger HUD/USDA ingestion when data is missing ([d022739](https://github.com/paruff/prei/commit/d0227394aa24cac95bdc376a86473ff1ec058770))
* **discovery:** rebuild discovery page and add pipeline screener (VIEW-DISCOVERY-1, VIEW-SCREENER-1) ([#283](https://github.com/paruff/prei/issues/283)) ([1944ccf](https://github.com/paruff/prei/commit/1944ccf7d8900138594ad082c6257340747d9bd7))
* **discovery:** show in-page results instead of redirecting to screener ([ba8a301](https://github.com/paruff/prei/commit/ba8a301220a09a5283f04dfb38eaa2a50ba9f5bf))
* **gitops:** phase 1 — deployment manifests with CI-driven image digest updates ([d848299](https://github.com/paruff/prei/commit/d848299f0daf0ce3879d9cbf193c4f15344614ab))
* **gitops:** phase 3 — environments, image signatures, drift detection ([aed6e50](https://github.com/paruff/prei/commit/aed6e5049572b026bbc46f5536d82b7e79f70fd7))
* **gitops:** phase 3 — environments, image signatures, drift detection ([#308](https://github.com/paruff/prei/issues/308)) ([a6f6c76](https://github.com/paruff/prei/commit/a6f6c7603dca39ed755a1b9e2a1b63518f4ab2c2))
* implement Phase A of TOP_01_PLAN — CI/test quality gaps ([#323](https://github.com/paruff/prei/issues/323)) ([e2bbf47](https://github.com/paruff/prei/commit/e2bbf471f5c298f48e726e69dbf454a70b46ed2c))
* implement Phase B of TOP_01_PLAN — financial math verification ([#324](https://github.com/paruff/prei/issues/324)) ([642321a](https://github.com/paruff/prei/commit/642321a7bb62458bb21a310a2a7df523ac9713f7))
* **ingestion:** wire full USDA TXT parser into ingestion service ([1b98376](https://github.com/paruff/prei/commit/1b9837649ca2d80d4a08fa9ff9da2ad4baff0b42))
* **leasing:** kanban board for leasing pipeline with drag-and-drop ([#292](https://github.com/paruff/prei/issues/292)) ([d553c9b](https://github.com/paruff/prei/commit/d553c9bcbde43001497f3eb50563e1fd413979a0))
* **leasing:** kanban board for leasing pipeline with drag-and-drop ([#292](https://github.com/paruff/prei/issues/292)) ([#293](https://github.com/paruff/prei/issues/293)) ([262ecde](https://github.com/paruff/prei/commit/262ecde52261bf7782019430a1bec07f226646bd))
* **make:** add Docker workflow targets — build, up, down, restart, logs, clean ([be9e172](https://github.com/paruff/prei/commit/be9e172a77de8819356912cbeae8933df81a3c60))
* **make:** add test-live target for live acceptance testing ([3ecadb5](https://github.com/paruff/prei/commit/3ecadb505aee7d8908a5ed59e4b73210ab773d74))
* **math:** phase B — financial math verification with 58 edge-case tests ([#304](https://github.com/paruff/prei/issues/304)) ([30fd355](https://github.com/paruff/prei/commit/30fd355b6dd8e5e31bf497e5fe7cfa60f291b422))
* **mobile:** pwa support — responsive templates, service worker, offline caching ([#384](https://github.com/paruff/prei/issues/384)) ([54260bd](https://github.com/paruff/prei/commit/54260bd57372e45d22a309dd4f9f300b130433e5))
* **p0:** crm kanban board + data source health dashboard ([#309](https://github.com/paruff/prei/issues/309)) ([3da9055](https://github.com/paruff/prei/commit/3da90551e150599a541c9516e3a88ffe694be562))
* **pipeline:** add location fields to PipelineProperty model (MODEL-PP-1) ([#282](https://github.com/paruff/prei/issues/282)) ([273ab75](https://github.com/paruff/prei/commit/273ab7550f852911694f3d452357cc6d10c5cf57))
* **pipeline:** kanban CRM board with drag-and-drop stage advancement ([#290](https://github.com/paruff/prei/issues/290)) ([b1aa5eb](https://github.com/paruff/prei/commit/b1aa5eb740ad41d0e4c2e99b93aa0677e6495784))
* **portfolio:** add market cycle indicators dashboard ([#383](https://github.com/paruff/prei/issues/383)) ([6a45dbd](https://github.com/paruff/prei/commit/6a45dbd50939051f211a3b9ed41f7603cf226bee))
* **screening:** range sliders for screening criteria; update Kanban spec ([#291](https://github.com/paruff/prei/issues/291)) ([be1458f](https://github.com/paruff/prei/commit/be1458f60bf7eceded0f4c3f4a2efee04c7c79bc))
* **sources:** sheriff sale scrapers for 5 TX counties + HUD dollar homes ([00da486](https://github.com/paruff/prei/commit/00da486e0968348e1bf1632e67e09893e906b047))
* **sources:** wire tarrant county source and fix hud fmr token selection ([#332](https://github.com/paruff/prei/issues/332)) ([3446ebe](https://github.com/paruff/prei/commit/3446ebe150c85e8d2024449596a17b0f563c6a9b))
* **system:** add 'Analyze Growth Areas' button to system page ([4413b27](https://github.com/paruff/prei/commit/4413b27a235dffb8b9205de6abd9c737c66a40fd))
* **ui:** system status page — data inventory + operations, no CLI needed ([442f867](https://github.com/paruff/prei/commit/442f86761dfa49092f8bfa6e7869d4b9c4ff29c0))
* **ux:** add 'This month' filter to pipeline list (PIPE-UX-3) ([#253](https://github.com/paruff/prei/issues/253)) ([cfd323b](https://github.com/paruff/prei/commit/cfd323b61a42b4442b375bee0e011f5e8032f26b))
* **ux:** add composite score breakdown rows to growth area lists (GA-UX-2) ([#258](https://github.com/paruff/prei/issues/258)) ([e63cfb7](https://github.com/paruff/prei/commit/e63cfb79cccbde8e15dfbf7af922c9fe4290752d))
* **ux:** add experimental score disclaimer banner to growth areas (GA-UX-1) ([#257](https://github.com/paruff/prei/issues/257)) ([10ec508](https://github.com/paruff/prei/commit/10ec508e5c659af03c1ccd348218b22f58175f26))
* **ux:** add pipeline review queue view (PIPE-UX-1) ([#251](https://github.com/paruff/prei/issues/251)) ([d9136a4](https://github.com/paruff/prei/commit/d9136a4ebd48f27da0c2a227c2d678811f5717bb))
* **ux:** add pipeline review queue view (PIPE-UX-1) ([#252](https://github.com/paruff/prei/issues/252)) ([6383da9](https://github.com/paruff/prei/commit/6383da9f23bf92cf6ef66f446e16bfa69b0431a7))
* **ux:** add supply_constraint_index column with ACS-derived badge (GA-DATA-2) ([#256](https://github.com/paruff/prei/issues/256)) ([b963791](https://github.com/paruff/prei/commit/b963791e83e42b49705542be366d98af5026fca8))
* **ux:** growth areas dashboard + BRRRR timeline ([#311](https://github.com/paruff/prei/issues/311)) ([ee0f6af](https://github.com/paruff/prei/commit/ee0f6af0b82f08769c5f8a7029166e13f463c457))
* **ux:** growth explorer redesign — no clutter, tier filter, multi-state ready ([#315](https://github.com/paruff/prei/issues/315)) ([2aa23db](https://github.com/paruff/prei/commit/2aa23dbea7c34c75c1b170e1652ab7df4ab186a3))
* **ux:** mao visualization, equity kpi, growth areas seed ([#313](https://github.com/paruff/prei/issues/313)) ([a8ef165](https://github.com/paruff/prei/commit/a8ef165a5ad818b9679e4db41df0a26e55904829))
* **ux:** move KPI cards to top with IDs, add live JS GRM recalc (PIPE-UX-4) ([#254](https://github.com/paruff/prei/issues/254)) ([5b356b5](https://github.com/paruff/prei/commit/5b356b5fd2b65e2442f008fc0f712e83f47fe6be))
* wire ATTOM to discovery, add county pipeline support, add data confidence (next wave) ([#260](https://github.com/paruff/prei/issues/260)) ([d8188ef](https://github.com/paruff/prei/commit/d8188ef814ef110703b8c13cb9beb76e742ef108))
* wire HUD FMR into screening, add 10 TX county scrapers ([#262](https://github.com/paruff/prei/issues/262)) ([5f14ecc](https://github.com/paruff/prei/commit/5f14eccc703222d93c0be09265ed7a52e96bbabb))


### Fixed

* add ATTOM_API_KEY to settings; suppress FMR ZIP-level log spam ([3852b1c](https://github.com/paruff/prei/commit/3852b1c9839282422e5a0d6b8347fd2cb83c4afe))
* add confidence column to growth area tables (GA-UX-1) ([#275](https://github.com/paruff/prei/issues/275)) ([a552bcf](https://github.com/paruff/prei/commit/a552bcf8754ea641575119661734604ef8551526))
* add structlog to mypy.ini, format settings.py ([#310](https://github.com/paruff/prei/issues/310)) ([3f8ab32](https://github.com/paruff/prei/commit/3f8ab32a5a7a557f1e9a14443915f561d47f9207))
* address review findings from [#384](https://github.com/paruff/prei/issues/384)/[#382](https://github.com/paruff/prei/issues/382)/[#381](https://github.com/paruff/prei/issues/381) (closes [#393](https://github.com/paruff/prei/issues/393), [#394](https://github.com/paruff/prei/issues/394), [#395](https://github.com/paruff/prei/issues/395)) ([#397](https://github.com/paruff/prei/issues/397)) ([f89dbe2](https://github.com/paruff/prei/commit/f89dbe2ba75dcdd211891801ee02a88ab2150f5c))
* audit findings — DRF permissions, password validators, pipeline/portfolio tests, SECURITY.md update ([#280](https://github.com/paruff/prei/issues/280)) ([68932b8](https://github.com/paruff/prei/commit/68932b86297f09e15b72482fb7e69f24c9abf500))
* **ci:** add --check-untyped-defs to mypy and fix test typing ([#337](https://github.com/paruff/prei/issues/337)) ([3ff4daf](https://github.com/paruff/prei/commit/3ff4dafb29f72d3f76500453f51df9eee0e3fc4a))
* **ci:** add explicit markers to BDD and post-deploy pytest runs ([#334](https://github.com/paruff/prei/issues/334)) ([7982e2a](https://github.com/paruff/prei/commit/7982e2a53f6a5c806cfeb11ac5f1f8fa77e43f81))
* **ci:** add source checkout to live-test job for BDD test files ([800aae7](https://github.com/paruff/prei/commit/800aae7c19029fa05e7183d096ad5b33c60026f9))
* **ci:** build single platform (amd64) to halve Docker build time ([77f7927](https://github.com/paruff/prei/commit/77f79271d4c064ceb15b0d0e7affd48264110ab8))
* **ci:** exclude acceptance tests from unit test run ([fc3366d](https://github.com/paruff/prei/commit/fc3366dc7ca66bec6a106fe87ccbd7eead804717))
* **ci:** fix live-test container crash from SQLite database path parsing ([954d6db](https://github.com/paruff/prei/commit/954d6dbb93969c1f344838f03b9d258d73fda167))
* **ci:** remove --noinput flag from seed_data command ([79373aa](https://github.com/paruff/prei/commit/79373aa32ee4f16d8b07e594cc577a72d955d150))
* **ci:** remove duplicate run key from lint job ([412942f](https://github.com/paruff/prei/commit/412942f4ddec2fc2edd47a0b4801ceb107c9f35e))
* **ci:** replace broken bandit security lint with ruff S rules ([#322](https://github.com/paruff/prei/issues/322)) ([7327569](https://github.com/paruff/prei/commit/732756949a6e35257b8b4c9d0e0409347b1f3ebb))
* **ci:** resolve Trivy HIGH CVEs blocking Tier 2 Governance on main ([#377](https://github.com/paruff/prei/issues/377)) ([5dc66b9](https://github.com/paruff/prei/commit/5dc66b9dc158a821a4f4cb6fc01f91a7152baec6))
* **ci:** run apt-get update before installing libcairo2-dev ([#406](https://github.com/paruff/prei/issues/406)) ([9229e39](https://github.com/paruff/prei/commit/9229e39858d5f2561cd68453e84b4674ae966afe))
* **ci:** show container logs on live-test failure ([1d6bf79](https://github.com/paruff/prei/commit/1d6bf79d5e920c5fa39333e178a3650f7a705295))
* **ci:** simplify workflow name and needs format for GitHub Actions parser ([ed1ffa4](https://github.com/paruff/prei/commit/ed1ffa431d07ee7c0327fe8f7896a758d5feb2ef))
* **ci:** speed up Docker build and fix live-test container startup ([b4aeab6](https://github.com/paruff/prei/commit/b4aeab64ce7ba57d3958ae1514836a4c6c42a765))
* city name matching for discovery; remove old Foreclosures link; UX picker ([c274f1b](https://github.com/paruff/prei/commit/c274f1b4e8994b86aa997913eb062fcbe3065d66))
* clarify HUD FMR 403 error — key needs separate FMR dataset registration ([70f4216](https://github.com/paruff/prei/commit/70f42164a7475299fefdd92a126ae198b518b08f))
* **config:** add FRED_API_KEY to .env.example and settings.py (GA-FIX-1) ([#259](https://github.com/paruff/prei/issues/259)) ([a4882de](https://github.com/paruff/prei/commit/a4882de78121b1c2d3df4e46c3af8d5398764019))
* **db:** enable SQLite WAL mode to prevent background thread lock errors ([a2337f2](https://github.com/paruff/prei/commit/a2337f2711ab81205a5f7035bd1bcf1521035db7))
* **deps:** bump opentelemetry-sdk and exporter-otlp alongside api to 1.44.0 ([e8009ff](https://github.com/paruff/prei/commit/e8009ff559d05aa3905636e56a0c213efaa81483))
* **deps:** pin structlog directly and guard middleware import ([#333](https://github.com/paruff/prei/issues/333)) ([c27ea5c](https://github.com/paruff/prei/commit/c27ea5c349d783337baffa0eb23c8ec007988884))
* **devcontainer:** add Python feature and use python -m pip ([23be4b0](https://github.com/paruff/prei/commit/23be4b002ad9bc5c45a87f1afb0659b2d40803ab))
* **devcontainer:** sync PYTHON_VERSION in docker-compose.yml with Dockerfile ([1ce4ed5](https://github.com/paruff/prei/commit/1ce4ed54596d787b09107c3da95c52a0ca132ef4))
* **devcontainer:** use latest Python feature image (3.14 not published yet) ([d984efa](https://github.com/paruff/prei/commit/d984efaaffc0adfc503147923d4274a628688039))
* **discovery:** auto-scrape VRM for state when data is missing ([159dde2](https://github.com/paruff/prei/commit/159dde2bb4917611294c4faafdea2a68984be13e))
* **discovery:** run HUD/USDA ingestion synchronously on first request ([9444e0a](https://github.com/paruff/prei/commit/9444e0aa88d0d8ffbc974b68345886ea0ebc3fd9))
* **discovery:** run VRM scrape in background thread; replace View Foreclosures ([6887535](https://github.com/paruff/prei/commit/688753522aed4ad128e31ec811d00dd6a48d6efc))
* **discovery:** wire landlord tier filter and convert discovery flow to AJAX ([825b4c3](https://github.com/paruff/prei/commit/825b4c3ea0e0f0087307f5b4cb967e5ac905fc4d))
* exempt health check from DRF rate limiting ([e75daab](https://github.com/paruff/prei/commit/e75daab8ac641c75587db5c9adde918ee146c3c1))
* **growth:** expand county FIPS map to 87 cities; fix template weights ([006da76](https://github.com/paruff/prei/commit/006da76d5a26b1b3d93aef438fef701a1b7601d5))
* **growth:** expand county_fips_map to 97 entries; backfill all cities ([780624c](https://github.com/paruff/prei/commit/780624c4da874588fe62f663b9c77acea976dbae))
* **growth:** reduce QCEW timeout to 5s; wrap in try/except ([659080a](https://github.com/paruff/prei/commit/659080a4387d65ca8af65db30da2012ff9f8ab05))
* **growth:** remove QCEW and FMR HTTP calls from web view (worker timeout) ([b48f0ab](https://github.com/paruff/prei/commit/b48f0ab0483e35fa5352884c0d14973ee82ef889))
* **growth:** try QCEW county-level employment on first explorer run ([381850c](https://github.com/paruff/prei/commit/381850c66b6d6221fefff0727ae4c7ae209ee671))
* **growth:** wire unified us_lookup into populate_growth_areas QCEW/FMR paths ([898fd03](https://github.com/paruff/prei/commit/898fd03c57fa348ecb9bc9ae7ad2a56c1a9556c0))
* HUD FMR 403 — token likely created before selecting FMR dataset ([ba1afe8](https://github.com/paruff/prei/commit/ba1afe808afc212e82784204eb32f8997b90db49))
* improve HUD FMR API error diagnostics on 403 ([22b63de](https://github.com/paruff/prei/commit/22b63de47468c63540ceb23ae3814633ff16c857))
* **infra:** increase gunicorn worker timeout 30→120s ([ca87f1a](https://github.com/paruff/prei/commit/ca87f1a1c4323681b6942727861de745101181cd))
* **nav:** change Rehab & Lease link from pipeline_list to leasing_list ([#250](https://github.com/paruff/prei/issues/250)) ([f07b436](https://github.com/paruff/prei/commit/f07b436374c30573a7b8461478440e84c2c7434a))
* **ops:** DB-aware health check + rate limit on paid API fan-out views ([#379](https://github.com/paruff/prei/issues/379)) ([bf2b802](https://github.com/paruff/prei/commit/bf2b8029594aadc6a90331f175ac8a59c3ad42fb))
* populate net_migration_rate in both ingestion paths (GA-DATA-1) ([#274](https://github.com/paruff/prei/issues/274)) ([dbb8a48](https://github.com/paruff/prei/commit/dbb8a48b46d77ee205939118aaffccce6c3948db))
* populate rent/school/migration in GACS; scale composite_score to 0-100 ([#289](https://github.com/paruff/prei/issues/289)) ([0099501](https://github.com/paruff/prei/commit/0099501b4d2b4d8b990656e09634c7e2894d358b))
* remove dead school_score lookup in growth_explorer (GA-BUG-3) ([#270](https://github.com/paruff/prei/issues/270)) ([b623533](https://github.com/paruff/prei/commit/b62353375f8b646a95b6ba0b24b55688cdcfef66))
* remove Jinja2 whitespace-trim syntax from branch/built_date tags ([04ad0fa](https://github.com/paruff/prei/commit/04ad0fadf6eecb76192c73746abadd50a96a7c51))
* remove Jinja2 whitespace-trim syntax from Django template ([a4caeeb](https://github.com/paruff/prei/commit/a4caeeb677563fc320cd8e544172892cb52b5e04))
* resolve 5 MEDIUM audit findings (save perf, data_confidence, index, imports) ([#288](https://github.com/paruff/prei/issues/288)) ([af87106](https://github.com/paruff/prei/commit/af87106fbb7974d9ff6d43a73caeff508bc9e601))
* resolve 6 BLOCKER audit findings (supply, pipeline, syntax, templates) ([#286](https://github.com/paruff/prei/issues/286)) ([c145378](https://github.com/paruff/prei/commit/c145378e9fce361ef9ec3af056a3cea21ae2f7c7))
* resolve 8 HIGH audit findings (indexes, double-screening, aggregation, auth) ([#287](https://github.com/paruff/prei/issues/287)) ([e18a296](https://github.com/paruff/prei/commit/e18a2963939445c649f8928aa06a5af9f03a21f6))
* resolve CI failures on PR [#288](https://github.com/paruff/prei/issues/288) — Makefile test + PDF exclusion ([39f9193](https://github.com/paruff/prei/commit/39f9193c8e5f4afa2b7ec26ea5f4b1d46e27745b))
* ruff format ([#255](https://github.com/paruff/prei/issues/255)) ([8694fb8](https://github.com/paruff/prei/commit/8694fb8538dd771950a16c752979959b2324aa2a))
* score breakdown matches actual GACS v2 weights (GA-BUG-1) ([#269](https://github.com/paruff/prei/issues/269)) ([719c646](https://github.com/paruff/prei/commit/719c646679d72dc917865096fd50351eaa201c9c))
* **screening:** address code-review findings on Rentometer fallback chain ([#378](https://github.com/paruff/prei/issues/378)) ([903b567](https://github.com/paruff/prei/commit/903b56733e17682a031c37030ae2d36b30adb7c7))
* **screening:** slider names must match updateLabel fieldName pattern ([e7f1971](https://github.com/paruff/prei/commit/e7f1971be51cd5894891e7bd14f3428c184f2e81))
* **security:** add [@login](https://github.com/login)_required to 5 unprotected views ([ad49c5b](https://github.com/paruff/prei/commit/ad49c5bb403b0b2687e393f8c603044bc4de5455))
* **security:** stop logging ZIP code in VRM source fetch ([2c42597](https://github.com/paruff/prei/commit/2c42597a0040bd691ede1afee3a97fc166748148))
* set metro_area to blank instead of city_name (GA-DATA-3) ([#272](https://github.com/paruff/prei/issues/272)) ([7f3ed9e](https://github.com/paruff/prei/commit/7f3ed9e0be5edb129bfe7213053ad835e32ede63))
* stop FMR warning spam per state ([3f3a38f](https://github.com/paruff/prei/commit/3f3a38fe73d13420f7a772d21241657f9d0d37aa))
* **tests:** update container startup tests for preiweb service rename ([#351](https://github.com/paruff/prei/issues/351)) ([2ca1bc0](https://github.com/paruff/prei/commit/2ca1bc0cc749f821f4a84424025063ee8a0f66c0))
* **ux:** redesign discovery page — remove redundant empty states, cleaner layout ([992c6d8](https://github.com/paruff/prei/commit/992c6d8e9ff67526b264763558dddf42480459dd))
* **ux:** redesign growth explorer — less clutter, tier filter, multi-state ready ([9b120ea](https://github.com/paruff/prei/commit/9b120ea020725d61261cf76c06a58a0f39a137fa))
* **workflow:** resolve docker-publish.yml syntax errors from PR [#301](https://github.com/paruff/prei/issues/301) ([ff5f4d7](https://github.com/paruff/prei/commit/ff5f4d7d4f059d9d53052e4ac1e37df49c23c213))


### Docs

* add branch discipline to GitOps principles (AGENTS.md) ([99c5903](https://github.com/paruff/prei/commit/99c590389ef8a4c4179dbca76e4fa00f426dc022))
* add GitOps principles, context files, and CONVENTIONS link to AGENTS.md ([f2cb6ed](https://github.com/paruff/prei/commit/f2cb6edca73b9455ffd85877a10fec9d8de52fe5))
* add investor workflow guides for growth, discovery, screening, underwriting ([#336](https://github.com/paruff/prei/issues/336)) ([ff42608](https://github.com/paruff/prei/commit/ff426085c151e6021cad1883373232f43554e2a7))
* add LIMIT-18 for FRED state-level employment coarseness ([#271](https://github.com/paruff/prei/issues/271)) ([1e3ec29](https://github.com/paruff/prei/commit/1e3ec29f148d1a8309535d623a179eeba61a6eb9))
* add product-level discovery brief and feature spec writing guide ([8260512](https://github.com/paruff/prei/commit/82605129c36f567c32d62642a719ba42b1f3ee14))
* audit docs, organize directory structure, add AGENTS.md guidance ([6b13ea0](https://github.com/paruff/prei/commit/6b13ea0720c1b7abac509380ca6dac839a1f0855))
* comprehensive plan to reach top 0.1% quality ([31f0a06](https://github.com/paruff/prei/commit/31f0a060fbc0ed469be4fcf029d81b9624eb6fac))
* document never-swallow-exceptions principle in Never Do list ([#345](https://github.com/paruff/prei/issues/345)) ([ef0fc04](https://github.com/paruff/prei/commit/ef0fc040156f88c475356a13ec06f5713f556f2f))
* document orphaned rent_growth_rate field (GA-DATA-2) ([#273](https://github.com/paruff/prei/issues/273)) ([acc5ef0](https://github.com/paruff/prei/commit/acc5ef0aa0fbef77c347c75c667630380bd089a7))
* fix stale Django 5.2→6.0, copyright 2024→2026, devcontainer Python 3.14→3.13 ([3443f0e](https://github.com/paruff/prei/commit/3443f0e6c81ad0e9a4117fe8dc8ca75f2e29f352))
* **gitops:** phase 2 — uFawkesObs integration guide, webhook, DORA metrics ([#307](https://github.com/paruff/prei/issues/307)) ([575f7d8](https://github.com/paruff/prei/commit/575f7d8ea8d641b9b9ed95b632230ca7d9c703ff))
* honest product maturity audit — replace outdated strategy with real statuses ([1ae6763](https://github.com/paruff/prei/commit/1ae6763a3f8736239b3d1d072743d4419d5ad260))
* local dev environment setup + prioritized P0-P2 plan ([ce1c8b8](https://github.com/paruff/prei/commit/ce1c8b89eadc66e51a3d67424a936986b0c5e6e0))
* move LIMIT-04 to resolved (composite_score is now a persisted DecimalField) ([#268](https://github.com/paruff/prei/issues/268)) ([51120b3](https://github.com/paruff/prei/commit/51120b338dacd3fd366498a83de18ca450953e04))
* revise discovery brief to cover full investor lifecycle ([fd346c1](https://github.com/paruff/prei/commit/fd346c164250311e2c63cf88b68858f2a06ca6f7))
* sync API_SURFACE, ARCHITECTURE, and add app review findings ([a32bef5](https://github.com/paruff/prei/commit/a32bef51362d87289d9b12b40556117c9689d938))


### Changed

* **ci:** parallel test jobs, post-deploy smoke, local/devcontainer deploy targets ([#285](https://github.com/paruff/prei/issues/285)) ([7888e1f](https://github.com/paruff/prei/commit/7888e1f8270b9ae990e3b9c2ae92971379a41440))
* **finance:** split finance utils into focused modules ([#331](https://github.com/paruff/prei/issues/331)) ([d70e70f](https://github.com/paruff/prei/commit/d70e70f137ab1f93692022ce25c3f5c54beac7ed))


### Chores

* audit medium batch — pin deps, session security, CORS docs, severity labels, new validator/scoring tests ([#281](https://github.com/paruff/prei/issues/281)) ([a425d15](https://github.com/paruff/prei/commit/a425d1584e33cc138c56ee5859ea842c024dfd0a))
* audit quick wins — ruff target, search, CSV export, README ([1ccbe32](https://github.com/paruff/prei/commit/1ccbe327560def2873df464838f439aaf690819c))
* **ci:** rename live acceptance tests to smoke tests; add test pyramid plan ([256f3b9](https://github.com/paruff/prei/commit/256f3b922426c6a24efec85e4487b05595c2dd8b))
* **deps:** bump actions/cache from 4 to 6 ([#392](https://github.com/paruff/prei/issues/392)) ([a3dd162](https://github.com/paruff/prei/commit/a3dd16281a8c5bb9a739b99f46f819ecc3b506e1))
* **deps:** bump actions/download-artifact from 5 to 8 ([ed56885](https://github.com/paruff/prei/commit/ed5688527ffa7d8d71a759fe30a65727b5220f37))
* **deps:** bump actions/setup-python from 6 to 7 ([#316](https://github.com/paruff/prei/issues/316)) ([eede239](https://github.com/paruff/prei/commit/eede239b9c1278cb72b9bdd5c12193585d92abfd))
* **deps:** bump actions/upload-artifact from 5 to 7 ([3ca8080](https://github.com/paruff/prei/commit/3ca8080bfc2970948e2d582103f194bd55f047e7))
* **deps:** bump aiohttp from 3.14.1 to 3.14.3 ([#343](https://github.com/paruff/prei/issues/343)) ([ade42b5](https://github.com/paruff/prei/commit/ade42b57675b25125e9f6bca839089100ef3532c))
* **deps:** bump aiohttp in the uv group across 1 directory ([#338](https://github.com/paruff/prei/issues/338)) ([e245397](https://github.com/paruff/prei/commit/e2453973439dce56ee37fae65a1bd1bbb131da17))
* **deps:** bump anomalyco/opencode/github from 1.18.18 to 1.18.21 ([#391](https://github.com/paruff/prei/issues/391)) ([ac34fea](https://github.com/paruff/prei/commit/ac34fea57de0c66b25f7b208f07fa3e13ba78837))
* **deps:** bump anomalyco/opencode/github from 1.18.21 to 1.18.25 ([#404](https://github.com/paruff/prei/issues/404)) ([56294a9](https://github.com/paruff/prei/commit/56294a9da8cbcf630172b3c64a1c864e856bcd9d))
* **deps:** bump commitizen from 4.16.4 to 4.16.5 ([#318](https://github.com/paruff/prei/issues/318)) ([6f30e49](https://github.com/paruff/prei/commit/6f30e4941a5a61221d66c9de1662e2d4c7ca8f6a))
* **deps:** bump commitizen from 4.16.5 to 4.17.0 ([#342](https://github.com/paruff/prei/issues/342)) ([c8cb537](https://github.com/paruff/prei/commit/c8cb537d296527e08b501f84ceff8869aa5a5c1c))
* **deps:** bump coverage from 7.15.0 to 7.15.1 ([022317b](https://github.com/paruff/prei/commit/022317bd52b8fe11ef656771b901004203300268))
* **deps:** bump coverage from 7.15.1 to 7.15.2 ([#330](https://github.com/paruff/prei/issues/330)) ([7cdfbff](https://github.com/paruff/prei/commit/7cdfbffbcd1727d62d3372f2a42aa8d1b08120c6))
* **deps:** bump coverage from 7.15.2 to 7.15.4 ([#349](https://github.com/paruff/prei/issues/349)) ([d087dc6](https://github.com/paruff/prei/commit/d087dc6b128e1d68635cc79a1c04b7aac8111a06))
* **deps:** bump coverage from 7.15.4 to 7.16.0 ([#400](https://github.com/paruff/prei/issues/400)) ([481698a](https://github.com/paruff/prei/commit/481698af075e6963a51bc94cab1ca3cf940db231))
* **deps:** bump cryptography from 49.0.0 to 50.0.0 ([#341](https://github.com/paruff/prei/issues/341)) ([d43f77a](https://github.com/paruff/prei/commit/d43f77ab8d328c6204e010d4a0b6cb72259d8c0c))
* **deps:** bump django-structlog from 9.0.0 to 10.1.0 ([#403](https://github.com/paruff/prei/issues/403)) ([2dea6c5](https://github.com/paruff/prei/commit/2dea6c5995ceef789612cdb413e58f173cb84c80))
* **deps:** bump django-stubs from 6.0.6 to 6.0.7 ([4b2fc39](https://github.com/paruff/prei/commit/4b2fc39cb051ddf31c8f72b314a5f19aaab3e877))
* **deps:** bump djangorestframework from 3.17.1 to 3.18.0 ([#386](https://github.com/paruff/prei/issues/386)) ([1f87ae8](https://github.com/paruff/prei/commit/1f87ae813f61b2ccf689881849db4a249946782c))
* **deps:** bump djlint from 1.40.3 to 1.42.1 ([#317](https://github.com/paruff/prei/issues/317)) ([1282528](https://github.com/paruff/prei/commit/1282528932ce704c59c53e09c3bd05e9ba6850ee))
* **deps:** bump fastapi from 0.139.0 to 0.139.2 ([#321](https://github.com/paruff/prei/issues/321)) ([e1d15c1](https://github.com/paruff/prei/commit/e1d15c1f4a9660583cd67e1528230ee3ee449df8))
* **deps:** bump matplotlib from 3.11.0 to 3.11.1 ([#320](https://github.com/paruff/prei/issues/320)) ([2ceaf41](https://github.com/paruff/prei/commit/2ceaf4173c3b67b1445d1579b0ba5a295dcb271f))
* **deps:** bump mypy from 2.2.0 to 2.3.0 ([#326](https://github.com/paruff/prei/issues/326)) ([faac958](https://github.com/paruff/prei/commit/faac95844fa8623b3c5435dc1bad8dd60f206a52))
* **deps:** bump mypy from 2.3.0 to 2.3.1 ([#401](https://github.com/paruff/prei/issues/401)) ([afaaaa8](https://github.com/paruff/prei/commit/afaaaa8d493db3a37e7e442fd4aa50f372a78f37))
* **deps:** bump opentelemetry-api from 1.32.1 to 1.44.0 ([6267be1](https://github.com/paruff/prei/commit/6267be1bee6f053bfa2916d3faaad734f503dbb5))
* **deps:** bump playwright from 1.61.0 to 1.62.0 ([#340](https://github.com/paruff/prei/issues/340)) ([2219f49](https://github.com/paruff/prei/commit/2219f4978c9151d71efa6d16524b51461324a618))
* **deps:** bump pymdown-extensions from 11.0.1 to 11.0.2 ([#390](https://github.com/paruff/prei/issues/390)) ([d736ad1](https://github.com/paruff/prei/commit/d736ad19d319ec9d3ca4277c0cf6827455903394))
* **deps:** bump pypdf in the uv group across 1 directory ([#398](https://github.com/paruff/prei/issues/398)) ([c104a16](https://github.com/paruff/prei/commit/c104a1697d850523e5a150ad18554cd1003463c1))
* **deps:** bump pytest-rerunfailures from 16.1 to 16.5 ([#348](https://github.com/paruff/prei/issues/348)) ([1b5bd30](https://github.com/paruff/prei/commit/1b5bd30504de02e9eaf630dc5bc74c6d0205a145))
* **deps:** bump python-json-logger from 3.3.0 to 4.1.0 ([#329](https://github.com/paruff/prei/issues/329)) ([fb0255c](https://github.com/paruff/prei/commit/fb0255ccccbb61435ba819f204cd517d9324827c))
* **deps:** bump python-json-logger from 4.1.0 to 4.2.0 ([#387](https://github.com/paruff/prei/issues/387)) ([029b5db](https://github.com/paruff/prei/commit/029b5dbf9ee577931eaeb292b995b725249c71ba))
* **deps:** bump reportlab from 5.0.0 to 5.0.1 ([#388](https://github.com/paruff/prei/issues/388)) ([ae8ede1](https://github.com/paruff/prei/commit/ae8ede1c931411a33063d2674198ada44d1b8652))
* **deps:** bump ruff from 0.15.20 to 0.15.21 ([79b217b](https://github.com/paruff/prei/commit/79b217b639d6e0560ed19d80f3278d8acaf27103))
* **deps:** bump ruff from 0.15.21 to 0.15.22 ([#319](https://github.com/paruff/prei/issues/319)) ([61773b9](https://github.com/paruff/prei/commit/61773b95375d21f131787d4accbe6f116bb594b7))
* **deps:** bump ruff from 0.15.22 to 0.16.0 ([#327](https://github.com/paruff/prei/issues/327)) ([8a8b347](https://github.com/paruff/prei/commit/8a8b3479c08993f9bc5f792ba055485cc705f6c2))
* **deps:** bump ruff from 0.16.0 to 0.16.5 ([#399](https://github.com/paruff/prei/issues/399)) ([82ffd51](https://github.com/paruff/prei/commit/82ffd5192f72c5c6c1796fc46a02d89a287178b4))
* **deps:** bump svglib from 2.0.2 to 2.2.0 ([#389](https://github.com/paruff/prei/issues/389)) ([70404e7](https://github.com/paruff/prei/commit/70404e7f72500d150225de280cc1884bc3607890))
* **deps:** bump types-psycopg2 from 2.9.21.20260518 to 2.9.21.20260712 ([04f2503](https://github.com/paruff/prei/commit/04f250397cee9cec5b64307dcb6648ba8bad4e62))
* **deps:** bump types-psycopg2 from 2.9.21.20260712 to 2.9.21.20260724 ([#402](https://github.com/paruff/prei/issues/402)) ([e73ea96](https://github.com/paruff/prei/commit/e73ea9632c53de447c4f209b3ebfd1f4aa68b435))
* **deps:** bump types-reportlab from 4.5.1.20260521 to 4.5.1.20260712 ([c8296ae](https://github.com/paruff/prei/commit/c8296ae9d5da9e00cd90806a34bb680d99f1105c))
* **deps:** bump types-reportlab from 4.5.1.20260712 to 4.5.1.20260728 ([#328](https://github.com/paruff/prei/issues/328)) ([9f827eb](https://github.com/paruff/prei/commit/9f827ebb49b516caafa352aff7532885005fef48))
* ignore .omo/ artifacts, commit Serena config migration ([5136735](https://github.com/paruff/prei/commit/5136735ebaf95b302554b0cb61fc713b7e2a0feb))
* major refactor - models package, notifications, portfolio dashboard ([#267](https://github.com/paruff/prei/issues/267)) ([679228b](https://github.com/paruff/prei/commit/679228bd7e9e7617bb4c431ae209661f85cbb80f))
* pin all dependencies for deterministic, reproducible builds ([#284](https://github.com/paruff/prei/issues/284)) ([b70c637](https://github.com/paruff/prei/commit/b70c637f95b91dee4cbaabeefbac9b9b32120e4b))
* pre-release cleanup — remove orphaned files, consolidate docs, fix Trivy CVEs ([#358](https://github.com/paruff/prei/issues/358)) ([5798467](https://github.com/paruff/prei/commit/5798467f5bc3e8654455b34f7323c3a5adc89601))
* rename compose service web to preiweb for observability clarity ([#344](https://github.com/paruff/prei/issues/344)) ([7253ef4](https://github.com/paruff/prei/commit/7253ef4500beac2b247d060b26d89391dd818553))

## [0.4.0] - 2026-07-08

### Added
- **Discovery Source Models (DISC-0)**: `HudProperty`, `UsdaProperty`, `CountyForeclosureNotice` models for structured HUD/USDA/county foreclosure data storage.
- **HUD REO Ingestion (DISC-1)**: `ingest_hud_reo` command fetching from HUD ArcGIS Hub GeoJSON feed. Confirmed real endpoint replaces guessed mock.
- **USDA REO Ingestion (DISC-2)**: `ingest_usda_reo` command with fixed-width TXT parser for USDA rural REO data.
- **HUD/USDA Pipeline Screening (DISC-3)**: Extended `screen_property()` to accept HudProperty/UsdaProperty directly; hard-kill criteria for non-rentable sources.
- **HUD/USDA List/Detail Views (DISC-4)**: Property list and detail pages with "Add to Pipeline" for HUD and USDA sources.
- **Dallas County TX NTS Scraper (DISC-5)**: First county-level foreclosure scraper targeting Dallas County publicsearch.us. Playwright-based with graceful auth-wall handling.
- **ATTOM Preforeclosure Integration (DISC-6)**: Wired existing `ATTOMAdapter` to fetch NOD/NTS/Lis Pendens notices by ZIP code into `CountyForeclosureNotice`. Management command `fetch_attom_preforeclosure`.
- **Property Discovery Page**: Source management and request system for triggering property fetches.
- **Fannie Mae HomePath Datasource**: Scraper stub for HomePath.com (blocked by Cloudflare WAF — returns empty results gracefully).

### Fixed
- HUD endpoint corrected from guessed URL to real ArcGIS Hub GeoJSON (DISC-HG-1).
- Migration conflicts resolved between DISC-0/DISC-1/DISC-2 branches.
- Test conftest merged HUD + USDA fixtures after merge conflict.
- Reportlab 5 upgrade unblocked by replacing xhtml2pdf with Playwright PDF generation.
- 7 CodeQL clear-text logging alerts suppressed in ATTOM adapter.
- CI failure for PR #241 (missing HUD test fixtures) and PR #232 (ruff/mypy/CodeQL gates).

### Changed
- **Python 3.14**: Project fully migrated from Python 3.12/3.13 to Python 3.14.6. All venvs, hooks, CI configs updated.
- **Django 6.0**: Upgraded from Django 5.2 to 6.0.7.
- **Reportlab 5.0**: Upgraded from reportlab 4.x to 5.0; xhtml2pdf replaced by Playwright `page.pdf()`.
- **ATTOM Adapter**: Added `postalcode` param support to `fetch_foreclosure_data()`.
- **Dependencies**: Updated django-stubs, svglib, types-reportlab; added pypdf for test PDF extraction.

### Removed
- `xhtml2pdf` dependency (replaced by Playwright for PDF generation).

## [0.3.1-alpha.2] - 2026-07-08

### Added
- **Pipeline Lifecycle System (PIPE-0 through PIPE-14)**: End-to-end deal pipeline with discovery, 9-criteria screening, offer/DD/renovation/closing/leasing views, and pipeline list/detail UI. Includes new models for pipeline transactions and leasing properties.
- **Semver 2.0 Versioning**: Version now auto-detected from git tags (dev) or baked-in Docker metadata (production). Docker labels, structured logging, and automated semantic-release workflow added.
- **ATTOM API + FRED API Integration**: ATTOM comps fixes and FRED economic data integration for market analysis.
- **Growth Area Enhancements**: Pagination, CSV export, UX overhaul, and overlay fixes for the Growth Area Explorer.
- **Pipeline Navigation**: Restructured main nav into Buy / Maintain / Sell groups with pipeline-focused links.

### Changed
- Version source: removed stale `VERSION` file, now reads from git tag at HEAD or baked Docker metadata.
- Docker image includes `org.opencontainers.image.version` and `revision` labels.
- Startup logging now emits structured JSON fields (`version`, `git_commit`, `python_version`, `django_version`).
- Automated releases via `python-semantic-release` on merge to `main`.

### Fixed
- Integration test skipping when API keys absent (CI #505).
- VRM scraper: replaced obsolete CSS selectors with embedded JSON model parsing.
- Growth Explorer overlay visibility on page load.
- Devcontainer SQLite path permissions and `collectstatic` ordering in entrypoint.

## [0.2.2] - 2026-07-06

### Added
- **Growth Area Explorer**: Full view and template for exploring growth areas with demographic and economic data.
- **Growth Area → VRM Foreclosures Linking**: Navigate from growth area rows to filtered VRM foreclosure lists.
- **Pipeline Navigation**: Restructured main nav into Buy / Maintain / Sell groups.
- **Census Integration**: `discover_places_in_state` function for discovering places by state.
- **Growth Phase B**: GrowthArea population, SQLite default configuration, ATTOM comps fix.
- **Tests**: Docker e2e smoke test, Makefile validation, Census adapter tests for discover_places and growth_explorer.

### Changed
- Devcontainer: switched to absolute SQLite path to resolve bind-mount permission errors (multiple fixes).
- CI: replaced `amannn/action-semantic-pull-request` with `github-script`; bumped pre-commit ruff to v0.15.20.
- Entrypoint now runs `collectstatic` and `seed_data` automatically in devcontainer.
- Nav bar now includes Growth Areas and VRM Foreclosures links.

### Fixed
- VRM scraper: parse embedded JSON model instead of obsolete CSS selectors.
- Devcontainer port visibility; `USE_X_FORWARDED_HOST` support added.
- Production settings tests; CodeQL logging sanitization.
- GitOps validation: skip `USER root` check for devcontainer Dockerfile.

## [0.2.1] - 2026-07-03

### Added
- **VRM JSON Import**: Importer, management command, API endpoint, template, and tests for importing VRM data from JSON.
- **Version Number in Footer**: Git commit SHA and version tag now displayed in the app footer.

### Changed
- CI: replaced `black` with `ruff format`; upgraded mypy `python_version` from 3.11 to 3.12.
- Docker build: installed `libcairo2-dev` for svglib 1.6+ pycairo compilation.
- Pre-commit hooks reorganized with modern ruff configuration.

### Fixed
- Various CodeQL, bandit, and mypy lint issues across the codebase.
- `reportlab` pinned to `<5.0` for xhtml2pdf compatibility.

### Dependencies
- Updated: `aiohttp`, `docker/setup-buildx-action` (v3→v4), `playwright`, `reportlab`, `actions/checkout` (v6→v7), `docker/build-push-action` (v6→v7).

## [0.2.0] - 2026-06-21

### Added
- **P1 RentCast API**: New `fetch_rent_estimate` for real rental estimates by address. Includes 7-day caching, daily budget guard (100 calls/day), and automatic fallback to PPSF heuristic on failure.
- **P2 GreatSchools API**: New `fetch_school_rating` for real school ratings by ZIP code (0-10 scale). Includes 30-day caching and fallback to stub values.
- **P3 Walk Score API**: New `fetch_walk_score` for walkability, transit, and bike scores by address. 30-day caching with graceful `None` return.
- **Configuration**: `RENTCAST_API_KEY`, `GREATSCHOOLS_API_KEY`, and `WALKSCORE_API_KEY` env vars supported in `.env.example` and devcontainer.
- **Test coverage**: 23 new unit tests across all three adapters (happy path, error handling, cache behavior, edge cases).

### Changed
- `core/integrations/market/__init__.py` updated with adapter documentation.
- Pipeline artifacts: `specification.md`, `design.md`, `tasks.json` produced and committed.

### Notes
- All three adapters follow the existing Census/BLS pattern: stateless functions, `requests` for HTTP, Django cache, `Decimal` precision, and `None`-on-failure semantics.
- Existing stub functions (`get_rent_estimate_for_listing`, `get_school_rating`) preserved for backward compatibility.
