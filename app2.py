import streamlit as st
import time
import hashlib
import json
from collections import defaultdict
import qrcode
from PIL import Image
from io import BytesIO
import pandas as pd
import base64
from pyzbar.pyzbar import decode

# --- Blockchain Classes ---
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True, default=str)
        return hashlib.sha256(block_string.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.voters = set()
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, [], time.time(), "0")
        self.chain.append(genesis_block)

    def add_transaction(self, voter_id, candidate, receipt_id):
        if voter_id in self.voters:
            return False  # Already voted
        tx = {
            'voter_id': voter_id,
            'candidate': candidate,
            'receipt_id': receipt_id,
            'timestamp': time.time()
        }
        self.pending_transactions.append(tx)
        self.voters.add(voter_id)
        return True

    def mine(self):
        if not self.pending_transactions:
            return False
        last_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            timestamp=time.time(),
            previous_hash=last_block.hash
        )
        self.chain.append(new_block)
        self.pending_transactions = []
        return True

    def get_all_transactions(self):
        txs = []
        for block in self.chain[1:]:  # skip genesis
            txs.extend(block.transactions)
        return txs

    def get_results(self):
        results = defaultdict(int)
        for tx in self.get_all_transactions():
            results[tx['candidate']] += 1
        return results

    def get_block_info(self):
        info = []
        for block in self.chain:
            info.append({
                'index': block.index,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp)),
                'transactions': block.transactions,
                'hash': block.hash,
                'previous_hash': block.previous_hash,
            })
        return info

# --- Helper Functions ---
def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def get_image_download_link(img_data, filename, text):
    b64 = base64.b64encode(img_data).decode()
    return f'<a href="data:image/png;base64,{b64}" download="{filename}">{text}</a>'

def generate_receipt_id(voter_id, candidate, timestamp):
    return hashlib.sha256(f"{voter_id}{candidate}{timestamp}".encode()).hexdigest()[:16]

# --- Streamlit State Initialization ---
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain()
if 'candidate_list' not in st.session_state:
    st.session_state.candidate_list = []
if 'registered_voters' not in st.session_state:
    st.session_state.registered_voters = {}
if 'qr_vote_counts' not in st.session_state:
    st.session_state.qr_vote_counts = defaultdict(int)
if 'votes_table' not in st.session_state:
    st.session_state.votes_table = pd.DataFrame(columns=[
        'Voter ID', 'Name', 'Email', 'Domain', 'Candidate', 
        'Receipt ID', 'Vote Method', 'Timestamp'
    ])
if 'qr_voters' not in st.session_state:
    st.session_state.qr_voters = set()

blockchain = st.session_state.blockchain
candidate_list = st.session_state.candidate_list
registered_voters = st.session_state.registered_voters
qr_vote_counts = st.session_state.qr_vote_counts
votes_table = st.session_state.votes_table

# --- UI Layout ---
st.set_page_config(
    page_title="VoteLedger - Secure Voting System",
    page_icon="🗳️",
    layout="wide"
)

