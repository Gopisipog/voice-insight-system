import time
import re

class SemanticSegmenter:
    def __init__(self, min_sentences=1, max_gap_seconds=10.0):
        self.buffer = ""
        self.last_input_time = time.time()
        self.min_sentences = min_sentences
        self.max_gap_seconds = max_gap_seconds

    def is_meaningful(self, text):
        """
        Filters out 'junk' segments like filler words, short fragments, or background noise.
        """
        clean_text = text.strip()
        
        # 1. Length Gate (Reject very short fragments)
        if len(clean_text) < 20: 
            return False
            
        # 2. Word Count Gate
        words = clean_text.split()
        if len(words) < 4:
            return False
            
        # 3. Filler Density (Rough heuristic)
        fillers = {'um', 'uh', 'ah', 'like', 'err', 'test'}
        meaningful_words = [w for w in words if w.lower() not in fillers]
        if len(meaningful_words) < 3:
            return False
            
        return True

    def add_text(self, text):
        """
        Groups streaming text into knowledge blocks.
        Returns units only when they are self-sufficient.
        """
        if not text.strip():
            return []

        self.buffer += " " + text.strip()
        self.last_input_time = time.time()
        
        # Split by typical sentence delimiters
        sentences = re.split(r'(?<=[.!?]) +', self.buffer)
        
        units = []
        TARGET_BLOCK_SIZE = 1

        if len(sentences) >= TARGET_BLOCK_SIZE:
            # Extract the first N sentences as a block
            block_sentences = []
            while len(block_sentences) < TARGET_BLOCK_SIZE and sentences:
                s = sentences.pop(0).strip()
                if self.is_meaningful(s):
                    block_sentences.append(s)
            
            if block_sentences:
                units.append(" ".join(block_sentences))
            
            # Put the remaining fragments back into the buffer
            self.buffer = " ".join(sentences)
        
        # If the user stops talking for a long time, force the current buffer out
        elif time.time() - self.last_input_time > self.max_gap_seconds and self.buffer.strip():
            final_unit = self.buffer.strip()
            self.buffer = ""
            if self.is_meaningful(final_unit):
                units.append(final_unit)

        return units

    def flush(self):
        """Force-emit buffered text if silence has exceeded max_gap_seconds."""
        if self.buffer.strip() and (time.time() - self.last_input_time > self.max_gap_seconds):
            unit = self.buffer.strip()
            self.buffer = ""
            if self.is_meaningful(unit):
                return [unit]
        return []
