import streamlit as st
from PIL import Image
import numpy as np
import io
import pyqrcode
import wave
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64

def encrypt(plain_text, secret_key):
    # Ensure key length is 16, 24, or 32 bytes for AES
    key = secret_key.encode('utf-8')
    key = key.ljust(32, b'\0')[:32]  # Adjust the key length to 32 bytes

    # Generate a random initialization vector (IV)
    iv = get_random_bytes(AES.block_size)
    
    # Create AES cipher in CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    # Pad the plaintext to make sure it is a multiple of block size
    padded_text = pad(plain_text.encode('utf-8'), AES.block_size)
    
    # Encrypt the padded plaintext
    cipher_text = cipher.encrypt(padded_text)
    
    # Return the encrypted text along with the IV (encoded in base64)
    return base64.b64encode(iv + cipher_text).decode('utf-8')

def decrypt(encrypted_text, secret_key):
    # Ensure key length is 16, 24, or 32 bytes for AES
    key = secret_key.encode('utf-8')
    key = key.ljust(32, b'\0')[:32]  # Adjust the key length to 32 bytes
    
    # Decode the encrypted text from base64
    encrypted_data = base64.b64decode(encrypted_text)
    
    # Extract the IV from the encrypted data
    iv = encrypted_data[:AES.block_size]
    cipher_text = encrypted_data[AES.block_size:]
    
    # Create AES cipher in CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    # Decrypt the ciphertext and unpad the result
    decrypted_data = unpad(cipher.decrypt(cipher_text), AES.block_size)
    
    # Return the decrypted plaintext
    return decrypted_data.decode('utf-8')


# Function to encode text into an image
def encode_image(image, message, secret):
    img = image.convert('RGB')
    data = np.array(img)
    message = encrypt(message, secret) + "###"
    binary_message = ''.join(format(ord(char), '08b') for char in message)
    
    idx = 0
    for row in data:
        for pixel in row:
            for channel in range(3):
                if idx < len(binary_message):
                    pixel[channel] = (pixel[channel] & ~1) | int(binary_message[idx])
                    idx += 1
                else:
                    break
    encoded_img = Image.fromarray(data)
    return encoded_img

# Function to decode text from an image
def decode_image(image, secret):
    img = image.convert('RGB')
    data = np.array(img)
    binary_message = ""
    for row in data:
        for pixel in row:
            for channel in range(3):
                binary_message += str(pixel[channel] & 1)
    
    chars = [binary_message[i:i+8] for i in range(0, len(binary_message), 8)]
    extracted_message = ''.join(chr(int(char, 2)) for char in chars)
    if "###" in extracted_message:
        extracted_message = extracted_message[:extracted_message.index("###")]
    return decrypt(extracted_message, secret)

# Function to generate QR code
def generate_qr(data):
    qr = pyqrcode.create(data)
    return qr.png_as_base64_str(scale=5)

# Function to encode text into audio
def encode_audio(audio_path, message, output_path, secret):
    message = encrypt(message, secret) + "###"
    audio = wave.open(audio_path, 'rb')
    frames = bytearray(list(audio.readframes(audio.getnframes())))
    binary_message = ''.join(format(ord(i), '08b') for i in message)
    
    for i in range(len(binary_message)):
        frames[i] = (frames[i] & 254) | int(binary_message[i])
    
    encoded_audio = wave.open(output_path, 'wb')
    encoded_audio.setparams(audio.getparams())
    encoded_audio.writeframes(bytes(frames))
    encoded_audio.close()

# Function to decode text from audio
def decode_audio(audio_path, secret):
    audio = wave.open(audio_path, 'rb')
    frames = bytearray(list(audio.readframes(audio.getnframes())))
    binary_message = "".join(str(frames[i] & 1) for i in range(len(frames)))
    chars = [binary_message[i:i+8] for i in range(0, len(binary_message), 8)]
    extracted_message = ''.join(chr(int(char, 2)) for char in chars)
    if "###" in extracted_message:
        extracted_message = extracted_message[:extracted_message.index("###")]
    return decrypt(extracted_message, secret)


# Streamlit GUI
st.title("Steganography App 🚀")

# Navigation bar
selected = st.sidebar.selectbox("Navigation", ["Encode", "Decode"])
type = st.sidebar.selectbox("Select the type of data", ["Image", "Audio"])

if selected == "Encode":
    if type == "Image":
        uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "bmp"])
        message = st.text_area("Enter the secret message:")
        secret = st.text_input("Enter the Secret Key", type="password")
        if st.button("Encode and Download") and uploaded_image and message and secret:
            image = Image.open(uploaded_image)
            start_time = time.time()
            with st.spinner("Encoding in progress..."):
                encoded_img = encode_image(image, message, secret)
            elapsed_time = time.time() - start_time
            st.success(f"Encoding completed in {elapsed_time:.2f} seconds")
            buf = io.BytesIO()
            encoded_img.save(buf, format="PNG")
            qr_data = generate_qr("Secure image saved!")
            st.image(f"data:image/png;base64,{qr_data}")
            st.download_button(label="Download Encoded Image", data=buf.getvalue(), file_name="encoded_image.png", mime="image/png")
    elif type == "Audio":
        uploaded_audio = st.file_uploader("Upload an audio file", type=["wav"])
        message = st.text_area("Enter the secret message:")
        secret = st.text_input("Enter the Secret Key", type="password")
        if st.button("Encode and Download") and uploaded_audio and message and secret:
            start_time = time.time()
            with st.spinner("Encoding in progress..."):
                encode_audio(uploaded_audio, message, "encoded_audio.wav", secret)
            elapsed_time = time.time() - start_time
            st.success(f"Encoding completed in {elapsed_time:.2f} seconds")
            st.download_button(label="Download Encoded Audio", data=open("encoded_audio.wav", "rb").read(), file_name="encoded_audio.wav", mime="audio/wav")


elif selected == "Decode":
    if type == "Image":
        uploaded_image = st.file_uploader("Upload an encoded image", type=["png", "jpg", "jpeg", "bmp"])
        secret = st.text_input("Enter the Secret Key", type="password")
        if st.button("Decode Message") and uploaded_image and secret:
            image = Image.open(uploaded_image)
            start_time = time.time()
            try: 
                with st.spinner("Decoding in progress..."):
                    decoded_message = decode_image(image, secret)
            except ValueError as e:
                st.error("Invalid Secret Key!")
                st.stop()
            elapsed_time = time.time() - start_time
            st.success(f"Decoded Message: {decoded_message}")
            st.info(f"Decoding completed in {elapsed_time:.2f} seconds")
    elif type == "Audio":
        uploaded_audio = st.file_uploader("Upload an encoded audio file", type=["wav"])
        secret = st.text_input("Enter the Secret Key", type="password")
        if st.button("Decode Message") and uploaded_audio and secret:
            start_time = time.time()
            try:
                with st.spinner("Decoding in progress..."):
                    decoded_message = decode_audio(uploaded_audio, secret)
            except ValueError as e:
                st.error("Invalid Secret Key!")
                st.stop()
            elapsed_time = time.time() - start_time
            st.success(f"Decoded Message: {decoded_message}")
            st.info(f"Decoding completed in {elapsed_time:.2f} seconds")
