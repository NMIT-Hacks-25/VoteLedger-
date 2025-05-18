from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import time
import hashlib
from collections import defaultdict
import pandas as pd
from flask import send_file
import qrcode
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---- User Management ----
USERS_FILE = 'users.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

# ---- Blockchain Classes ----
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
            return False
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
        for block in self.chain[1:]:
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

# ---- Global State ----
blockchain = Blockchain()
candidate_list = []
qr_vote_counts = {}
registered_voters = {}  # voter_id: {name, email, domain}
votes_table = []        # list of dicts: {'Voter ID', 'Name', 'Email', 'Domain', 'Candidate', 'Receipt', 'Timestamp'}

# ---- Login Required Decorator ----
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---- Auth Routes ----
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']
        users = load_users()
        if email in users or any(u['mobile'] == mobile for u in users.values()):
            error = "Email or mobile already registered."
        else:
            users[email] = {"username": username, "mobile": mobile, "password": password}
            save_users(users)
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users = load_users()
        user = users.get(email)
        if user and user['password'] == password:
            session['user'] = email
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid credentials."
    # Pass hide_nav_footer=True to hide navbar and footer on login page
    return render_template('login.html', error=error, hide_nav_footer=True)


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# ---- QR code-----

@app.route('/download_qr/<candidate>')
@login_required
def download_qr(candidate):
    if candidate not in candidate_list:
        flash("Candidate not found.")
        return redirect(url_for('qr_code_voting'))
    # Generate QR code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(candidate)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(
        buf,
        mimetype='image/png',
        as_attachment=True,
        download_name=f"{candidate}_qr.png"
    )


# ---- Dashboard ----
@app.route('/dashboard')
@login_required
def dashboard():
    num_candidates = len(candidate_list)
    num_voters = len(registered_voters)
    results = blockchain.get_results()
    total_votes = sum(results.values())
    turnout = f"{(total_votes/num_voters*100):.1f}%" if num_voters else "0%"
    latest_block_hash = blockchain.chain[-1].hash if blockchain.chain else "N/A"
    return render_template(
        'dashboard.html',
        active_tab='dashboard',
        num_candidates=num_candidates,
        num_voters=num_voters,
        total_votes=total_votes,
        turnout=turnout,
        latest_block_hash=latest_block_hash
    )

# ---- Admin Panel ----
@app.route('/admin_panel', methods=['GET', 'POST'])
@login_required
def admin_panel():
    global candidate_list, qr_vote_counts
    tab = request.args.get('tab', 'candidate')
    message = None

    # Candidate Updation
    if tab == 'candidate':
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                new_candidate = request.form.get('new_candidate')
                if new_candidate and new_candidate not in candidate_list:
                    candidate_list.append(new_candidate)
                    qr_vote_counts[new_candidate] = 0
                    message = f"Added candidate: {new_candidate}"
                else:
                    message = "Candidate already exists or name is empty."
            elif action == 'remove':
                remove_candidate = request.form.get('remove_candidate')
                if remove_candidate in candidate_list:
                    candidate_list.remove(remove_candidate)
                    qr_vote_counts.pop(remove_candidate, None)
                    message = f"Removed candidate: {remove_candidate}"

    # Mine Blocks & Results
    if tab == 'mine':
        if request.method == 'POST':
            if request.form.get('action') == 'mine':
                if blockchain.mine():
                    message = "Block mined successfully!"
                else:
                    message = "No pending votes to mine."

    # Voters Table
    votes_tbl = votes_table

    # Blockchain Info
    results = blockchain.get_results()
    block_info = blockchain.get_block_info()

    # Fraud Detection Tab
    flagged_df = None
    if tab == 'fraud':
        voters_df = pd.DataFrame([
            {'Voter ID': voter_id, 'Name': v['name'], 'Email': v['email'], 'Domain': v['domain']}
            for voter_id, v in registered_voters.items()
        ])
        votes_table_df = pd.DataFrame(votes_table)
        suspicious_domains = ['spam.com', 'fake.com', 'test.com']
        flagged = set()

        # 1. Flag emails with suspicious domains
        for idx, row in voters_df.iterrows():
            email = row['Email'].lower()
            if any(email.endswith("@" + s) for s in suspicious_domains):
                flagged.add(idx)

        # 2. Flag if more than 3 voters from the same domain voted for the same candidate
        if not votes_table_df.empty:
            group = votes_table_df.groupby(['Domain', 'Candidate']).size().reset_index(name='Count')
            suspicious_groups = group[group['Count'] > 3]
            for _, row in suspicious_groups.iterrows():
                mask = (votes_table_df['Domain'] == row['Domain']) & (votes_table_df['Candidate'] == row['Candidate'])
                flagged.update(votes_table_df[mask].index.tolist())

        flagged = list(flagged)
        flagged_df = voters_df.loc[flagged] if not voters_df.empty and flagged else pd.DataFrame()

    return render_template(
        'admin_panel.html',
        active_tab='admin',
        tab=tab,
        candidate_list=candidate_list,
        message=message,
        results=results,
        block_info=block_info,
        votes_table=votes_tbl,
        flagged_df=flagged_df
    )

