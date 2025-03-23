import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from streamlit.logger import get_logger

 

logger = get_logger(__name__)

def get_secret(secret_path, env_var_name):
    """
    Attempt to read a secret from the given file path.
    If that fails, fall back to the environment variable.
    """
    try:
        with open(secret_path, "r") as f:
            secret = f.read().strip()
            if secret:
                return secret
    except Exception as e:
        logger.warning(f"Could not read secret from {secret_path}: {e}")
    # Fall back to environment variable
    return os.getenv(env_var_name)

# Retrieve the OpenAI API key from the mounted secret file
openai_api_key = get_secret("/mnt/secrets-store/OPENAI_TOKEN", "OPENAI_TOKEN")
if not openai_api_key:
    raise Exception("OpenAI API key not found in secret file or environment variable")

client = OpenAI(api_key=openai_api_key)

@st.cache_resource
def load_pinecone(index_name="docker-genai"):
    # Retrieve Pinecone token similarly if needed:
    pinecone_token = get_secret("/mnt/secrets-store/PINECONE_TOKEN", "PINECONE_TOKEN")
    if not pinecone_token:
        raise Exception("Pinecone API key not found in secret file or environment variable")
    # initialize pinecone
    pc = Pinecone(api_key=pinecone_token)
    if index_name not in pc.list_indexes().names():
        logger.info(f"Creating index {index_name}, therefore there are no videos yet.")
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-west-2"),
        )
    index = pc.Index(index_name)
    return index

def generate_response(input_text):
    question_embedding = client.embeddings.create(
        input=[input_text], model="text-embedding-3-small"
    )
    num_embeddings = list(question_embedding.data[0].embedding)
    res_contex = load_pinecone().query(
        vector=num_embeddings,
        top_k=5,
        include_metadata=True,
    )

    matches = res_contex["matches"]

    context = (
        "The following are the top 5 videos transcription that match your query: \n"
    )
    references = ""
    for match in matches:
        context += "Title: " + match.metadata["title"] + "\n"
        context += "Transcription: " + match.metadata["text"] + "\n"
        references += "\n - " + match.metadata["video_url"] + "\n"

    primer = """You are Q&A bot. A highly intelligent system that answers 
    user questions based on the information provided by videos transcriptions. You can use your inner knowledge,
    but consider more with emphasis the information provided. Put emphasis on the transcriptions provided. If you see titles repeated, you can assume it is the same video.
    Provide samples of the transcriptions that are important to your query.
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": primer},
            {
                "role": "user",
                "content": context,
            },
            {"role": "user", "content": input_text},
        ],
        model="gpt-4-turbo-preview",
    )
    response = chat_completion.choices[0].message.content

    response += "\n Click on the following for more information: " + references

    return response

logger = get_logger(__name__)

# Streamlit UI remains unchanged...
styl = """
<style>
    /* Styles omitted for brevity */
</style>
"""
st.markdown(styl, unsafe_allow_html=True)

def chat_input():
    user_input = st.chat_input("What you want to know about your videos?")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            st.caption("Dockerbot")
            result = generate_response(user_input)
            st.session_state["user_input"].append(user_input)
            st.session_state["generated"].append(result)
            st.rerun()

def display_chat():
    if "generated" not in st.session_state:
        st.session_state["generated"] = []
    if "user_input" not in st.session_state:
        st.session_state["user_input"] = []
    if st.session_state["generated"]:
        size = len(st.session_state["generated"])
        for i in range(max(size - 3, 0), size):
            with st.chat_message("user"):
                st.write(st.session_state["user_input"][i])
            with st.chat_message("assistant"):
                st.caption("Dockerbot")
                st.write(st.session_state["generated"][i])
        with st.container():
            st.write("&nbsp;")

display_chat()
chat_input()
