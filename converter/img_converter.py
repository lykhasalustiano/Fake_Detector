import cv2
import pytesseract
from PIL import Image
import numpy as np
import re
from typing import Tuple, Optional

class AdaptiveImageTextAnalyzer:
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize the AdaptiveImageTextAnalyzer
        
        Args:
            tesseract_path: Path to tesseract executable (if not in PATH)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Article indicator keywords (for content analysis)
        self.article_keywords = [
            'article', 'news', 'report', 'story', 'according', 'sources',
            'said', 'told', 'reported', 'published', 'breaking', 'update',
            'journalist', 'correspondent', 'editor', 'newspaper', 'magazine',
            'headline', 'byline', 'dateline', 'press', 'media'
        ]
    
    def preprocess_image(self, image_path: str) -> list:
        """
        Preprocess the image with multiple techniques to improve OCR accuracy
        
        Args:
            image_path: Path to the input image
            
        Returns:
            List of processed images to try for OCR
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Could not load image. Please check the file path.")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            processed_images = []
            
            # Method 1: Original image (sometimes works best)
            processed_images.append(("original", gray))
            
            # Method 2: Simple thresholding
            _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("otsu_threshold", thresh1))
            
            # Method 3: Gaussian blur + threshold
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh2 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("blur_threshold", thresh2))
            
            # Method 4: Adaptive thresholding
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            processed_images.append(("adaptive", adaptive))
            
            # Method 5: Morphological operations
            kernel = np.ones((2, 2), np.uint8)
            opening = cv2.morphologyEx(thresh1, cv2.MORPH_OPEN, kernel)
            processed_images.append(("morphological", opening))
            
            # Method 6: Erosion and dilation
            kernel2 = np.ones((1, 1), np.uint8)
            erosion = cv2.erode(thresh1, kernel2, iterations=1)
            dilation = cv2.dilate(erosion, kernel2, iterations=1)
            processed_images.append(("erosion_dilation", dilation))
            
            # Method 7: Contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            _, thresh_enhanced = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("enhanced_contrast", thresh_enhanced))
            
            return processed_images
            
        except Exception as e:
            raise Exception(f"Error preprocessing image: {str(e)}")
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using multiple OCR approaches for best readability
        
        Args:
            image_path: Path to the input image
            
        Returns:
            Best extracted text as string
        """
        try:
            # Get multiple preprocessed versions of the image
            processed_images = self.preprocess_image(image_path)
            
            best_text = ""
            best_score = 0
            best_method = ""
            
            # Different OCR configurations optimized for readability
            ocr_configs = [
                # Assume a single uniform block of vertically aligned text
                '--oem 3 --psm 6',
                # Assume a single uniform block of text
                '--oem 3 --psm 4',
                # Fully automatic page segmentation
                '--oem 3 --psm 3',
                # Assume a single column of text of variable sizes
                '--oem 3 --psm 5',
                # Single text line
                '--oem 3 --psm 7',
                # Sparse text (find as much text as possible in no particular order)
                '--oem 3 --psm 11',
                # Raw line (treat the image as a single text line)
                '--oem 3 --psm 13',
                # Single word in a circle (if that's the case)
                '--oem 3 --psm 8'
            ]
            
            print("🔍 Trying different OCR methods for best readability...")
            
            for method_name, processed_img in processed_images:
                for i, config in enumerate(ocr_configs):
                    try:
                        # Extract text using current configuration
                        text = pytesseract.image_to_string(processed_img, config=config)
                        
                        if text and len(text.strip()) > 0:
                            # Clean up the extracted text while preserving structure
                            cleaned_text = self.clean_text_preserve_structure(text)
                            
                            # Score this result for readability
                            score = self._score_readability(cleaned_text)
                            
                            if score > best_score:
                                best_text = cleaned_text
                                best_score = score
                                best_method = f"{method_name} + config_{i+1}"
                                print(f"  ✅ Better result found: {method_name} + config_{i+1} (readability score: {score:.2f})")
                    
                    except Exception:
                        continue  # Try next configuration
            
            if best_text:
                print(f"🏆 Best method: {best_method} (final readability score: {best_score:.2f})")
                return best_text
            else:
                return ""
            
        except Exception as e:
            raise Exception(f"Error extracting text from image: {str(e)}")
    
    def clean_text_preserve_structure(self, text: str) -> str:
        """
        Clean text while preserving paragraph structure and readability
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text with preserved structure
        """
        # First, normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Fix common OCR spacing issues
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between lowercase-uppercase
        text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)  # Add space between letter-digit
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)  # Add space between digit-letter
        
        # Fix word spacing issues (common OCR problem)
        text = re.sub(r'([a-z])([a-z][A-Z])', r'\1 \2', text)  # Fix words stuck together
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)  # Add space after sentence endings
        
        # Clean up obvious OCR artifacts but keep structure
        text = re.sub(r'[^\w\s.,!?;:"\'()\-\[\]{}/@#$%^&*+=<>|\\~`_\n]', ' ', text)
        
        # Fix excessive punctuation
        text = re.sub(r'[.,!?;:]{3,}', '.', text)
        
        # Process line by line to preserve paragraph structure
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # Only process non-empty lines
                # Remove excessive spaces within the line
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)
            else:
                # Preserve paragraph breaks
                if cleaned_lines and cleaned_lines[-1] != '':
                    cleaned_lines.append('')
        
        # Join lines back together with proper spacing
        result = '\n'.join(cleaned_lines)
        
        # Clean up multiple empty lines but preserve paragraph structure
        result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)
        
        return result.strip()
    
    def _score_readability(self, text: str) -> float:
        """
        Score text based on readability and structure preservation
        
        Args:
            text: Cleaned text
            
        Returns:
            Readability score (higher is better)
        """
        if not text or len(text.strip()) < 1:
            return 0.0
        
        score = 0.0
        
        # Basic length score
        words = text.split()
        word_count = len(words)
        length_score = min(word_count, 100) / 100.0
        score += length_score * 15
        
        # Readability indicators
        if words:
            # Count properly formed English words
            readable_words = 0
            for word in words:
                # Clean word for checking
                clean_word = re.sub(r'[^\w]', '', word.lower())
                if len(clean_word) > 1:
                    # Check if word looks readable (has vowels, reasonable length, not garbled)
                    has_vowels = any(vowel in clean_word for vowel in 'aeiouAEIOU')
                    reasonable_length = 2 <= len(clean_word) <= 20
                    not_garbled = not re.search(r'(.)\1{3,}', clean_word)  # No 4+ repeated chars
                    no_excessive_consonants = len(re.findall(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{5,}', clean_word)) == 0
                    
                    if has_vowels and reasonable_length and not_garbled and no_excessive_consonants:
                        readable_words += 1
            
            if word_count > 0:
                readability_ratio = readable_words / word_count
                score += readability_ratio * 40
        
        # Sentence structure score
        sentences = re.split(r'[.!?]+', text)
        valid_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence.split()) >= 3:  # At least 3 words
                valid_sentences.append(sentence)
        
        if len(sentences) > 0:
            sentence_quality = len(valid_sentences) / len(sentences)
            score += sentence_quality * 25
        
        # Paragraph structure bonus
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) > 1:
            score += 10  # Bonus for preserving paragraph structure
        
        # Penalty for excessive special characters
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s.,!?;:"\'\-()]', text)) / max(len(text), 1)
        score -= special_char_ratio * 20
        
        # Penalty for excessive repeated characters or obvious artifacts
        repeated_patterns = len(re.findall(r'(.)\1{3,}', text))
        score -= repeated_patterns * 3
        
        # Bonus for proper capitalization patterns
        sentences_with_caps = len(re.findall(r'[.!?]\s+[A-Z]', text)) + (1 if text and text[0].isupper() else 0)
        if len(valid_sentences) > 0:
            cap_ratio = sentences_with_caps / len(valid_sentences)
            score += cap_ratio * 10
        
        return max(0.0, score)
    
    def analyze_text_content(self, text: str) -> dict:
        """
        Analyze the extracted text content without fixed thresholds
        
        Args:
            text: Extracted text to analyze
            
        Returns:
            Dictionary with analysis results
        """
        if not text or len(text.strip()) < 1:
            return {
                'content_type': 'empty',
                'confidence': 0,
                'details': "No readable text detected in the image"
            }
        
        # Count words and sentences
        words = text.split()
        word_count = len(words)
        
        # Count sentences (simple approach)
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Count paragraphs
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        # Calculate text characteristics
        avg_words_per_sentence = word_count / max(sentence_count, 1)
        
        # Analyze content type based on structure and keywords
        text_lower = text.lower()
        
        # Count article keywords
        keyword_matches = [keyword for keyword in self.article_keywords if keyword in text_lower]
        keyword_count = len(keyword_matches)
        
        # Determine content type based on adaptive analysis
        content_analysis = self._classify_content_type(
            word_count, sentence_count, paragraph_count, 
            keyword_count, avg_words_per_sentence, text_lower
        )
        
        return {
            'content_type': content_analysis['type'],
            'confidence': content_analysis['confidence'],
            'details': content_analysis['details'],
            'statistics': {
                'word_count': word_count,
                'sentence_count': sentence_count,
                'paragraph_count': paragraph_count,
                'avg_words_per_sentence': round(avg_words_per_sentence, 2),
                'keyword_matches': keyword_matches,
                'keyword_count': keyword_count
            }
        }
    
    def _classify_content_type(self, word_count: int, sentence_count: int, 
                              paragraph_count: int, keyword_count: int, 
                              avg_words_per_sentence: float, text_lower: str) -> dict:
        """
        Classify content type based on adaptive analysis
        """
        # Score different content types
        article_score = 0
        document_score = 0
        snippet_score = 0
        list_score = 0
        
        # Article indicators
        if keyword_count > 0:
            article_score += keyword_count * 2
        if 8 <= avg_words_per_sentence <= 25:  # Typical article sentence length
            article_score += 2
        if paragraph_count > 1:
            article_score += 1
        if sentence_count > 2:
            article_score += 1
        if any(indicator in text_lower for indicator in ['by ', 'published', 'date', 'author']):
            article_score += 2
        
        # Document indicators
        if paragraph_count > 3:
            document_score += 2
        if word_count > 100:
            document_score += 1
        if any(indicator in text_lower for indicator in ['section', 'chapter', 'page', 'document']):
            document_score += 2
        
        # Snippet indicators (short text, single idea)
        if word_count < 50 and sentence_count <= 3:
            snippet_score += 3
        if paragraph_count == 1:
            snippet_score += 1
        
        # List indicators
        if text_lower.count('\n') > word_count * 0.1:  # Many line breaks relative to words
            list_score += 2
        if any(char in text_lower for char in ['•', '-', '*', '1.', '2.', '3.']):
            list_score += 2
        
        # Determine the most likely content type
        scores = {
            'article': article_score,
            'document': document_score,
            'snippet': snippet_score,
            'list': list_score
        }
        
        max_score = max(scores.values())
        
        if max_score == 0:
            return {
                'type': 'general_text',
                'confidence': 50,
                'details': f"General text content detected ({word_count} words, {sentence_count} sentences)"
            }
        
        content_type = max(scores, key=scores.get)
        confidence = min(95, max(60, (max_score / (word_count/20 + 1)) * 100))
        
        details_map = {
            'article': f"Article-like content detected ({word_count} words, {sentence_count} sentences, {keyword_count} article keywords found)",
            'document': f"Document content detected ({word_count} words, {paragraph_count} paragraphs)",
            'snippet': f"Text snippet detected ({word_count} words, {sentence_count} sentences)",
            'list': f"List-like content detected ({paragraph_count} items)"
        }
        
        return {
            'type': content_type,
            'confidence': round(confidence),
            'details': details_map[content_type]
        }
    
    def analyze_image(self, image_path: str) -> dict:
        """
        Main method to analyze image text content adaptively
        
        Args:
            image_path: Path to the input image
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Extract text from image
            extracted_text = self.extract_text_from_image(image_path)
            
            # Analyze the extracted text
            analysis = self.analyze_text_content(extracted_text)
            
            result = {
                'success': True,
                'text': extracted_text,
                'content_type': analysis['content_type'],
                'confidence': analysis['confidence'],
                'details': analysis['details'],
                'statistics': analysis.get('statistics', {}),
                'message': None
            }
            
            # Generate appropriate message
            if analysis['content_type'] == 'empty':
                result['message'] = f"❌ {analysis['details']}"
            else:
                result['message'] = f"✅ Content analyzed successfully. {analysis['details']} (Confidence: {analysis['confidence']}%)"
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'text': None,
                'content_type': 'error',
                'confidence': 0,
                'details': f"Error processing image: {str(e)}",
                'statistics': {},
                'message': f"❌ Failed to process image: {str(e)}"
            }

def main():
    """
    Example usage of the AdaptiveImageTextAnalyzer
    """
    # Initialize analyzer
    analyzer = AdaptiveImageTextAnalyzer()
    
    # Example usage
    print("=== Adaptive Image Text Analyzer ===\n")
    
    # Get image path from user
    image_path = input("Enter the path to your image file: ").strip()
    
    if not image_path:
        print("❌ No image path provided.")
        return
    
    print(f"\n🔍 Analyzing image: {image_path}")
    print("=" * 50)
    
    # Analyze image text
    result = analyzer.analyze_image(image_path)
    
    # Display results
    print(f"Status: {'✅ Success' if result['success'] else '❌ Failed'}")
    print(f"Message: {result['message']}")
    print(f"Content Type: {result['content_type'].replace('_', ' ').title()}")
    print(f"Confidence: {result['confidence']}%")
    
    if result['statistics']:
        stats = result['statistics']
        print(f"\n📊 Text Statistics:")
        print(f"  • Words: {stats['word_count']}")
        print(f"  • Sentences: {stats['sentence_count']}")
        print(f"  • Paragraphs: {stats['paragraph_count']}")
        print(f"  • Avg Words per Sentence: {stats['avg_words_per_sentence']}")
        if stats['keyword_matches']:
            print(f"  • Article Keywords Found: {', '.join(stats['keyword_matches'])}")
    
    if result['text']:
        print(f"\n📄 Extracted Text:")
        print("-" * 50)
        print(result['text'])
        print("-" * 50)
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()