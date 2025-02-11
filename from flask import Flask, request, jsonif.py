from flask import Flask, request, jsonify
import yt_dlp
import requests

app = Flask(__name__)

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
        return {"error": str(e)}, 500


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


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "YouTube Transcript API is running!"})


@app.route("/transcript", methods=["GET"])
def transcript():
    video_url = request.args.get("video_url")
    if not video_url:
        return jsonify({"error": "Missing 'video_url' parameter"}), 400
    
    return jsonify(get_transcript(video_url))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=True)
