# Building an OSINT Agent for Crypto Addresses

Investigators often find cryptocurrency addresses in chat channels such as Telegram. Some are typed into messages, others are printed on donation posters or hidden in QR codes. Collecting them by hand is slow, and a single misread character can send a case in the wrong direction. This section builds a small AI agent that automates collection and first-pass checks while leaving every judgment to a human analyst.

The complete code, data, setup instructions, and sample outputs are available at:

**https://github.com/<REPO>/tree/main/ch11**

## What the Agent Does

The agent, `ch11_osint_agent.py`, is built with LangGraph, a library that connects processing steps into a graph. Here the graph is a straight line of five steps. Each step reads and updates one shared `state` dictionary.

```text
collect → extract → validate → llm_osint → report
```

In a single run, the agent does the following:

1. Parses Telegram-style JSON messages.
2. Checks each image against its recorded SHA-256 hash, to confirm the evidence has not changed.
3. Decodes any QR codes and reads text from images with OCR.
4. Finds Bitcoin addresses in the extracted text with a regular expression.
5. Validates their checksums and networks.
6. Compares each address against a register of human-verified sources.
7. Optionally asks GPT-6 to search the web for public mentions.
8. Writes an audit-ready JSON report.

## The Input Data

The input is seven synthetic Telegram messages based on the U.S. Department of Justice's 2020 terror-finance complaints. Each message tests one skill an investigator needs:

- **T01** is ordinary chat with no address.
- **T02 and T03** are donation images. T03 contains a QR code.
- **T04** contains an address with one mistyped character.
- **T05 and T06** use a test-network address. T06 adds an unsupported claim that a terrorist fundraiser operates it.
- **T07** is an **OSINT poisoning** attempt. The sender, KimChi, plays a North Korea–linked actor who labels an innocent exchange's address a "terrorist fundraising wallet."

A second file, the review register, records what a human analyst has verified. It lists the address read from each image, with the DOJ complaint and page that support it.

## Core Logic

**Extraction.** For every message, the agent keeps the text. If a message has an image, the agent first verifies its hash, then decodes the image two ways:

```python
qr, _, _ = cv2.QRCodeDetector().detectAndDecode(pix)
ocr = pytesseract.image_to_string(pix, config="--psm 6", timeout=20)
```

If the register contains a human reading of the image, the agent adds it as a separate `human_source_review` entry. This keeps the output honest about whether software or a person found each address.

**Validation.** A regular expression finds candidate addresses. Each candidate is then decoded with Base58Check:

- If the checksum fails, the candidate is marked `invalid`.
- If the version byte is 0, it is marked `bitcoin_mainnet`.
- If the version byte is 111, it is marked `bitcoin_test_family`.

Every address starts as `unsupported`. It is upgraded only when the address is on mainnet and exactly matches the human register entry for the same image:

```python
if row["network"] == "bitcoin_mainnet" and rev.get("address") == addr:
    row.update(attribution="source_register_match", ...)
```

Nothing in the code refers to particular senders or messages. A claim in a chat message can never become an attribution on its own.

**LLM OSINT.** When run with `--llm`, the agent sends GPT-6 a short, strict prompt:

```python
prompt = ("OSINT: public mentions for mainnet addresses; test-family/invalid are controls; "
          "≤200-word summary. No ownership/freeze claims.\n"
          f"rows={json.dumps(rows)}\nregister={json.dumps(s['register'])[:4000]}")
client.responses.create(model=MODEL, store=False, tools=[{"type": "web_search"}], input=prompt)
```

Each part of the prompt and the call does a specific job:

- The prompt limits the search to mainnet addresses and tells the model to treat invalid and test-network strings as controls.
- It forbids claims about ownership or freezing funds.
- It sends only the structured address rows, never the raw message text. This means T06's claim and KimChi's accusation cannot steer the model.
- `store=False` asks the provider not to retain the exchange.
- The full prompt and reply are saved with the result, for audit.

**Report.** The final step bundles the rows, image extractions, input hashes, and summary. It always sets `human_review_required: true` and `action_authorized: false`. The agent prepares findings; people decide what they mean.

## Results

The run produces seven address rows:

| Message | Method | Network | Attribution |
|---|---|---|---|
| T02 | human review | mainnet | register match |
| T03 | QR | mainnet | register match |
| T03 | human review | mainnet | register match |
| T04 | text | invalid | unsupported |
| T05 | text | test network | unsupported |
| T06 | text | test network | unsupported |
| T07 | text | test network | unsupported |

The table shows the safeguards working:

- Only T02 and T03 match the register. They point to Defendant Properties 79 and 4 in the DOJ complaints.
- T03 appears twice because the QR code and the human reviewer found the same address. That is one lead confirmed two ways.
- The checksum rejects T04's typo.
- The terrorism claims in T06 and T07 have no effect. KimChi's innocent address stays `unsupported`, so the poisoning attempt fails.

**OCR versus QR.** OCR guesses each character from its pixels. Bitcoin addresses are random mixed-case strings, so lookalike characters are easily confused. A QR code stores the exact bytes and includes error correction, so it either decodes perfectly or fails outright. Our run shows the difference:

```text
true:  17QAWGVpFV4gZ25NQug46e5mBho4uDP6MD
OCR:   T?QAWGVpFV4gZ25NQug46e5mBho4uDP6MD   ("17" misread)
QR:    17QAWGVpFV4gZ25NQug46e5mBho4uDP6MD   (exact)
```

On the Al Sadaqah image, which has no QR code, OCR made eight errors, including `Z→7`, `q→a`, and `3→s`, and split the address across two lines. The rule follows: prefer the QR result, treat OCR as a hint, and never trust an OCR address that fails its checksum.

**GPT-6 summary.** With web search enabled, GPT-6 did four useful things:

- It confirmed that both mainnet addresses appear in the DOJ's 2020 civil complaints, citing the public justice.gov PDF.
- It recognized that the two T03 rows describe one address, not two independent mentions.
- It described the links as "allegations in civil complaints, not findings of fact," which is the correct legal framing.
- It ignored the control addresses.

It found no new sources beyond the register, and it said nothing about on-chain activity. Its value is fast, cited, and appropriately cautious confirmation. An analyst must still open each citation and check it.

## Scaling Investigations with AI Agents

Seven messages can be checked by hand; a real case may involve thousands of messages across dozens of channels. The same pipeline scales because every step is mechanical, repeatable, and recorded:

- **Triage at volume.** OCR, QR decoding, regex, and checksums reduce thousands of raw strings to a short list of valid leads.
- **Built-in noise and poison filtering.** Typos and test-network addresses are dropped. Chat claims never become attributions, which protects the team from honest mistakes and deliberate deception alike.
- **Reusable knowledge.** An address verified once in the register is matched automatically in every later run and every case.
- **OSINT on demand.** An LLM with web search performs the first public-mention lookup in seconds and returns citations to check.
- **Defensible evidence.** Input hashes, exact prompts, replies, and response IDs make each run reproducible. This matters if the work reaches court.
- **Extensible design.** New steps, such as Ethereum or TRON detection, blockchain lookups, or sanctions screening, can be added as new LangGraph nodes.

Above all, the agent keeps humans in control. Automation handles the repetitive work at scale, while attribution and action remain human decisions.
