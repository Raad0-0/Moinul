# **PLAN.md — ScamShield BD (NSUCEC NeuraHack 2026 Preliminary)**

> READ THIS FILE FIRST before writing any code. It is the single source of truth for the task, the rules, and the project conventions. If a request conflicts with this file, follow this file and tell me.

---

## **1\. Goal**

Build ScamShield BD: a system that reads an SMS / chat message or a whole conversation (English, Bangla script, Banglish, or mixed) and predicts, per record:

| Output | Task | Meaning |
| ----- | ----- | ----- |
| `label` | A (primary) | One of 6 classes |
| `techniques` | B | Multi-label, codes T1..T6 joined by `|`, or `NONE` |
| `action` | C | Intended victim action, 0..5 |
| `confidence` | D | Probability (0..1) that `label` is correct. Must be calibrated |

Data: `data/sample.csv` (86 labeled rows: id,text,label,techniques,action), `data/test.csv` (500,000 rows: id,text), `data/sample_submission.csv`. Sample ids start at 10001, test ids at 20001\. All UTF-8.

All data is synthetic. Phone numbers are masked (`01XXXXXXXXX`), links are defanged (`hxxps://example[.]com`).

---

## **2\. Label definitions**

### **Task A: label**

| Label | Class | Description |
| ----- | ----- | ----- |
| 0 | Legitimate | Genuine transactional, informational, personal, or service message/conversation |
| 1 | MFS/OTP scam | Asks for PIN, OTP, password, NID, card details, credentials; or claims a mistaken transfer and asks for money back; or impersonates support to get account access |
| 2 | Prize/lottery scam | Fake winnings, gifts, cashback, rewards that need a deceptive action to claim (pay, click, share details) |
| 3 | Fake job/investment | Unrealistic income, upfront recruitment fee, task-based earning, money doubling, crypto/investment scheme, redirect into a deceptive earning scheme |
| 4 | Delivery/parcel phishing | Deceptive or unexpected parcel/customs/delivery-fee/address-confirmation/tracking-link request |
| 5 | Promotional spam | Unsolicited or spam-like marketing that is NOT fraudulent |

### **PRIORITY ORDER (when several classes apply, stop at first match)**

**1 → 2 → 4 → 3 → 5 → 0**

Priority examples:

* A prize message that asks for OTP/PIN/NID → class 1  
* A "gift" parcel that demands a customs payment → class 2  
* A job offer that asks for an OTP → class 1  
* A genuine OTP delivery message that says "do not share" → class 0  
* A message ABOUT a scam (friend warns about a phishing text and quotes it) → class 0

### **Task B: techniques (multi-label)**

| Code | Technique |
| ----- | ----- |
| T1 | Authority or organization impersonation (only when an organization/role is claimed: bank, MFS, courier, government, telecom, employer, ...). NOT for generic messages with no claimed sender |
| T2 | Credential, OTP, PIN, or sensitive-information harvesting |
| T3 | Advance-fee or payment deception |
| T4 | Prize, reward, lottery, or cashback baiting |
| T5 | Urgency, threat, pressure, trust-building, or other social-engineering manipulation |
| T6 | Task-based earning, fake job, investment, or financial manipulation |

### **Task C: action**

| Label | Intended action |
| ----- | ----- |
| 0 | No suspicious action / informational only |
| 1 | Share, enter, or disclose confidential info or credentials |
| 2 | Transfer money, pay a fee, or make a financial transaction |
| 3 | Click, open, or visit a link or website |
| 4 | Install an app, join a group, or complete a task |
| 5 | Contact, call, reply to, or communicate with the sender or another party |

When several things are asked, label the MOST CONSEQUENTIAL: explicit pay request \= 2; only open a link \= 3; hand over credentials \= 1 even if it arrives through a link.

### **Conventions (hard constraints used in post-processing)**

* Class 0 and 5 → `techniques = NONE`, `action = 0` (a link or code in a promo or legit message is NOT a suspicious action).  
* Class 1–4 → techniques must NOT be `NONE`, action must NOT be 0\.  
* Noise-only records (no meaningful content) → label 0, `NONE`, action 0\.  
* Keyword presence alone must never decide the label. Intent and behavior of the WHOLE message/conversation decide.

### **Illustrative examples**

