import os
import subprocess
import zipfile

import faiss
import streamlit as st
from sentence_transformers import SentenceTransformer

# Define paths for both folders
# These are the paths where the SDKs are stored after extraction.
folders = [
    "E:/Projects/Dynamics-365-SDK-Chatbot/Dynamics365Commerce.InStore-release-9.52",
    "E:/Projects/Dynamics-365-SDK-Chatbot/Dynamics365Commerce.ScaleUnit-release-9.52",
]

# Define paths for the zip files that contain the SDKs
# These are the zip files that will be extracted if the folders do not exist.
zip_files = [
    "E:/Projects/Dynamics-365-SDK-Chatbot/Dynamics365Commerce.InStore-release-9.52.zip",
    "E:/Projects/Dynamics-365-SDK-Chatbot/Dynamics365Commerce.ScaleUnit-release-9.52.zip",
]

# Check if the folders exist, if not, extract the respective zip files
# Loop through each folder and its corresponding zip file to ensure extraction.
for folder, zip_file_path in zip(folders, zip_files):
    if not os.path.exists(folder):
        # If the folder does not exist, check if the zip file is available
        if os.path.exists(zip_file_path):
            # Extract the zip file to the folder
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(folder)
            print(f"Extracted SDK to {folder}")
        else:
            # Display an error if the zip file is missing
            st.error(
                f"The zip file {zip_file_path} does not exist. Please ensure the file is present."
            )
            st.stop()

# Initialize a Sentence Transformer to create embeddings
# The model is used to convert text data into numerical embeddings for similarity search.
# Set to use only CPU.
model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

# Store all file contents and their paths
file_contents = []
file_paths = []

# Read all files in both SDK folders
# Loop through each folder, and read all the files to store their contents and paths.
for sdk_dir in folders:
    for root, _, files in os.walk(sdk_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Read the file with UTF-8 encoding, ignoring errors if any
                with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    content = f.read()
                    file_contents.append(content)
                    file_paths.append(file_path)
            except Exception as e:
                # Print an error message if the file could not be read
                print(f"Could not read file {file_path}: {e}")

# Create embeddings for all contents
# Convert the contents of all files into embeddings for similarity search.
# Set `convert_to_tensor` to False to return embeddings as NumPy arrays.
embeddings = model.encode(file_contents, convert_to_tensor=False)

# Create a FAISS index
# FAISS is used to perform similarity search on the embeddings.
dimension = embeddings.shape[1]  # Get the dimension of the embeddings
index = faiss.IndexFlatL2(dimension)  # Create a FAISS index using L2 distance
# Add the embeddings to the FAISS index directly as they are now NumPy arrays.
index.add(embeddings)


# Function to find relevant content based on user query
def find_relevant_content(user_query):
    # Create embedding for the user query, using NumPy arrays
    query_embedding = model.encode([user_query], convert_to_tensor=False)

    # Search FAISS index for similar content
    # Retrieve the top 5 most similar contents
    _, indices = index.search(query_embedding, k=5)

    # Fetch relevant file contents using the indices from the FAISS search
    relevant_contents = [file_contents[i] for i in indices[0]]
    return relevant_contents


# Function to generate an answer based on user query
def generate_answer(user_query):
    # Retrieve relevant SDK content
    relevant_contents = find_relevant_content(user_query)

    # Construct the prompt using the relevant content
    # The prompt includes the user query and relevant content to provide context
    prompt = f"You are an assistant for Microsoft Dynamics 365 SDK. Provide detailed, step-by-step C# code examples for the following question based on the provided content. The answer must include complete C# code to add a custom button in the POS.\n"
    for content in relevant_contents:
        prompt += f"\n---\n{content}\n"
    prompt += f"\n---\nUser Question: {user_query}\nAnswer with step-by-step C# code examples:\n"

    # Use subprocess to call Ollama with the constructed prompt
    try:
        # Use llama3 model for response generation
        result = subprocess.run(
            ["ollama", "run", "llama3"],
            input=prompt.encode("utf-8"),  # Encode input explicitly as utf-8
            capture_output=True,
        )
        if result.returncode == 0:
            # Return the generated response if the subprocess was successful
            return result.stdout.decode(
                "utf-8"
            ).strip()  # Decode output explicitly as utf-8
        else:
            # Return an error message if the subprocess failed
            return f"Error generating response: {result.stderr.decode('utf-8').strip()}"
    except Exception as e:
        # Return an error message if there was an exception
        return f"Error while trying to generate response: {str(e)}"


# Streamlit UI for Chatbot
# Create a simple UI for the chatbot using Streamlit
st.title("Dynamics 365 SDK Chatbot")

# Input text box for user question
user_question = st.text_input("Ask a question about Dynamics 365 SDK:")

# Button to get the answer
if st.button("Get Answer"):
    if user_question:
        # Show a spinner while generating the answer
        with st.spinner("Generating answer..."):
            answer = generate_answer(user_question)
        # Display the answer
        st.write("**Answer:**")
        st.write(answer)
    else:
        # Prompt user to enter a question if the text box is empty
        st.write("Please enter a question.")
