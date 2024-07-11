from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import io
import base64
from PIL import Image
import pdf2image
import google.generativeai as genai
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Configure the Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

application = Flask(__name__)

def get_gemini_response(input_text, pdf_content, prompt):
    try:
        model = genai.GenerativeModel('gemini-pro-vision')
        response = model.generate_content([input_text, pdf_content[0], prompt])
        return response.text
    except Exception as e:
        logging.error(f"Error generating content: {e}")
        raise

def input_pdf_setup(uploaded_file):
    try:
        # Convert the PDF to image
        images = pdf2image.convert_from_bytes(uploaded_file.read())
        first_page = images[0]

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        pdf_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()  # encode to base64
            }
        ]
        return pdf_parts
    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        raise

@application.route('/')
def index():
    return render_template('index.html')

@application.route('/analyze_resume', methods=['POST'])
def analyze_resume():
    data = request.form
    input_text = data.get('input_text')
    prompt_type = data.get('prompt_type')

    uploaded_file = request.files.get('uploaded_file')
    if not uploaded_file:
        return jsonify({"error": "Please upload the resume"}), 400

    try:
        pdf_content = input_pdf_setup(uploaded_file)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if prompt_type == 'evaluation':
        input_prompt = """
        You are an experienced Technical Human Resource Manager in the field of any one job role of Data Science, Data Analytics, DEVOPS, 
        Big data engineer, full stack web and app development. Your task is to review the provided resume against the job description. 
        Please share your professional evaluation on whether the candidate's profile aligns with the role. 
        Highlight the strengths and weaknesses of the applicant in relation to the specified job requirements.
        """
    elif prompt_type == 'match_percentage':
        input_prompt = """
        You are a skilled ATS (Applicant Tracking System) scanner with a deep understanding in the field of any one job role of Data Science, Data Analytics, DEVOPS, 
        Big data engineer, full stack web and app development, and deep ATS functionality. 
        Your task is to evaluate the resume against the provided job description. Give me the percentage of match if the resume matches
        the job description. First, the output should come as percentage and then keywords missing and last final thoughts.
        """
    else:
        return jsonify({"error": "Invalid prompt type"}), 400

    try:
        response = get_gemini_response(input_text, pdf_content, input_prompt)
        return jsonify({"response": response}), 200
    except Exception as e:
        logging.error(f"Error in generating response: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    application.run(port=8000)
