import re
from typing import Dict, Any, List, Optional

class IntentClassifier:
    """
    Classifies user input into different intent categories with high precision.
    This classifier focuses on reducing false positives and avoiding mixing intents.
    """
    def __init__(self):
        """Initialize the intent classifier with precise patterns for each intent type."""
        # Define contexts to disambiguate similar patterns
        self.contexts = {
            "review": [
                r'\breview\b', r'\bquiz\b', r'\btest\b', r'\bsession\b', 
                r'\bpractice\b', r'\bquestion\b', r'\bdifficulty\b'
            ],
            "speech": [
                r'\bspeech\b', r'\bvoice\b', r'\btalk\b', r'\blisten\b', 
                r'\bmicrophone\b', r'\bspeak\b', r'\brecognition\b'
            ],
            "document": [
                r'\bdocument\b', r'\bfile\b', r'\bpdf\b', r'\bpptx\b', 
                r'\bupload\b', r'\btext\b', r'\bmaterial\b'
            ],
            "settings": [
                r'\bsetting\b', r'\boption\b', r'\bconfigure\b', 
                r'\bpreferenc\b', r'\bcustom\b'
            ]
        }
        
        # Define intent patterns with word boundaries and more specific phrases
        self.patterns = {
            # Document-related intents
            "document_upload": [
                r'\b(upload|add|attach|send).{1,20}(document|pdf|file|pptx)\b',
                r'\b(document|pdf|file|pptx).{1,20}(upload|add|attach|send)\b',
                r'\bI.{1,10}(want|like|need).{1,20}(upload|add).{1,20}(document|pdf|file)\b'
            ],
            
            # Review session intents
            "start_review": [
                r'\b(start|begin|launch).{1,10}(review|quiz|test|practice|session)\b',
                r'\blet\'s (start|begin|do).{1,10}(review|quiz|test|practice)\b',
                r'\bI.{1,10}(want|like|ready).{1,10}(start|begin|do).{1,10}(review|quiz|test)\b'
            ],
            
            "stop_review": [
                r'\b(stop|end|finish|quit|exit|terminate).{1,10}(review|quiz|test|session|practice)\b',
                r'\b(cancel|halt).{1,10}(review|quiz|test|session|practice)\b'
            ],
            
            "review_status": [
                r'\b(what.{1,10}(status|progress)|how.{1,10}(doing|progressing))\b',
                r'\b(status|progress).{1,10}(review|quiz|test|session)\b',
                r'\bhow.{1,10}(am|are|is|was).{1,10}(doing|performing|scoring)\b',
                r'\b(correct|right|wrong|score|result).{1,10}(answer|question)\b'
            ],
            
            # Settings intents
            "review_settings": [
                r'\b(what|show|display|list).{1,15}(settings|options|configuration)\b',
                r'\b(what).{1,10}(is|are).{1,10}(current|available).{1,10}(settings|options)\b',
                r'\bcurrent.{1,10}(settings|options|configuration)\b',
                r'\bsettings.{1,10}(now|current|available)\b'
            ],
            
            "set_question_type": [
                r'\b(set|change|switch|use).{1,10}(question).{1,10}(type|style|format).{1,10}(to|as).{1,10}(multiple.?choice|free.?text|open.?ended)\b',
                r'\b(use|do|set).{1,10}(multiple.?choice|free.?text|open.?ended).{1,10}(question|format|style)\b',
                r'\b(multiple.?choice|free.?text|open.?ended).{1,10}(question|format|style)\b',
                r'\b(question).{1,10}(type|style|format).{1,10}(to|as|:).{1,10}(multiple.?choice|free.?text|open.?ended)\b'  # New pattern without "set"
            ],

            
            "set_num_questions": [
                r'\b(\d+)\s+questions?\b',  # Simple "10 questions"
                r'\bquestions?\s+(\d+)\b',  # "questions 10"
                r'\b(set|use|do|want|have|give|ask|make).{0,10}(\d+).{0,5}questions?\b',  # "set 10 questions"
                r'\b(set|change|make).{0,10}(number|amount|count).{0,10}questions?.{0,10}(\d+)\b',  # "set number of questions to 10"
                r'\bI.{0,10}(want|would like|need).{0,10}(\d+).{0,5}questions?\b',  # "I want 10 questions"
                r'\b(prepare|create|have|do).{0,5}(\d+).{0,5}questions?\b',  # "prepare 10 questions"
                r'\bquestions?.{0,5}(should|will).{0,5}be.{0,5}(\d+)\b',  # "questions should be 10"
                r'\b(number|amount|count).{1,10}(of)?.{1,5}questions?.{1,10}(\d+)\b', # "number of questions 10" without "set"
                r'\band.{1,10}(\d+).{1,5}questions?\b', # "and 10 questions"
                r'\band.{1,10}(number|amount|count).{1,10}(of)?.{1,5}questions?.{1,10}(\d+)\b', # "and number of questions 10"
                r'\buse.{1,10}(\d+).{1,5}questions?\b', # "use 10 questions" without "set"
                r'(number|amount|count).{1,10}(of)?.{1,5}questions?.{1,10}(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b',  # "number of questions five"
            ],
            
            "set_topic": [
                r'\b(set|change|focus|concentrate).{1,10}(topic|subject).{1,10}(to|on|about)\b',
                r'\b(topic|subject).{1,5}(should|will|must).{1,5}(be|include)\b',
                r'\bfocus.{1,10}(on).{1,10}(topic|subject)\b',
                r'\b(topic|subject).{1,10}(to|as|:).{1,15}([^,.!?;]+)\b', # Topic to X without "set"
                r'\band.{1,10}(topic|subject).{1,10}(to|on|about|as|:).{1,15}([^,.!?;]+)\b', # And topic to X
                r'\bthe.{1,5}(topic|subject).{1,10}(to|on|about|as|:).{1,15}([^,.!?;]+)\b', # The topic to X
            ],
            
            "set_difficulty": [
                r'\b(set|change|use).{1,10}(difficulty|level).{1,10}(to|as).{1,10}(easy|medium|hard|simple|intermediate|difficult|challenging)\b',
                r'\b(easy|medium|hard|simple|difficult|challenging).{1,10}(difficulty|level|questions)\b',
                r'\b(make|set).{1,10}(it|questions).{1,10}(easy|medium|hard|simple|difficult|challenging)\b',
                r'\b(difficulty).{1,10}(to|as|:).{1,10}(easy|medium|hard|simple|intermediate|difficult|challenging)\b',  # New pattern without "set"
                r'\band.{1,10}(difficulty|level).{1,10}(to|as|:).{1,10}(easy|medium|hard|simple|intermediate|difficult|challenging)\b'  # Pattern with "and difficulty"
            ],
            
            # Speech recognition intents - very specific to avoid confusion
            "enable_speech": [
                r'\b(enable|activate|turn.{1,5}on).{1,10}(speech|voice|microphone|speaking|recognition)\b',
                r'\b(use|start).{1,10}(speech|voice).{1,10}(recognition|input|mode)\b',
                r'\bI.{1,10}(want|like).{1,10}(speak|talk).{1,10}(to|with|instead).{1,10}(typing|text)\b'
            ],
            
            "disable_speech": [
                r'\b(disable|deactivate|turn.{1,5}off).{1,10}(speech|voice|microphone|speaking|recognition)\b',
                r'\b(stop|don\'t).{1,10}(use|listen).{1,10}(speech|voice|microphone)\b',
                r'\b(type|text).{1,10}(only|instead).{1,10}(speech|voice|talking)\b'
            ],

            "continue": [
                r'\b(next|continue|proceed|go on|go ahead|move on)\b',
                r'\b(next question|another question|ask another|ask next)\b',
                r'^(ok|okay|sure|yes|yep|yeah|y|alright|fine|ready|got it)\b'
            ],

            "out_of_scope": [
                r'\b(who|what|where|when|why|how).{1,30}(world|universe|life|economy|politics|news|weather)\b',
                r'\b(tell|explain|describe).{1,20}(yourself|history|science|math|physics|chemistry|biology)\b',
                r'\b(what).{1,5}(is|are).{1,20}(meaning|purpose|goal|objective).{1,10}(life|universe|existence)\b',
                r'\b(browse|search|find|google|look up|navigate).{1,20}(internet|web|online)\b',
                r'\b(write|create|generate).{1,20}(program|app|application|website|code).{1,20}(not|unrelated).{1,20}(document|study|review)\b',
                r'\b(analyze|process|examine).{1,20}(data|information|statistics).{1,20}(not|unrelated).{1,20}(document|study|review)\b'
            ],

            "unknown": [
                r'^\s*\b(help|assist|do something|not sure|confused|lost)\b\s*$',  # Make these match only when they're the entire message
                r'^(?!.*\b(review|document|speech|question|topic|difficulty|setting)\b)^\s*\b(what|how|can you|would you|could you)\b.{0,50}$',  # Shorter queries only
                r'^(?!.*\b(upload|start|stop|status|setting|question|topic|difficulty|speech)\b)^\s*\b(do|work|function|capability)\b.{0,50}$'  # Shorter queries only
            ]
        }
    
    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify text into intent types with improved multi-intent support.
        Specifically enhanced for compound setting commands.
        
        Args:
            text: User input text
            
        Returns:
            Dictionary with primary intent type and associated data
        """
        # Determine the dominant context in the text
        context_scores = self._determine_context(text)
        dominant_context = max(context_scores.items(), key=lambda x: x[1])[0] if context_scores else None
        
        # Log for debugging
        print(f"Context scores: {context_scores}")
        print(f"Dominant context: {dominant_context}")
        
        # Initialize result with default intent as "answer"
        result = {
            "intent": "answer", 
            "answer": text,
            "text": text,
            "additional_intents": []
        }
        
        # Check for set_num_questions intent first (special handling)
        num_questions_match = self._check_num_questions(text)
        if num_questions_match:
            result = {
                "intent": "set_num_questions",
                "num_questions": num_questions_match,
                "text": text,
                "additional_intents": []
            }
            print(f"Direct number match: {num_questions_match}")
            
            # Now look for other intents in the same message
            other_intents = self._find_other_intents(text, "set_num_questions")
            if other_intents:
                result["additional_intents"] = other_intents
            
            return result
        
        # Check for compound settings in a single command
        # This helps with cases like "set question type to multiple choice and difficulty to hard"
        compound_settings = self._check_compound_settings(text)
        if compound_settings and len(compound_settings) > 1:
            # We found multiple settings in one command
            print(f"Detected compound settings: {compound_settings}")
            
            # Sort by priority (lowest number is highest priority)
            priority_order = {
                "set_difficulty": 1,
                "set_question_type": 2,
                "set_num_questions": 3,
                "set_topic": 4
            }
            
            sorted_intents = sorted(compound_settings, key=lambda x: priority_order.get(x["intent"], 99))
            
            # Use the first one as primary intent
            primary_intent = sorted_intents[0]
            result = primary_intent
            
            # Add the rest as additional intents
            result["additional_intents"] = sorted_intents[1:]
            
            # Also add any other intents like "start_review"
            other_intents = self._find_other_intents(text, exclude_intents=[i["intent"] for i in compound_settings])
            if other_intents:
                result["additional_intents"].extend(other_intents)
                
            return result
        
        # Process multiple sentences for potential multiple intents
        sentences = self._split_into_sentences(text)
        print(f"Split into {len(sentences)} parts: {sentences}")
        
        detected_intents = []
        sentence_intent_map = {}  # Maps sentences to their detected intents
        
        # Process each sentence
        for sentence in sentences:
            intent_match = self._match_intent(sentence, dominant_context)
            if intent_match:
                detected_intents.append(intent_match)
                sentence_intent_map[sentence] = intent_match
                print(f"Matched intent '{intent_match}' in sentence: '{sentence}'")
            else:
                print(f"No intent match for sentence: '{sentence}'")
        
        # If no intents were detected in sentences, check for out-of-scope or unknown intents
        if not detected_intents:
            # Check if the text matches out-of-scope patterns
            for pattern in self.patterns["out_of_scope"]:
                if re.search(pattern, text, re.IGNORECASE):
                    # Return immediately if we find an out-of-scope match
                    return {
                        "intent": "out_of_scope",
                        "text": text,
                        "additional_intents": []
                    }
            
            # Only check for unknown intent if we didn't find an out-of-scope match
            for pattern in self.patterns["unknown"]:
                if re.search(pattern, text, re.IGNORECASE):
                    return {
                        "intent": "unknown",
                        "text": text,
                        "additional_intents": []
                    }
            
            # If still no match, return the default answer intent
            return result
        
        # Process detected intents - prioritize action intents
        priority_order = {
            "set_difficulty": 1,      # Settings intents have highest priority
            "set_question_type": 1,
            "set_num_questions": 1,
            "set_topic": 1,
            "enable_speech": 2,
            "disable_speech": 2,
            "start_review": 3,        # Action intents have medium priority
            "stop_review": 3,
            "document_upload": 3,
            "continue": 3,
            "review_status": 4,       # Information intents have lower priority
            "review_settings": 4,
            "answer": 5,
            "unknown": 6,
            "out_of_scope": 7
        }
        
        # Sort intents by priority (lower number is higher priority)
        sorted_intents = sorted(detected_intents, key=lambda x: priority_order.get(x, 99))
        primary_intent = sorted_intents[0]
        
        # Find the sentence that matched the primary intent
        primary_sentence = next((s for s, i in sentence_intent_map.items() if i == primary_intent), text)
        
        # Extract data from the primary intent using its matched sentence
        primary_data = self._extract_intent_data(primary_sentence, primary_intent)
        
        # Update the result with primary intent data
        result.update(primary_data)
        
        # Add additional intents, with their specific sentence data
        additional_intents = []
        for intent in sorted_intents[1:]:
            if intent != primary_intent:  # Avoid duplicates
                # Find the sentence that matched this intent
                intent_sentence = next((s for s, i in sentence_intent_map.items() if i == intent), text)
                intent_data = self._extract_intent_data(intent_sentence, intent)
                additional_intents.append(intent_data)
        
        # Only include additional intents in the result if there are any
        if additional_intents:
            result["additional_intents"] = additional_intents
            
        return result

    def _check_compound_settings(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for multiple settings in a single command.
        For example: "set question type to multiple choice and difficulty to hard"
        
        Returns:
            A list of intent data dictionaries for each detected setting
        """
        settings = []
        
        # Check for difficulty setting
        difficulty_match = re.search(r'\b(difficulty|level).{1,10}(to|:|\bas\b).{1,10}(easy|medium|hard|challenging|simple|difficult)', text, re.IGNORECASE)
        if difficulty_match:
            difficulty = None
            if re.search(r'\b(easy|simple|beginner)\b', difficulty_match.group(3), re.IGNORECASE):
                difficulty = "easy"
            elif re.search(r'\b(medium|moderate|intermediate)\b', difficulty_match.group(3), re.IGNORECASE):
                difficulty = "medium"
            elif re.search(r'\b(hard|difficult|challenging|advanced)\b', difficulty_match.group(3), re.IGNORECASE):
                difficulty = "hard"
                
            if difficulty:
                settings.append({
                    "intent": "set_difficulty",
                    "difficulty": difficulty,
                    "text": text
                })
        
        # Check for question type setting
        question_type_match = re.search(r'\b(question|type).{1,15}(to|:|\bas\b).{1,15}(multiple.?choice|free.?text|open.?ended)', text, re.IGNORECASE)
        if question_type_match:
            question_type = None
            if re.search(r'\b(multiple.?choice|mc)\b', question_type_match.group(3), re.IGNORECASE):
                question_type = "multiple-choice"
            elif re.search(r'\b(free.?text|open.?ended)\b', question_type_match.group(3), re.IGNORECASE):
                question_type = "free-text"
                
            if question_type:
                settings.append({
                    "intent": "set_question_type",
                    "question_type": question_type,
                    "text": text
                })
        
        # Check for number of questions
        # First check for digit numbers
        num_questions_match = re.search(r'\b(\d+).{1,5}(questions)\b|\b(questions).{1,5}(\d+)\b', text, re.IGNORECASE)
        if num_questions_match:
            # Find the number
            num_str = next((g for g in num_questions_match.groups() if g and g.isdigit()), None)
            if num_str:
                try:
                    num_questions = int(num_str)
                    settings.append({
                        "intent": "set_num_questions",
                        "num_questions": num_questions,
                        "text": text
                    })
                except ValueError:
                    pass
        else:
            # Check for word numbers
            word_num_match = re.search(r'\b(\w+[-\s]?\w*).{1,5}(questions)\b|\b(questions).{1,5}(\w+[-\s]?\w*)\b', text, re.IGNORECASE)
            if word_num_match:
                # Find the potential word number
                word_match = None
                for g in word_num_match.groups():
                    if g and g.lower() != 'questions':
                        word_match = g
                        break
                
                if word_match:
                    number = self._word_to_number(word_match)
                    if number is not None:
                        settings.append({
                            "intent": "set_num_questions",
                            "num_questions": number,
                            "text": text
                        })
        
        # Check for topic setting
        topic_match = re.search(r'\b(topic|subject).{1,10}(to|:|\bon\b|\babout\b).{1,30}', text, re.IGNORECASE)
        if topic_match:
            # Extract potential topic
            topic_text = topic_match.group(0)
            after_to = re.sub(r'^.*?(to|:|\bon\b|\babout\b)\s+', '', topic_text).strip()
            
            if after_to and len(after_to) > 1:
                # Clean up the topic
                topics = [after_to]
                settings.append({
                    "intent": "set_topic",
                    "topics": topics,
                    "text": text
                })
        
        return settings
            
    def _word_to_number(self, word: str) -> Optional[int]:
        """
        Convert a word representation of a number to an integer.
        
        Args:
            word: Word representation of a number (e.g., 'five', 'twenty')
            
        Returns:
            Integer value or None if not recognized
        """
        word = word.lower().strip()
        
        # Dictionary of basic number words
        number_words = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
            'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
            'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
            'eighty': 80, 'ninety': 90
        }
        
        # Check if it's a basic number word
        if word in number_words:
            return number_words[word]
        
        # Handle compound words like 'twenty-five'
        if '-' in word:
            parts = word.split('-')
            if len(parts) == 2 and parts[0] in number_words and parts[1] in number_words:
                # Ensure first part is a tens value and second is a ones value
                if parts[0] in ['twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']:
                    return number_words[parts[0]] + number_words[parts[1]]
        
        # Handle compound words like 'twenty five' (without hyphen)
        words = word.split()
        if len(words) == 2:
            if words[0] in ['twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'] and words[1] in number_words:
                return number_words[words[0]] + number_words[words[1]]
        
        return None

    def _check_num_questions(self, text: str) -> Optional[int]:
        """Direct check for number of questions pattern with word number support."""
        # First try digit patterns
        patterns = [
            r'\b(\d+)\s+questions?\b',  # "10 questions"
            r'\b(\d+)\s+q\b',  # "10 q"
            r'\bquestions?\s+(\d+)\b',  # "questions 10"
            r'\b(set|use|do|want|have).{1,10}(\d+).{1,5}questions?\b',  # "set 10 questions"
            r'\b(set|change|make).{0,10}(number|amount|count).{0,10}questions?.{0,10}(to|as|at|of).{0,5}(\d+)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract the number from the match
                num_str = next((g for g in match.groups() if g and g.isdigit()), None)
                if num_str:
                    try:
                        return int(num_str)
                    except ValueError:
                        continue
        
        # Then try word number patterns
        word_patterns = [
            r'\b(\w+[-\s]?\w*)\s+questions?\b',  # "five questions" or "twenty-five questions"
            r'\b(\w+[-\s]?\w*)\s+q\b',  # "five q"
            r'\bquestions?\s+(\w+[-\s]?\w*)\b',  # "questions five"
            r'\b(set|use|do|want|have).{1,10}(\w+[-\s]?\w*).{1,5}questions?\b',  # "set five questions"
            r'\b(set|change|make).{0,10}(number|amount|count).{0,10}questions?.{0,10}(to|as|at|of).{0,5}(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b',  # "set number of questions to five"
        ]
        
        for pattern in word_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Find the word that might be a number
                    word_match = None
                    for g in match.groups():
                        if g and not re.match(r'^(set|use|do|want|have|to|as|at|of|number|amount|count)$', g, re.IGNORECASE):
                            word_match = g
                            break
                    
                    if word_match:
                        number = self._word_to_number(word_match)
                        if number is not None:
                            return number
        
        return None
    
    def _find_other_intents(self, text: str, exclude_intent: str = None, exclude_intents: List[str] = None) -> List[Dict[str, Any]]:
        """
        Find other intents in the text excluding specified intents.
        
        Args:
            text: The input text
            exclude_intent: A single intent to exclude
            exclude_intents: A list of intents to exclude
            
        Returns:
            A list of intent data dictionaries for other detected intents
        """
        other_intents = []
        sentences = self._split_into_sentences(text)
        
        # Create the exclusion list
        excluded = []
        if exclude_intent:
            excluded.append(exclude_intent)
        if exclude_intents:
            excluded.extend(exclude_intents)
        
        for sentence in sentences:
            for intent, patterns in self.patterns.items():
                if intent in excluded:
                    continue
                    
                for pattern in patterns:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        intent_data = self._extract_intent_data(sentence, intent)
                        if not any(i["intent"] == intent for i in other_intents):
                            other_intents.append(intent_data)
                            break
        
        return other_intents
    
    def _determine_context(self, text: str) -> Dict[str, float]:
        """
        Determine the contextual domain of the text to aid in disambiguation.
        Returns a dictionary of context types and their scores.
        """
        context_scores = {context: 0 for context in self.contexts}
        
        for context_type, patterns in self.contexts.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                context_scores[context_type] += len(matches) * 2  # Weight direct matches
                
            # Look for related words or partial matches
            if context_type == "review" and re.search(r'\b(ask|question|quiz)\b', text, re.IGNORECASE):
                context_scores[context_type] += 1
            elif context_type == "speech" and re.search(r'\b(talk|hear|audio|sound)\b', text, re.IGNORECASE):
                context_scores[context_type] += 1
            elif context_type == "document" and re.search(r'\b(content|read|material|learn)\b', text, re.IGNORECASE):
                context_scores[context_type] += 1
            elif context_type == "settings" and re.search(r'\b(change|adjust|modify|set)\b', text, re.IGNORECASE):
                context_scores[context_type] += 1
         
        # Add context detection for out-of-scope queries
        out_of_scope_keywords = [
            r'\b(news|weather|sports|politics|economy|stock|crypto|bitcoin)\b',
            r'\b(meaning of life|universe|philosophy|religion|beliefs)\b',
            r'\b(tell me about yourself|who are you|how do you work|what can you do)\b',
            r'\b(search|find|browse|google|web|internet)\b'
        ]

        for pattern in out_of_scope_keywords:
            if re.search(pattern, text, re.IGNORECASE):
                # If we detect out-of-scope keywords, reduce the scores of other contexts
                for key in context_scores:
                    context_scores[key] -= 1
                break

        return context_scores
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into semantic units that can contain different intents.
        Enhanced to identify compound settings commands.
        """
        # First split on obvious sentence boundaries
        rough_sentences = re.split(r'[.!?]\s+', text)
        
        # Process each rough sentence
        detailed_sentences = []
        
        for sentence in rough_sentences:
            if not sentence.strip():
                continue
                
            # Check for explicit compound commands with "and" or "with"
            # First, check if this might be a compound setting command
            if re.search(r'\b(set|change|make).+\b(and|with)\b', sentence, re.IGNORECASE):
                # This is likely a compound command like "set X to Y and Z to W"
                
                # Look for settings parameters in the text
                settings_types = [
                    ('question type', r'\b(question\s+type|type|format)\b'),
                    ('difficulty', r'\b(difficulty|level)\b'),
                    ('num_questions', r'\b(questions|number of questions)\b'),
                    ('topic', r'\b(topic|subject)\b')
                ]
                
                # Try to extract settings segments
                found_segments = []
                
                for setting_name, setting_pattern in settings_types:
                    # Look for this setting type in the sentence
                    setting_matches = list(re.finditer(setting_pattern, sentence, re.IGNORECASE))
                    
                    for i, match in enumerate(setting_matches):
                        start_pos = match.start()
                        
                        # Find the next setting or end of sentence
                        if i < len(setting_matches) - 1:
                            end_pos = setting_matches[i+1].start()
                        else:
                            # If we have other setting types after this one
                            other_settings = []
                            for other_name, other_pattern in settings_types:
                                if other_name != setting_name:
                                    other_match = re.search(other_pattern, sentence[start_pos:], re.IGNORECASE)
                                    if other_match:
                                        other_settings.append(start_pos + other_match.start())
                            
                            if other_settings:
                                end_pos = min(other_settings)
                            else:
                                end_pos = len(sentence)
                        
                        # Extract the setting segment
                        segment = sentence[start_pos:end_pos].strip()
                        
                        # Add "set" at the beginning if it doesn't start with command words
                        if not re.match(r'\b(set|change|use|make)\b', segment, re.IGNORECASE):
                            segment = "set " + segment
                        
                        found_segments.append(segment)
                
                # If we found setting segments, use them
                if found_segments:
                    detailed_sentences.extend(found_segments)
                    continue
            
            # If not handled as compound command, try splitting on conjunctions
            conjunction_patterns = [
                r'\s+and\s+(?=(?:then|also|set|change|make|start|stop|enable|disable))',
                r'\s+then\s+(?=(?:set|change|make|start|stop|enable|disable))',
                r'\s*,\s*(?=(?:then|next|after that|afterwards|subsequently|finally)\s+)'
            ]
            
            split_made = False
            
            for pattern in conjunction_patterns:
                matches = list(re.finditer(pattern, sentence, re.IGNORECASE))
                if matches:
                    splits = []
                    current_pos = 0
                    
                    for match in matches:
                        end_pos = match.start()
                        if end_pos > current_pos:
                            part = sentence[current_pos:end_pos].strip()
                            if part:
                                splits.append(part)
                        current_pos = match.end()
                    
                    # Add the final part
                    if current_pos < len(sentence):
                        part = sentence[current_pos:].strip()
                        if part:
                            splits.append(part)
                    
                    if len(splits) > 1:
                        detailed_sentences.extend(splits)
                        split_made = True
                        break
            
            # If no splits were made, add the whole sentence
            if not split_made:
                detailed_sentences.append(sentence.strip())
        
        # For compound commands like "set question type to X and difficulty to Y"
        # where splitting might not have captured the full intents, also create
        # synthetic sentences that explicitly add the setting type
        enhanced_sentences = detailed_sentences.copy()
        
        for sentence in detailed_sentences:
            # Check for "and something to something" patterns without a clear setting type
            matches = re.finditer(r'\b(and|with)\s+([a-z]+)\s+(to|as|:)\s+([a-z]+)', sentence, re.IGNORECASE)
            
            for match in matches:
                # Extract what might be a setting
                potential_setting = match.group(2).lower()
                
                # Determine if this is a known setting
                if potential_setting in ['difficulty', 'level']:
                    value = match.group(4)
                    enhanced_sentences.append(f"set difficulty to {value}")
                elif potential_setting in ['type', 'format', 'questions']:
                    value = match.group(4)
                    if potential_setting == 'questions':
                        enhanced_sentences.append(f"set number of questions to {value}")
                    else:
                        enhanced_sentences.append(f"set question type to {value}")
        
        # Ensure we don't have empty strings
        return [s for s in enhanced_sentences if s.strip()]
    
    def _match_intent(self, text: str, dominant_context: Optional[str] = None) -> Optional[str]:
        """
        Match text against intent patterns, using context to disambiguate.
        Returns the matched intent or None.
        """
        matched_intents = {}
        
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # If we have a match, associate it with this intent
                    if intent not in matched_intents:
                        matched_intents[intent] = 0
                    matched_intents[intent] += 1
        
        if not matched_intents:
            return None
            
        # If we have multiple matches, use context to disambiguate
        if len(matched_intents) > 1 and dominant_context:
            for intent in list(matched_intents.keys()):
                # Resolve ambiguity between start_review and enable_speech
                if intent == "start_review" and "enable_speech" in matched_intents:
                    # If the dominant context is speech, prefer speech-related intent
                    if dominant_context == "speech":
                        matched_intents.pop("start_review", None)
                    # If the dominant context is review, prefer review-related intent
                    elif dominant_context == "review":
                        matched_intents.pop("enable_speech", None)
        
        # Return the intent with the most matches
        if matched_intents:
            return max(matched_intents.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _extract_intent_data(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Extract relevant data for a specific intent with improved compound command support.
        Returns a dictionary with intent and associated data.
        """
        result = {"intent": intent, "text": text}
        
        # Extract specific data based on intent type
        if intent == "set_question_type":
            if re.search(r'\b(multiple.?choice|mc)\b', text, re.IGNORECASE):
                result["question_type"] = "multiple-choice"
            elif re.search(r'\b(free.?text|open.?ended)\b', text, re.IGNORECASE):
                result["question_type"] = "free-text"
        
        elif intent == "set_num_questions":
            # First try to extract numeric digits
            # Enhanced number extraction - try multiple patterns
            patterns = [
                r'(\d+)\s+questions?',  # "10 questions"
                r'questions?\s+(\d+)',  # "questions 10"
                r'(set|use|have|want|do).{1,15}(\d+).{1,5}questions?',  # "set 10 questions"
                r'questions?.{1,15}(be|is|to|as|at|of).{1,5}(\d+)',  # "questions to 10"
                r'(number|amount|count).{1,10}(of)?.{1,5}questions?.{1,10}(\d+)',  # "number of questions 10"
                r'and.{1,10}(\d+).{1,5}questions?', # "and 10 questions"
            ]
            
            num_found = False
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Find the first group that contains a digit
                    num_str = next((g for g in match.groups() if g and g.isdigit()), None)
                    if num_str:
                        try:
                            result["num_questions"] = int(num_str)
                            num_found = True
                            break
                        except ValueError:
                            continue
            
            # If we didn't find a numeric digit, try word numbers
            if not num_found:
                # Patterns for word numbers
                word_patterns = [
                    r'(\w+)\s+questions?',  # "five questions"
                    r'questions?\s+(\w+)',  # "questions five"
                    r'(set|use|have|want|do).{1,15}(\w+[-\s]?\w*).{1,5}questions?',  # "set five questions" or "set twenty-five questions"
                    r'questions?.{1,15}(be|is|to|as|at|of).{1,5}(\w+[-\s]?\w*)',  # "questions to five"
                    r'(number|amount|count).{1,10}(of)?.{1,5}questions?.{1,10}(\w+[-\s]?\w*)',  # "number of questions five"
                    r'and.{1,10}(\w+[-\s]?\w*).{1,5}questions?', # "and five questions"
                ]
                
                for pattern in word_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        # Find the word that might be a number
                        word_match = None
                        for g in match.groups():
                            if g and not re.match(r'^(set|use|have|want|do|be|is|to|as|at|of|number|amount|count)$', g, re.IGNORECASE):
                                word_match = g
                                break
                        
                        if word_match:
                            number = self._word_to_number(word_match)
                            if number is not None:
                                result["num_questions"] = number
                                break
            
        elif intent == "set_difficulty":
            # Extract difficulty level
            if re.search(r'\b(easy|simple|beginner)\b', text, re.IGNORECASE):
                result["difficulty"] = "easy"
            elif re.search(r'\b(medium|moderate|intermediate)\b', text, re.IGNORECASE):
                result["difficulty"] = "medium"
            elif re.search(r'\b(hard|difficult|challenging|advanced)\b', text, re.IGNORECASE):
                result["difficulty"] = "hard"
        
        elif intent == "set_topic":
            # Enhanced topic extraction for compound commands
            # First, look for topic after specific markers
            topic_match = None
            topic_patterns = [
                r'(?:topic|subject)\s+(?:to|on|about|as|:)\s+([^,.!?;]+)',  # "topic to X"
                r'(?:and|with).*?(?:topic|subject)\s+(?:to|on|about|as|:)\s+([^,.!?;]+)',  # "and topic to X" 
                r'(?:focus)\s+(?:on)\s+([^,.!?;]+)',  # "focus on X"
                r'(?:about|regarding|concerning)\s+([^,.!?;]+)'  # "about X"
            ]
            
            for pattern in topic_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    topic_match = match.group(1).strip()
                    break
            
            # If found a match, process it
            if topic_match:
                # Clean up and split multiple topics
                topics = []
                if ',' in topic_match or ' and ' in topic_match:
                    # Split by comma and "and"
                    sub_topics = re.split(r',\s*|\s+and\s+', topic_match)
                    topics.extend([t.strip() for t in sub_topics if t.strip()])
                else:
                    topics.append(topic_match)
                
                # Clean up topics
                clean_topics = []
                for topic in topics:
                    # Remove any leading/trailing punctuation or whitespace
                    clean_topic = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', topic).strip()
                    # Remove common connector words at the beginning
                    clean_topic = re.sub(r'^(the|a|an|is|are|be|to|of)\s+', '', clean_topic, flags=re.IGNORECASE).strip()
                    
                    if clean_topic and len(clean_topic) > 1:  # Avoid single letter topics
                        if not any(t.lower() == clean_topic.lower() for t in clean_topics):
                            clean_topics.append(clean_topic)
                
                # If we found topics, add them to the result
                if clean_topics:
                    result["topics"] = clean_topics
                else:
                    # If extraction failed, flag it
                    result["topic_extraction_failed"] = True
            else:
                # If no clear topic pattern found, flag it
                result["topic_extraction_failed"] = True
        
        elif intent == "answer":
            result["answer"] = text
        
        return result