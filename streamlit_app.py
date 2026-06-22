import streamlit as st
import requests
import uuid
import base64

API_URL = st.secrets.get("API_URL", "http://127.0.0.1:8000")
API_KEY = st.secrets.get("API_SECRET_KEY", "")

HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

st.set_page_config(page_title="Home Intelligence Agent", page_icon="🏠", layout="centered")
st.title("🏠 Home Intelligence Agent")

# Custom styling
st.markdown("""
<style>
    [data-testid="stChatMessage"] {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
        margin-bottom: 8px;
        padding: 8px;
    }
</style>
""", unsafe_allow_html=True)


tab1, tab2, tab3 = st.tabs(["Chat", "Upload Documents", "Action History"])

# --- Chat Tab ---
with tab1:
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.button("New conversation"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    # Display chat history
    if st.session_state.messages:
        with st.expander(f"Chat history ({len(st.session_state.messages)} messages)"):
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

    # Image upload
    uploaded_image = st.file_uploader(
        "Attach a photo (optional)",
        type=["jpg", "jpeg", "png"],
        key="image_upload"
    )

    # Chat input
    if question := st.chat_input("Ask about your home..."):
        # Show user message immediately
        with st.chat_message("user"):
            st.write(question)
        st.session_state.messages.append({"role": "user", "content": question})

        payload = {
            "question": question,
            "thread_id": st.session_state.thread_id
        }

        if uploaded_image:
            image_bytes = uploaded_image.read()
            payload["image"] = base64.b64encode(image_bytes).decode("utf-8")

        # Show thinking spinner, then response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_URL}/api/ask",
                        json=payload,
                        headers=HEADERS,
                        timeout=60
                    )

                    if response.status_code == 401:
                        answer = "Authentication failed. Check your API key."
                    elif response.status_code == 200:
                        data = response.json()
                        answer = data["answer"]

                        if data.get("actions"):
                            action_lines = "\n".join(
                                f"\n> Action submitted: **{a['type']}**"
                                for a in data["actions"]
                            )
                            answer += action_lines

                        st.session_state.thread_id = data["thread_id"]
                    else:
                        answer = f"Error: {response.status_code} — {response.text}"

                except requests.exceptions.Timeout:
                    answer = "Request timed out. The server may be waking up, try again."
                except requests.exceptions.ConnectionError:
                    answer = "Could not connect to the API. Is the server running?"

            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

# --- Upload Tab ---
with tab2:
    st.subheader("Upload a home document")

    doc_type = st.selectbox("Document type", [
        "inspection_report",
        "mortgage",
        "appliance_manual",
        "warranty",
        "contractor_quote",
        "hoa_rules",
        "permit",
        "general"
    ])

    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt", "md"])

    if st.button("Upload & Ingest") and uploaded_file:
        with st.spinner("Ingesting document..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                data = {"doc_type": doc_type}
                response = requests.post(
                    f"{API_URL}/api/ingest",
                    files=files,
                    data=data,
                    headers=HEADERS,
                    timeout=120
                )

                if response.status_code == 200:
                    result = response.json()
                    if result["success"]:
                        st.success(f"Ingested {result['filename']} into {result['chunks_stored']} chunks.")
                    else:
                        st.error("Ingestion failed.")
                elif response.status_code == 401:
                    st.error("Authentication failed. Check your API key.")
                else:
                    st.error(f"Error: {response.status_code} — {response.text}")

            except requests.exceptions.Timeout:
                st.error("Upload timed out. Large documents may take longer.")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the API.")

# --- Action History Tab ---
with tab3:
    st.subheader("Action History")

    if st.button("Refresh"):
        st.rerun()

    try:
        response = requests.get(
            f"{API_URL}/api/actions/history",
            headers=HEADERS,
            timeout=10
        )

        if response.status_code == 200:
            actions = response.json().get("actions", [])

            if not actions:
                st.write("No actions yet.")
            else:
                for action in reversed(actions):
                    status_icon = "✅" if action["status"] == "complete" else "⏳"
                    st.markdown(
                        f"{status_icon} **{action['type']}** — "
                        f"{action['data']} — "
                        f"*{action['created_at'][:16]}*"
                    )
        elif response.status_code == 401:
            st.error("Authentication failed.")
        else:
            st.error(f"Error: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.write("Could not connect to the API.")