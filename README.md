# Blockchain-Integrated Multimodal Biometric Electronic Voting System
### Final-Year BTech Data Science Capstone Project

---

## 📌 Project Overview
The **Blockchain-Integrated Multimodal Biometric Electronic Voting System** is a next-generation decentralized electronic voting web application designed to solve critical challenges in modern electoral governance: **voter impersonation, duplicate voting, unauthorized ballot tampering, and lack of verifiable auditability**.

By combining **OpenCV-based Multimodal Biometrics (Fingerprint + Facial Recognition)** with **ECDSA Digital Signatures**, **SHA-256 Cryptographic Hashing**, and an **Autonomous Proof-of-Work Blockchain**, this system ensures that:
1. Only verified, eligible human citizens can authenticate.
2. Every citizen can vote exactly once.
3. Voter identities and ballot choices are logically and cryptographically decoupled.
4. Any retroactive modification to past voting records is immediately and mathematically detected.
5. Election results are audited independently from raw on-chain blocks.

---

## 🏗️ Technology Stack

| Domain | Technology / Library | Role in System |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3 | Responsive modern UI with dark blue & white theme, live camera canvas capture, candidate ballot cards, and interactive blockchain link visualizer. |
| **Visual Analytics** | Chart.js 4.4 | Real-time candidate distribution bar charts and percentage donut charts. |
| **Backend** | Python 3.14, Flask, Werkzeug | MVC routing, session management, RESTful endpoints, cryptographic coordination. |
| **Database** | SQLite 3 | Relational persistence for voter registration, candidate rosters, election state, and system audit logs. |
| **Computer Vision (AI)** | OpenCV 4 (`cv2`), NumPy | Haar Cascade frontal face detection, CLAHE contrast enhancement, Bilateral filtering, ORB minutiae extraction, and Spatial LBP embeddings. |
| **Security & Signatures** | `cryptography` (SECP256K1), `hashlib` | ECDSA asymmetric keypair generation, transaction digital signing, SHA-256 canonical hashing, and template hashing. |
| **Blockchain** | Python Custom PoW Blockchain Engine | Genesis block generation, Proof-of-Work mining, SHA-256 block linkage, tamper detection, and Ethereum EVM compatibility interface. |

---

## 📁 System Folder Structure
```
Blockchain_Voting_System/
│
├── app.py                          # Main Flask application entry point with all routes
├── config.py                       # System configurations, thresholds, and paths
├── requirements.txt                # Python package dependencies
├── database.py                     # SQLite initialization, schema, and queries
├── blockchain.py                   # Blockchain core engine, Block class, PoW, and tamper test
├── hashing.py                      # SHA-256 canonical transaction and template hashing
├── signatures.py                   # ECDSA SECP256K1 key generation, signing, and verification
├── authentication.py               # Multimodal biometric fusion and eligibility engine
├── fingerprint.py                  # OpenCV fingerprint enhancement, minutiae, and ORB matching
├── face_recognition_module.py      # OpenCV Haar cascade face detection and LBP embeddings
├── voting.py                       # Cryptographic vote casting and blockchain block sealing
├── results.py                      # Vote tallying, on-chain cross-audit, and Chart.js datasets
│
├── database/
│   └── voting.db                   # SQLite database (auto-initialized on startup)
│
├── templates/
│   ├── base.html                   # Master layout template (navbar, alerts, footer)
│   ├── index.html                  # Public home landing page and workflow summary
│   ├── admin_login.html            # Election authority administrator login
│   ├── dashboard.html              # Admin dashboard for candidates, voters, and controls
│   ├── register.html               # Voter registration portal with eligibility checks
│   ├── fingerprint.html            # Fingerprint capture (webcam/upload/demo simulation)
│   ├── face.html                   # Facial capture (webcam/upload/demo simulation)
│   ├── authenticate.html           # Multimodal dual-biometric authentication page
│   ├── eligibility.html            # Voter eligibility verification search engine
│   ├── voting.html                 # Official candidate selection electronic ballot
│   ├── confirmation.html           # Ballot confirmation and cryptographic vote receipt
│   ├── blockchain.html             # Public decentralized blockchain explorer & tamper test
│   ├── results.html                # Certified election results with charts & winner banner
│   └── about.html                  # Project architecture, math models, and Web3 roadmap
│
├── static/
│   ├── css/
│   │   └── style.css               # Professional dark blue & white theme stylesheet
│   ├── js/
│   │   └── script.js               # Client-side webcam capture and UX interactivity
│   └── images/                     # Static graphical assets
│
├── uploads/
│   ├── fingerprints/               # Protected numpy biometric templates (.npy)
│   └── faces/                      # Protected numpy facial embeddings (.npy)
│
└── tests/
    ├── test_hashing.py             # Unit tests for SHA-256, avalanche effect, and hashing
    ├── test_blockchain.py          # Unit tests for block linkage, mining, and tamper detection
    ├── test_voting.py              # Unit tests for eligibility, duplicate votes, and ECDSA
    └── test_e2e_workflow.py        # End-to-end integration tests for all 17 workflow steps
```

