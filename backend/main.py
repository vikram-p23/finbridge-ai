from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fpdf import FPDF
import random
import re
import os
import requests # New import for fetching QR
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users_db = {} 

# --- MODELS ---
class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    dob: str
    phone: str
    email: str
    password: str

class LoginRequest(BaseModel):
    user_id: str
    password: str

class BankAccountRequest(BaseModel):
    user_id: str
    father_name: str
    aadhar: str
    pan: str
    address: str

class BankLoginRequest(BaseModel):
    account_number: str
    dob: str

class PaymentRequest(BaseModel):
    account_number: str
    amount: float

class ChatRequest(BaseModel):
    message: str
    user_id: str
    service_mode: str 

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'FinBridge AI Bank - Official Statement', 0, 1, 'C')
        self.ln(10)

def generate_sanction_pdf(user_name, offer, loan_type, score):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=1, align='R')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"To: {user_name}", ln=1)
    pdf.cell(200, 10, txt=f"Credit Score: {score}", ln=1)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt=f"Subject: Final Sanction for {loan_type}", ln=1, align='C')
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=f"Dear Sir/Madam,\n\nWe are pleased to inform you that your application for {loan_type} has been FINALIZED and APPROVED based on the agreed terms.")
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"Sanctioned Amount: INR {offer['amount']:,}", ln=1)
    pdf.cell(200, 10, txt=f"Interest Rate: {offer['rate']}% p.a.", ln=1)
    pdf.cell(200, 10, txt=f"Tenure: {offer['tenure']} Months", ln=1)
    pdf.ln(20)
    pdf.cell(200, 10, txt="Authorized Signatory, FinBridge AI", ln=1)
    filename = f"Sanction_Letter_{user_name.split()[0]}.pdf"
    pdf.output(filename)
    return filename

# --- NEW: GENERATE BANK STATEMENT PDF WITH QR ---
def generate_statement_pdf(user_data):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. Header Details
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1, align='R')
    pdf.ln(5)
    
    # 2. Customer Details
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="Customer Details:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 8, txt=f"Name: {user_data['name']}", ln=1)
    pdf.cell(200, 8, txt=f"Phone: {user_data['phone']}", ln=1)
    pdf.cell(200, 8, txt=f"Email: {user_data['email']}", ln=1)
    pdf.cell(200, 8, txt=f"Address: {user_data['bank_account']['address']}", ln=1)
    pdf.ln(10)

    # 3. Account Summary
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="Account Summary:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 8, txt=f"Account Number: {user_data['bank_account']['account_number']}", ln=1)
    pdf.cell(200, 8, txt=f"IFSC Code: FINB0001234", ln=1)
    pdf.cell(200, 8, txt=f"Available Balance: INR {user_data['bank_account']['balance']:,}", ln=1)
    pdf.ln(10)

    # 4. QR Code Generation & Embedding
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="Payment QR Code (Vikram P):", ln=1)
    
    # Fetch QR from API
    qr_data = f"upi://pay?pa=9916698774@kotak811&pn=Vikram%20P"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={qr_data}"
    
    try:
        response = requests.get(qr_url)
        if response.status_code == 200:
            with open("temp_qr.png", "wb") as f:
                f.write(response.content)
            pdf.image("temp_qr.png", x=10, y=pdf.get_y(), w=40)
            pdf.ln(45) # Move cursor past image
    except:
        pdf.cell(200, 10, txt="[QR Code Could not be loaded]", ln=1)

    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, txt="Scan this QR to pay directly to this account via GPay/UPI.", ln=1)
    
    filename = f"Bank_Statement_{user_data['first_name']}.pdf"
    pdf.output(filename)
    return filename

# --- HELPER: SMART INTENT CHECKER ---
def check_intent(msg, intent_type):
    msg = msg.lower()
    if intent_type == "yes":
        return any(x in msg for x in ["yes", "yep", "yeah", "sure", "ok", "confirm", "proceed", "perfect", "accept", "lock"])
    if intent_type == "no":
        return any(x in msg for x in ["no", "nah", "nope", "cancel", "decline", "reject", "edit", "change", "wait"])
    return False

