import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import yaml
from pathlib import Path

from .prompt import generate_content, generate_image, generate_art_prompt, create_flux_pro_image
from .utils import get_clean_path
from .code_blocks import convert_markdown_to_wp
from .wordpress_client import WordPressAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArticleError(Exception):
    """Base exception for Article-related errors"""
    pass

class ArticleNotFoundError(ArticleError):
    """Raised when an article cannot be found"""
    pass

class ArticleValidationError(ArticleError):
    """Raised when article validation fails"""
    pass

@dataclass
class Article:
    title: str
    content: str
    date: str
    tags: List[str]
    categories: List[str] = field(default_factory=list)  
    company: str = ""
    key_details: str = ""
    image_path: Optional[str] = None
    image_prompt: str = ""
    wordpress_data: Optional[Dict] = None
    _file_path: Optional[Path] = None

    @classmethod
    def load(cls, file_path: Path) -> 'Article':
        try:
            with open(file_path) as f:
                yaml_data = yaml.safe_load(f)
            article = cls.from_yaml(yaml_data)
            article._file_path = file_path
            return article
        except FileNotFoundError:
            raise ArticleNotFoundError(f"Article file not found: {file_path}")
        except yaml.YAMLError as e:
            raise ArticleValidationError(f"Invalid YAML in article file: {e}")

    def save(self, file_path=None) -> None:
        save_path = file_path or self._file_path
        if not save_path:
            raise ArticleError("No file path associated with this article")
        
        try:
            yaml_content = self.to_yaml()

            with open(save_path, 'w') as f:
                yaml.safe_dump(yaml_content, f)
                
        except Exception as e:
            raise ArticleError(f"Failed to save article: {e}")
        
    @classmethod
    def from_yaml(cls, yaml_data: Dict) -> 'Article':
        if yaml_data==None:
            raise ArticleValidationError(f"Empty file")

        required_fields = {'title', 'content', 'date', 'tags'}
        missing_fields = required_fields - set(yaml_data.keys())
        if missing_fields:
            raise ArticleValidationError(f"Missing required fields: {missing_fields}")
        return cls(**yaml_data)

    def to_yaml(self) -> Dict:
        return {
            'title': self.title,
            'content': self.content,
            'date': self.date,
            'tags': self.tags,
            'categories': self.categories, 
            'company': self.company,
            'key_details': self.key_details,
            'image_path': self.image_path,
            'image_prompt': self.image_prompt,
            'wordpress_data': self.wordpress_data
        }

    def upload_to_wordpress(self, wp_client: WordPressAPIClient) -> bool:
        try:
            wp_content = convert_markdown_to_wp(self.content)
            post_data = wp_client.create_post(
                postdate=self.date,
                title=self.title,
                content=wp_content,
                image_path=self.image_path,
                tags=self.tags,
                categories=self.categories
            )
            
            if post_data:
                self.wordpress_data = post_data
                return True
            return False
            
        except Exception as e:
            raise ArticleError(f"Failed to upload to WordPress: {e}")

class ArticleGenerator:
    def __init__(self, config: Dict):
        self.config = config
        self.articles_dir = Path(config['folders']['articles'])
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        if 'wordpress' in config:
            self.wp_client = WordPressAPIClient(
                config['wordpress']['url'],
                config['wordpress']['username'],
                config['wordpress']['password']
            )
        else:
            self.wp_client = None

    def _get_article_path(self, title: str) -> Path:
        """Generate filesystem path for article"""
        article_dir, article_file = get_clean_path(title,"article.yaml")
        Path(article_dir).mkdir(parents=True, exist_ok=True)
        return Path(article_file)

    def create(self, topic_data: Dict) -> Article:
        try:
            content = generate_content('article', topic_data)
            title = topic_data.get('topic', '')
            
            if not title or not content:
                raise ArticleValidationError("Missing title or content")

            # Strip HTML from content
            content = re.sub(r'<[^>]+>', '', content)

            article = Article(
                title=title,
                content=content,
                date=topic_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                tags=topic_data.get('tags', []),
                categories=['Tech Blog'],
                company=topic_data.get('company', ''),
                key_details=topic_data.get('key_details', '')
            )
            

            try:
                replicate=self.config['replicate']
                prompt=generate_art_prompt(title)
                folder,file_name=get_clean_path(title)
                article.image_prompt=prompt 
                article.image_path=create_flux_pro_image(file_name,  folder, prompt,
                            file_type="webp", 
                            target_width=replicate['width'], 
                            target_height=replicate['height'], 
                            crop=True, 
                            resize=True)
            except Exception as e:
                logger.warning(f"Failed to generate image for article '{title}': {e}")

            file_path = self._get_article_path(article.title)
            print ("TRYING WP")
            article.upload_to_wordpress(self.wp_client)
            article.save(file_path)
            print ("DONE WITH WP")
            return article

        except Exception as e:
            logger.error(f"Failed to create article: {e}")
            raise ArticleError(f"Failed to create article: {e}")

    def save(self, article: Article) -> None:
        try:
            file_path = self._get_article_path(article.title)
            with open(file_path, 'w') as f:
                yaml.safe_dump(article.to_yaml(), f)
            return file_path
        except Exception as e:
            logger.error(f"Failed to save article '{article.title}': {e}")
            raise ArticleError(f"Failed to save article: {e}")

    def get(self, title: str) -> Article:
        try:
            file_path = self._get_article_path(title)
            if not file_path.exists():
                raise ArticleNotFoundError(f"Article not found: {title}")

            with open(file_path) as f:
                return Article.from_yaml(yaml.safe_load(f))
        except ArticleNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve article '{title}': {e}")
            raise ArticleError(f"Failed to retrieve article: {e}")

    def update(self, article: Article) -> None:
        try:
            if not self._get_article_path(article.title).exists():
                raise ArticleNotFoundError(f"Article not found: {article.title}")
            self.save(article)
        except ArticleNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update article '{article.title}': {e}")
            raise ArticleError(f"Failed to update article: {e}")

    def delete(self, title: str) -> None:
        try:
            file_path = self._get_article_path(title)
            if not file_path.exists():
                raise ArticleNotFoundError(f"Article not found: {title}")
            file_path.unlink()
        except ArticleNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete article '{title}': {e}")
            raise ArticleError(f"Failed to delete article: {e}")

    def generate_batch(self, topics: List[Dict]) -> List[Article]:
        # Ensure `topics` is always a list
        if isinstance(topics, dict):
            topics = [topics]  # Wrap single object in a list
            
        articles = []
        for topic in topics:
            try:
                article = self.create(topic)
                articles.append(article)
                logger.info(f"Generated article: {article.title}")
            except ArticleError as e:
                logger.error(f"Error generating article for topic {topic.get('topic', 'unknown')}: {e}")
                continue
        return articles
