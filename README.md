# 🏛️ LMPC Compliance Engine (SIH26034)
**Automated Verification of Mandatory Declarations on Pre-packaged Commodities under the Legal Metrology (Packaged Commodities) Rules, 2011**

Developed for **Smart India Hackathon (SIH)** — Ministry of Consumer Affairs, Food & Public Distribution (Department of Consumer Affairs).

---

## 📌 Project Overview
The **LMPC Compliance Engine** is an AI-powered automated regulatory auditor and multi-agent system designed to inspect product packaging images and e-commerce product listings for mandatory declarations under the Legal Metrology Act, 2009 and LMPC Rules, 2011.

### 🌟 Key Features
- **Multimodal Vision & OCR Pipeline**: Principal Display Panel (PDP) segmentation, font height verification in mm, contrast analysis, and text extraction.
- **LMPC Regulatory Rule Engine**: Automated validation of 10 mandatory declarations (Manufacturer, Country of Origin, MRP, Net Quantity in standard units, Unit Sale Price, Expiry/Best Before, Consumer Care, etc.).
- **E-Commerce Listing Cross-Auditor**: Scrapes and cross-verifies textual product specifications against actual physical package images.
- **Modern Interactive Dashboard**: Real-time auditing UI with dark glassmorphism, instant infraction reports, and compliance scores.
- **Multi-Database Support**: Out-of-the-box SQLite local development and cloud PostgreSQL (Neon / Supabase / Railway).

---

## 🚀 Getting Started for Team Members

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & `npm`
- **Git**

---

### 2. Clone the Repository
```bash
git clone https://github.com/himanshushukla0/SIH26034.git
cd SIH26034
```

---

### 3. Backend Setup (FastAPI)

1. Navigate to the project root and create a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

2. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment Variables:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Open `.env` and add your `GOOGLE_API_KEY` (Gemini API key).

4. Run the Backend Server:
   ```bash
   uvicorn backend.app:app --reload --port 8000
   ```
   API Docs will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 4. Frontend Setup (React + Vite + TypeScript)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open the frontend in your browser at: [http://localhost:5173](http://localhost:5173)

---

### 5. Running with Docker Compose (Optional)
```bash
docker-compose up --build
```

---

## 👥 Collaboration & Git Workflow

1. Always pull latest changes before starting:
   ```bash
   git pull origin main
   ```
2. Create a feature branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit and push your changes:
   ```bash
   git add .
   git commit -m "feat: description of changes"
   git push origin feature/your-feature-name
   ```
4. Open a Pull Request on GitHub for review!
