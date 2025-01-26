import argparse
from datetime import datetime
from .config import config
from .topic import TopicGenerator
from .article import Article, ArticleGenerator
from .utils import create_config_folders
from .wordpress_client import WordPressAPIClient
from pathlib import Path

def upload_article(file_path: Path) -> None:
    article = Article.load(file_path)
    if 'wordpress' in config:
        wp_client = WordPressAPIClient(
            config['wordpress']['url'],
            config['wordpress']['username'],
            config['wordpress']['password']
        )
    else:
        wp_client = None

    
    if not wp_client:
        print("WordPress client not configured")
        return
        
    try:
        if article.upload_to_wordpress(wp_client):
            print(f"Successfully uploaded article: {article.title}")
            article.save()
        else:
            print(f"Failed to upload article: {article.title}")
    except Exception as e:
        print(f"Error uploading article: {e}")

def generate_topics(from_date: datetime, to_date: datetime, count: int, rebuild: bool) -> None:
    topic_generator = TopicGenerator(config)
    topics = topic_generator.generate_topics(from_date, to_date, count, rebuild)
    if topics:
        print(f"Generated {len(topics)} topics")

def generate_articles(from_date: datetime, to_date: datetime, count: int, rebuild: bool, file_path: Path = None) -> None:
    topic_generator = TopicGenerator(config)
    article_generator = ArticleGenerator(config)
    
    if file_path:
        article = Article.load(file_path)
        articles = article_generator.generate_batch([article])
    else:
        topics = topic_generator.generate_topics(from_date, to_date, count, rebuild)
        if topics:
            articles = article_generator.generate_batch(topics)
            
    if articles:
        print(f"Generated {len(articles)} articles")


def main():
    parser = argparse.ArgumentParser(description="Blog Article Generator")
    parser.add_argument(
        "--topic",
        action="store_true",
        help="Generate topics"
    )
    parser.add_argument(
        "--article",
        action="store_true",
        help="Generate articles"
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload article"
    )
    parser.add_argument(
        "--from-date",
        type=str,
        help="Start date (YYYY-MM-DD)",
        default=datetime.today().strftime('%Y-%m-%d')
    )
    parser.add_argument(
        "--to-date",
        type=str,
        help="End date (YYYY-MM-DD)",
        default=None
    )
    parser.add_argument(
        "--count",
        type=int,
        help="Items per month",
        default=1
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force regeneration"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="YAML file path",
        default=None
    )
    
    args = parser.parse_args()
    create_config_folders(config)

    from_date = datetime.strptime(args.from_date, '%Y-%m-%d').date()
    to_date = datetime.strptime(args.to_date, '%Y-%m-%d').date() if args.to_date else None
    file_path = Path(args.file) if args.file else None

    if args.upload:
        if not file_path:
            print("--file required for upload")
            return
        upload_article(file_path)
    elif args.topic:
        generate_topics(from_date, to_date, args.count, args.rebuild)
    elif args.article:
        generate_articles(from_date, to_date, args.count, args.rebuild, file_path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()