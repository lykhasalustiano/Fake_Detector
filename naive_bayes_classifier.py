# naive_bayes_classifier.py
import math
import re
import os
from collections import defaultdict, Counter
import pandas as pd
import joblib
from sklearn.feature_extraction.text import CountVectorizer

class NaiveBayesClassifier:
    def __init__(self, alpha=1.0, use_ngrams=False):
        self.alpha = alpha  # Laplace smoothing parameter
        self.class_priors = {}
        self.word_likelihoods = {}
        self.vocab = set()
        self.is_trained = False
        self.use_ngrams = use_ngrams
        self.vectorizer = CountVectorizer(ngram_range=(1, 2) if use_ngrams else (1, 1))
        
    def preprocess_text(self, text):
        """Preprocess text: lowercase, remove punctuation, handle negation"""
        # Handle NaN and None values
        if not isinstance(text, str) or pd.isna(text):
            return []
            
        # Convert to lowercase
        text = text.lower()
        
        # Handle negation by adding NOT_ prefix to words after negation until punctuation
        negation_patterns = [
            r"\b(not|no|never|none|n't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't|haven't|hasn't|hadn't|won't|wouldn't|shouldn't|couldn't|can't|cannot)\b"
        ]
        
        # Find negation phrases
        for pattern in negation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Find the next punctuation after the negation
                punctuation_match = re.search(r"[.,!?;:]", text[match.end():])
                if punctuation_match:
                    end_pos = match.end() + punctuation_match.start()
                else:
                    end_pos = len(text)
                
                # Add NOT_ prefix to all words between negation and punctuation
                words_to_negate = text[match.end():end_pos].split()
                negated_words = ["NOT_" + word for word in words_to_negate]
                text = text[:match.end()] + " " + " ".join(negated_words) + text[end_pos:]
        
        # Remove special characters and digits, keep only words
        text = re.sub(r"[^a-zNOT_]", " ", text)
        
        # Tokenize
        tokens = text.split()
        
        return tokens
    
    def train(self, documents, labels):
        """Train the Naive Bayes classifier"""
        if len(documents) != len(labels):
            raise ValueError("Documents and labels must have the same length")
            
        # Count documents per class
        class_counts = Counter(labels)
        total_documents = len(documents)
        
        # Calculate class priors
        self.class_priors = {cls: count / total_documents for cls, count in class_counts.items()}
        
        # If using n-grams, fit the vectorizer
        if self.use_ngrams:
            self.vectorizer.fit(documents)
            self.vocab = set(self.vectorizer.get_feature_names_out())
        
        # Count words per class
        word_counts = defaultdict(lambda: defaultdict(int))
        
        for doc, label in zip(documents, labels):
            if self.use_ngrams:
                # Use vectorizer for n-grams
                bow = self.vectorizer.transform([doc]).toarray()[0]
                feature_names = self.vectorizer.get_feature_names_out()
                for i, count in enumerate(bow):
                    if count > 0:
                        word = feature_names[i]
                        word_counts[label][word] += count
                        self.vocab.add(word)
            else:
                # Use traditional tokenization
                tokens = self.preprocess_text(doc)
                for token in tokens:
                    word_counts[label][token] += 1
                    self.vocab.add(token)
        
        # Calculate word likelihoods with Laplace smoothing
        vocab_size = len(self.vocab)
        self.word_likelihoods = {}
        
        for label in class_counts:
            total_words_in_class = sum(word_counts[label].values())
            self.word_likelihoods[label] = {}
            
            for word in self.vocab:
                count = word_counts[label].get(word, 0)
                # Laplace smoothing
                self.word_likelihoods[label][word] = (count + self.alpha) / (total_words_in_class + self.alpha * vocab_size)
        
        self.is_trained = True
        return self
    
    def predict(self, document, return_details=False):
        """Predict the class of a document with optional feature contributions"""
        if not self.is_trained:
            raise ValueError("Classifier not trained. Please train first.")
            
        # Handle NaN and empty documents
        if not document or pd.isna(document) or str(document).strip() == '':
            # Return equal probability for both classes if document is empty
            if return_details:
                return 0, {0: 0.5, 1: 0.5}, {}
            return 0, {0: 0.5, 1: 0.5}
            
        if self.use_ngrams:
            # Use vectorizer for n-grams
            bow = self.vectorizer.transform([document]).toarray()[0]
            feature_names = self.vectorizer.get_feature_names_out()
            tokens = [feature_names[i] for i, count in enumerate(bow) if count > 0]
        else:
            # Use traditional tokenization
            tokens = self.preprocess_text(document)
        
        # Calculate log probabilities for each class
        log_probs = {}
        feature_contributions = {}
        
        for label in self.class_priors:
            # Start with log of class prior
            log_probs[label] = math.log(self.class_priors[label])
            feature_contributions[label] = {}
            
            # Add log likelihoods for each word
            for token in tokens:
                if token in self.word_likelihoods[label]:
                    token_prob = self.word_likelihoods[label][token]
                    log_probs[label] += math.log(token_prob)
                    feature_contributions[label][token] = math.log(token_prob)
                else:
                    # Handle unknown words with Laplace smoothing
                    vocab_size = len(self.vocab)
                    total_words_in_class = sum(self.word_likelihoods[label].values())
                    unknown_prob = self.alpha / (total_words_in_class + self.alpha * vocab_size)
                    log_probs[label] += math.log(unknown_prob)
                    feature_contributions[label][token] = math.log(unknown_prob)
        
        # Find the class with the highest probability
        predicted_class = max(log_probs.items(), key=lambda x: x[1])[0]
        
        # Convert log probabilities back to regular probabilities
        # Using the log-sum-exp trick to avoid underflow
        max_log_prob = max(log_probs.values())
        exp_sum = sum(math.exp(log_prob - max_log_prob) for log_prob in log_probs.values())
        
        probabilities = {}
        for label, log_prob in log_probs.items():
            probabilities[label] = math.exp(log_prob - max_log_prob) / exp_sum
        
        if return_details:
            return predicted_class, probabilities, feature_contributions
        return predicted_class, probabilities
    
    def evaluate(self, test_documents, test_labels):
        """Evaluate the classifier on test data"""
        if len(test_documents) != len(test_labels):
            raise ValueError("Test documents and labels must have the same length")
            
        correct = 0
        predictions = []
        
        for doc, true_label in zip(test_documents, test_labels):
            pred_label, _ = self.predict(doc)
            predictions.append(pred_label)
            if pred_label == true_label:
                correct += 1
        
        accuracy = correct / len(test_documents)
        return accuracy, predictions

