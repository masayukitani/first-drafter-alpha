# First Drafter alpha

**Slack-based chatbot with slash commands assisting lawyers in writing a first draft of reports, emails and contracts**

This repository contains a Slack chatbot designed for legal and contract research and drafting tasks. It integrates Slack Bolt with OpenAI's GPT (via `langchain_openai`), a Chroma vector database for retrieval, Tavily internet search, and Momento for conversation history.

---

## Features

1. **AI-Powered Q&A**  
   - Quickly answer legal or general questions.

2. **Retrieval-Augmented Research**  
   - Search a local Chroma database for relevant documents or perform web-based research with Tavily Search.
   - Output the summary of the documents retrieved.

3. **Email Drafting**  
   - Draft an email answering a question based on current conversation history.

4. **Contract Drafting**  
   - Prepare a preliminary draft of a contract based on your request (e.g., NDA, licensing agreement, etc.).

5. **Automated Question Reformulation**  
   - When no command is specified, the chatbot reformulates the user's query based on recent history for a more context-aware response, and answers the reformulated question.

## Commands Summary

- **`/help`**  
  Displays a list of available commands and basic usage instructions.

- **`/clear`**  
  Clears the conversation history (stored in Momento) for the current thread.

- **`/answer <your-question>`**  
  Obtains a direct AI-generated response without any specialized retrieval.

- **`/research db <your-topic>`**  
  1. Uses a hypothetical answer to locate relevant documents in a Chroma database.  
  2. Summarizes the retrieved documents and provides an answer.

- **`/research web <your-topic>`, `/research web2 <your-topic>`, `/research web3 <your-topic>`**  
  Performs a web search (using Tavily) for `<your-topic>` and summarizes the results.  
  - `web` fetches a single set of results (max 1).  
  - `web2` and `web3` fetch larger sets (max 2 or 3).

- **`/em <question-to-draft-email-for>`**  
  Drafts an email answering to a question based on current conversation history (assuming research has been done in the previous conversation).

- **`/contract <type-of-contract>`**  
  Drafts a simple contract based on your request (e.g., NDA, licensing agreement, etc.).

- **Default (no command)**  
  If no recognized command is found, the bot will reformulate your query using the conversation history, then answer to the reformulated question.

## Usage (except the part implementing the Chroma DB)

### Install Dependencies with `uv`

If you're using the `uv` package manager, please install the required libraries as specified in your `pyproject.toml` file. For example:

```bash
uv sync
```

### Set Environment and Configuration Variables

> - All scripts rely on environment variables in `.env` in the root directory and configuration in `config.py` in `app` directory.
> - Please refer to the `.env.example` file for the required environment variables.
> - Please refer to each service in the Requirements section below for the required API keys.

### Start the app

```bash
uv run app/main.py
```

The Slack bot is then ready to receive mentions in your Slack workspace.

### Interact in Slack

- Mention your bot with `@YourBotNameOnSlack /help` to see available commands.  
- Use the commands summarized above to perform Q&A, research, email drafting, or contract drafting.

### Sample Interactions

- `@YourBotNameOnSlack /answer What is a force majeure clause?`  
- `@YourBotNameOnSlack /research db Please find documents related to regulations over high-risk AI systems in the world.`  
- `@YourBotNameOnSlack /research web3 Recent updates on data privacy regulations in California.`  
- `@YourBotNameOnSlack /em Write an email of overview of the recent updates on AI governance in the world.`  
- `@YourBotNameOnSlack /contract basic service agreement for outsourcing artwork creation.`

#### Conversation History

- All conversation messages in a Slack thread are cached by Momento under the thread timestamp.  
- Clear the cache for the current thread anytime:

```bash
@YourBotNameOnSlack /clear
```

### Create and Manage Your Chroma Database

We provide three supplementary scripts for building, updating, and querying your Chroma database. These scripts read metadata from JSON files, load PDF documents, chunk them, and store/retrieve embeddings in Chroma.

#### 1. Set Chroma Specific Configuration

Please refer to the `config.py` file in the `app` directory for the Chroma specific configuration.

#### 2. `create_db.py`

Creates a new Chroma database using the **last** entry (document) from your JSON metadata file.

```bash
python create_db.py \
  --context db/data/context/doc_context.json \
  --dir db/chroma_db
```

- `--context`: Path to the JSON metadata file.

#### 3. `add_data.py`

Adds one or more documents (from your JSON file) to an **existing** Chroma database.

```bash
python add_data.py \
  --num 2 \
  --context db/data/context/doc_context.json \
  --dir db/chroma_db
```

- `--num`: Number of most recent documents (from the end of the JSON list) to add.
- `--context`: Path to the JSON metadata file.
- `--dir`: Directory of the existing Chroma database.

