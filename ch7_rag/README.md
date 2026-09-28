# Chapter 7 — Build the Investigation Agent: RAG, Tools, and MCP

Cryptocurrency Investigation with Agentic AI · Victor Fang · Wiley · 2026

This lab compares the same OpenAI model with and without retrieved evidence. The knowledge base is three short public documents: Bitcoin, Ethereum/Uniswap, and Solana. Cosine similarity ranks the documents; the highest score selects one document; that document is inserted into the model prompt. The model proposes an answer, and ordinary Python decides whether the cited source can enter accepted state.

The program does not scrape websites, access a blockchain, hold private keys, sign transactions, move funds, or perform enforcement. Do not use confidential case material unless your organization has approved the provider, account, retention settings, and data-handling controls.

The companion files are `ch7_rag.py`, `requirements.txt`, `.env_example`, `tutorial.md`, and this README. `tutorial.md` walks through the ranking, the gate, and the saved figures.

## 1. Prepare Python

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` pins LlamaIndex, Chroma, NumPy, Matplotlib, Pydantic, and `python-dotenv==1.1.1`. These versions resolve to OpenAI Python SDK 2.54.0. Windows PowerShell users activate with `.venv\Scripts\Activate.ps1`.

Embeddings and the Chroma store use LlamaIndex. The chat call uses the OpenAI SDK directly, because `gpt-6-luna` expects `max_completion_tokens` rather than `max_tokens`.

## 2. Supply the API key and model names

Create an OpenAI API key under an approved account. Copy `.env_example` to `.env` and fill in the key there. Never paste the key into the Python file, a notebook, a screenshot, or the companion archive. `.env` is gitignored.

```bash
cp .env_example .env
```

```bash
OPENAI_API_KEY=your-key-from-the-approved-secret-store
OPENAI_MODEL=gpt-6-luna
EMBED_MODEL=text-embedding-3-small
```

`ch7_rag.py` loads that file with `load_dotenv` before it reads the settings. A variable already set in the shell is left as-is. The shipped defaults are the chat model `gpt-6-luna` and the embedding model `text-embedding-3-small` at 384 coordinates. On startup the script prints both names. Enable both for this API key in the OpenAI platform before the first call. Record the exact model alias or snapshot with every retained experiment.

## 3. Run the controlled comparison

Run the commands in this folder, `ch7_rag/`. From the repository root, `python ch7_rag.py` looks for the script in the wrong place.

```bash
cd ch7_rag
python ch7_rag.py
```

With no `QUESTION` set, the question is: “According to this knowledge base, which document discusses Uniswap, and what does it say users can do?”

The program performs this sequence:

1. It embeds the knowledge base and the question with `text-embedding-3-small`, requesting 384 coordinates for a compact teaching index, and stores those vectors in Chroma.
2. It ranks the three documents by cosine similarity and selects the highest score.
3. The no-RAG call sends the question with an empty evidence object.
4. The RAG call sends the identical question and instruction plus the selected document in the `Evidence` field.
5. The deterministic gate checks the returned source ID against the exact document supplied to that call. Any other number in the answer must appear in that document text. Digits that are only part of the cited document id, such as `01` in `ETH-01`, are the label of that document.

The model never searches the vector store by itself. Python performs retrieval first and serializes the selected text into the model prompt.

With no `OUT_DIR` set, the run writes `output/` and creates:

- `blockchain_rag_result.json`: rankings, scores, retrieved text, candidate answers, gate routes, vectors, and timings.
- `chroma/`: the small persistent vector collection.
- `Qx_similarity_bars.jpg`: full-vector query-to-document cosine similarity. The axis runs from −1 to 1 because cosine similarity can be negative.
- `Qx_heatmap_384.jpg`: the query and the three document vectors, all 384 coordinates.

The heatmap is 9 by 3.8 inches at 300 dpi (2700×1140 pixels). Titles are 16 pt, axis and color-bar labels are 14 pt, and tick labels are 12 pt, so the type remains readable when the figure is printed at about a 6-inch book width.

Use a fresh `OUT_DIR` for every retained experiment. Reusing a folder overwrites its JSON and figures.

## 4. Read the output in the right order

Open `blockchain_rag_result.json` and inspect:

1. `similarity`: the cosine similarity of each document to the question. The bar chart draws these values.
2. `ranked`: the same documents, highest similarity first. The first id is the retrieved document.
3. `retrieved`: the only document inserted into the RAG prompt.
4. `runs.no_rag` and `runs.rag`: the two model candidates and their gate routes.
5. `accepted_sources`: approved source records copied by Python, not prose promoted by the model.

For the default question, ETH-01 is the required document because it is the only document in the knowledge base that mentions Uniswap and states what users can do. The exact wording of a hosted-model answer can vary. Grade source support and required facts rather than demanding one sentence verbatim.

An empty evidence object cannot produce an accepted source. On the retained `gpt-6-luna` run, that call answers “The knowledge base does not support an answer.” and stays on `human_review`. The RAG answer can pass the source gate only by citing the supplied, unchanged document. Naming that document id in the sentence is allowed. A number that is not part of the id, and is not in the document text, stays on `human_review`. A source match is not semantic proof that every word in the summary is correct.

## 5. Retained questions

These four runs are saved with `gpt-6-luna` and `text-embedding-3-small`. The longest similarity bar is the retrieved document. A short longest bar is still retrieved.

```bash
cd ch7_rag
QUESTION="According to this knowledge base, which document discusses Uniswap, and what does it say users can do?" OUT_DIR=output_01 python ch7_rag.py
QUESTION="What does a Bitcoin input reference?" OUT_DIR=output_02 python ch7_rag.py
QUESTION="What is the current Bitcoin price?" OUT_DIR=output_03 python ch7_rag.py
QUESTION="what's the capital of usa." OUT_DIR=output_04 python ch7_rag.py
```

| Folder | Retrieved | RAG route | What the run shows |
| --- | --- | --- | --- |
| `output_01` | ETH-01 (0.683) | `source_matched` | The Ethereum document is the only one that discusses Uniswap. |
| `output_02` | BTC-01 (0.489) | `source_matched` | A Bitcoin input references an earlier transaction’s identifier and output index. |
| `output_03` | BTC-01 (0.325) | `human_review` | BTC-01 is nearest because the question says Bitcoin, and that document states it does not provide live prices. |
| `output_04` | SOL-01 (0.133) | `human_review` | The question is outside the knowledge base. SOL-01 is only the nearest of three weak scores. |

Both calls on Q3 and Q4 stay on `human_review`. Retrieval should expose that coverage gap rather than convert a model's general knowledge into case evidence.