---

## 🔄 17-Step Systematic Project Workflow

```
[1] START
  │
[2] Voter Registration ──> Validate Age >= 18 ──> Generate ECDSA SECP256K1 Keypair
  │
[3] Fingerprint Enrollment ──> OpenCV CLAHE + Bilateral Filter ──> ORB Minutiae Extraction
  │
[4] Face Enrollment ──> OpenCV Haar Cascade Detection ──> Spatial LBP Embedding Vector
  │
[5] Multimodal Biometric Authentication (Voter presents ID, Print, and Face)
  │
[6] Authentication Decision:
      ├─ Fingerprint Score < Threshold OR Face Similarity < 0.65 ──> [REJECT VOTER]
      └─ BOTH Biometrics Pass ──> Continue
  │
[7] Eligibility Check (Registered? Age >= 18? Approved Flag?)
  │
[8] Already Voted Check?
      ├─ has_voted == 1 ──> [REJECT DUPLICATE VOTE ATTEMPT]
      └─ has_voted == 0 ──> Issue Temporary Secure Session
  │
[9] Cast Vote (Voter selects candidate on official ballot screen)
  │
[10] Generate SHA-256 Hash & Decoupled Anonymized Token H(voter_id + salt)
  │
[11] Digitally Sign Vote Payload with Voter's ECDSA Private Key
  │
[12] Record on Blockchain (Mine Block with Proof-of-Work & Link Previous Hash)
  │
[13] Update Database (Atomically set has_voted = 1 and increment candidate tally)
  │
[14] Election Closes (Admin triggers official closure from dashboard)
  │
[15] Count Votes (Independent on-chain block tally cross-audited against database)
  │
[16] Display Final Results (Chart.js Bar/Pie charts and Winner declaration)
  │
[17] END
```

---

## 🔐 Cryptographic Specifications & Privacy Architecture

### 1. Ballot Secrecy & Decoupled Voter Identity
In traditional databases, storing `voter_id` directly next to `candidate_id` destroys ballot secrecy. In this system:
* The voter's personal identity (name, email, age, biometrics) remains strictly inside the local SQLite database.
* The blockchain block payload records **only**:
  $$\text{VoterAuthHash} = \text{SHA256}(\text{VoterID} + \text{SECRET\_SALT})$$
* This hash is computationally non-invertible (pre-image resistant). It allows verifying that an authorized voter cast the ballot without revealing **which voter** cast it.

### 2. ECDSA Digital Signatures (SECP256K1)
* Each voter receives a unique 256-bit elliptic curve keypair generated over `SECP256K1` (the same curve powering Ethereum and Bitcoin).
* Before broadcasting a vote transaction, the client transaction payload is digitally signed:
  $$\sigma = \text{ECDSA\_Sign}_{K_{priv}}(\text{SHA256}(\text{CandidateID} \parallel \text{Timestamp} \parallel \text{VoterAuthHash}))$$
* The blockchain verifies $\sigma$ using $K_{pub}$ before mining the block. This prevents ballot stuffing, impersonation, and repudiation.

### 3. Proof-of-Work (PoW) & Tamper Detection
* Each block contains:
  * `index`: Block sequence number.
  * `timestamp`: Exact time of mining.
  * `transactions`: List containing vote payloads, anonymized authorization hash, and ECDSA signature.
  * `previous_hash`: 64-character SHA-256 hash of previous block.
  * `transaction_hash`: SHA-256 hash of all transactions inside this block.
  * `nonce`: Iterative counter solved to meet the target difficulty (leading zeros).
  * `current_hash`: Current sealed block hash.
* If an attacker alters a single character inside a past block:
  1. The transaction hash changes immediately.
  2. The block header hash changes immediately.
  3. The next block's `previous_hash` points to an invalid link.
  4. The validation algorithm flags `Data Tampering Detected in Block #X` in real-time.

---

## 👁️ Multimodal Biometric Computer Vision Pipeline