#### 4. `query_data.py`

Checks and queries your Chroma database to validate stored documents and embeddings.

```bash
python query_data.py \
  --query "AI regulations in Europe" \
  --dir db/chroma_db
```

- `--query`: The search query to test against your Chroma database.
- `--dir`: Directory of the Chroma database you want to query.

#### Note

> - For English-language PDFs, the loader is `PyPDFLoader`; for Japanese-language PDFs, the loader is `PDFPlumberLoader`. For other languages, the loader cannot be set at this moment.
> - By default, the scripts expect raw PDF files in `db/data/raw/` and metadata in `db/data/context/doc_context.json`. Adjust paths as needed.

## Requirements

- [Slack Bolt for Python](https://github.com/slackapi/bolt-python)  
- [LangChain](https://github.com/hwchase17/langchain)  
- [Chroma](https://docs.trychroma.com/)
- [Tavily](https://docs.tavily.com/welcome)
- [Momento](https://docs.momentohq.com/)

## Environment Variables

Your `.env` file should include the following variables:

```plaintext
LANGCHAIN_TRACING_V2=[true|false] # if true, LangSmith will be used for tracing
LANGCHAIN_API_KEY= # Create from LangSmith
MOMENTO_AUTH_TOKEN=
MOMENTO_CACHE=
MOMENTO_TTL=
OPENAI_API_KEY=
SLACK_SIGNING_SECRET=
SLACK_BOT_TOKEN=
SLACK_APP_TOKEN=
TAVILY_API_KEY=
```

---

## License & Disclaimer

**Definition of “Software”:** For purposes of this Disclaimer, “Software” includes all code, documentation, associated content, and any outputs or results generated by the Software. This project is provided on an **“as is”** and **“as available”** basis, without warranties of any kind, whether express or implied. By accessing, using, contributing to, or distributing the Software, you acknowledge and agree to the following terms:

### 1. No Legal Advice

- The Software is provided solely for informational and educational purposes.  
- Nothing contained in the Software shall be construed as legal advice or as a substitute for consultation with a qualified attorney.  
- Always seek the advice of a licensed professional for any legal questions you may have.

### 2. No Attorney-Client Relationship

- The use of the Software, including any interactions on forums (public or private), pull requests, or other channels, does **not** create an attorney-client relationship between you and any author(s), contributor(s), or distributor(s).  
- Communication through these channels does not form a confidential or privileged relationship under any circumstances.  
- Neither the Software nor anything generated by it constitutes legal or professional advice of any kind.

### 3. Disclaimer of Warranties

- The author(s), contributor(s), and distributor(s) provide the Software **without any warranty** of any kind, including but not limited to warranties of merchantability, fitness for a particular purpose, accuracy, or non-infringement.  
- There is no guarantee that the Software is free of errors, bugs, or vulnerabilities, nor is there any obligation to maintain, update, or correct the Software.

### 4. Assumption of Risk & Limitation of Liability

- You assume **full responsibility** and **all risks** associated with your use of the Software.  
- Under no circumstances shall the author(s), contributor(s), or distributor(s) be liable for any direct, indirect, incidental, special, consequential, or exemplary damages (including, but not limited to, business interruption, loss of data, or loss of profits) arising out of or in connection with the use or inability to use the Software, even if advised of the possibility of such damages.  
- You agree to indemnify and hold harmless the author(s), contributor(s), and distributor(s) from any claims, losses, or damages resulting from or related to your use, modification, or distribution of the Software.

### 5. Compliance with Laws & Regulations

- You are solely responsible for determining and complying with all applicable local, national, and international laws, regulations, and industry standards relevant to your use of the Software.  
- The author(s), contributor(s), and distributor(s) make **no representation** that the Software complies with any particular legal or regulatory framework.

### 6. Open-Source License

- The Software is released under an open-source license. The specific terms of this license are set forth in the `LICENSE` file accompanying this repository.  
- By using or distributing the Software, you agree to abide by all terms and conditions of the applicable open-source license, including any requirements for attribution or notice.

### 7. Third-Party Content & Services

- This Software may rely on or link to third-party content, libraries, or services. The author(s), contributor(s), and distributor(s) do not endorse, control, or assume responsibility for any third-party materials or services.  
- Any reliance on or use of such third-party content is solely at your own risk and is subject to the terms and conditions imposed by the third party.

### 8. No Obligation to Update

- The author(s), contributor(s), and distributor(s) have no obligation to update, support, maintain, correct, or improve the Software.  
- Any future modifications, updates, or enhancements provided are still subject to all disclaimers and limitations of liability stated herein.

### 9. Severability

- If any portion of this Disclaimer is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.