# --- AUTH ENDPOINTS ---
@app.post("/register")
def register(req: RegisterRequest):
    rand_id = f"USER{random.randint(1000, 9999)}"
    users_db[rand_id] = {
        "first_name": req.first_name,
        "last_name": req.last_name,
        "name": f"{req.first_name} {req.last_name}",
        "dob": req.dob,
        "phone": req.phone,
        "email": req.email,
        "password": req.password, 
        "credit_score": None, "max_limit": 0, 
        "kyc_status": "Pending", 
        "salary_slip": False, 
        "selected_loan": None, "loan_category": None, 
        "loan_status": "INIT",
        "gold_grams": None,
        "current_offer": {"amount": 0, "rate": 0, "tenure": 0},
        "bank_account": None
    }
    return {"status": "success", "user_id": rand_id, "message": f"Welcome {req.first_name}! Your ID is {rand_id}"}

@app.post("/login")
def login(req: LoginRequest):
    if req.user_id in users_db and users_db[req.user_id]["password"] == req.password:
        return {"status": "success", "user_data": users_db[req.user_id]}
    return {"status": "failed", "message": "Invalid Credentials"}

@app.post("/get_user")
def get_user(req: LoginRequest):
    if req.user_id in users_db: return {"status": "success", "user_data": users_db[req.user_id]}
    return {"status": "failed"}

# --- BANKING ENDPOINTS ---
@app.post("/create_bank_account")
def create_bank_account(req: BankAccountRequest):
    user = users_db.get(req.user_id)
    if not user: return {"status": "failed", "message": "User not found"}
    acc_num = f"{random.randint(100000000000, 999999999999)}"
    user['bank_account'] = {
        "account_number": acc_num,
        "father_name": req.father_name,
        "aadhar": req.aadhar,
        "pan": req.pan,
        "address": req.address,
        "balance": 25000.00 
    }
    return {"status": "success", "account_number": acc_num}

@app.post("/login_bank")
def login_bank(req: BankLoginRequest):
    for uid, user in users_db.items():
        if user.get('bank_account') and \
           user['bank_account']['account_number'] == req.account_number and \
           user['dob'] == req.dob:
            return {"status": "success", "bank_data": user['bank_account'], "user_data": user}
    return {"status": "failed", "message": "Invalid Details"}

@app.post("/pay")
def pay(req: PaymentRequest):
    for uid, user in users_db.items():
        if user.get('bank_account') and user['bank_account']['account_number'] == req.account_number:
            if user['bank_account']['balance'] >= req.amount:
                user['bank_account']['balance'] -= req.amount
                return {"status": "success", "new_balance": user['bank_account']['balance'], "message": "Payment Successful!"}
            else:
                return {"status": "failed", "message": "Insufficient Balance"}
    return {"status": "failed", "message": "Account not found"}

# --- NEW: DOWNLOAD STATEMENT ENDPOINT ---
@app.get("/download_statement/{user_id}")
def download_statement(user_id: str):
    user = users_db.get(user_id)
    if not user or not user.get('bank_account'):
        return {"message": "Account not found"}
    
    filename = generate_statement_pdf(user)
    return FileResponse(f"./{filename}", media_type='application/pdf', filename=filename)

