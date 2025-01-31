import json

import whisper
from flask import Blueprint, request, render_template, current_app
from ollama import chat, ChatResponse

from shared import base

products_voice_filter_bp = Blueprint('products-voice-filter', __name__, template_folder='templates', url_prefix='/api')

message_template = {
    "role": "user",
    "content": "Переспроси. Отвечай в JSON."
}

model = whisper.load_model("turbo")

@products_voice_filter_bp.route('/products-voice-filter', methods=['POST'])
def products_filter():
    # TODO: implement authorization
    try:
        # Retrieve the uploaded audio file from the form
        audio_file = request.files.get('audio_file')
        if not audio_file or audio_file.filename == '':
            flash('No audio file provided.', 'error')
            return redirect(url_for('index'))

        if not allowed_file(audio_file.filename):
            flash('Invalid audio file type. Allowed types: wav, webm, mp3.', 'error')
            return redirect(url_for('index'))

        # Secure the filename and save the file
        filename = secure_filename(audio_file.filename)
        temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
        audio_file.save(temp_audio_path)

        # (Optional) Convert to WAV if necessary
        # wav_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"voice_input_{int(time.time())}.wav")
        # if convert_to_wav(temp_audio_path, wav_audio_path):
        #     os.remove(temp_audio_path)
        #     transcription_file_path = wav_audio_path
        # else:
        #     os.remove(temp_audio_path)
        #     flash('Audio conversion failed.', 'error')
        #     return redirect(url_for('index'))

        # Transcribe using Whisper
        with open(temp_audio_path, "rb") as f:
            transcription = model.transcribe(f)
        text_query = transcription.text.strip()
        print("Transcription:", text_query)

        # Remove the uploaded audio file after transcription
        os.remove(temp_audio_path)

        if not text_query:
            raise ValueError("No transcription text received.")


        message_template["content"] = text_query
        
        response: ChatResponse = chat(model='testy', messages = [message_template])

        print(response['message']['content'])

        
        return render_template('result.html', query=text_query, response=response_text)

    except Exception as e:
        response_text = f"Error processing query: {str(e)}"
        return render_template('result.html', response=response_text)