| Text | Label | Reason |
| ----- | ----- | ----- |
| Apnar cash-out 500 taka successful. Balance 1,240 taka. | 0 | Genuine transaction notice |
| Your OTP is 482913\. Do not share it with anyone. | 0 | OTP delivery, not harvesting |
| Ami agent, bhul number-e taka pathaisi. Ferot din, PIN ta bolen. | 1 | Mistaken transfer \+ credential request |
| Apni 5 lakh taka jitechen. Claim korte link e click korun. | 2 | Unearned reward with required action |
| Ghor bose din e 3000 taka income. WhatsApp e join korun. | 3 | Deceptive income lure |
| Parcel atke ase. Delivery fee dite link e jan. | 4 | Unexpected fee/link request |
| Your order \#4471 is out for delivery today. | 0 | Genuine delivery update |
| Eid offer\! Sob item e 30% discount. | 5 | Ordinary promotion |

Sample rows (from sample.csv) for reference of technique/action style:

* `SA Paribahan: Parcel SP2271 held at Kamalapur. Pay Tk 45 storage fee: hxxps://sap-fee[.]top` → 4, `T1|T3`, 2  
* `bKash Helpline: Apnar account e unusual login detect hoyeche. Block theke bachte 6 digit code ta ei ...` → 1, `T1|T2|T5`, 1  
* `You won cashback. Click to claim within 1 hour.` → 2, `T4|T5`, 3  
* `Part-time job: like YouTube videos, earn Tk 500 per task. Join Telegram: ...` → 3, `T6`, 4

---

## **3\. Text format**

* A record is a single message OR a conversation of up to 12 messages separated by `|||` in chronological order.  
* Speaker markers appear in several styles: `S:` / `R:`, `A:` / `B:`, `[Sender]` / `[You]`, `Caller:` / `You:`, `[Group] Name:`. Markers are not always present and their meaning differs between records.  
* Classify the conversation AS A WHOLE. Intent may appear late (trust-building, chatter, delayed request, multiple senders, strategy shift). Never rely on the last message alone.  
* Longer formal records exist too: emails, call transcripts, group chats, notices.  
* Adversarial distortions in a hidden subset: character insertion/deletion/substitution/repetition, missing or irregular spaces, random capitalization, emojis, Unicode lookalikes (Cyrillic that looks Latin), zero-width characters, deliberate misspelling of sensitive words, random noise strings (e.g. `wkrjfejejrn`) inside real text, and noise-only records.

---

## **4\. Evaluation**

```
S = 0.40*F_A + 0.15*F_B + 0.10*F_C + 0.10*F_domain + 0.10*F_robust + 0.05*Calibration + 0.10*F_novel
```

* F\_A: macro F1 over the 6 classes. F\_B: macro F1 over T1..T6 across all rows. F\_C: macro F1 over the 6 actions.  
* F\_domain / F\_robust / F\_novel: Task A macro F1 on HIDDEN subsets (domain shift: different register/length/channel; corrupted text; novel scenarios/brands/sender identities/tactic combinations).  
* Calibration \= 1 − Brier score of `confidence` vs. whether label was correct.  
* Macro F1 means rare classes matter as much as common ones. The test class distribution is undisclosed and differs from the sample.  
* The test set was written to reduce overlap with sample.csv, so a random split of sample.csv does NOT estimate generalization.  
* Public leaderboard is a partial progress indicator only. Do not overfit to it.  
* Limit: 10 submissions per team per day.

### **Submission format (strict)**

```
id,label,techniques,action,confidence
20001,1,T1|T2,1,0.94
20002,0,NONE,0,0.98
```

1. Every test id exactly once, ids unchanged, same order as test.csv.  
2. `label` int 0..5. `action` int 0..5.  
3. `techniques`: codes T1..T6 separated by `|`, or `NONE`. Never empty.  
4. `confidence`: float in \[0, 1\].  
5. No other columns, no blanks, no invalid codes. Invalid files are rejected.

---

## **5\. HARD RULES (violations can disqualify the team)**

### **Forbidden**

1. **Never use test.csv text for training or fitting in ANY form**: no pseudo-labeling, self-training, label propagation, clustering-based labeling, domain adaptation on test, and also NO fitting of `TfidfVectorizer`, tokenizers, scalers, vocabularies, thresholds, or calibrators on test text. test.csv is read ONLY at inference time via `transform`/`predict`.  
2. No hand-labeling test records. No copying test text or test predictions into training data.  
3. No private exchange of code/data/predictions/API keys with other teams.  
4. No undeclared datasets, models, APIs, or resources.  
5. Multiple Kaggle accounts are forbidden.

### **Allowed (must be declared)**

* Open-source pretrained models and embeddings (check license).  
* Hosted LLMs/inference APIs, only if called PROGRAMMATICALLY from the notebook and disclosed (purpose, provider, model, expected cost).  
* Public external datasets, fine-tuning, ensembling, augmentation.  
* Creating extra training examples (writing templates, augmenting sample.csv, generating with a model) as long as the process is reproducible from the notebook and contains no test text.

### **API keys**

