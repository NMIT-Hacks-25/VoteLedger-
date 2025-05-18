import streamlit as st
import time
import hashlib
import json
from collections import defaultdict
import qrcode
from PIL import Image
from io import BytesIO
import pandas as pd

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

# --- Streamlit State ---
if 'blockchain' not in st.session_state:
    st.session_state['blockchain'] = Blockchain()
if 'candidate_list' not in st.session_state:
    st.session_state['candidate_list'] = []
if 'voter_details' not in st.session_state:
    st.session_state['voter_details'] = []  # List of dicts with voter info
if 'registered_voters' not in st.session_state:
    st.session_state['registered_voters'] = {}  # voter_id: {name, email, domain}
if 'qr_vote_counts' not in st.session_state:
    st.session_state['qr_vote_counts'] = {}
if 'votes_table' not in st.session_state:
    st.session_state['votes_table'] = pd.DataFrame(columns=['Voter ID', 'Name', 'Email', 'Domain', 'Candidate', 'Receipt', 'Timestamp'])

blockchain = st.session_state['blockchain']
candidate_list = st.session_state['candidate_list']
voter_details = st.session_state['voter_details']
registered_voters = st.session_state['registered_voters']
qr_vote_counts = st.session_state['qr_vote_counts']
votes_table = st.session_state['votes_table']

# --- Title ---
st.title("VoteLedger")

tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Admin Panel", "Voter Panel", "QR Code Voting"])

# --- Dashboard ---
with tab1:
    st.header("Dashboard")
    num_candidates = len(candidate_list)
    num_voters = len(registered_voters)
    total_votes = sum(blockchain.get_results().values())
    turnout = f"{(total_votes/num_voters*100):.1f}%" if num_voters else "0%"
    st.metric("Candidates", num_candidates)
    st.metric("Registered Voters", num_voters)
    st.metric("Total Votes", total_votes)
    st.metric("Turnout", turnout)
    st.write("Latest Block Hash:", blockchain.chain[-1].hash if blockchain.chain else "N/A")

# --- Admin Panel with Sub-tabs ---
with tab2:
    st.header("Admin Panel")
    admin_subtab = st.tabs(["Candidate Updation", "Mine Blocks & Results", "Blockchain Info", "AI Fraud Detection", "Voters Table"])

    # Candidate Updation
    with admin_subtab[0]:
        st.subheader("Add Candidate")
        new_candidate = st.text_input("Candidate", key="admin_add_candidate")
        if st.button("Add Candidate", key="admin_add_candidate_btn"):
            if new_candidate and new_candidate not in candidate_list:
                candidate_list.append(new_candidate)
                qr_vote_counts[new_candidate] = 0
                st.success(f"Added candidate: {new_candidate}")
            else:
                st.warning("Candidate already exists or name is empty.")

        st.subheader("Remove Candidate")
        if candidate_list:
            remove_cand = st.selectbox("Select Candidate to Remove", candidate_list, key="admin_remove_candidate")
            if st.button("Remove Candidate", key="admin_remove_candidate_btn"):
                candidate_list.remove(remove_cand)
                qr_vote_counts.pop(remove_cand, None)
                st.success(f"Removed candidate: {remove_cand}")
        else:
            st.info("No candidates to remove.")

        # --- Display current candidate list below add/remove section ---
        st.markdown("### Current Candidates:")
        if candidate_list:
            for cand in candidate_list:
                st.write(f"- {cand}")
        else:
            st.info("No candidates added yet.")

    # Mine Blocks & Results
    with admin_subtab[1]:
        st.subheader("Mine Block")
        if st.button("Mine Pending Votes", key="admin_mine_block_btn"):
            if blockchain.mine():
                st.success("Block mined successfully!")
            else:
                st.warning("No pending votes to mine.")

        st.subheader("Results")
        results = blockchain.get_results()
        if results:
            st.table([{"Candidate": k, "Votes": v} for k, v in results.items()])
        else:
            st.info("No votes yet.")

    # Blockchain Info
    with admin_subtab[2]:
        st.subheader("Blockchain Info")
        for block in blockchain.get_block_info():
            st.json(block)

    # AI Fraud Detection
    with admin_subtab[3]:
        st.subheader("AI Fraud Detection")
        if len(registered_voters) > 0:
            voters_df = pd.DataFrame([
                {
                    'Voter ID': voter_id,
                    'Name': v['name'],
                    'Email': v['email'],
                    'Domain': v['domain']
                }
                for voter_id, v in registered_voters.items()
            ])
            suspicious_domains = ['spam.com', 'fake.com', 'test.com']
            flagged = []

            # Multiple entries with same email
            email_counts = voters_df['Email'].value_counts()
            for email, count in email_counts.items():
                if count > 1:
                    flagged.extend(voters_df[voters_df['Email'] == email].index.tolist())

            # Suspicious domains
            for idx, row in voters_df.iterrows():
                domain = row['Domain'].lower()
                if any(s in domain for s in suspicious_domains):
                    flagged.append(idx)

            flagged = list(set(flagged))
            flagged_df = voters_df.loc[flagged]
            if not flagged_df.empty:
                st.warning("Suspicious registrations detected:")
                st.dataframe(flagged_df)
            else:
                st.success("No suspicious activity detected.")
        else:
            st.info("No registered voters yet.")

    # Voters Table
    with admin_subtab[4]:
        st.subheader("Voters Table")
        if len(votes_table) > 0:
            st.dataframe(votes_table)
        else:
            st.info("No votes cast yet.")

