from flask import Flask, request, jsonify
import yt_dlp
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Helper function to extract video ID from URL
def get_video_id(url):
    parsed_url = urlparse(url)
    video_id = None
    
    if "youtube.com" in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
    elif "youtu.be" in parsed_url.netloc:
        video_id = parsed_url.path.strip('/')

    return video_id

# Function to fetch transcript using yt-dlp
def get_transcript(video_url):
    ydl_opts = {
        'skip_download': True,  # Don't download video
        'writesubtitles': True,  # Fetch subtitles
        'writeautomaticsub': True,  # Fetch auto-generated subtitles
        'quiet': True,
        #  'proxy': '155.54.239.64:80'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            subtitles = info.get("subtitles", {})
            auto_captions = info.get("automatic_captions", {})

            transcript_url = None
            original_lang = None

            # Check manually uploaded subtitles first
            if subtitles:
                original_lang = list(subtitles.keys())[0]  # First available language
                transcript_url = subtitles[original_lang][0]["url"]
            
            # If no manually uploaded subtitles, check auto-generated captions
            elif auto_captions:
                original_lang = list(auto_captions.keys())[0]  # First available language
                transcript_url = auto_captions[original_lang][0]["url"]

            if not transcript_url:
                return {"error": "No transcript available"}, 404

            # Fetch transcript text
            transcript_text = fetch_transcript_text(transcript_url)

            return {"transcript": transcript_text, "original_language": original_lang}

    except Exception as e:
        return {"error": str(e)}, 500

# Helper function to fetch transcript text from URL
def fetch_transcript_text(transcript_url):
    try:
        response = requests.get(transcript_url)
        data = response.json()  # Load JSON3 formatted data
        
        transcript = ""
        for entry in data.get("events", []):  # Iterate through caption segments
            if "segs" in entry:
                transcript += " ".join(seg["utf8"] for seg in entry["segs"]) + " "

        return transcript.strip()
    
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"

# Function to fetch transcript using youtube-transcript-api
def get_transcript_api(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        full_text = " ".join([t["text"] for t in transcript])
        return {"transcript": full_text}
    except Exception as e:
        print(e)
        return {"error": str(e)}

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "YouTube Transcript API is running!"})

# Endpoint using yt-dlp to get transcript
@app.route("/transcript", methods=["GET"])
def transcript_dlp():
    video_url = request.args.get("video_url")
    if not video_url:
        return jsonify({"error": "Missing 'video_url' parameter"}), 400
    
    return jsonify(get_transcript(video_url))

# Endpoint using youtube-transcript-api to get transcript
@app.route("/transcript-api", methods=["GET"])
def transcript_api():
    video_url = request.args.get("video_url")
    
    if not video_url:
        return jsonify({"error": "Missing 'video_url' parameter"}), 400
    
    video_id = get_video_id(video_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    return jsonify(get_transcript_api(video_id))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=True)