# --- CHATBOT LOGIC ---
def smart_bot_logic(mode, msg, user_id):
    user = users_db[user_id]
    clean_msg = msg.replace(" ", "").strip()
    msg_lower = msg.lower()
    system_msgs = [] 

    if mode == "Live Agent Support":
        if check_intent(msg, "no") and ("bye" in msg_lower or "end" in msg_lower): 
            return "Agent Sarah: Thank you. Redirecting...", "Customer Engagement", []
        if "rate" in msg_lower: return "Agent Sarah: Personal Loan rates start at 8.5%.", None, []
        if "human" in msg_lower: return "Agent Sarah: Yes, I am a real human agent.", None, []
        return "Agent Sarah: I'm checking that detail. Please hold.", None, []

    if mode == "Help & Support":
        if "call" in msg_lower: return "📞 Hotline: 1800-123-4567.", None, []
        if "chat" in msg_lower: return "💬 Connecting to Live Agent...", "Live Agent Support", ["🔄 Handoff to Human Agent..."]
        return "Select option:", None, []

    if mode == "Customer Engagement":
        if "back" in msg_lower:
            user["loan_category"] = None
            return "Main Menu: Select Category.", None, []
        if user['loan_status'] == "APPROVED":
            return "⚠️ ACTIVE LOAN DETECTED. Please clear dues.", None, []
        
        if "unsecured" in msg_lower:
            user["loan_category"] = "Unsecured"
            return "🔓 Unsecured Loans Selected.", None, []
        elif "secured" in msg_lower:
            user["loan_category"] = "Secured"
            return "🔒 Secured Loans Selected. Choose product:", None, []

        if "car" in msg_lower: user["selected_loan"] = "Car Loan"; user["loan_category"]="Secured"; 
        elif "home" in msg_lower: user["selected_loan"] = "Home Loan"; user["loan_category"]="Secured";
        elif "gold" in msg_lower: user["selected_loan"] = "Gold Loan"; user["loan_category"]="Secured";
        elif "personal" in msg_lower: user["selected_loan"] = "Personal Loan"; user["loan_category"]="Unsecured";
        if user["selected_loan"]:
            system_msgs.append(f"🔄 Handoff to Verification Agent...")
            return f"✅ {user['selected_loan']} Selected. Initializing KYC...", "KYC Verification", system_msgs
        return "Welcome to FinBridge. Select Secured or Unsecured.", None, []

    elif mode == "KYC Verification":
        if not user['selected_loan']: return "⚠️ Select loan first.", "Customer Engagement", []
        match = re.search(r'\d{12}', clean_msg)
        if match:
            user['kyc_status'] = "Verified"
            system_msgs.append("✅ Identity Verified.")
            system_msgs.append("🔄 Handoff to Underwriting Agent...")
            return f"Proceeding to Credit Check...", "Credit Evaluation", system_msgs
        return "⚠️ INVALID AADHAR.\nFormat: 12 Digits.\nExample: 458912563258", None, []

    elif mode == "Credit Evaluation":
        if user['kyc_status'] != "Verified": return "⚠️ Complete KYC first.", "KYC Verification", []
        match = re.search(r'[A-Z]{5}\d{4}[A-Z]', clean_msg.upper())
        if match:
            user['credit_score'] = random.randint(600, 850) 
            system_msgs.append("🔍 Underwriting Agent is analyzing credit score...")
            system_msgs.append(f"📊 Bureau Score Fetched: {user['credit_score']}")
            return f"Analysis Complete. Forwarding to Sales...", "Bank Loan Approval", system_msgs
        return "⚠️ INVALID PAN.\n\nFormat: 5 Letters, 4 Numbers, 1 Letter.\nExample: ABCDE1234F\nPlease try again.", None, []

    elif mode == "Bank Loan Approval":
        if not user['credit_score']: return "⚠️ No Score.", "Credit Evaluation", []
        
        if user['selected_loan'] == "Gold Loan":
            if user['loan_status'] == "PIVOT_OFFER": pass
            if user.get('gold_grams') is None and user['loan_status'] not in ["NEGOTIATING", "APPROVED", "REJECTED"]:
                nums = re.findall(r'\d+', clean_msg)
                if nums and int(nums[0]) > 0:
                    grams = int(nums[0])
                    user['gold_grams'] = grams
                    limit = grams * 5000 
                    user['max_limit'] = limit
                    user['current_offer'] = {"amount": limit, "rate": 9.0, "tenure": 24}
                    user['loan_status'] = "NEGOTIATING"
                    system_msgs.append("⚖️ Valuation Agent calculated LTV...")
                    return (f"✨ GOLD VALUATION:\nWeight: {grams}g\n💰 Max: ₹{limit:,}\n⏳ Tenure: 24 Months\nIs this perfect?"), None, system_msgs
                else:
                    return "🟡 GOLD LOAN: Enter Total Grams (e.g. 50).", None, []

        if user['credit_score'] < 600:
            user['loan_status'] = "REJECTED"
            system_msgs.append("❌ Risk Policy Check Failed.")
            return (f"🚫 REJECTED\nScore ({user['credit_score']}) < 600.\nAdvice: Clear dues and try in 90 days."), None, system_msgs

        if 600 <= user['credit_score'] < 700 and user['loan_category'] == "Unsecured":
            if user['loan_status'] not in ["PIVOT_OFFER", "APPROVED", "REJECTED", "NEGOTIATING"]:
                user['loan_status'] = "PIVOT_OFFER"
                system_msgs.append("⚠️ Score Low for Personal Loan.")
                system_msgs.append("💡 Recommendation: Gold Loan.")
                return (f"Score ({user['credit_score']}) too low for Personal Loan.\n\n🔄 PIVOT: **Gold Loan** Pre-approved.\nProceed?"), None, system_msgs
        
        if user['loan_status'] == "PIVOT_OFFER":
            if check_intent(msg, "yes"):
                user['selected_loan'] = "Gold Loan"
                user['loan_category'] = "Secured"
                user['loan_status'] = "INIT" 
                system_msgs.append("🔄 Switching Workflow to Secured Loan...")
                return "✅ Excellent. Please enter **Total Grams** of gold.", None, system_msgs
            if check_intent(msg, "no"):
                user['loan_status'] = "REJECTED"
                return "❌ Offer Declined.", None, []

        if 700 <= user['credit_score'] < 750 and user['selected_loan'] != "Gold Loan":
            if user['loan_status'] not in ["NEGOTIATING", "APPROVED", "REJECTED"]:
                if not user.get('salary_slip'):
                    user['loan_status'] = "NEEDS_DOCS"
                    system_msgs.append("⚠️ Income Verification Required.")
                    return (f"Eligible for ₹5L.\n🔓 **To unlock ₹8L**, upload **Salary Slip (PDF)**."), None, system_msgs
                else:
                    user['loan_status'] = "INIT" 

        if (user['loan_status'] == "INIT" or user['loan_status'] == "NEEDS_DOCS") and user['selected_loan'] != "Gold Loan":
            base_limit = 1000000 if user['credit_score'] > 750 else 800000
            user['max_limit'] = base_limit
            user['current_offer'] = {"amount": base_limit, "rate": 8.5, "tenure": 48}
            user['loan_status'] = "NEGOTIATING"
            system_msgs.append("🎉 Sales Agent generated offer.")
            return (f"Great news, {user['name']}! 🌟\n\n"
                    f"💰 Amount: ₹{base_limit:,}\n"
                    f"📉 Rate: 8.5%\n"
                    f"⏳ Tenure: 48 Months\n\n"
                    f"Shall we lock this in?"), None, system_msgs

        if user['loan_status'] == "NEGOTIATING":
            if check_intent(msg, "yes"):
                user['loan_status'] = "APPROVED"
                system_msgs.append("🤝 Deal Closed.")
                system_msgs.append("📄 Sanction Agent is generating PDF...")
                return "✅ Offer Accepted! Finalizing...", "Generated PDF", system_msgs
            
            nums = re.findall(r'\d+', clean_msg)
            if nums:
                val = float(nums[0])
                if "amount" in msg_lower:
                    if val > user['max_limit']: return f"⚠️ Limit Exceeded (Max ₹{user['max_limit']}).", None, []
                    user['current_offer']['amount'] = int(val)
                    return f"🔄 Amount Updated: ₹{int(val)}.", None, []
                if "tenure" in msg_lower:
                    if val > 60: return "⚠️ Max 60 months.", None, []
                    user['current_offer']['tenure'] = int(val)
                    return f"🔄 Tenure Updated: {int(val)}.", None, []
            return "Use buttons below.", None, []

        if user['loan_status'] == "APPROVED": return "🎉 Approved.", "Generated PDF", []

    elif mode == "Generated PDF":
        if "auto_trigger" in msg_lower or user['loan_status'] == "APPROVED":
            if user['loan_status'] == "APPROVED":
                filename = generate_sanction_pdf(user['name'], user['current_offer'], user['selected_loan'], user['credit_score'])
                return f"DOWNLOAD_FILE:{filename}", None, []
        if user['loan_status'] == "REJECTED": return "❌ Rejected.", None, []
        return "Processing...", "Bank Loan Approval", []

    return "I didn't quite catch that.", None, []

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if req.user_id not in users_db: return {"response": "Error: User not found."}
    response_text, next_stage, system_msgs = smart_bot_logic(req.service_mode, req.message, req.user_id)
    return {"response": response_text, "next_stage": next_stage, "system_msgs": system_msgs, "updated_user": users_db[req.user_id]}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user_id: str = Form(...)):
    user = users_db.get(user_id)
    if not user: return {"message": "User not found"}
    if not file.filename.lower().endswith(".pdf"): return {"message": "❌ PDF Only."}
    if user.get('loan_status') != "NEEDS_DOCS": return {"message": "⚠️ Not required."}
    user["salary_slip"] = True
    return {"message": "✅ Verified. Limit Unlocked.", "next_stage": "Bank Loan Approval"}

@app.get("/download/{filename}")
def download_pdf(filename: str):
    return FileResponse(f"./{filename}", media_type='application/pdf', filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)