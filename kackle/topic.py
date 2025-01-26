import re
import os
import yaml
import calendar
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Union, Tuple

from .prompt import generate_content, get_prompts
from .schema_validator import SchemaValidator
from .utils import get_clean_path

class TopicGenerator:
    def __init__(self, config):
        self.config = config
        self.validator = SchemaValidator()
        self.max_tries = self.config.get('validator', {}).get('attempts', 3)
        self.all_topics = self.load_topics()


    def save_topic(self, topic: Dict, target_date: date) -> None:
        """Save topic to its own directory in YAML format"""
        topic_dir, topic_file = get_clean_path(topic['topic'],'topic.yaml')
        os.makedirs(topic_dir, exist_ok=True)
        
        with open(topic_file, 'w') as f:
            yaml.safe_dump(topic, f)
            
        print(f"Generated topic saved to {topic_file}")


    def load(self,topic_file):
        try:
            with open(topic_file, 'r') as file:
                data = yaml.safe_load(file)
            return data
        except FileNotFoundError:
            print(f"Error: The file {topic_file} was not found.")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error: Invalid YAML file. Details: {e}")
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
            self.data=data
        return data


    def load_topics(self) -> List[Dict]:
        """Load all existing topics from YAML files"""
        all_topics = []
        articles_folder = self.config['folders']['articles']
        
        if not os.path.exists(articles_folder):
            return all_topics

        for folder_name in os.listdir(articles_folder):
            topic_file = os.path.join(articles_folder, folder_name, 'topic.yaml')
            if os.path.exists(topic_file):
                with open(topic_file) as f:
                    topic = yaml.safe_load(f)
                    all_topics.append(topic)
                    
        return all_topics

    def score_topic_match(self, query: str, topics: List[str]) -> float:
        def get_key_terms(text: str) -> set:
            common_words = {'and', 'the', 'in', 'on', 'at', 'to', 'for', 'of'}
            return set(word.lower() for word in text.split() 
                      if word.lower() not in common_words)
            
        query_terms = get_key_terms(query)
        best_score = 0
        
        for topic in topics:
            topic_terms = get_key_terms(topic)
            common_terms = len(query_terms & topic_terms)
            total_terms = len(query_terms | topic_terms)
            score = common_terms / total_terms if total_terms > 0 else 0
            best_score = max(best_score, score)
        
        return best_score

    def generate_topic(self, target_date: date, num_topics: int = 1, rebuild: bool = False) -> Optional[List[Dict]]:
        existing_topics = [topic['topic'] for topic in self.all_topics]
        neg_prompt = ""
        if existing_topics:
            neg_prompt = "that is not like " + "\n- ".join(existing_topics)
        
    
        for attempt in range(self.max_tries):
            try:
                data = {'neg_prompt': neg_prompt, 'num_topics': num_topics, 'date_str': target_date}
                
                content=generate_content("article_topics",data)
                
                is_valid, issues, topics = self.validator.validate("article_topics.system.txt", content)
                
                if is_valid:
                    valid_topics = []
                    for topic in topics:
                        score = self.score_topic_match(topic['topic'], existing_topics)
                        if score > 0.8:
                            print(f"Topic too similar to existing ones: {topic['topic']}")
                            continue
                        
                        self.save_topic(topic, target_date)
                        valid_topics.append(topic)
                        
                    if valid_topics:
                        self.all_topics.extend(valid_topics)
                        return valid_topics
                
                print(f"Attempt {attempt + 1}/{self.max_tries} failed validation:", issues)
                
            except Exception as e:
                print(f"Attempt {attempt + 1}/{self.max_tries} failed with error:", str(e))
        
        return None

    def generate_topics(self, 
                        from_date: date, 
                        to_date: Optional[date] = None, 
                        total_topics: int = 1,
                        rebuild: bool = False) -> List[Dict]:

        if to_date is None or to_date == from_date:
            return self.generate_topic(from_date, total_topics) or []

        # Calculate the total number of days in the range
        day_count = (to_date - from_date).days + 1
        if total_topics > day_count:
            raise ValueError("Total topics exceed the number of available days in the range.")

        # Calculate the interval to distribute topics evenly
        interval = day_count // total_topics
        remaining_days = day_count % total_topics

        generated_topics = []
        current_date = from_date

        for _ in range(total_topics):
            # Generate a single topic for the current date
            topics = self.generate_topic(current_date, 1, rebuild)
            if topics:
                generated_topics.extend(topics)

            # Increment the date by the interval, add an extra day if needed
            increment = interval + (1 if remaining_days > 0 else 0)
            if remaining_days > 0:
                remaining_days -= 1
            current_date += timedelta(days=increment)

        return generated_topics



    def _get_first_monday(self, year: int, month: int) -> date:
        c = calendar.monthcalendar(year, month)
        for week in c:
            monday = week[0]
            if monday != 0:
                return date(year, month, monday)

    def _get_next_month(self, current_date: date) -> date:
        if current_date.month == 12:
            next_month = 1
            next_year = current_date.year + 1
        else:
            next_month = current_date.month + 1
            next_year = current_date.year
            
        return self._get_first_monday(next_year, next_month)

    def _count_months(self, from_date: date, to_date: date) -> int:
        return (to_date.year - from_date.year) * 12 + to_date.month - from_date.month + 1