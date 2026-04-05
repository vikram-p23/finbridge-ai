# FinBridge AI — Agentic Loan Orchestration Platform

> *Revolutionizing Loan Sales with an AI-Driven Conversational Agent*

## Executive Summary

FinBridge AI is an intelligent Digital Sales Officer that replaces rigid banking
forms with a persuasive, conversational interface. It features an **Agentic Pivot
Strategy**: if a customer is rejected for a Personal Loan due to a low credit
score, the system automatically pivots to offer a Secured Gold Loan, recovering
lost revenue.

## Key Features

- **Agentic Orchestration** — Custom State Machine manages Sales, Verification (KYC), and Underwriting agents
- **Pivot Logic** — Automatically converts rejections (score < 700) into Gold Loan opportunities
- **Visual Credit Card** — Interactive glassmorphism-based credit card eligibility check
- **Instant Sanction** — Generates a PDF Sanction Letter in real-time
- **GPay Integration** — Deep-linking (`upi://pay`) for immediate processing fee payment

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend  | React.js, Framer Motion |
| Backend   | Python FastAPI |
| AI        | Google Gemini API |
| PDF       | FPDF |
| Validation | Regex (Aadhaar/PAN) |

## Project Structure
```
finbridge-ai/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   ├── index.html
│   │   ├── manifest.json
│   │   └── favicon.ico
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   ├── index.js
│   │   └── index.css
│   └── package.json
├── .gitignore
└── README.md
```

## Setup Instructions

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
# Server starts at http://127.0.0.1:8000
```

### Frontend
```bash
cd frontend
npm install
npm start
# App runs at http://localhost:3000
```

### Environment Variables
Create a `.env` file in the backend folder:
```
GEMINI_API_KEY=your_key_here
```

