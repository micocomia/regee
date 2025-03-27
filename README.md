# ReGee: Educational Review Virtual Assistant

ReGee (Review + Gee-Gees) is an interactive question-answering focused virtual assistant designed to help students review class materials through active recall. Unlike other educational RAG-based assistants that merely summarize uploaded materials, ReGee reverses the roles by quizzing students, encouraging critical thinking and deeper engagement with the material.

## Overview

ReGee creates questions from student-uploaded documents and evaluates answers, providing immediate feedback. This approach is based on the educational hypothesis that students who actively explain topics learn more effectively than those who passively receive summaries. ReGee leverages LLMs via Ollama to be able to generate questions and evaluate answers offline.

## Components

- **Document Processing:** Extracts content from PDF and PowerPoint files with support for embedded images via PyMuPDF
- **Retrieval-Augmented Generation (RAG):** Pulls information from uploaded documents to generate relevant questions. Uses ChromaDB for the Vector storage.
- **Question Generation:** Creates multiple-choice and free-text questions with adjustable difficulty levels. Generation via Ollama and your choice of LLM.
- **Answer Evaluation:** Assesses student responses with meaningful feedback. Evaluation via Ollama and your choice of LLM.
- **Speech Recognition:** Allows voice input for a more natural interaction experience using WebSpeech API.
- **Text-to-Speech:** Provides spoken output for questions and feedback using Edge TTS.

## Getting Started

### Prerequisites

Make sure you have Python 3.9+ installed on your system. This project also requires several external dependencies which are listed in the `requirements.txt` file.

You may also need to install Tesseract OCR for image text extraction:
- For Ubuntu/Debian: `sudo apt install tesseract-ocr`
- For macOS: `brew install tesseract`
- For Windows: Download and install from [Tesseract GitHub page](https://github.com/UB-Mannheim/tesseract/wiki)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/regee.git
   cd regee
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   # Create a .env file in the project root
   touch .env
   
   # Add the following variables to your .env file:
   OLLAMA_ENDPOINT=http://localhost:11434/api/generate
   OLLAMA_MODEL=llama3.1:8b
   ```

### Running ReGee

Start the Streamlit application:

```bash
streamlit run app.py
```

Then open your browser and navigate to `http://localhost:8501` to access the ReGee interface.

## Using ReGee

1. **Upload Documents:** Drag and drop your PDF or PowerPoint files directly into the chat input or click the upload button.

2. **Configure Settings (Optional):** Customize your review session with commands like:
   - "Show me the current review settings"
   - "Set question type to multiple choice"
   - "I would like 10 questions"
   - "Set difficulty to hard"
   - "Focus on topic X"

3. **Start Review:** Type "Start review" to begin your study session.

4. **Answer Questions:** Respond to the questions in the chat. For multiple-choice, you can simply enter A, B, C, or D.

5. **Voice Interaction:** Toggle speech recognition in the sidebar to answer questions using your voice.

## Key Components

- **Document Processor:** Extracts and processes text from uploaded files
- **Vector Store:** Stores document embeddings for efficient retrieval
- **Retrieval System:** Finds relevant content from the documents
- **Question Generator:** Creates meaningful questions based on the retrieved content
- **Answer Evaluator:** Assesses the correctness of student responses
- **Intent Classifier:** Interprets user commands and queries
- **Speech Recognition:** Converts spoken input to text
- **Text-to-Speech:** Provides spoken output

## Project Structure

```
regee/
├── app.py                  # Main Streamlit application
├── document_processor.py   # Document processing and embedding
├── vector_store.py         # Vector database for document storage
├── retrieval.py            # Content retrieval system
├── question_generator.py   # Question generation module
├── answer_evaluator.py     # Answer evaluation module
├── intent_classifier.py    # Intent classification for NLU
├── intent_handler.py       # Intent handling logic
├── speech_recognition.py   # Speech-to-text functionality
├── text_to_speech.py       # Text-to-speech functionality
├── requirements.txt        # Project dependencies
├── data/                   # Directory for vector store data
├── uploads/                # Directory for uploaded documents
└── docs/                   # Documentation assets
```

## Optional Enhancements

- **Ollama Integration:** For better question generation and answer evaluation, install [Ollama](https://ollama.ai) and run the llama3.1:8b model locally.
- **PyMuPDF (fitz):** Optional dependency for better PDF processing including image extraction.
- **Image Captioning:** Requires additional dependencies for image analysis and description.

## Limitations

- Document processing is limited to text-based PDFs and PowerPoint files
- Speech recognition requires a compatible browser and microphone
- Performance depends on the quality and clarity of the uploaded documents
- Intent classifiation uses regex patterns, so some commands may not be dected

## Acknowledgments

- This project was developed as part of CSI 5180