### Module 3: Fingerprint Minutiae Matching
1. **Preprocessing**: Grayscale conversion, CLAHE contrast enhancement, Gaussian bilateral edge-preserving smoothing.
2. **Segmentation**: Otsu adaptive thresholding for ridge skeletonization.
3. **Feature Extraction**: ORB (Oriented FAST and Rotated BRIEF) detector extracting 500 keypoints and descriptor matrices.
4. **Template Storage**: Descriptor matrices are saved as numpy templates (`.npy`) and protected with a SHA-256 cryptographic hash.
5. **Matching**: Brute-Force Matcher with Hamming distance + Lowe's ratio test. Verification requires:
   $$\text{Minutiae Matches} \ge 12 \quad \text{OR} \quad \text{Match Score} \ge 0.55$$

### Module 4: Facial Landmark & Embedding Matching
1. **Detection**: OpenCV Frontal Face Haar Cascade (`haarcascade_frontalface_default.xml`).
2. **Geometric Normalization**: Automatic face cropping with bounding margin, standardized to $128 \times 128$ pixels with histogram equalization.
3. **Feature Embedding**: Spatial Local Binary Pattern (LBP) texture analysis across a $4 \times 4$ spatial grid, generating a unit $L_2$-normalized feature vector.
4. **Matching**: Cosine similarity against enrolled face embedding:
   $$\text{Cosine Similarity} = \mathbf{u} \cdot \mathbf{v} \ge 0.65 \quad (65\% \text{ confidence})$$

---

## 🚀 Setup & Execution Guide (Windows / VS Code)

### Prerequisites
* Windows 10 or 11
* Python 3.10 to 3.14 installed with `pip`
* Visual Studio Code (or any terminal)

### Step 1: Open the Project Directory
Open your terminal or VS Code in:
```powershell
cd C:\Users\monas\OneDrive\Documents\blockchain
```

### Step 2: Install Required Dependencies
All dependencies are standard, pre-compiled wheels available on PyPI:
```powershell
pip install -r Blockchain_Voting_System/requirements.txt
```
*(Dependencies: `Flask`, `Werkzeug`, `opencv-python`, `numpy`, `cryptography`)*

### Step 3: Run the Complete Test Suite
Verify that all 21 unit tests and end-to-end integration tests pass:
```powershell
python -m unittest discover -s Blockchain_Voting_System/tests -p "test_*.py"
```
**Expected Output:**
```
Ran 21 tests in 1.016s
OK
```

### Step 4: Launch the Web Application
Execute the root launcher:
```powershell
python run.py
```
*(Or run `python Blockchain_Voting_System/app.py`)*

The terminal will display:
```
===========================================================================
  BLOCKCHAIN-INTEGRATED MULTIMODAL BIOMETRIC ELECTRONIC VOTING SYSTEM  
  Final-Year BTech Data Science Capstone Project                       
===========================================================================
  Server URL : http://127.0.0.1:5000
  Admin User : admin
  Admin Pass : Admin@2026!
  Mode       : DEMO MODE (Simulation Active)
===========================================================================
 * Running on http://127.0.0.1:5000
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🧪 Pre-Seeded Accounts & Demonstration Walkthrough

### 1. Default Administrator Credentials
* **Login URL**: `http://127.0.0.1:5000/admin/login`
* **Username**: `admin`
* **Password**: `Admin@2026!`
* **Capabilities**: Open/Close election, view full voter registry, add new candidates, inspect system audit logs, and test real-time blockchain tampering.

### 2. Pre-Seeded Voters for Immediate Testing
| Voter ID | Full Name | Age | Status | Biometrics Enrolled | Purpose |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `VOTER-1001` | Aarav Patel | 24 | Eligible | Yes | Complete standard voting walkthrough |
| `VOTER-1002` | Diya Roy | 28 | Eligible | Yes | Second voter for multi-candidate testing |
| `VOTER-1003` | Rohan Gupta | 22 | Eligible | Yes | Third voter for turnout & results |
| `VOTER-1004` | Ananya Verma | 17 | **Ineligible** | Yes | **Negative test case: Underage rejection** |

### 3. Biometric Operating Modes (Demo vs Live Hardware)
* **Demo Simulation Mode (Default)**:
  * Allows thorough testing without requiring a physical fingerprint scanner or webcam.
  * Generates high-contrast mathematical sinusoidal fingerprint ridges and synthetic facial embeddings deterministically linked to the voter ID.
  * Clicking "Authenticate" or "Enroll" runs the real OpenCV algorithms on these synthetic biometric images.