st.markdown("""
<style>
/* App background */
[data-testid="stAppViewContainer"] {
    background-image: url('https://i.pinimg.com/originals/5c/f2/66/5cf2660af5f4214def7166dc7a7c8062.jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    padding-top: 0 !important;
}

/* Transparent main block */
[data-testid="stApp"], .block-container {
    background: rgba(255, 255, 255, 0.85);
    border-radius: 15px;
    padding: 2rem;
    margin-top: 0 !important;
}

/* Title section */
#title-container {
    padding-top: 2rem;
    padding-bottom: 1rem;
}

/* Title */
h1 {
    font-size: 3.5rem;
    text-align: center;
    background: linear-gradient(90deg, #00c6ff, #0072ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: bold;
    margin: 0;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    background-color: #f0f2f6;
    border-radius: 10px 10px 0 0;
    font-weight: 600;
    padding: 10px 20px;
}
.stTabs [aria-selected="true"] {
    background-color: #0072ff;
    color: white;
}

/* Buttons */
.stButton > button {
    background-color: #0072ff;
    color: white;
    border-radius: 10px;
    font-size: 16px;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
    transition: 0.3s ease;
}
.stButton > button:hover {
    background-color: #005bb5;
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
}

/* Inputs */
input, select, textarea {
    border-radius: 8px !important;
    padding: 10px !important;
    font-size: 15px !important;
}

/* DataFrame */
.stDataFrame {
    border: 1px solid #ccc;
    border-radius: 10px;
    overflow: hidden;
}

/* Metrics */
[data-testid="stMetric"] {
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    padding: 20px;
}

/* QR code */
.qr-code {
    border: 1px solid #ddd;
    background: white;
    border-radius: 10px;
    padding: 1rem;
    margin-top: 1rem;
}

/* Alerts */
.stAlert[data-testid="stAlertSuccess"] [data-testid="stMarkdownContainer"] {
    color: #28a745;
}
.stAlert[data-testid="stAlertError"] [data-testid="stMarkdownContainer"] {
    color: #dc3545;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        #title-container {
            text-align: center;
            padding: 30px 0;
            animation: fadeIn 2s ease-in-out;
        }

        #title-container h1 {
            font-size: 3em;
            background: linear-gradient(to right, #4facfe, #00f2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>

    <div id="title-container">
        <h1>VoteLedger: A Secure Blockchain Voting System</h1>
    </div>
""", unsafe_allow_html=True)



tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔒 Admin Panel", "👤 Voter Panel", "📱 QR Voting"])

# --- Dashboard Tab ---
with tab1:
    st.header("Election Overview")
    
    num_candidates = len(candidate_list)
    num_voters = len(registered_voters)
    manual_votes = sum(blockchain.get_results().values())
    qr_votes = sum(qr_vote_counts.values())
    total_votes = manual_votes + qr_votes
    turnout = (total_votes / num_voters * 100) if num_voters > 0 else 0
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("Total Candidates", num_candidates, help="Number of registered candidates")
    with cols[1]:
        st.metric("Registered Voters", num_voters, help="Number of eligible voters")
    with cols[2]:
        st.metric("Total Votes Cast", total_votes, help="Manual + QR code votes")
    with cols[3]:
        st.metric("Voter Turnout", f"{turnout:.1f}%", help="Percentage of voters who participated")
    
    st.divider()
    
    if candidate_list:
        st.subheader("Vote Distribution")
        manual_results = blockchain.get_results()
        
        # Create vote distribution chart
        vote_data = pd.DataFrame({
            'Candidate': candidate_list,
            'Manual Votes': [manual_results.get(c, 0) for c in candidate_list],
            'QR Votes': [qr_vote_counts.get(c, 0) for c in candidate_list]
        })
        vote_data['Total Votes'] = vote_data['Manual Votes'] + vote_data['QR Votes']
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.bar_chart(vote_data.set_index('Candidate')[['Manual Votes', 'QR Votes']],
                        color=["#1f77b4", "#ff7f0e"])
        
        with col2:
            st.dataframe(vote_data.sort_values('Total Votes', ascending=False),
                         use_container_width=True,
                         hide_index=True)
        
        st.divider()
        
        # Blockchain status
        st.subheader("Blockchain Status")
        bc_cols = st.columns(3)
        with bc_cols[0]:
            st.metric("Blocks", len(blockchain.chain))
        with bc_cols[1]:
            st.metric("Pending Transactions", len(blockchain.pending_transactions))
        with bc_cols[2]:
            st.metric("Total Votes Recorded", len(blockchain.get_all_transactions()))
        
        if st.button("⛏️ Mine Pending Transactions", help="Add pending votes to the blockchain"):
            if blockchain.mine():
                st.success(f"Block #{len(blockchain.chain)-1} mined successfully!")
            else:
                st.warning("No pending transactions to mine")
    else:
        st.info("ℹ️ No candidates registered yet. Admin can add candidates in the Admin Panel.")

