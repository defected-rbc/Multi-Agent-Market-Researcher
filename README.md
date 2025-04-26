# 🤖 AI & Generative AI Use Case Generator

This project implements a multi-agent AI system designed to perform market research for a given company or industry and generate relevant AI/ML/GenAI use cases. The system leverages large language models (LLMs) and web search capabilities to identify opportunities for enhancing operations and customer experiences.

The application is built using Streamlit, providing a simple web interface to interact with the agents.

## ✨ Features

* **Market Research:** Automatically researches a company or industry using web search.
* **Industry Analysis:** Identifies key offerings, strategic focus areas, and relevant AI/ML/GenAI trends.
* **Use Case Generation:** Proposes tailored AI/ML/GenAI use cases based on research findings.
* **Resource Collection:** Searches for relevant datasets and code resources on platforms like Kaggle, HuggingFace, and GitHub.
* **General GenAI Suggestions:** Offers ideas for implementing common GenAI solutions like chatbots or automated reporting.
* **Streamlit UI:** Provides an easy-to-use web interface to input the company/industry and view the generated proposal.
* **Downloadable Resources:** Allows downloading the collected resource links as a markdown file.

## 🧠 Architecture

The system employs a simple sequential multi-agent architecture:

1.  **Research Agent:** Gathers information about the input company/industry using a web search tool.
2.  **Market Standards & Use Case Generation Agent:** Analyzes research and industry trends to propose specific AI/GenAI/ML use cases.
3.  **Resource Asset Collection Agent:** Finds relevant datasets and code links for the proposed use cases.
4.  **Optional GenAI Solutions Proposer Agent:** Suggests general GenAI applications.
5.  **Orchestrator:** Manages the workflow and data flow between the agents and compiles the final output.

(You might want to add an architecture flowchart diagram here later if you create one!)

## 📋 Prerequisites

Before running this application, you need:

* **Python 3.8+**
* **Git**
* **API Keys:**
    * **Google Gemini API Key:** Obtain from [Google AI Studio](https://aistudio.google.com/) or Google Cloud's Vertex AI.
    * **Google Custom Search Engine (CSE):** Create one via the [Programmable Search Engine website](https://programmablesearchengine.google.com/) to search the entire web. Get your **Search Engine ID (CX)**.
    * **Google Cloud API Key:** Obtain from the [Google Cloud Console](https://console.cloud.google.com/). Enable the **"Custom Search API"** for your project.

## 🚀 Setup

1.  **Clone the Repository:**
    ```bash
    git clone <Your Repository URL>
    cd <your-repository-name>
    ```
    (Replace `<Your Repository URL>` and `<your-repository-name>` with your actual GitHub details)

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment.
    ```bash
    # For venv (Python 3.3+ is included)
    python -m venv .venv
    ```

3.  **Activate the Virtual Environment:**
    ```bash
    # On Windows
    .\.venv\Scripts\activate
    # On macOS/Linux
    source ./.venv/bin/activate
    ```
    Your terminal prompt should show `(.venv)` indicating the environment is active.

4.  **Install Dependencies:**
    Install the required libraries using `pip`.
    ```bash
    pip install -r requirements.txt
    ```
    The `requirements.txt` file should contain:
    ```
    streamlit
    google-generativeai
    google-api-python-client
    ```

5.  **Set up API Keys using Streamlit Secrets:**
    Create a secure way for the app to access your API keys.
    * In your project's root directory, create a folder named `.streamlit`.
    * Inside `.streamlit`, create a file named `secrets.toml`.
    * Add your API keys to `secrets.toml` in the following format:
        ```toml
        # .streamlit/secrets.toml

        GEMINI_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY"
        GOOGLE_CSE_ID = "YOUR_ACTUAL_GOOGLE_CUSTOM_SEARCH_ENGINE_ID"
        GOOGLE_CSE_API_KEY = "YOUR_ACTUAL_GOOGLE_CLOUD_API_KEY_FOR_SEARCH"
        ```
        **Replace the placeholder values with your actual keys.**

    * **Note on Security:** While `secrets.toml` is used for *local* testing, when deploying to Streamlit Cloud via GitHub, you should add these secrets directly in the Streamlit Cloud dashboard settings for your app. The `secrets.toml` file itself might be committed to the repository, but it's critical that your *actual, sensitive keys* are stored securely in the Streamlit Cloud dashboard secrets, not directly in the file in your public repo.

## 🏃 Running Locally

1.  Activate your virtual environment (if not already active).
2.  Navigate to your project's root directory.
3.  Run the Streamlit application:
    ```bash
    streamlit run streamlit_app.py
    ```
4.  The app will open in your web browser, usually at `http://localhost:8501`.

## ☁️ Deployment on Streamlit Cloud

1.  Ensure your code (including `streamlit_app.py`, `requirements.txt`, and the `.streamlit` folder with `secrets.toml`) is pushed to your GitHub repository.
2.  Go to [Streamlit Cloud](https://streamlit.io/cloud) and log in.
3.  Click "New app" and select your GitHub repository.
4.  Choose the branch and the main file path (`streamlit_app.py`).
5.  In "Advanced settings" -> "Secrets", add your API keys **securely**. Copy the key names (`GEMINI_API_KEY`, `GOOGLE_CSE_ID`, `GOOGLE_CSE_API_KEY`) and their *actual secret values* from your `secrets.toml` and paste them into the Streamlit Cloud secrets text area in the correct format (same `KEY_NAME = "Value"` structure).
6.  Click "Deploy!".

Streamlit Cloud will build your app and provide you with a public URL.

## 📂 File Structure
