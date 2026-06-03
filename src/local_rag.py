import os
import re
import numpy as np

class LocalVectorDB:
    def __init__(self, rules_file_path):
        self.rules_file_path = rules_file_path
        self.chunks = []
        self.vocabulary = []
        self.tfidf_matrix = []
        self.load_and_index()
        
    def _tokenize(self, text):
        # Convert to lowercase and get alphanumeric tokens
        return re.findall(r'\b\w+\b', text.lower())
        
    def _compute_tf(self, tokens):
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        total = len(tokens) if tokens else 1
        for k in tf:
            tf[k] = tf[k] / total
        return tf
        
    def load_and_index(self):
        if not os.path.exists(self.rules_file_path):
            print(f"Warning: Rules file not found at: {self.rules_file_path}")
            return
            
        with open(self.rules_file_path, "r") as f:
            content = f.read()
            
        # Split manual by double newlines into rule sections
        sections = content.split("\n\n")
        self.chunks = [sec.strip() for sec in sections if sec.strip()]
        
        # Build vocabulary and count doc occurrences for IDF
        doc_tokens_list = [self._tokenize(chunk) for chunk in self.chunks]
        all_words = set()
        for tokens in doc_tokens_list:
            all_words.update(tokens)
        self.vocabulary = list(all_words)
        
        # IDF calculations
        N = len(self.chunks)
        df = {word: 0 for word in self.vocabulary}
        for tokens in doc_tokens_list:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                if token in df:
                    df[token] += 1
                    
        self.idf = {}
        for word in self.vocabulary:
            # log smoothing
            self.idf[word] = np.log((1 + N) / (1 + df[word])) + 1
            
        # Compute TF-IDF vectors for all chunks
        self.tfidf_matrix = []
        for tokens in doc_tokens_list:
            tf = self._compute_tf(tokens)
            vec = np.zeros(len(self.vocabulary))
            for i, word in enumerate(self.vocabulary):
                vec[i] = tf.get(word, 0) * self.idf[word]
            # Normalize vector
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            self.tfidf_matrix.append(vec)
            
        print(f"Indexed {len(self.chunks)} rule sections in LocalVectorDB.")
        
    def query(self, query_text, top_k=1):
        """
        Runs cosine similarity matches against indexed compliance rule text blocks.
        """
        query_tokens = self._tokenize(query_text)
        query_tf = self._compute_tf(query_tokens)
        
        query_vec = np.zeros(len(self.vocabulary))
        for i, word in enumerate(self.vocabulary):
            query_vec[i] = query_tf.get(word, 0) * self.idf.get(word, 0.0)
            
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm
            
        similarities = []
        for doc_vec in self.tfidf_matrix:
            sim = np.dot(query_vec, doc_vec)
            similarities.append(sim)
            
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "text": self.chunks[idx],
                "score": float(similarities[idx])
            })
        return results

if __name__ == "__main__":
    # Self-test
    rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules", "compliance_rules.txt")
    db = LocalVectorDB(rules_path)
    res = db.query("Separation of duties and approval limit manual overrides")
    print("\nQuery results:")
    for r in res:
        print(f"Score: {r['score']:.4f}\nContent:\n{r['text']}\n")