# --- Admin Panel Tab ---
with tab2:
    st.header("Administration Console")
    admin_tabs = st.tabs(["👥 Manage Candidates", "⛓️ Blockchain", "📋 Voter Management", "🕵️ Fraud Detection"])
    
    with admin_tabs[0]:
        st.subheader("Candidate Management")
        
        # Add new candidate
        with st.expander("➕ Add New Candidate", expanded=True):
            with st.form("add_candidate_form"):
                new_candidate = st.text_input("Candidate Name", placeholder="Enter candidate name", key="new_candidate")
                add_btn = st.form_submit_button("Add Candidate")
                
                if add_btn:
                    if new_candidate and new_candidate.strip() != "":
                        if new_candidate not in candidate_list:
                            candidate_list.append(new_candidate)
                            qr_vote_counts[new_candidate] = 0
                            st.success(f"✅ Added candidate: {new_candidate}")
                        else:
                            st.error("❌ Candidate already exists")
                    else:
                        st.error("❌ Please enter a valid candidate name")
        
        # Current candidates
        st.subheader("Current Candidates")
        if candidate_list:
            for candidate in candidate_list:
                with st.container():
                    cols = st.columns([1, 3, 1])
                    with cols[0]:
                        st.image(generate_qr_code(candidate), width=120, caption=f"QR for {candidate}")
                    with cols[1]:
                        st.markdown(f"### {candidate}")
                        st.markdown(f"""
                        - **Manual Votes:** {blockchain.get_results().get(candidate, 0)}
                        - **QR Votes:** {qr_vote_counts.get(candidate, 0)}
                        - **Total Votes:** {blockchain.get_results().get(candidate, 0) + qr_vote_counts.get(candidate, 0)}
                        """)
                    with cols[2]:
                        if st.button("🗑️ Remove", key=f"remove_{candidate}"):
                            candidate_list.remove(candidate)
                            qr_vote_counts.pop(candidate, None)
                            st.rerun()
                    st.divider()
        else:
            st.info("ℹ️ No candidates available. Add candidates using the form above.")
    
    with admin_tabs[1]:
        st.subheader("Blockchain Explorer")
        
        # Blockchain operations
        with st.expander("🔧 Blockchain Operations", expanded=True):
            cols = st.columns(3)
            with cols[0]:
                if st.button("🔄 Refresh Blockchain"):
                    st.rerun()
            with cols[1]:
                if st.button("⛏️ Mine Block", help="Create a new block with pending transactions"):
                    if blockchain.mine():
                        st.success(f"Block #{len(blockchain.chain)-1} mined successfully!")
                    else:
                        st.warning("No pending transactions to mine")
            with cols[2]:
                if st.button("🧹 Clear Pending", help="Clear pending transactions (for testing only)"):
                    blockchain.pending_transactions = []
                    st.warning("Pending transactions cleared")
        
        # Block explorer
        st.subheader("Block Details")
        if blockchain.chain:
            block_select = st.selectbox("Select Block", range(len(blockchain.chain)), 
                                      format_func=lambda x: f"Block {x} - {len(blockchain.chain[x].transactions)} transactions")
            
            block = blockchain.chain[block_select]
            with st.expander(f"Block {block.index} Details", expanded=True):
                st.json({
                    "Index": block.index,
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp)),
                    "Transactions": len(block.transactions),
                    "Previous Hash": block.previous_hash[:20] + "...",
                    "Hash": block.hash[:20] + "..."
                })
                
                if block.transactions:
                    st.subheader(f"Transactions ({len(block.transactions)})")
                    st.dataframe(pd.DataFrame(block.transactions), hide_index=True)
                else:
                    st.info("No transactions in this block")
        else:
            st.info("Blockchain is empty")
    
    with admin_tabs[2]:
        st.subheader("Voter Registration Management")
        
        # Voter registration form
        with st.expander("➕ Register New Voter", expanded=True):
            with st.form("admin_voter_reg_form"):
                cols = st.columns(2)
                with cols[0]:
                    voter_id = st.text_input("National ID/Passport Number", key="admin_voter_id")
                    name = st.text_input("Full Name", key="admin_name")
                with cols[1]:
                    email = st.text_input("Email Address", key="admin_email")
                    domain = st.text_input("Domain (Organization/Institution)", key="admin_domain")
                
                if st.form_submit_button("Register Voter"):
                    if not all([voter_id, name, email]):
                        st.error("All fields are required")
                    elif voter_id in registered_voters:
                        st.error("Voter ID already registered")
                    elif any(email == v['email'] for v in registered_voters.values()):
                        st.warning("This email is already registered.")
                    else:
                        registered_voters[voter_id] = {
                            'name': name,
                            'email': email,
                            'domain': domain,
                            'registered_at': time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.success("✅ Registration successful!")
        
        # Voter list
        st.subheader("Registered Voters")
        if registered_voters:
            voters_df = pd.DataFrame.from_dict(registered_voters, orient='index')
            voters_df.index.name = 'Voter ID'
            st.dataframe(voters_df, use_container_width=True)
            
            # Export options
            st.download_button(
                label="📥 Export Voter List",
                data=voters_df.to_csv().encode('utf-8'),
                file_name='voter_registrations.csv',
                mime='text/csv'
            )
        else:
            st.info("ℹ️ No voters registered yet")
    
    with admin_tabs[3]:
        st.subheader("Fraud Detection System")
        
        if not registered_voters:
            st.info("ℹ️ No registered voters to analyze")
        else:
            voters_df = pd.DataFrame([
                {
                    'Voter ID': voter_id,
                    'Name': v['name'],
                    'Email': v['email'],
                    'Domain': v.get('domain', 'N/A')
                }
                for voter_id, v in registered_voters.items()
            ])
            
            # AI Fraud Detection Rules
            st.info("🔍 Analyzing voter registrations for potential fraud patterns...")
            
            suspicious_domains = ['spam.com', 'fake.com', 'test.com', 'example.com', 'mailinator.com']
            flagged = []

            # Rule 1: Multiple registrations with same email
            email_counts = voters_df['Email'].value_counts()
            for email, count in email_counts.items():
                if count > 1:
                    flagged.extend(voters_df[voters_df['Email'] == email].index.tolist())

            # Rule 2: Suspicious email domains
            for idx, row in voters_df.iterrows():
                domain = str(row['Domain']).lower()
                if any(s in domain for s in suspicious_domains):
                    flagged.append(idx)

            # Rule 3: Names that are too short or suspicious
            for idx, row in voters_df.iterrows():
                if len(row['Name'].split()) < 2 or len(row['Name']) < 5:
                    flagged.append(idx)

            flagged = list(set(flagged))
            flagged_df = voters_df.loc[flagged]
            
            if not flagged_df.empty:
                st.warning(f"⚠️ Detected {len(flagged)} potentially fraudulent registrations:")
                
                cols = st.columns([4, 1])
                with cols[0]:
                    st.dataframe(flagged_df, use_container_width=True)
                
                with cols[1]:
                    st.metric("Total Flagged", len(flagged))
                    st.metric("Suspicious Emails", len([d for d in voters_df['Domain'] if any(s in str(d).lower() for s in suspicious_domains)]))
                    st.metric("Duplicate Emails", len(email_counts[email_counts > 1]))
                
                if st.button("❌ Remove Flagged Registrations", type="primary"):
                    for voter_id in flagged_df['Voter ID']:
                        registered_voters.pop(voter_id, None)
                    st.success("✅ Removed flagged registrations!")
                    st.rerun()
            else:
                st.success("✅ No suspicious activity detected.")

# --- Voter Panel Tab ---
with tab3:
    st.header("Voter Services")
    voter_tabs = st.tabs(["📝 Registration", "✏️ Manual Voting", "🔎 Verify Vote"])
    
    with voter_tabs[0]:
        st.subheader("Voter Registration")
        st.info("Register to participate in the election")
        
        with st.form("voter_reg_form"):
            cols = st.columns(2)
            with cols[0]:
                voter_id = st.text_input("National ID/Passport Number", help="Your government-issued ID")
                name = st.text_input("Full Name")
            with cols[1]:
                email = st.text_input("Email Address", help="We'll send your receipt to this email")
                domain = st.text_input("Domain (Organization/Institution)", help="Your company, school, etc.")
            
            submitted = st.form_submit_button("Register")
            
            if submitted:
                if not all([voter_id, name, email]):
                    st.error("❌ All fields are required")
                elif voter_id in registered_voters:
                    st.error("❌ Voter ID already registered")
                elif any(email == v['email'] for v in registered_voters.values()):
                    st.warning("⚠️ This email is already registered.")
                else:
                    registered_voters[voter_id] = {
                        'name': name,
                        'email': email,
                        'domain': domain,
                        'registered_at': time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.success("✅ Registration successful!")
                    st.balloons()
    
    with voter_tabs[1]:
        st.subheader("Cast Your Vote")
        
        if not registered_voters:
            st.info("ℹ️ Please register first before voting")
        else:
            voter_id = st.selectbox("Select Your Voter ID", list(registered_voters.keys()),
                                  help="Find your registration ID")
            
            if not candidate_list:
                st.info("ℹ️ No candidates available to vote for")
            else:
                candidate = st.selectbox("Select Candidate", candidate_list,
                                       help="Choose your preferred candidate")
                
                if st.button("✅ Submit Vote"):
                    if voter_id in blockchain.voters:
                        st.error("❌ You have already voted")
                    else:
                        timestamp = time.time()
                        receipt_id = generate_receipt_id(voter_id, candidate, timestamp)
                        if blockchain.add_transaction(voter_id, candidate, receipt_id):
                            # Add to votes table
                            votes_table.loc[len(votes_table)] = [
                                voter_id,
                                registered_voters[voter_id]['name'],
                                registered_voters[voter_id]['email'],
                                registered_voters[voter_id].get('domain', 'N/A'),
                                candidate,
                                receipt_id,
                                "Manual",
                                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                            ]
                            
                            # Show success message with receipt
                            st.success("✅ Vote cast successfully!")
                            st.balloons()
                            st.markdown(f"""
                            ### Your Voting Receipt
                            - **Voter ID:** {voter_id}
                            - **Candidate:** {candidate}
                            - **Receipt ID:** `{receipt_id}`
                            - **Timestamp:** {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))}
                            
                            ⚠️ Please save this receipt for verification
                            """)
    
    with voter_tabs[2]:
        st.subheader("Vote Verification")
        st.info("Verify that your vote was correctly recorded in the system")
        
        receipt_id = st.text_input("Enter Your Receipt ID", placeholder="Paste your receipt ID here")
        
        if st.button("🔍 Verify Vote"):
            if not receipt_id:
                st.error("❌ Please enter a receipt ID")
            else:
                # Check blockchain votes
                blockchain_vote_found = False
                for tx in blockchain.get_all_transactions():
                    if tx['receipt_id'] == receipt_id:
                        st.success("✅ Blockchain Vote Verified!")
                        with st.expander("View Vote Details", expanded=True):
                            st.json({
                                'Voter ID': tx['voter_id'],
                                'Name': registered_voters.get(tx['voter_id'], {}).get('name', 'Unknown'),
                                'Candidate': tx['candidate'],
                                'Receipt ID': tx['receipt_id'],
                                'Timestamp': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tx['timestamp']))
                            })
                        blockchain_vote_found = True
                        break
                
                # Check QR votes if not found in blockchain
                if not blockchain_vote_found:
                    qr_vote_found = False
                    for _, row in votes_table.iterrows():
                        if row['Receipt ID'] == receipt_id and row['Vote Method'] == "QR":
                            st.success("✅ QR Vote Verified!")
                            with st.expander("View Vote Details", expanded=True):
                                st.json({
                                    'Voter ID': row['Voter ID'],
                                    'Name': row['Name'],
                                    'Candidate': row['Candidate'],
                                    'Receipt ID': row['Receipt ID'],
                                    'Timestamp': row['Timestamp']
                                })
                            qr_vote_found = True
                            break
                    
                    if not qr_vote_found:
                        st.error("❌ Receipt ID not found in the system")

