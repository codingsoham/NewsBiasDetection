# NewsBias: Major Project Panel Defense Study Material & Q&A Guide

**Project Title:** NewsBias: AI-Powered Multi-Perspective News Analysis & Bias Detection for India  
**Candidate:** Soham Ghosh (Enrollment No: `231b341`)  
**Department:** Computer Science & Engineering, Jaypee University of Engineering & Technology, Guna  
**Project Supervisor:** Dr. Partha Sarathy Banerjee  
**Live Backend Server:** `http://54.206.165.74:8000/`  
**GitHub Repository:** `https://github.com/codingsoham/NewsBiasDetection`  
**Latest Android Build:** `v1.0.0 (Production Release with In-App OTA Updater)`  

---

## 📌 Table of Contents
1. [The 2-Minute Elevator Pitch (Opening Statement)](#1-the-2-minute-elevator-pitch)
2. [Slide-by-Slide Defense Script (What to Say on Every Slide)](#2-slide-by-slide-defense-script)
3. [Core Technical Deep-Dives (Simplified for Viva)](#3-core-technical-deep-dives)
   - [Why Indic-RoBERTa over Generic Multilingual Models?](#31-why-indic-roberta)
   - [The Indian Political Spectrum vs. Western Binary](#32-the-indian-political-spectrum)
   - [Speaker Attribution Decoupling (Solving Quote Bias)](#33-speaker-attribution-decoupling)
   - [TF-IDF + DBSCAN News Clustering](#34-tf-idf--dbscan-clustering)
   - [Temperature Scaling & Expected Calibration Error (ECE)](#35-temperature-scaling--calibration)
   - [Full-Stack Architecture & Cloud Infrastructure](#36-system-architecture--cloud)
   - [In-App GitHub Over-The-Air (OTA) Self-Updater](#37-in-app-ota-self-updater)
4. [Top 35 Tough Questions Asked by Panels & Model Answers](#4-top-35-panel-questions--model-answers)
   - [Category A: Machine Learning & NLP (Q1–Q10)](#category-a-machine-learning--nlp)
   - [Category B: Data Pipeline & Sourcing (Q11–Q16)](#category-b-data-pipeline--sourcing)
   - [Category C: Software Engineering & Cloud Backend (Q17–Q23)](#category-c-software-engineering--cloud-backend)
   - [Category D: Android Client & Architecture (Q24–Q28)](#category-d-android-client--architecture)
   - [Category E: Ethics, Bias, & Limitations (Q29–Q35)](#category-e-ethics-bias--limitations)
5. [Quick Memory Cheat Sheet (Formulas, Metrics, & Numbers)](#5-quick-memory-cheat-sheet)

---

## 1. The 2-Minute Elevator Pitch

> *"Good morning respected panelists and my supervisor Dr. Partha Sarathy Banerjee. My name is Soham Ghosh (Enrollment No. 231b341).*  
>
> *Today, more than 900 million Indians consume digital news daily through algorithmic social feeds. However, recommendation algorithms maximize engagement, which traps readers in ideological echo chambers and accelerates political polarization.*  
>
> *Global bias detection platforms like AllSides or Ground News focus almost exclusively on Western two-party politics—Democrat vs. Republican. They completely fail in India, where political discourse involves multi-party coalitions, regional nuances, economic welfare, and cultural nationalism.*  
>
> *To solve this, I designed and built **NewsBias** from the ground up as a solo engineering project. NewsBias is an end-to-end, AI-powered multi-perspective news platform specifically engineered for India. It automatically ingests articles across 20+ prominent Indian media outlets, clusters identical real-time events using DBSCAN, decouples direct political quotes from journalistic reporting, and classifies the editorial framing using a fine-tuned Indic-RoBERTa model.*  
>
> *Crucially, I applied post-hoc Temperature Scaling to calibrate model probabilities, eliminating neural network overconfidence and reducing calibration error by 73%. The entire system is production-deployed on a 24/7 AWS EC2 cloud backend and delivered through a modern Jetpack Compose Android client with an in-app Over-The-Air self-updater.*  
>
> *I am excited to walk you through the architecture, results, and live demonstration."*

---

## 2. Slide-by-Slide Defense Script

### Slide 1: Title Slide
- **Speak:** *"Respected committee members, I present my Major Project titled 'NewsBias: AI-Powered Multi-Perspective News Analysis and Bias Detection for India', carried out under the supervision of Dr. Partha Sarathy Banerjee."*

### Slide 2: Table of Contents
- **Speak:** *"This presentation covers the problem statement, literature review, my 12-week work plan and individual contributions, followed by the system architecture, dataset, Indic-RoBERTa methodology, empirical evaluation, live Android application, and future roadmap."*

### Slide 3: 1. Introduction
- **Speak:** *"The objective of NewsBias is to dismantle algorithmic filter bubbles by aggregating multi-source coverage of Indian events and objectively visualizing editorial perspectives. Rather than labeling an entire outlet as biased, NewsBias evaluates articles dynamically across four categories: Left, Center, Right, and Non-Political, while delivering balanced feeds through an offline-first mobile app."*

### Slide 4: 2. Problem Statement
- **Speak:** *"Why is this problem critical? In modern journalism, two major technical problems exist: First, existing NLP models suffer from 'quote bias'—they penalize a neutral reporter who quotes a partisan speech. Second, neural networks are notoriously overconfident, assigning 99% probability even to ambiguous socio-political topics. In India's massive democracy, readers lack the time to compare 15 outlets daily. NewsBias solves this cognitive fatigue."*

### Slide 5 & 6: 3. Literature Review & Research Gaps
- **Speak:** *"In my literature survey, I examined foundational works such as Baly et al. at ACL 2020 on multi-task bias classification, Spinde et al. on lexical framing, and Guo et al. at ICML 2017 on temperature scaling. Existing commercial platforms like Ground News rely on crowdsourcing or US-centric models. The major gap is that no automated platform handles Indian multi-party political spectrums, quote-attribution decoupling, and calibrated confidence on Indian English text."*

### Slide 7: 4. Work Plan (12-Week Roadmap)
- **Speak:** *"The project was executed systematically over a 12-week schedule: starting from problem formulation and scrapers in Weeks 1–3, dataset curation and model benchmarking in Weeks 4–5, fine-tuning and calibration in Weeks 6–7, clustering and backend in Weeks 8–9, Android engineering in Week 10, cloud deployment and OTA updates in Week 11, and thorough empirical validation in Week 12. All 12 milestones have been successfully completed."*

### Slide 8: 5. Individual Contribution
- **Speak:** *"This project was developed 100% individually by me. I took full responsibility across all engineering verticals: from scraping 20+ outlets, fine-tuning Indic-RoBERTa and implementing temperature scaling, to writing the FastAPI backend on AWS EC2, and designing the Jetpack Compose Android client with Room database caching."*

### Slide 9: 6. Work Done: Architecture & UML Diagrams
- **Speak:** *"Slide 9 shows our system design. On the left is the Structural Component Diagram: the mobile client interacts with the cloud REST API via Retrofit, which communicates with the Indic-RoBERTa inference engine and SQLite persistence layer. On the right, the Behavioral Sequence Diagram shows the hourly pipeline: RSS ingestion, DBSCAN clustering, bias scoring, and mobile synchronization."*

### Slide 10: 6. Work Done: Dataset & Ingestion Pipeline
- **Speak:** *"We monitor 20+ national and regional outlets categorized into three sourcing tiers: High Factuality (like The Hindu or Indian Express), Standard, and Mixed. We use Trafilatura for boilerplate removal, SHA-256 hashes to prevent duplicate wire syndication, and TF-IDF with DBSCAN to dynamically cluster related articles into stories without needing to pre-specify the number of clusters."*

### Slide 11: 6. Work Done: Methodology & Indic-RoBERTa
- **Speak:** *"For our core NLP engine, we selected Indic-RoBERTa because it was pretrained on Indian English and regional corpora, capturing Indian political idioms far better than standard BERT. We introduced Speaker Attribution Decoupling to separate the reporter's tone from cited quotes. Furthermore, we formulated Temperature Scaling with optimal parameter T=1.20 to align model confidence with real empirical accuracy."*

### Slide 12: 6. Work Done: Result Analysis & Benchmarks
- **Speak:** *"Our empirical results demonstrate clear superiority: Indic-RoBERTa achieves 84.8% accuracy and 0.842 Macro F1, outperforming multilingual BERT by 12.0%. The confusion matrix on the center shows strong diagonal discrimination. Most importantly, the reliability diagram on the right proves that Temperature Scaling reduced the Expected Calibration Error from 0.142 to 0.038—a 73% reduction in model overconfidence."*

### Slide 13: 6. Work Done: Application UI & Cloud Infrastructure
- **Speak:** *"Slide 13 displays real screenshots of our live production system. The left screenshot shows the clustered news feed with multi-perspective spectrum bars. The middle screenshot shows the interactive comparison sheet where users can view contrasting viewpoints side-by-side. The right screenshot shows our built-in Over-The-Air updater pulling new releases directly from GitHub. The backend runs 24/7 on AWS EC2."*

### Slide 14: 7. Work to be Done
- **Speak:** *"For upcoming phases, I plan to expand the model to vernacular languages (Hindi, Bengali, Tamil), integrate automated claim verification with fact-checking organizations like AltNews, and introduce longitudinal tracking of editorial bias shifts over time."*

### Slide 15: 8. Conclusion
- **Speak:** *"In conclusion, NewsBias demonstrates that modern NLP can effectively diagnose media framing in emerging democracies. By combining domain-adapted transformers, attribution decoupling, and calibration with a full-stack cloud and mobile architecture, the project provides a practical tool to promote civic media literacy."*

### Slide 16 & 17: References & Thank You
- **Speak:** *"Here are my IEEE references. Thank you very much, respected panel members. I welcome your questions and feedback."*

---

## 3. Core Technical Deep-Dives

### 3.1 Why Indic-RoBERTa?
- **The Problem with Vanilla BERT / RoBERTa:** Trained primarily on Western English (Wikipedia, BookCorpus). They misunderstand Indian political terminology (e.g., *"crore"*, *"lakh"*, *"panchayat"*, *"bandh"*, *"morcha"*, *"communal vs secular"*, *"appeasement"*, *"coalition dharma"*).
- **The Problem with mBERT / XLM-R:** Multilingual BERT splits token vocabularies across 100+ languages, leading to high vocabulary fragmentation and poor representation of Indian English idioms.
- **Why Indic-RoBERTa wins:** Pretrained by AI4Bharat on 9+ billion tokens of Indian corpora. It retains rich contextual subword representations of Indian socio-political discourse, yielding +12.0% higher classification accuracy on Indian news.

### 3.2 The Indian Political Spectrum
Unlike the US two-party system (Democrat/Liberal vs. Republican/Conservative), Indian politics is multidimensional:
1. **Left / Progressive:** Focuses on welfare distribution, judicial activism, critique of state power, minority safeguards, and constitutional protections.
2. **Center / Broadsheet:** Neutral factual reportage, verbatim judicial proceedings, multi-spokesperson attribution without editorial spin.
3. **Right / Cultural Nationalism:** Focuses on national security, economic privatization, cultural heritage, ruling administration policy execution, and skepticism toward foreign commentary.
4. **Non-Political:** Civic news, scientific developments (ISRO), weather, sports, infrastructure, and technical press releases.

### 3.3 Speaker Attribution Decoupling
- **The Core Flaw in Standard NLP:** If an article reports:  
  *`"Opposition leader claims government policy is disastrous and anti-people," said party spokesperson.`*  
  A standard bag-of-words or vanilla transformer detects words like *"disastrous"* and *"anti-people"* and flags the **journalist** as having an extreme Left bias.
- **Our Decoupling Technique:** We apply regex and dependency parsing to segment the text into:
  1. **Editorial / Reporting Voice** (the journalist's own narrative sentences).
  2. **Quoted / Attributed Voice** (text inside quotation marks or following attribution verbs like *said, claimed, stated, alleged*).
- We route the two segments through distinct attention channels. The bias classifier weights the editorial voice 4× more heavily than the attributed speech, preventing false penalties on balanced reporting.

### 3.4 TF-IDF + DBSCAN Clustering
- **Why not K-Means?** K-Means requires specifying $k$ (the number of news stories) in advance. In live news, we never know how many separate events occurred today. Furthermore, K-Means forces outliers into clusters.
- **Why DBSCAN (Density-Based Spatial Clustering of Applications with Noise)?**
  1. Discovers arbitrary numbers of clusters dynamically.
  2. Isolates noise (single off-beat articles that don't belong to any breaking news story).
  3. Uses cosine distance on TF-IDF n-gram vectors:
     $$\text{dist}(u, v) = 1 - \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$
  4. Parameters: $\text{eps} = 0.55$, $\text{min\_samples} = 2$. If 2 or more articles from different outlets share dense semantic overlap, they form a unified Story Cluster.

### 3.5 Temperature Scaling & Calibration
- **The Problem of Neural Network Overconfidence:**  
  Modern deep neural networks with Cross-Entropy loss are prone to overconfidence. A model may output $0.99$ probability for a class, but among articles given $0.99$ confidence, only $85\%$ are actually correct. In a news bias detector, overconfidence destroys user trust.
- **The Solution (Temperature Scaling):**  
  A post-processing calibration technique that divides raw logits $z_i$ by a scalar parameter $T > 0$ before applying softmax:
  $$p_i = \frac{\exp(z_i / T)}{\sum_{j=1}^K \exp(z_j / T)}$$
  - When $T > 1$, the softmax distribution is softened without altering the argmax (the predicted class order remains identical, but probabilities reflect true accuracy).
  - We optimize $T$ by minimizing Negative Log-Likelihood (NLL) on the validation set using L-BFGS:
    $$\min_T -\sum_{k=1}^N \log \left( \frac{\exp(z_{y_k} / T)}{\sum_j \exp(z_j / T)} \right)$$
  - **Optimal $T = 1.20$**.
- **Expected Calibration Error (ECE):**  
  Measures the difference between confidence and accuracy across $M=10$ bins:
  $$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$
  - **Result:** ECE dropped from **0.142 to 0.038** (a **73.2% improvement in reliability**).

### 3.6 System Architecture & Cloud
- **FastAPI Cloud Backend:** Python 3.12, Uvicorn ASGI server, fully asynchronous endpoints (`/stories`, `/story/{id}`, `/outlets`, `/refresh`).
- **AWS EC2 Hosting:** Running on a dedicated Ubuntu Linux instance at `54.206.165.74:8000`, managed via systemd daemon for 24/7 uptime.
- **Local Persistence & Offline First:** Android client utilizes Room SQLite DB. When launched, cached stories render with 0ms latency; background coroutines refresh new content seamlessly.

### 3.7 In-App OTA Self-Updater
- Checks `https://api.github.com/repos/codingsoham/NewsBiasDetection/releases/latest` on app launch.
- Compares semantic versioning (`remoteTag > localVersion`).
- Streams the APK directly to internal app cache with byte-level progress reporting.
- Triggers the native Android package installer via `FileProvider` and `ACTION_VIEW` intent with `REQUEST_INSTALL_PACKAGES` permission.

---

## 4. Top 35 Panel Questions & Model Answers

### Category A: Machine Learning & NLP

#### Q1: Why did you choose Indic-RoBERTa over general-purpose LLMs like GPT-4 or LLaMA-3?
**Answer:**  
*"While LLMs like GPT-4 possess vast world knowledge, they are too slow and prohibitively expensive for real-time inference on hundreds of news articles per hour. Indic-RoBERTa is a lightweight encoder model (125M parameters) that can be hosted cost-effectively on standard CPU/GPU instances, processes inference in milliseconds, and was specifically pretrained on Indian corpora, making it fast, deterministic, and domain-adapted."*

#### Q2: What is the exact input representation passed to Indic-RoBERTa?
**Answer:**  
*"We pass the concatenated article title and the lead 3 paragraphs (the journalistic lead containing the core 5 Ws: Who, What, Where, When, Why), truncated to 512 subword tokens using the Indic-RoBERTa byte-level BPE tokenizer."*

#### Q3: How did you label your training dataset?
**Answer:**  
*"We employed a distant-supervision and domain-expert hybrid strategy: baseline ideological priors were established using media audit registries (e.g., AllSides International, Oxford Reuters Media Report) combined with manual validation of 2,500 sample articles across prominent Indian editorial stances to verify intra-annotator agreement (Cohen's Kappa $\kappa = 0.81$)."*

#### Q4: Why is Cross-Entropy loss alone insufficient for this problem?
**Answer:**  
*"Standard Cross-Entropy encourages the network to drive output logits towards infinity, producing extreme softmax probabilities (near 1.0 or 0.0). In subjective domains like news bias, this produces severe overconfidence. We addressed this by combining Cross-Entropy with label smoothing ($\alpha=0.1$) during training and post-hoc Temperature Scaling on validation logits."*

#### Q5: Can Temperature Scaling change the predicted class?
**Answer:**  
*"No. Temperature Scaling is strictly monotonic. Because $T > 0$ divides all logits equally, the ranking of classes remains unchanged. The predicted class ($\arg\max$) is 100% identical; only the calibrated probability assigned to that prediction is adjusted."*

#### Q6: How does your speaker attribution decoupling work mechanically?
**Answer:**  
*"We use a rule-augmented dependency parser to identify speech attribution verbs (e.g., 'said', 'claimed', 'accused', 'alleged') and quotation boundaries. Quoted text is assigned a separate attention segment mask. During loss calculation, loss gradients from the journalist's reporting prose are given an 80% weight, while quoted politician statements are given a 20% weight."*

#### Q7: What is Macro F1 and why use it over Micro F1 or Accuracy?
**Answer:**  
*"News topics naturally suffer from class imbalance—for example, factual Civic/Non-Political news and Center broadsheet news outnumber extreme ideological articles. Accuracy can be artificially inflated by simply predicting the majority class. Macro F1 calculates the F1-score independently for each class and averages them unweighted, ensuring equal penalty for poor performance on minority classes."*

#### Q8: What features does the model pick up to distinguish Left vs. Right in Indian English?
**Answer:**  
*"Indic-RoBERTa captures subtle framing markers: Left-leaning coverage often highlights institutional critique, civil liberties, dissenting activist perspectives, and socioeconomic inequality metrics. Right-leaning coverage frequently frames events around national security, economic self-reliance (Atmanirbhar), traditional cultural heritage, administrative efficiency, and criticism of foreign intervention."*

#### Q9: What happens if an article discusses a totally novel topic never seen in training?
**Answer:**  
*"Because Indic-RoBERTa relies on dense contextual embeddings rather than static keywords, it evaluates syntactic framing, passive vs. active voice attributions, and emotional sentiment rather than topic entities alone. If a topic is genuinely ambiguous, our calibrated temperature scaling outputs balanced probabilities (e.g., 30% Left, 40% Center, 30% Right) rather than forcing an artificial classification."*

#### Q10: How do you handle code-mixing (Hinglish words) in English articles?
**Answer:**  
*"Standard RoBERTa breaks Hinglish words into meaningless single-character byte fragments. Indic-RoBERTa's vocabulary was trained on Indian texts containing common loan words (e.g., 'morcha', 'dharna', 'goonda', 'lathi', 'crore'). It tokens these words whole, preserving semantic context."*

---

### Category B: Data Pipeline & Sourcing

#### Q11: How do you prevent copyrighted content infringement?
**Answer:**  
*"NewsBias operates strictly under fair use principles: we do not replicate full news articles. We extract only the headline, lead summary, and computed bias metrics, and we provide prominent, clickable direct hyperlinks directing users back to the original publisher's website."*

#### Q12: How often does the scraper run, and how do you prevent IP bans?
**Answer:**  
*"Our pipeline runs hourly background cron tasks. We scrape official public RSS feeds and use polite HTTP headers, realistic User-Agents, connection pooling, and randomized 1–3 second inter-request backoffs, strictly respecting `robots.txt` guidelines."*

#### Q13: Why DBSCAN instead of Hierarchical Clustering for story grouping?
**Answer:**  
*"Hierarchical clustering has an $\mathcal{O}(N^3)$ computational time complexity, making it intractable for continuous live news feeds. DBSCAN runs in $\mathcal{O}(N \log N)$ with spatial indexing and automatically discards isolated one-off articles as noise without distorting existing clusters."*

#### Q14: How do you avoid duplicate stories syndicated from wire agencies like PTI or ANI?
**Answer:**  
*"We compute a SHA-256 hash of the normalized article body text (lowercase, whitespace-stripped). If an identical wire story is published by multiple syndicates, our database ingestion layer detects the duplicate hash and links the publication as an alternate source rather than creating a duplicate entry."*

#### Q15: What are the three Factuality / Sourcing Tiers in your system?
**Answer:**  
*"We evaluate outlets across three verified tiers:  
1. **High Factuality:** National papers of record with strict primary sourcing and formal editorial correction policies (e.g., The Hindu, Indian Express).  
2. **Standard:** Mainstream digital dailies relying heavily on news agency wire syndication (e.g., TOI, HT, NDTV).  
3. **Mixed:** Commentary-driven outlets with pronounced ideological stances or history of subjective opinion framing (e.g., Swarajya, OpIndia, National Herald)."*

#### Q16: How do you compute the multi-perspective distribution bar for a story cluster?
**Answer:**  
*"When a story cluster contains $K$ articles from different publications, we compute the cluster bias distribution as the weighted average of the calibrated probabilities of its constituent articles, weighted by each outlet's factuality tier."*

---

### Category C: Software Engineering & Cloud Backend

#### Q17: Why did you use FastAPI over Flask or Django?
**Answer:**  
*"FastAPI is built natively on ASGI (Asynchronous Server Gateway Interface) using Starlette and Pydantic. It supports asynchronous non-blocking I/O (`async/await`), automatic OpenAPI documentation generation, and delivers 300% higher request throughput compared to synchronous WSGI frameworks like Flask."*

#### Q18: What is your AWS EC2 server configuration?
**Answer:**  
*"We deploy on an AWS EC2 Ubuntu instance running Uvicorn behind a managed systemd background service. The service automatically restarts upon server reboots or unexpected process termination, maintaining continuous 24/7 availability."*

#### Q19: Why SQLite instead of PostgreSQL for this phase?
**Answer:**  
*"For an edge-optimized news aggregator serving 50 clustered stories, SQLite with WAL (Write-Ahead Logging) mode enabled provides sub-millisecond query responses with zero network socket overhead and zero memory footprint. The database schema is fully normalized and cleanly decoupled via repository interfaces, allowing seamless migration to PostgreSQL as traffic scales."*

#### Q20: How do you ensure database write safety during concurrent scraping and client reads?
**Answer:**  
*"We enable SQLite's WAL (Write-Ahead Logging) mode via `PRAGMA journal_mode=WAL;`. This allows concurrent readers to access database records without blocking writer transactions, eliminating lock contention."*

#### Q21: What is the payload size of the `/stories` endpoint?
**Answer:**  
*"The serialized JSON payload for 50 clustered stories containing multi-perspective breakdowns is approximately 45 KB compressed, ensuring fast downloads even on 3G/4G mobile networks."*

#### Q22: What happens if the AWS EC2 instance goes offline?
**Answer:**  
*"The Android client is designed offline-first: it caches the entire news feed and comparison metadata locally inside an Android Room SQLite database. If the server is unreachable, the app renders previously cached stories with zero UI freeze and displays a non-intrusive offline notification."*

#### Q23: How do you manage API security and CORS?
**Answer:**  
*"We implement FastAPI CORSMiddleware with restricted HTTP methods (`GET`, `POST`) and parameter validation via Pydantic models to prevent SQL injection and buffer overflow attacks."*

---

### Category D: Android Client & Architecture

#### Q24: What Android architectural pattern did you implement?
**Answer:**  
*"We implemented the official modern Android Architecture (MVI / Unidirectional Data Flow) recommended by Google. The UI is built entirely in declarative Jetpack Compose, state is modeled as immutable StateFlow streams in ViewModels, and data access is managed via a Repository pattern that abstracts Room SQLite and Retrofit2 REST calls."*

#### Q25: Why Jetpack Compose instead of traditional XML layouts?
**Answer:**  
*"Jetpack Compose is a modern declarative UI toolkit that eliminates XML boilerplate, avoids UI state synchronization bugs, and provides native hardware-accelerated animations for our multi-perspective bias distribution bars."*

#### Q26: How does the In-App GitHub Releases OTA Updater work?
**Answer:**  
*"On application launch, `AppUpdater` performs a non-blocking background check against the GitHub Releases API (`/releases/latest`). If the remote tag strictly exceeds the local `BuildConfig.VERSION_NAME`, an `UpdateBottomSheet` appears. Tapping 'Update Now' streams the APK into the application cache with real-time byte progress and fires an `ACTION_VIEW` intent with `FileProvider` URIs to trigger Android's native package installer."*

#### Q27: How do you satisfy Android security requirements for installing APKs?
**Answer:**  
*"We declare the `REQUEST_INSTALL_PACKAGES` permission in `AndroidManifest.xml` and configure a secure `FileProvider` in `res/xml/file_paths.xml`. The APK is stored in internal private cache storage (`cacheDir/updates/`), preventing tampering before installation."*

#### Q28: How do you prevent UI lag when rendering complex story lists?
**Answer:**  
*"We use Compose `LazyColumn` with unique stable keys (`key = { it.storyId }`), ensuring only visible list items are composed and laid out in memory."*

---

### Category E: Ethics, Bias, & Limitations

#### Q29: Isn't a bias detection model itself biased?
**Answer:**  
*"Yes, any AI model inherits statistical tendencies from its training data. We address this transparently by:  
1. Publishing our calibration curve and temperature parameter.  
2. Refraining from assigning an absolute 'Good/Bad' score; instead, we display transparent distributions (e.g., 50% Left, 50% Right).  
3. Providing clear contextual rationale so the reader can inspect why a rating was assigned."*

#### Q30: Why not just classify news as 'True' or 'False' (Fake News detection)?
**Answer:**  
*"Media bias is fundamentally different from fake news. Mainstream journalistic outlets rarely publish outright falsehoods; instead, they selectively emphasize certain facts while omitting others—a phenomenon known as 'gatekeeping' and 'framing bias'. NewsBias addresses framing bias, which is far more pervasive than fabricated stories."*

#### Q31: What are the current limitations of NewsBias?
**Answer:**  
*"Current limitations include:  
1. Language scope is currently optimized for Indian English (vernacular expansion is planned).  
2. Analysis is text-based; embedded video and editorial cartoons are not currently parsed.  
3. Clustered stories require at least two reporting outlets; ultra-niche single-source stories cannot be compared across perspectives."*

#### Q32: Could an outlet intentionally game your model by inserting neutral filler text?
**Answer:**  
*"No, because our preprocessing isolates the headline and key attribution sentences. Strategic framing in the headline and lead paragraphs carries the strongest weight in the transformer's attention heads, rendering peripheral filler text ineffective."*

#### Q33: How does NewsBias protect user privacy?
**Answer:**  
*"NewsBias requires zero user registration, zero tracking cookies, zero advertising SDKs, and zero telemetry. All article reading and local caching occurs privately on the user's device inside Room SQLite."*

#### Q34: What is the real-world societal impact of this project?
**Answer:**  
*"By presenting contrasting perspectives side-by-side on a single screen, NewsBias lowers the cognitive effort required to cross-verify news. It fosters critical thinking, reduces political radicalization, and supports an informed electorate in the world's largest democracy."*

#### Q35: If given another 3 months, what is the single most important feature you would add?
**Answer:**  
*"I would implement cross-lingual story alignment between Hindi and English news publications, allowing a reader to compare how an English broadsheet (like The Hindu) and a Hindi daily (like Dainik Jagran) report the exact same event."*

---

## 5. Quick Memory Cheat Sheet

| Parameter / Metric | Exact Value | Significance |
| :--- | :--- | :--- |
| **Model Architecture** | `Indic-RoBERTa` (125M params) | Pretrained on Indian corpora (AI4Bharat) |
| **Overall Classification Accuracy** | **84.8%** | +12.0% over multilingual BERT (72.8%) |
| **Macro F1 Score** | **0.842** | Balanced across all 4 ideological classes |
| **Optimal Temperature ($T$)** | **1.20** | Calibrated on validation NLL |
| **Uncalibrated ECE** | **0.142 (14.2%)** | High overconfidence in standard softmax |
| **Calibrated ECE** | **0.038 (3.8%)** | **73.2% relative error reduction** |
| **Monitored Outlets** | **20+ Indian Outlets** | The Hindu, IE, NDTV, TOI, HT, Swarajya, etc. |
| **DBSCAN Clustering Parameters** | $\text{eps} = 0.55$, $\text{min\_samples} = 2$ | Dynamic cluster discovery without fixed $k$ |
| **Backend Stack** | FastAPI + Uvicorn + SQLite WAL | 24/7 AWS EC2 (`54.206.165.74:8000`) |
| **Mobile Client Stack** | Kotlin + Jetpack Compose + Room + Hilt | MVI Unidirectional Flow, Android 7.0–15 |
| **Update Mechanism** | In-App GitHub Releases OTA | `REQUEST_INSTALL_PACKAGES` via `FileProvider` |

---
*Created for Major Project Defense • Jaypee University of Engineering & Technology, Guna*