* **Live Hardware Mode**:
  * Users can click the **`Mode: DEMO / LIVE HW`** pill in the top navigation bar at any time to switch.
  * Activates real browser webcam stream via `getUserMedia` for live facial capture and photo upload for fingerprints.

### 4. How to Demonstrate Real-Time Tamper-Evidence
1. Navigate to `http://127.0.0.1:5000/blockchain`.
2. Observe that the Genesis Block and all subsequent blocks are displayed with green badges and **"100% SECURE & VERIFIED"**.
3. Under the **Academic Tamper-Evidence Demonstration** panel, click **"Tamper Block #1 (Demo)"** (requires admin login).
4. This artificially modifies the candidate recorded inside Block #1 without updating subsequent cryptographic hashes.
5. Click **"Validate Blockchain Integrity"**.
6. The system immediately turns **CRIMSON RED** and displays:
   > ⚠️ **SECURITY ALERT: Data Tampering Detected in Block #1! Transaction payload does not match transaction_hash.**
7. Click **"Restore Block #1"** to reset the ledger back to its verified state.

---

## 📊 Evaluation & Viva Checklist
* [x] **Complete Working Code**: Every file generated with zero TODOs or empty stubs.
* [x] **Relational Persistence**: SQLite automatically initializes tables and seed data.
* [x] **OpenCV Computer Vision**: Haar Cascade face detection, CLAHE, and ORB minutiae extraction.
* [x] **Multimodal Fusion**: Dual-biometric AND-gate logic enforced.
* [x] **Ballot Secrecy**: Voter identity decoupled from candidate choice using hashed tokens.
* [x] **Non-Repudiation**: ECDSA SECP256K1 digital signatures on vote transactions.
* [x] **Decentralized Ledger**: Custom Proof-of-Work blockchain with previous hash linking.
* [x] **Tamper Detection**: Real-time detection and visual notification of corrupted blocks.
* [x] **Double-Vote Prevention**: Rejection of duplicate voting attempts across both database and consensus layers.
* [x] **Visual Analytics**: Interactive Chart.js bar and donut charts for election outcome.
* [x] **Unit & Integration Tests**: 24 passing automated tests covering all modules and Vercel serverless entrypoint.

---

## ☁️ Vercel Cloud Deployment Guide

This project is configured for deployment to **Vercel** serverless cloud infrastructure.

### Files Configured for Vercel
1. **`vercel.json`**: Configures Vercel Python runtime (`@vercel/python`) and routes static assets directly to CDN.
2. **`api/index.py`**: The serverless WSGI entry point exposing the Flask `app` object.
3. **`requirements.txt`**: Specifies `opencv-python-headless>=4.8.0` so Vercel's Amazon Linux containers install without requiring X11/OpenGL desktop GUI libraries (`libGL.so.1`).
4. **`config.py`**: Automatically detects serverless runtime (`VERCEL=1`) and routes SQLite writes and uploads safely to `/tmp`.
5. **`.gitignore`**: Excludes local `venv/`, compiled bytecode, and `.env` from Git commits.

### Step-by-Step Vercel Deployment Instructions
1. **Push to GitHub**:
   Initialize git and push the repository to your GitHub account:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Vercel deployment"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
2. **Import into Vercel**:
   * Go to [vercel.com](https://vercel.com) and log in.
   * Click **"Add New..."** $\rightarrow$ **"Project"**.
   * Select your GitHub repository.
3. **Configure Environment Variables in Vercel Dashboard**:
   Under **Project Settings** $\rightarrow$ **Environment Variables**, optionally set:
   * `SECRET_KEY`: A strong random string.
   * `DEMO_MODE`: `True` *(essential for cloud evaluation without physical USB hardware)*.
   * `DEFAULT_ADMIN_USER`: `admin`
   * `DEFAULT_ADMIN_PASS`: `Admin@2026!`
4. **Deploy**:
   * Click **"Deploy"**. Vercel will build the serverless functions and serve your application live!

### ⚠️ Cloud vs. Local Academic Prototype Constraints
* **Physical USB Fingerprint Scanners**: Cannot communicate across cloud boundaries to serverless containers without special local client software. The application's **Demo Biometric Mode** and **Webcam / File Upload Mode** provide the working academic evaluation solution.
* **Persistent Storage**: Vercel serverless lambda filesystem is read-only except `/tmp`. Data written to SQLite in `/tmp` is ephemeral and resets during cold starts. For persistent enterprise production, the architecture seamlessly supports external cloud databases (e.g., Neon Postgres, Supabase) and public Ethereum/Polygon smart contracts.