# --- QR Voting Tab ---
with tab4:
    st.header("Mobile QR Code Voting")
    qr_tabs = st.tabs(["🎫 Candidate QR Codes", "📸 Scan QR Code", "📊 QR Vote Results"])
    
    with qr_tabs[0]:
        st.subheader("Candidate QR Codes")
        st.info("Download QR codes for each candidate to enable mobile voting")
        
        if not candidate_list:
            st.info("ℹ️ No candidates available")
        else:
            selected_candidate = st.selectbox("Select Candidate", candidate_list,
                                           key="qr_candidate_select")
            
            qr_img = generate_qr_code(selected_candidate)
            
            cols = st.columns([2, 3])
            with cols[0]:
                st.image(qr_img, caption=f"QR Code for {selected_candidate}", width=250)
                
                st.markdown(get_image_download_link(
                    qr_img, 
                    f"{selected_candidate}_vote_qr.png", 
                    "⬇️ Download QR Code"
                ), unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f"""
                ### {selected_candidate} QR Code
                - **Total QR Votes:** {qr_vote_counts.get(selected_candidate, 0)}
                - **Manual Votes:** {blockchain.get_results().get(selected_candidate, 0)}
                
                **Instructions:**
                1. Download the QR code
                2. Share with voters
                3. Voters can scan to vote
                """)
    
    with qr_tabs[1]:
        st.subheader("QR Code Voting")
        st.info("Scan a candidate's QR code to vote instantly")
        
        uploaded_file = st.file_uploader("Upload QR Code Image", type=["png", "jpg", "jpeg"],
                                       help="Take a photo or upload an image of the QR code")
        
        if uploaded_file is not None:
            try:
                img = Image.open(uploaded_file)
                decoded = decode(img)
                
                if decoded:
                    candidate = decoded[0].data.decode('utf-8')
                    
                    if candidate in candidate_list:
                        # Create unique voter session based on image content
                        voter_id = f"qr_voter_{hashlib.md5(uploaded_file.getvalue()).hexdigest()}"
                        
                        if voter_id not in st.session_state.qr_voters:
                            timestamp = time.time()
                            receipt_id = generate_receipt_id(voter_id, candidate, timestamp)
                            
                            # Record QR vote
                            qr_vote_counts[candidate] += 1
                            st.session_state.qr_voters.add(voter_id)
                            
                            # Add to votes table
                            votes_table.loc[len(votes_table)] = [
                                voter_id,
                                "QR Voter",
                                "qr@voter.com",
                                "Mobile",
                                candidate,
                                receipt_id,
                                "QR",
                                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                            ]
                            
                            st.success(f"✅ Vote recorded for {candidate}!")
                            st.balloons()
                            
                            # Show receipt
                            st.markdown(f"""
                            ### Your QR Voting Receipt
                            - **Candidate:** {candidate}
                            - **Receipt ID:** `{receipt_id}`
                            - **Timestamp:** {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))}
                            
                            ⚠️ Please save this receipt for verification
                            """)
                        else:
                            st.warning("⚠️ You have already voted using this QR code")
                    else:
                        st.error("❌ Invalid candidate QR code")
                else:
                    st.warning("🔍 No QR code detected in the image")
            except Exception as e:
                st.error(f"❌ Error processing QR code: {str(e)}")
    
    with qr_tabs[2]:
        st.subheader("QR Voting Statistics")
        
        if qr_vote_counts:
            qr_results = pd.DataFrame({
                'Candidate': list(qr_vote_counts.keys()),
                'QR Votes': list(qr_vote_counts.values())
            }).sort_values('QR Votes', ascending=False)
            
            cols = st.columns([3, 2])
            with cols[0]:
                st.bar_chart(qr_results.set_index('Candidate'), color="#28a745")
            
            with cols[1]:
                st.dataframe(qr_results, hide_index=True)
            
            st.download_button(
                label="📥 Export QR Results",
                data=qr_results.to_csv(index=False).encode('utf-8'),
                file_name='qr_vote_results.csv',
                mime='text/csv'
            )
        else:
            st.info("ℹ️ No QR votes recorded yet")