* Never hardcode keys. Read from `.env` only (`python-dotenv`). Never commit or print keys.  
* If no API is used, `.env` must still exist and be empty.

### **Anything generated must be reproducible**

* All synthetic data must be produced by code in the notebook (fixed seeds). Do NOT paste hand-generated data from an IDE chat into data files without the generating code being in the notebook. If an LLM is used to generate data, do it through a programmatic call in the notebook and save the output with the exact prompt.

---

## **6\. Final package (due 27 Nov 2026, 10:00 PM BST)**

ZIP named `NeuraHack_Preli_<Team_Name>.zip` containing EXACTLY four items:

| Item | Content |
| ----- | ----- |
| `submission.csv` | Must match one of the two selected Kaggle submissions |
| `notebook.ipynb` | Reproducible end-to-end notebook that generates the predictions, INCLUDING the code that creates/augments training data, plus a declaration of every external dataset, model, API, and resource |
| `README.md` | Team name, short approach summary, external models/datasets/resources, random seeds, run instructions |
| `.env` | Every API key used; empty file if none |

Notebook/README must declare: (1) libraries \+ versions, (2) external datasets/models/APIs with license/provider, (3) methodology, preprocessing, training, inference, validation strategy, (4) seeds \+ reproduction steps, (5) API-dependent steps, expected cost, model versions.

Reviewers also look at: validation without leakage, class confusion analysis, language variation, hard legitimate cases, unseen scenarios, robustness, and justification of model choices. Organizers may re-run the notebook in a clean environment. Latency (average and P95 per record, throughput) may be checked separately.

---

## **7\. Project structure**

```
scamshield/
├── PLAN.md
├── data/                 sample.csv, test.csv, sample_submission.csv
├── src/
│   ├── normalize.py      text cleaning + is_noise_only()
│   ├── gen_templates.py  synthetic data (templates, hard negatives, conversations, domain-shift formats)
│   ├── augment.py        noise/corruption augmentation
│   ├── split.py          group-based validation split + per-subset metrics
│   ├── train_baseline.py char TF-IDF + linear models
│   ├── train_transformer.py multi-task multilingual encoder
│   ├── postprocess.py    consistency rules, thresholds
│   ├── calibrate.py      temperature scaling
│   └── predict.py        500k-row inference + submission checks
├── notebook.ipynb        final deliverable (assembles everything)
├── README.md
├── .env
└── requirements.txt
```

---

## **8\. Pipeline**

```
raw text → normalize → model(s) → postprocess rules → calibrated confidence → submission.csv
```

### **8.1 normalize.py**

* Unicode NFKC; remove zero-width chars (U+200B, U+200C, U+200D, U+FEFF).  
* Map Cyrillic/Greek lookalikes to Latin.  
* Collapse repeated chars (3+ → 2\) and repeated/odd spaces; lowercase.  
* Replace defanged URLs (`hxxp`, `[.]`) with `<URL>`, masked phones with `<PHONE>`.  
* Remove emojis. Remove gibberish tokens (long, vowel-less or low-probability strings).  
* Do NOT damage Bangla script.  
* `is_noise_only(text)` → True if no meaningful content remains.  
* Keep the `|||` delimiter and speaker markers available (they carry structure).

### **8.2 Synthetic data (most important lever)**

* Template scenarios per class (15+ each) with slots `{brand} {amount} {link} {phone} {time} {name}`.  
* Languages: English, Bangla script, Banglish, mixed.  
* Brands/identities: bKash, Nagad, Rocket, Upay, GP, Robi, Banglalink, Daraz, Pathao, Steadfast, SA Paribahan, Bdjobs, banks, government offices, telecom support, relatives/friends.  
* **Hard negatives (class 0/5)**: genuine OTP with "do not share"; real transaction/bill/delivery notices; friend warning about a scam while quoting it; promos with links/codes; real offers with no deceptive action.  
* **Multi-turn conversations**: 2–12 messages joined by `|||`, varied speaker-marker styles (including none), scams that start innocent and reveal the ask in message 3–8, legit conversations that look suspicious midway. Label the whole conversation using the priority order.  
* **Domain-shift formats**: formal emails, call transcripts, group chats, long notices.  
* Every synthetic row carries `scenario_id` and `group` (brand/sender) for grouped validation.  
* Targets: \~200+ per class before augmentation; keep class balance but also include realistic skew variants.

### **8.3 augment.py**

Seeded `corrupt(text, level)` applying a random mix of: char insert/delete/substitute/repeat, missing/extra spaces, random capitalization, emoji insertion, Cyrillic lookalike swaps, zero-width chars, deliberate misspelling of sensitive words (OTP, PIN, bKash, parcel, link), embedded noise strings. Add noise-only samples as 0/NONE/0. Apply to \~25% of training data.

