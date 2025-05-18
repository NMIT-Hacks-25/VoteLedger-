# 🗳️ VoteLedger 
## :A Smart & Secure Voting Platform
VoteLedger is a modern, secure, and transparent electronic voting platform built using Streamlit and blockchain technology. It supports manual and QR code voting, real-time vote verification, and fraud detection, ensuring the integrity of democratic processes in organizations, institutions, or public elections.

### 🚀 Features
✅ Blockchain-Powered Security
Immutable vote recording using a custom blockchain implementation

Each vote is cryptographically hashed and stored in blocks

### 📊 Real-Time Dashboard
Track total candidates, registered voters, votes cast, and voter turnout

View vote distributions with charts and tables

Monitor blockchain status and transaction mining

### 👨‍💼 Admin Panel
Add and manage candidates with QR code generation

Register voters and manage voter database

View and mine blockchain transactions

Built-in fraud detection system using heuristic rules (e.g., fake domains, duplicate emails, suspicious names)

### 👥 Voter Panel
Register voters securely

Cast manual votes with immediate receipt generation

Verify vote authenticity using receipt ID

### 📱 QR Code Voting
Automatically generate and download QR codes for candidates

Voters can scan and submit votes via QR images

QR-based votes are tracked and logged with receipts

### 🧰 Technologies Used
Python 3.8+

Streamlit for interactive frontend

Pandas for data handling

Pillow and pyzbar for image/QR processing

qrcode for QR code generation

Custom Blockchain written from scratch

### 🛠️ Installation
Clone the Repository

bash
Copy
Edit
git clone https://github.com/yourusername/voteledger.git
cd voteledger
Install Dependencies

bash
Copy
Edit
pip install -r requirements.txt
Run the App

bash
Copy
Edit
streamlit run app.py
Replace app.py with the actual filename if different.


### 📋 Example Use Cases
University Elections – Conduct student union or council elections

Corporate Polls – Secure decision making within companies

NGOs & Local Governance – Transparent community voting

### 🔐 Security Highlights
Only registered voters can vote

Duplicate voting prevention via Voter ID hashing

Receipt-based vote verification

Immutable blockchain records with hash links

### 📦 Requirements
Create a requirements.txt with:

txt
Copy
Edit
streamlit
pandas
qrcode
Pillow
pyzbar
Also ensure that zbar is installed on your system for QR code scanning (pyzbar relies on it).

### 🧠 Future Enhancements (Ideas)
Biometric voter authentication

Integration with government voter databases

End-to-end encryption of transactions

Blockchain explorer via external tools



### 🤝 Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