# ---- Voter Panel ----
@app.route('/voter_panel', methods=['GET', 'POST'])
@login_required
def voter_panel():
    tab = request.args.get('tab', 'registration')
    message = None
    vote_message = None

    if tab == 'registration':
        if request.method == 'POST':
            voter_id = request.form.get('voter_id')
            name = request.form.get('name')
            email = request.form.get('email')
            domain = request.form.get('domain')
            if not voter_id or not name or not email or not domain:
                message = "All fields are required."
            elif voter_id in registered_voters:
                message = "Voter ID already registered."
            elif any(email == v['email'] for v in registered_voters.values()):
                message = "This email is already registered."
            else:
                registered_voters[voter_id] = {'name': name, 'email': email, 'domain': domain}
                message = "Registration successful!"

        # Vote Casting
        if request.form.get('vote_action') == 'vote':
            voter_id_vote = request.form.get('voter_id_vote')
            candidate_vote = request.form.get('candidate_vote')
            if voter_id_vote not in registered_voters:
                vote_message = "You must register before voting."
            elif voter_id_vote in blockchain.voters:
                vote_message = "You have already voted."
            else:
                receipt_id = hashlib.sha256(f"{voter_id_vote}{candidate_vote}{time.time()}".encode()).hexdigest()[:10]
                success = blockchain.add_transaction(voter_id_vote, candidate_vote, receipt_id)
                if success:
                    voter_info = registered_voters[voter_id_vote]
                    votes_table.append({
                        'Voter ID': voter_id_vote,
                        'Name': voter_info['name'],
                        'Email': voter_info['email'],
                        'Domain': voter_info['domain'],
                        'Candidate': candidate_vote,
                        'Receipt': receipt_id,
                        'Timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    vote_message = f"Vote cast successfully! Your receipt: {receipt_id}"
                else:
                    vote_message = "You have already voted!"

    # Vote Validator
    check_result = None
    if tab == 'validator' and request.method == 'POST':
        check_receipt = request.form.get('check_receipt')
        found = False
        for tx in blockchain.get_all_transactions():
            if tx['receipt_id'] == check_receipt:
                check_result = f"Vote found: {tx}"
                found = True
                break
        if not found:
            check_result = "Receipt not found."

    return render_template(
        'voter_panel.html',
        active_tab='voter',
        tab=tab,
        candidate_list=candidate_list,
        message=message,
        vote_message=vote_message,
        registered_voters=registered_voters,
        check_result=check_result
    )

from datetime import datetime

@app.context_processor
def inject_now():
    return {'current_year': datetime.now().year}

# ---- QR Code Voting ----
@app.route('/qr_code_voting', methods=['GET', 'POST'])
@login_required
def qr_code_voting():
    import qrcode
    import base64
    from io import BytesIO
    tab = request.args.get('tab', 'candidates')
    message = None

    # Simulate QR scan
    if tab == 'scanner' and request.method == 'POST':
        selected_cand = request.form.get('selected_cand')
        if selected_cand in candidate_list:
            qr_vote_counts[selected_cand] = qr_vote_counts.get(selected_cand, 0) + 1
            message = f"Simulated QR vote for {selected_cand}! Total QR votes: {qr_vote_counts[selected_cand]}"
        else:
            message = "Invalid candidate selected."

    # Generate QR codes for candidates
    qr_images = {}
    if candidate_list:
        for cand in candidate_list:
            qr = qrcode.QRCode(box_size=4, border=2)
            qr.add_data(cand)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf)
            img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            qr_images[cand] = img_b64

    return render_template(
        'qr_code_voting.html',
        active_tab='qr',
        tab=tab,
        candidate_list=candidate_list,
        qr_images=qr_images,
        qr_vote_counts=qr_vote_counts,
        message=message
    )

if __name__ == '__main__':
    app.run(debug=True)
