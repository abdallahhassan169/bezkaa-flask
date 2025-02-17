from flask import Flask, request, jsonify
import yt_dlp
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import re
import requests
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

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
        print(e)
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
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"] , proxies={'http':'133.18.234.13:80'})
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







headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
@app.route('/fetch_transcript', methods=['GET'])
def fetch_transcripty():
    try:
        # Step 1: Get the video URL from the request parameters
        url = request.args.get('url' , headers)
        if not url:
            return jsonify({"error": "URL parameter is required"}), 400

        # Step 2: Make a GET request to the YouTube video page
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses

        # Step 3: Extract all base URLs
        transcript_urls = re.findall(r'"baseUrl":"(https:\/\/www\.youtube\.com\/api\/timedtext[^"]+)"', response.text)
        return jsonify({"transcript": str(response.text)})
        if transcript_urls:
            # Step 4: Clean the URLs
            cleaned_urls = [url.replace("\\u0026", "&") for url in transcript_urls]

            # Step 5: Fetch the transcript from the first URL
            transcript_response = requests.get(cleaned_urls[0] + "&fmt=json3")
            transcript_response.raise_for_status()
            transcript_data = transcript_response.json()

            # Step 6: Extract the text segments
            events = transcript_data.get("events", [])
            text_segments = [seg["utf8"] for event in events for seg in event.get("segs", []) if "utf8" in seg]

            # Combine all text segments
            final_text = "".join(text_segments)

            # Step 7: Return the extracted text
            return jsonify({"transcript": final_text})
        else:
            return jsonify({"message": "No transcript URLs found."}), 404

    except Exception as e:
        return jsonify({"error": f"Error fetching transcript: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=True)