# --- Voter Panel with Sub-tabs ---
with tab3:
    st.header("Voter Panel")
    voter_subtab = st.tabs(["Registration", "Vote Validator"])

    # Registration & Vote Casting
    with voter_subtab[0]:
        st.subheader("Voter Registration")
        with st.form("voter_registration_form"):
            voter_id = st.text_input("Voter ID")
            name = st.text_input("Name")
            email = st.text_input("Email")
            domain = st.text_input("Domain")
            submitted = st.form_submit_button("Register")
            if submitted:
                if not voter_id or not name or not email or not domain:
                    st.error("All fields are required.")
                elif voter_id in registered_voters:
                    st.warning("Voter ID already registered.")
                elif any(email == v['email'] for v in registered_voters.values()):
                    st.warning("This email is already registered.")
                else:
                    registered_voters[voter_id] = {'name': name, 'email': email, 'domain': domain}
                    st.success("Registration successful!")

        st.subheader("Vote Casting")
        if len(registered_voters) > 0:
            voter_id_vote = st.text_input("Enter your Voter ID to Vote", key="voter_id_vote")
            candidate_vote = st.selectbox("Select Candidate", candidate_list, key="voter_candidate_select")
            if st.button("Cast Vote", key="voter_cast_vote_btn"):
                if voter_id_vote not in registered_voters:
                    st.error("You must register before voting.")
                elif voter_id_vote in blockchain.voters:
                    st.error("You have already voted.")
                else:
                    receipt_id = hashlib.sha256(f"{voter_id_vote}{candidate_vote}{time.time()}".encode()).hexdigest()[:10]
                    success = blockchain.add_transaction(voter_id_vote, candidate_vote, receipt_id)
                    if success:
                        voter_info = registered_voters[voter_id_vote]
                        votes_table.loc[len(votes_table)] = [
                            voter_id_vote, voter_info['name'], voter_info['email'], voter_info['domain'],
                            candidate_vote, receipt_id, time.strftime("%Y-%m-%d %H:%M:%S")
                        ]
                        st.success(f"Vote cast successfully! Your receipt: {receipt_id}")
                    else:
                        st.error("You have already voted!")
        else:
            st.info("Register first to cast your vote.")

    # Vote Checking by Receipt
    with voter_subtab[1]:
        st.subheader("Check Vote by Receipt")
        check_receipt = st.text_input("Enter your receipt ID to verify vote", key="voter_check_receipt")
        if st.button("Check Vote", key="voter_check_vote_btn"):
            found = False
            for tx in blockchain.get_all_transactions():
                if tx['receipt_id'] == check_receipt:
                    st.success(f"Vote found: {tx}")
                    found = True
                    break
            if not found:
                st.warning("Receipt not found.")

# --- QR Code Voting with Sub-tabs ---
with tab4:
    st.header("QR Code Voting")
    qr_subtab = st.tabs(["Candidates QR Code", "QR Scanner", "Live QR Vote Tally"])

    # Candidates QR Code
    with qr_subtab[0]:
        st.subheader("Candidates QR Code")
        if candidate_list:
            for cand in candidate_list:
                col1, col2 = st.columns([1, 4])
                with col1:
                    qr = qrcode.QRCode(box_size=4, border=2)
                    qr.add_data(cand)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    buf = BytesIO()
                    img.save(buf)
                    st.image(buf.getvalue(), caption=f"QR for {cand}")
                with col2:
                    st.write(f"**{cand}**")
        else:
            st.info("No candidates yet. Add candidates in the Admin Panel.")

    # Simulate Scanning QR Code
    with qr_subtab[1]:
        st.subheader("QR Scanner")
        if candidate_list:
            selected_cand = st.selectbox("Select Candidate QR to Scan", candidate_list, key="qr_sim_scan_select")
            if st.button("Scan QR (Simulate Vote)", key="qr_sim_scan_btn"):
                qr_vote_counts[selected_cand] = qr_vote_counts.get(selected_cand, 0) + 1
                st.success(f"Simulated QR vote for {selected_cand}! Total QR votes: {qr_vote_counts[selected_cand]}")
        else:
            st.info("Add candidates first to simulate QR voting.")

    # Live QR Vote Tally
    with qr_subtab[2]:
        st.subheader("Live QR Vote Tally")
        if qr_vote_counts:
            st.table([{"Candidate": k, "QR Votes": v} for k, v in qr_vote_counts.items()])
        else:
            st.info("No QR votes yet.")
