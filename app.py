import streamlit as st
from main import setup_agent, Session, User, Chat
from werkzeug.security import generate_password_hash, check_password_hash
import json
import datetime  # Add this at the top with other imports

# Database session
def get_db():
    return Session()

# Authentication functions
def register_user(username, password, email):
    db = get_db()
    try:
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password, email=email)
        db.add(new_user)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        return False

def authenticate_user(username, password):
    db = get_db()
    user = db.query(User).filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        return user
    return None

# Chat management functions
def save_chat(user_id, messages, chat_name=None, chat_id=None):
    db = get_db()
    try:
        if chat_id:  # Update existing chat
            chat = db.query(Chat).filter_by(id=chat_id).first()
            if chat:
                chat.messages = json.dumps(messages)
                chat.timestamp = datetime.datetime.now()
                db.commit()
                return chat.id
        else:  # Create new chat
            if not chat_name:
                chat_name = f"Chat {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            new_chat = Chat(
                user_id=user_id,
                chat_name=chat_name,
                messages=json.dumps(messages)
            )
            db.add(new_chat)
            db.commit()
            return new_chat.id
        return None
    except Exception as e:
        db.rollback()
        return None

def load_chat(chat_id):
    db = get_db()
    chat = db.query(Chat).filter_by(id=chat_id).first()
    if chat:
        return json.loads(chat.messages)
    return []

def delete_chat(chat_id):
    db = get_db()
    try:
        chat = db.query(Chat).filter_by(id=chat_id).first()
        if chat:
            db.delete(chat)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        return False

# Streamlit UI
st.set_page_config(page_title="🛒 AI Shopping Assistant", page_icon="🛍", layout="wide")

st.markdown("""
        <style>
                .e1xss9yb2{
                    display: none !important;
                    background : transparent !important;
                }
                 
                .stVerticalBlock .st-emotion-cache-izam2r{
                    margin-bottom: 0px;
                    gap: 0px !important;
                }

                .stSelectbox {
                    cursor: pointer;
                }
        </style>
                
    """,unsafe_allow_html=True)
# Add this custom CSS
# st.markdown("""
#     <style>
#         /* Target specific chat item by its ID */
#         div.chat-item-3 > div[data-testid="stVerticalBlock"] {
#             gap: 0 !important;
#             row-gap: 0 !important;
#             column-gap: 0 !important;
#         }
#     </style>
# """, unsafe_allow_html=True)

# Authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.current_chat_id = None

# Authentication sidebar
if not st.session_state.authenticated:
    st.sidebar.title("User Authentication")
    auth_choice = st.sidebar.selectbox("Choose Option", ["Login", "Register"])
    
    if auth_choice == "Login":
        st.markdown("## Login")
        with st.form("Login"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔑 Password", type="password")
            if st.form_submit_button("🚀 Login"):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("⚠️ Invalid credentials. Please try again.")
    
    elif auth_choice == "Register":
        st.markdown("## Register")
        with st.form("Register"):
            new_username = st.text_input("👤 New Username")
            new_email = st.text_input("📧 Email")
            new_password = st.text_input("🔒 New Password", type="password")
            confirm_password = st.text_input("🔑 Confirm Password", type="password")
            if st.form_submit_button("Register"):
                if new_password == confirm_password:
                    if register_user(new_username, new_password, new_email):
                        st.success("🎉 Registration successful! Please login.")
                    else:
                        st.error("⚠️ Username already exists")
                else:
                    st.error("🔒 Passwords do not match")
    st.stop()

# Main application after authentication
# Chat management sidebar
# st.sidebar.title("🎯 AI Shopping Assistant")
st.sidebar.title(f"👋 Hi, {st.session_state.user.username}!")

st.sidebar.button("➕ New Chat", on_click=lambda: st.session_state.update({
    'messages': [],
    'current_chat_id': None
}))

st.sidebar.title("Your Recent Chats")

# Load user chats
db = get_db()
user_chats = db.query(Chat).filter_by(user_id=st.session_state.user.id).order_by(Chat.timestamp.desc()).all()


for chat in user_chats:
    is_active = chat.id == st.session_state.current_chat_id

    # Chat item container
    col1, col2 = st.sidebar.columns([5, 1])
    with col1:
        # Clickable chat name
        if st.button(
            f"📝 {chat.chat_name}", 
            key=f"chat_{chat.id}",
            help="Click to load chat",
            use_container_width=True
        ):
            st.session_state.messages = load_chat(chat.id)
            st.session_state.current_chat_id = chat.id
            st.session_state.agent = setup_agent(chat_history=st.session_state.messages)
            st.rerun()
        
        # Hidden HTML styling element
        st.markdown(
            f"<div class='chat-item-{chat.id}'></div>", 
            unsafe_allow_html=True
        )

    with col2:
        # Delete button
        if st.button("🗑️", key=f"delete_{chat.id}", help="Delete chat"):
            delete_chat(chat.id)
            if st.session_state.current_chat_id == chat.id:
                st.session_state.messages = []
                st.session_state.current_chat_id = None
            st.rerun()

st.sidebar.markdown("## 📌 How to Use")
st.sidebar.markdown("""
- 💡 Ask about product recommendations, availability, or pricing.
- 🛒 Example Queries:
    - 📱 *"What are the best smartphones under 50,000?"*
    - 💻 *"Find me a laptop for gaming."*
    - 📷 *"Compare iPhone 14 and Samsung Galaxy S23."*
""")

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout", help="Click to logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.messages = []
    st.session_state.current_chat_id = None
    st.session_state.agent = None
    st.rerun()

# Main chat interface
st.title("AI Shopping Assistant 🤖")
    
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize agent and chat history
if "agent" not in st.session_state:
    # Load agent with existing messages if any
    st.session_state.agent = setup_agent(chat_history=st.session_state.messages)

# Display messages
# Display welcome message if no chat history
if not st.session_state.messages:
    st.markdown("## 🌟 Getting Started Guide")
    st.markdown("""
    **💡 Ask about:**
    - Product recommendations
    - Price comparisons
    - Feature specifications

    **🛒 Try these examples:**
    - *"Best smartphones under ₹50,000?"*
    - *"Find me a gaming laptop under 80k"*
    - *"Compare complete specifications of iPhone 15 and Samsung S24"*

    **🔍 Pro tip:** Add your preferred brands or features for better results!
    """)
else:
    # Display existing messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Handle user input
# Handle user input
if prompt := st.chat_input("What can I help you with? 🤔"):
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Append user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get agent response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner("🔄 Thinking..."):
            try:
                result = st.session_state.agent.invoke({"input": prompt})
                full_response = result['output']
            except Exception as e:
                full_response = f"❌ An error occurred: {e}"
        
        message_placeholder.markdown(full_response)
    
    # Append assistant response
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # Auto-save chat (fix datetime reference)
    # Auto-save chat
if len(st.session_state.messages) > 2:
    if not st.session_state.current_chat_id:
        # Create new chat
        chat_name = f"Chat {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        chat_id = save_chat(
            user_id=st.session_state.user.id,
            messages=st.session_state.messages,
            chat_name=chat_name
        )
        st.session_state.current_chat_id = chat_id
    else:
        # Update existing chat
        save_chat(
            user_id=st.session_state.user.id,
            messages=st.session_state.messages,
            chat_id=st.session_state.current_chat_id
        )