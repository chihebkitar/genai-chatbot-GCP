import os
import json
import subprocess
import shlex
import tempfile
from pathlib import Path
from tempfile import mkdtemp

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from streamlit.logger import get_logger

from yt_whisper.vtt_utils import merge_webvtt_to_list

load_dotenv(".env")
logger = get_logger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_TOKEN"))

@st.cache_resource
def load_pinecone(index_name="docker-genai"):
    pc = Pinecone(api_key=os.getenv("PINECONE_TOKEN"))
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return pc.Index(index_name)

@st.cache_data
def process_video(video_url: str) -> dict[str, str]:
    # Fetch metadata via yt-dlp JSON
    try:
        meta = json.loads(subprocess.check_output(
            shlex.split(f"yt-dlp --dump-json '{video_url}'"), stderr=subprocess.DEVNULL
        ))
    except Exception as e:
        st.error(f"Failed to fetch YouTube metadata: {e}", icon="🚨")
        return

    video_id = meta["id"]
    title = meta["title"]
    thumbnail = meta.get("thumbnail", "")

    with st.spinner("Downloading audio…"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / f"{video_id}.mp3"
            cmd = f"yt-dlp --no-cache-dir -x --audio-format mp3 -o '{output_path}' '{video_url}'"
            try:
                subprocess.run(shlex.split(cmd), check=True)
            except subprocess.CalledProcessError as e:
                st.error(f"Audio download failed: {e}", icon="🚨")
                return

            audio_file = str(output_path)
            size = os.stat(audio_file).st_size
            if size > 25 * 1024 * 1024:
                st.error("Video too large (>25MB). Pick a shorter clip.", icon="🚨")
                return

            transcript_vtt = client.audio.transcriptions.create(
                model="whisper-1", file=open(audio_file, "rb"), response_format="vtt"
            )
            logger.info("Transcription done")

            transcript = merge_webvtt_to_list(transcript_vtt, 8)
            stride, batch = 3, []

            def upload(batch):
                idx = load_pinecone()
                texts = [b["text"] for b in batch]
                ids = [b["id"] for b in batch]
                metas = [
                    {
                        "initial_time": b["initial_time"],
                        "title": title,
                        "thumbnail": thumbnail,
                        "video_url": f"{video_url}&t={b['initial_time']}s",
                        "text": b["text"],
                    }
                    for b in batch
                ]
                embeds = client.embeddings.create(input=texts, model="text-embedding-3-small")
                idx.upsert(list(zip(ids, [e.embedding for e in embeds.data], metas)))

            for i in range(0, len(transcript), stride):
                start = transcript[i]["initial_time_in_seconds"]
                batch.append({"id": f"{video_id}-t{start}", "initial_time": start,
                              "text": " ".join(t["text"] for t in transcript[i:i+stride]).replace("\n"," ")})
                if len(batch) >= 64:
                    upload(batch); batch.clear()

            if batch:
                upload(batch)

            out_file = st.session_state.tempfolder / f"{video_id}.txt"
            out_file.write_text(transcript_vtt)

            return {"video_id": video_id, "title": title, "thumbnail": thumbnail}

def disable(b):
    st.session_state.processing = b

def main():
    if "tempfolder" not in st.session_state:
        st.session_state.tempfolder = Path(mkdtemp(prefix="yt_transcription_"))
    if "videos" not in st.session_state:
        st.session_state.videos = []
    if "processing" not in st.session_state:
        st.session_state.processing = False

    st.header("Chat with your YouTube videos")
    url = st.text_input("YouTube URL", "https://www.youtube.com/watch?v=8CY2aq3tcXA")
    if st.button("Submit", on_click=disable, args=(True,), disabled=st.session_state.processing):
        result = process_video(url)
        if result:
            st.session_state.videos.append(result)
        st.session_state.processing = False
        st.rerun()

    st.header("Processed videos")
    for vid in st.session_state.videos:
        st.subheader(vid["title"])
        st.image(vid["thumbnail"], width=320)
        if st.button("Download transcript", key=vid["video_id"]):
            path = st.session_state.tempfolder / f"{vid['video_id']}.txt"
            with open(path) as f:
                st.download_button("Download", f, file_name=f"{vid['video_id']}.txt")

if __name__ == "__main__":
    main()
