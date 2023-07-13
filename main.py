import os    
from PIL import Image    
import pyheif    
from flask import Flask, request, render_template, redirect, url_for, session    
from werkzeug.utils import secure_filename    
from google.cloud import vision    
from google.cloud import storage    
from google.cloud import secretmanager    
from werkzeug.security import check_password_hash
import cohere    
  
# Set up the Google Cloud Vision API client    
client = vision.ImageAnnotatorClient()

def get_secret(secret_id):    
    client = secretmanager.SecretManagerServiceClient()    
    secret_name = f"projects/driven-photon-381417/secrets/{secret_id}/versions/latest"
  
    # Use the secret_name directly to access the secret version    
    response = client.access_secret_version(name=secret_name)    
  
    return response.payload.data.decode('UTF-8')    
  
# Set up the Cohere client    
api_key = get_secret('cohere')  # replace with your actual API key   
hasp = get_secret('hashp')
GOOGLE_APPLICATION_CREDENTIALS = get_secret('KEYG')
co = cohere.Client(api_key)

  
app = Flask(__name__)    
app.secret_key = os.urandom(24)  # replace with your actual secret key    
  
input_message = "This is unstructured text from an intake at a restraining order legal clinic. Please extract the relevant information for the restraining order -- meaning only the information about what happened and when, ignoring the scanned fields from the form (like ATTORNEY OR PARTY WITHOUT AN ATTORNEY). Output an outline with dates and events."    
  
@app.route('/login', methods=['GET', 'POST'])    
def login():    
    if request.method == 'POST':    
        master_password_hash = hasp  # replace with your actual master password hash    
        if not check_password_hash(master_password_hash, request.form['password']):    
            return render_template('login.html', error='Invalid password')    
        else:    
            session['logged_in'] = True    
            return redirect(url_for('upload_file'))    
    return render_template('login.html')    
  
@app.route('/logout')    
def logout():    
    session.pop('logged_in', None)    
    return redirect(url_for('login'))    
  
@app.route('/', methods=['GET', 'POST'])    
def upload_file():    
    if not session.get('logged_in'):    
        return redirect(url_for('login'))    
  
    if request.method == 'POST':      
        # check if the post request has the file part      
        if 'file' not in request.files:      
            return redirect(request.url)      
  
        file = request.files['file']      
  
        # if user does not select file, browser also      
        # submit an empty part without filename      
        if file.filename == '':      
            return redirect(request.url)      
  
        if file:      
            if file.filename.lower().endswith('.heic'):      
                heif_file = pyheif.read(file.read())      
                image = Image.frombytes(      
                    heif_file.mode,      
                    heif_file.size,      
                    heif_file.data,      
                    "raw",      
                    heif_file.mode,      
                    heif_file.stride,      
                )      
                filename = secure_filename(file.filename.rsplit('.', 1)[0] + '.jpeg')      
                image.save(filename)      
            else:      
                filename = secure_filename(file.filename)      
                file.save(filename)      
  
            # Upload file to Google Cloud Storage      
            storage_client = storage.Client()      
            bucket = storage_client.get_bucket('lassd')
            blob = bucket.blob(filename)      
            blob.upload_from_filename(filename)      
  
            # Process images with Google Vision API      
            vision_client = vision.ImageAnnotatorClient()      
            image = vision.Image()      
            image.source.image_uri = 'gs://lassd/' + filename      
  
            response = vision_client.text_detection(image=image)      
            texts = response.text_annotations      
  

            prompt = input_message + " " + texts[0].description  

            response = co.generate(
                model='command-nightly',
                prompt = prompt,
                max_tokens=800,
                temperature=0.5)

            intro_paragraph = response.generations[0].text

            print(intro_paragraph) 
    
  
            # Return the extracted text and the generated text      
            return render_template('result.html', extracted_text=texts[0].description, generated_text=intro_paragraph)      
  
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)




