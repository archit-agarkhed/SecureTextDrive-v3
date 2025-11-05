"""
CLI tool to summarize a text file using Google's Gemini API.
Usage in WSL/Linux:

# Set your API key (recommended)
export GOOGLE_API_KEY="your-key-here"
python3 tools/summarize_cli.py --file path/to/file.txt

# Save summary to a file
python3 tools/summarize_cli.py -f path/to/file.txt -o summary.txt

Supports chunking for large files by summarizing chunks then combining them.
"""
import argparse
import os
import sys
import google.generativeai as genai

CHUNK_SIZE = 15000  # chars per chunk (adjust if needed)
GEMINI_MODEL = "gemini-pro"  # Gemini's text model

PROMPT_INSTRUCTIONS = """
You are a helpful assistant. Please provide a concise, clear summary of the provided text.
Aim for a short summary (about 100-250 words) that captures the main points.

Text to summarize:
"""

def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Split text into roughly equal chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks

def setup_gemini(api_key):
    """Configure Gemini API with the provided key."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    return model

def summarize_text(model, text):
    """Summarize a single text chunk using Gemini."""
    prompt = PROMPT_INSTRUCTIONS + text
    response = model.generate_content(prompt)
    return response.text.strip()

def summarize_file_flow(api_key, file_path, out_file=None):
    """Main flow: read file, chunk if needed, summarize, and optionally save."""
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return 2

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    if not text.strip():
        print("Input file is empty.")
        return 1

    # Initialize Gemini
    try:
        model = setup_gemini(api_key)
    except Exception as e:
        print(f"Failed to initialize Gemini: {e}")
        return 3

    # Process text in chunks if needed
    chunks = chunk_text(text)
    print(f"Read {len(text)} characters; splitting into {len(chunks)} chunk(s).")

    summaries = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Summarizing chunk {i}/{len(chunks)}...")
        try:
            s = summarize_text(model, chunk)
            summaries.append(s)
        except Exception as e:
            print(f"Error summarizing chunk {i}: {e}")
            return 4

    # For multiple chunks, generate a final combined summary
    if len(summaries) == 1:
        final_summary = summaries[0]
    else:
        combined = "\n\n".join(summaries)
        prompt = (
            "The following are summaries of different parts of a longer document. "
            "Please produce a single concise coherent summary that synthesizes the main points:\n\n" + 
            combined
        )
        try:
            final_summary = summarize_text(model, prompt)
        except Exception as e:
            print(f"Error generating final summary: {e}")
            return 5

    # Output results
    print("\n=== SUMMARY ===\n")
    print(final_summary)

    if out_file:
        try:
            with open(out_file, 'w', encoding='utf-8') as of:
                of.write(final_summary)
            print(f"\nSaved summary to {out_file}")
        except Exception as e:
            print(f"Failed to write summary to file: {e}")

    return 0

def main(argv=None):
    parser = argparse.ArgumentParser(description='Summarize a text file using Google Gemini.')
    parser.add_argument('--file', '-f', required=True, help='Path to the text file to summarize')
    parser.add_argument('--api-key', '-k', help='Gemini API key (if not provided, reads from GOOGLE_API_KEY env var)')
    parser.add_argument('--out', '-o', help='Optional output file path to save the summary')

    args = parser.parse_args(argv)

    # Get API key from args or environment
    api_key = args.api_key or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print('API key not provided. Set GOOGLE_API_KEY env var or pass --api-key.')
        return 1

    exit_code = summarize_file_flow(api_key, args.file, out_file=args.out)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
