import streamlit as st
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
import re
from collections import Counter
from typing import List, Dict, Set, Tuple
import os
from joblib import load
import graphviz

# Download required NLTK data
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Define custom stop words
custom_stop_words = [
    "fig", "figure", "image", "sample", "using", 
    "show", "result", "large", 
    "also", "one", "two", "three", 
    "four", "five", "seven", "eight", "nine"
]

# Get the set of English stop words and add custom stop words
stop_words: Set[str] = set(stopwords.words('english')).union(custom_stop_words)

@st.cache_resource
def load_model():
    """Load the pre-trained word probabilities and vocabulary."""
    probs_file = os.path.join(os.getcwd(), 'word-probability-spellings.joblib')
    vocab_file = os.path.join(os.getcwd(), 'vocab-spellings.joblib')
    
    if not os.path.exists(probs_file) or not os.path.exists(vocab_file):
        raise FileNotFoundError("Required model files not found. Please ensure 'word-probability-spellings.joblib' and 'vocab-spellings.joblib' are in the current directory.")
    
    probs = load(probs_file)
    vocab = load(vocab_file)
    
    return probs, vocab

def edit_one_letter(word: str, allow_switches: bool = True) -> Set[str]:
    """Generate all strings that are one edit away from the input word."""
    letters = 'abcdefghijklmnopqrstuvwxyz'
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
    inserts = [L + c + R for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)

def edit_two_letters(word: str, allow_switches: bool = True) -> Set[str]:
    """Generate all strings that are two edits away from the input word."""
    return set(e2 for e1 in edit_one_letter(word, allow_switches) for e2 in edit_one_letter(e1, allow_switches))

def get_corrections(word: str, probs: Dict[str, float], vocab: Set[str]) -> List[Tuple[str, float]]:
    """Generate spelling correction suggestions for the input word."""
    suggestions = list(edit_two_letters(word).intersection(vocab))
    return sorted([(s, probs.get(s, 0)) for s in suggestions], key=lambda x: x[1], reverse=True)

def create_spelling_correction_flowchart(test_word: str, 
                                         one_edits: Set[str], 
                                         two_edits: Set[str], 
                                         valid_words: Set[str], 
                                         corrections: List[Tuple[str, float]]):
    """Create a flowchart visualization of the spelling correction process."""
    dot = graphviz.Digraph()
    dot.attr(rankdir='TB', size='12,12')

    colors = {
        'start': '#E6F3FF',
        'process': '#FFF2CC',
        'decision': '#E2F0D9',
        'end': '#FCE4D6'
    }

    dot.attr('node', shape='rectangle', style='filled', fontname='Arial', fontsize='12')

    dot.node('A', f'Input word:\n"{test_word}"', fillcolor=colors['start'])
    dot.node('B', f'Generate one-edit words\n(e.g., {", ".join(list(one_edits)[:3])}...)', fillcolor=colors['process'])
    dot.node('C', f'Generate two-edit words\n(e.g., {", ".join(list(two_edits)[:3])}...)', fillcolor=colors['process'])
    dot.node('D', f'Filter valid words\n(e.g., {", ".join(list(valid_words)[:3])}...)', fillcolor=colors['decision'])
    dot.node('E', 'Calculate probabilities', fillcolor=colors['process'])
    dot.node('F', 'Sort by probability', fillcolor=colors['process'])
    
    suggestions = '\n'.join([f'{word}: {prob:.6f}' for word, prob in corrections[:5]])
    dot.node('G', f'Top suggestions:\n{suggestions}', fillcolor=colors['end'])

    dot.edges(['AB', 'BC', 'CD', 'DE', 'EF', 'FG'])

    return dot

def main():
    st.title("Spelling Correction App")
    st.write("This app demonstrates a spelling correction algorithm using NLP techniques.")

    # Load model
    try:
        with st.spinner("Loading model..."):
            probs, vocab = load_model()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    st.divider()

    # User input
    with st.form("spelling_form"):
        user_word = st.text_input("Enter a word to check:", "algoritm")
        submitted = st.form_submit_button("Check Spelling")

    if submitted:
        st.write(f"Checking spelling for: '{user_word}'")

        # Spelling correction process
        with st.spinner("Generating suggestions..."):
            st.write("Step 1: Generating one-edit words")
            one_edits = edit_one_letter(user_word)
            
            st.write("Step 2: Generating two-edit words")
            two_edits = edit_two_letters(user_word)
            
            st.write("Step 3: Filtering valid words")
            valid_words = two_edits.intersection(vocab)
            
            st.write("Step 4: Calculating probabilities and sorting")
            corrections = get_corrections(user_word, probs, vocab)
            
            st.write("Step 5: Generating visualization")
            dot = create_spelling_correction_flowchart(user_word, one_edits, two_edits, valid_words, corrections)

        st.divider()

        # Display results
        st.subheader("Spelling Suggestions:")
        for i, (word, prob) in enumerate(corrections[:5], 1):
            st.metric(label=f"Suggestion {i}", value=word, delta=f"{prob:.6f}")

        st.divider()

        st.subheader("Spelling Correction Process:")
        st.graphviz_chart(dot)

        st.divider()

        # Display some statistics
        st.subheader("Process Statistics:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="One-edit words", value=len(one_edits))
        with col2:
            st.metric(label="Two-edit words", value=len(two_edits))
        with col3:
            st.metric(label="Valid suggestions", value=len(valid_words))

if __name__ == "__main__":
    main()