### **8.4 Validation (no leakage)**

* NEVER use a random split. Use group split by `scenario_id`/brand/sender; hold out \~20% of groups entirely.  
* Report separately on: clean, corrupted, long/formal, novel-scenario subsets.  
* The 86 original sample rows are used only as a final sanity check, not for tuning.  
* Report macro F1 for label, techniques (macro over T1..T6), action; also confusion matrix for Task A.

### **8.5 Models**

* **Baseline**: char n-gram TF-IDF (`char_wb`, 2–5) \+ LogisticRegression (label, action) \+ OneVsRest LR (techniques). Fit on training data ONLY.  
* **Main**: multi-task multilingual encoder (`xlm-roberta-base` or `mdeberta-v3-base`) with three heads: label (6-way softmax), techniques (6 sigmoid), action (6-way softmax). Loss \= 1.0·label \+ 0.5·techniques \+ 0.5·action, class-weighted. max\_length 256, fp16, lr 2e-5, 3–4 epochs, fixed seed.  
* Conversations: feed the whole conversation (keep `|||`). If too long, keep head \+ tail or pool message-level encodings. Never use only the last message.  
* Final prediction: ensemble (weights tuned on the group-held-out validation set).

### **8.6 postprocess.py**

* Label 0 or 5 → `NONE` and action 0\.  
* Label 1–4 → non-empty techniques, action ≠ 0\.  
* T1 only if an organization/role is claimed.  
* If credential request (OTP/PIN/NID/password/card) is detected → label 1 (priority rule).  
* Typical links: label 1 → T2; label 2 → T4; label 3 → T6; label 4 → T1 (+T3/T5).  
* Per-technique thresholds tuned on validation (grid 0.2–0.7). Thresholds are tuned on validation only.  
* `is_noise_only` → 0/NONE/0.

### **8.7 calibrate.py**

* Temperature scaling (or isotonic) fit on validation logits only.  
* confidence \= calibrated max probability for the predicted label.  
* Cap or reduce confidence for very short, heavily corrupted, or hard-negative-like inputs. Avoid 0.99+ unless truly certain. Report Brier score before/after.

### **8.8 predict.py (500,000 rows)**

* Normalize, dedupe identical texts and predict once, sort by length, dynamic-padding batches (\~128), fp16.  
* Measure speed on 10k rows first and extrapolate before the full run. Checkpoint partial outputs.  
* Final validation of submission: all ids exactly once, labels 0..5, valid technique codes, no empty techniques, confidence in \[0,1\], class 0/5 consistency.

---

## **9\. Coding conventions (for the code assistant)**

* Python 3.10+. Allowed libs: pandas, numpy, scikit-learn, torch, transformers, datasets, python-dotenv, tqdm, regex, emoji (declare versions in `requirements.txt`).  
* Set seeds everywhere (`random`, `numpy`, `torch`) with one global `SEED = 42`.  
* One file / one function at a time. Small, testable functions with docstrings and a quick self-test at the bottom.  
* Never read `test.csv` in any training/fitting step. Add an explicit comment `# TEST DATA: inference only` wherever it is loaded.  
* Never hardcode API keys. Never print secrets.  
* Keep everything runnable end-to-end from `notebook.ipynb` in a clean environment (no reliance on local paths or manual steps).  
* Keep memory in mind for 500k rows (chunked processing, no giant Python lists of tensors).  
* Log metrics to console and save validation outputs to `outputs/`.

---

## **10\. Timeline (BST, 27 Nov 2026\)**

| Deadline | Event |
| ----- | ----- |
| 6:00 PM | Preliminary ends (last Kaggle submission) |
| 10:00 PM | Final ZIP package due |

Work order if time is short (fast track): normalize → template data \+ hard negatives \+ conversations \+ augmentation → char TF-IDF \+ LR baseline with group validation → postprocess \+ thresholds → calibration → full predict → notebook/README/ZIP. Submit a baseline EARLY to catch format errors; then iterate within the 10/day limit.

---

## **11\. Pre-submission checklist**

* \[ \] No test text used for any fit/training (check every `.fit(` call)  
* \[ \] All seeds fixed; notebook re-runs end-to-end in a clean environment  
* \[ \] All external models/datasets/APIs declared (provider \+ license \+ version) in notebook AND README  
* \[ \] `.env` present (empty if no keys), no keys hardcoded anywhere  
* \[ \] `submission.csv` passes format checks and matches one of the two selected Kaggle submissions  
* \[ \] ZIP name `NeuraHack_Preli_<Team_Name>.zip` with exactly: `submission.csv`, `notebook.ipynb`, `README.md`, `.env`