# Function to load and prepare training data from CSV
def load_training_data(csv_filepath, text_column="text", label_column="label", max_samples=None):
    """Load training data from CSV file"""
    if not os.path.exists(csv_filepath):
        raise FileNotFoundError(f"CSV file not found: {csv_filepath}")
    
    df = pd.read_csv(csv_filepath)
    
    # Handle missing values
    df = df.dropna(subset=[text_column, label_column])
    
    # Limit samples if needed
    if max_samples and len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)
    
    # Return documents and labels
    return df[text_column].tolist(), df[label_column].tolist()

def get_top_features(feature_contributions, predicted_class, top_n=10):
    """Get the top features that contributed to the prediction"""
    features = {}
    for feature, contribution in feature_contributions[predicted_class].items():
        features[feature] = contribution
    
    # Sort by absolute contribution and take top N
    sorted_features = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:top_n]
    return dict(sorted_features)

# Function to integrate with the main application
def detect_fake_news_with_nb(articles_data, model_path="models/naive_bayes_classifier.pkl", use_ngrams=True):
    """Detect fake news using Naive Bayes classifier with detailed computation info"""
    # Try to load existing model
    try:
        classifier = joblib.load(model_path)
        print("✅ Loaded pre-trained Naive Bayes model")
    except:
        print("❌ No pre-trained model found. Training new model...")
        # Try to train from CSV data
        csv_path = "data/WELFake_Dataset.csv"
        if os.path.exists(csv_path):
            try:
                # Load training data
                documents, labels = load_training_data(
                    csv_path, 
                    text_column="text",  # Using text content for training
                    label_column="label",
                    max_samples=1000  # Reduced to 1000 samples for faster training
                )
                
                # Train classifier with enhanced features
                classifier = NaiveBayesClassifier(alpha=1.0, use_ngrams=use_ngrams)
                classifier.train(documents, labels)
                
                # Save the model
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                joblib.dump(classifier, model_path)
                print("✅ Model trained successfully with enhanced features")
            except Exception as e:
                print(f"❌ Error training model: {e}")
                return articles_data
        else:
            print("❌ Could not train model - CSV file not found")
            return articles_data
    
    # Analyze each article
    for article in articles_data:
        # Use full content if available, otherwise use title and teaser
        if 'Full Content' in article and article['Full Content'] and pd.notna(article['Full Content']):
            text = article['Full Content']
        elif 'Content Paragraphs' in article and article['Content Paragraphs'] and pd.notna(article['Content Paragraphs']):
            text = article['Content Paragraphs']
        else:
            text = str(article['Title']) + ' ' + str(article.get('Teaser', ''))
        
        # Skip if text is empty or NaN
        if not text or pd.isna(text) or text == 'nan' or text.strip() == '':
            print(f"⚠️ Skipping article with empty content: {article['Title']}")
            # Add default values if text is empty
            article['Prediction'] = 'Unknown'
            article['Fake_Probability'] = 0.5
            article['Real_Probability'] = 0.5
            article['Confidence'] = 0.5
            article['Fake_News_Label'] = '❓ NO CONTENT'
            article['Model_Used'] = 'N/A - No content'
            article['Key_Features'] = {}
            continue
            
        try:
            prediction, probabilities, feature_contributions = classifier.predict(text, return_details=True)
            
            # Add predictions to article with detailed computation info
            article['Prediction'] = 'Fake' if prediction == 1 else 'Real'
            article['Fake_Probability'] = probabilities.get(1, 0.5)
            article['Real_Probability'] = probabilities.get(0, 0.5)
            article['Confidence'] = max(probabilities.values())
            
            # Set a label for display
            if prediction == 1:
                article['Fake_News_Label'] = '⚠️ POTENTIALLY FAKE'
            else:
                article['Fake_News_Label'] = '✅ LIKELY REAL'
            
            # Add model info for computation details
            article['Model_Used'] = 'Enhanced Naive Bayes with N-grams' if use_ngrams else 'Standard Naive Bayes'
            
            # Extract key features that contributed to the decision
            article['Key_Features'] = get_top_features(feature_contributions, prediction, top_n=10)
                
        except Exception as e:
            print(f"❌ Error predicting article: {e}")
            # Add default values if prediction fails
            article['Prediction'] = 'Unknown'
            article['Fake_Probability'] = 0.5
            article['Real_Probability'] = 0.5
            article['Confidence'] = 0.5
            article['Fake_News_Label'] = '❓ ANALYSIS FAILED'
            article['Model_Used'] = 'Error - Could not analyze'
            article['Key_Features'] = {}
    
    print(f"✅ Successfully analyzed {len(articles_data)} articles with Enhanced Naive Bayes")
    return articles_data